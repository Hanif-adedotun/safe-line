from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from xml.sax.saxutils import quoteattr
from pydantic import BaseModel

from app.agent.triage_agent import run_intake_pipeline
from app.models import (
    CaseRecord,
    CaseStatus,
    ForensicQueryRequest,
    ForensicQueryResponse,
    IntakeRequest,
    IntakeResponse,
)
from app.services import live_location
from app.services.case_store import init_db, list_cases, query_forensics, update_case_status
from app.services.voice_twilio import router as twilio_router, transcribe_audio_bytes
from app.voice.caller_location import from_twilio_webhook
from app.voice.twilio_stream import PUBLIC_BASE_PARAM, TwilioMediaBridge

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompts" / "safeline_prompt.md"
if PROMPT_PATH.exists():
    SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = "You are SafeLine, a warm, calm, trauma-informed AI voice companion for youth."


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="SafeLine API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(twilio_router)

# Routes that must be reachable through the public tunnel (Twilio, the caller's
# location link, health). Everything else holds children's case data, so a
# request that came through a proxy (ngrok adds X-Forwarded-For) is refused
# unless it carries DASHBOARD_KEY. The local dashboard talks to 127.0.0.1
# directly and is unaffected.
_PUBLIC_PREFIXES = ("/voice/", "/ws/", "/l/", "/api/l/", "/api/health", "/api/twilio/", "/api/photon/")


@app.middleware("http")
async def guard_case_data(request: Request, call_next):
    path = request.url.path
    proxied = "x-forwarded-for" in request.headers
    if proxied and request.method != "OPTIONS" and not path.startswith(_PUBLIC_PREFIXES):
        key = os.getenv("DASHBOARD_KEY", "").strip()
        if not key or request.headers.get("x-safeline-key") != key:
            return JSONResponse({"detail": "Not available over the public tunnel"}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
        "twilio_configured": bool(os.getenv("TWILIO_ACCOUNT_SID", "").strip()),
        "photon_configured": bool(os.getenv("PHOTON_API_KEY", "").strip()),
    }


@app.get("/api/macro-stats")
async def macro_stats():
    cases = list_cases()
    return {
        "global_children_affected_annual": "1B+",
        "global_missed_helpline_contacts": "500,000+",
        "nigeria_prevalence": "6 in 10",
        "nigeria_help_received": "< 5%",
        "abuser_known_pct": "88%",
        "us_988_understaffed_pct": "71%",
        "live_cases_total": len(cases),
        "live_high_risk_cases": sum(1 for c in cases if c.risk_level >= 2),
    }


@app.get("/api/cases", response_model=list[CaseRecord])
async def get_cases():
    return list_cases()


class StatusUpdate(BaseModel):
    status: CaseStatus


@app.patch("/api/cases/{case_id}/status", response_model=CaseRecord)
async def patch_case_status(case_id: str, body: StatusUpdate):
    updated = update_case_status(case_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Case not found")
    return updated


@app.post("/api/intake", response_model=IntakeResponse)
async def post_intake(req: IntakeRequest):
    return await run_intake_pipeline(req)


@app.post("/api/intake/audio", response_model=IntakeResponse)
async def post_intake_audio(
    file: UploadFile = File(...),
    region: Literal["NG", "US"] = Form("NG"),
    case_id: str | None = Form(None),
):
    raw = await file.read()
    transcript = await transcribe_audio_bytes(raw, file.filename or "mic.webm")
    if not transcript:
        raise HTTPException(status_code=422, detail="Could not transcribe audio (check GROQ_API_KEY or mic input)")
    return await run_intake_pipeline(
        IntakeRequest(case_id=case_id, message=transcript, channel="web_mic", region=region)
    )


class PhotonInbound(BaseModel):
    text: str
    sender_id: str | None = None
    case_id: str | None = None
    region: Literal["NG", "US"] = "NG"


@app.post("/api/photon/webhook")
async def photon_webhook(request: Request):
    """Photon 2.0 silent text / iMessage inbound webhook."""
    data = await request.json()

    text = ""
    sender_id = "anonymous"
    case_id = None
    region = "US"

    if "message" in data and isinstance(data["message"], dict):
        msg = data["message"]
        content = msg.get("content", {})
        text = content.get("text") or ""
        sender_id = (msg.get("sender") or {}).get("id") or "anonymous"
    elif "text" in data:
        text = data["text"]
        sender_id = data.get("sender_id") or "anonymous"
        case_id = data.get("case_id")
        region = data.get("region", "US")

    if not text:
        return {"status": "ignored", "reason": "empty_text"}

    result = await run_intake_pipeline(
        IntakeRequest(
            case_id=case_id,
            message=text,
            channel="photon_imessage",
            region=region,
        )
    )
    return result


@app.post("/api/forensics/query", response_model=ForensicQueryResponse)
async def forensics_query(body: ForensicQueryRequest):
    return query_forensics(body.question)


def _public_base_url(request: Request) -> str:
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")
    proto = request.headers.get("x-forwarded-proto")
    if not proto:
        proto = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"
    return f"{proto}://{host}"


@app.api_route("/voice/incoming", methods=["GET", "POST"])
async def voice_incoming(request: Request):
    """Twilio inbound voice webhook.

    Twilio sends the caller's FromCity/FromState/FromZip/FromCountry here, but
    not on the media WebSocket, so they ride along as <Parameter> elements and
    come back as start.customParameters in TwilioMediaBridge.
    """
    form = dict(await request.form()) if request.method == "POST" else dict(request.query_params)
    location = from_twilio_webhook({k: str(v) for k, v in form.items()})
    base = _public_base_url(request)
    ws_url = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/ws/twilio"

    params = location.to_custom_parameters()
    params[PUBLIC_BASE_PARAM] = base
    param_xml = "\n".join(
        f"            <Parameter name={quoteattr(k)} value={quoteattr(v)} />" for k, v in params.items()
    )
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url={quoteattr(ws_url)}>
{param_xml}
        </Stream>
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws/twilio")
async def ws_twilio(websocket: WebSocket):
    """Twilio Media Streams full-duplex WebSocket endpoint."""
    await websocket.accept()

    transcript_accumulator: list[str] = []

    async def on_turn(caller_text: str, model_text: str):
        if caller_text:
            transcript_accumulator.append(f"Caller: {caller_text}")
        if model_text:
            transcript_accumulator.append(f"SafeLine: {model_text}")

    bridge = TwilioMediaBridge(
        websocket=websocket,
        system_prompt=SYSTEM_PROMPT,
        voice_name=os.getenv("GEMINI_VOICE", "Puck"),
        on_turn_complete=on_turn,
    )
    await bridge.run()

    region = "NG" if (bridge.caller_location and bridge.caller_location.country == "NG") else "US"
    if bridge.case_id:
        live_location.end_call(bridge.case_id)
    # When the call finishes, run the transcript through triage into the same case.
    if transcript_accumulator:
        try:
            await run_intake_pipeline(
                IntakeRequest(
                    case_id=bridge.case_id,
                    message="\n".join(transcript_accumulator)[:4000],
                    channel="twilio_voice",
                    region=region,
                )
            )
        except Exception:
            logging.getLogger("safeline").exception("Post-call triage failed case=%s", bridge.case_id)


# --------------------------------------------------------------------------- #
# One-tap location link (sent to the caller by iMessage/SMS during a call)
# --------------------------------------------------------------------------- #
_LINK_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Confirm</title><style>
body{font:18px/1.45 -apple-system,system-ui,sans-serif;margin:0;padding:28px 22px;background:#0e0e0e;color:#f7f1e4}
button{display:block;width:100%;padding:18px;font-size:20px;font-weight:600;border:0;border-radius:14px;background:#cba868;color:#111;margin-top:22px}
p{margin:0 0 10px}#s{margin-top:18px;color:#cfc8b8}
</style></head><body>
<p><b>SafeLine</b></p><p>Tap the button, then allow location. This shares where you are with the people helping you.</p>
<button id="b">Share my location</button><p id="s"></p>
<script>
var b=document.getElementById('b'),s=document.getElementById('s');
b.onclick=function(){
 if(!navigator.geolocation){s.textContent='This phone cannot share location. Tell the person on the call where you are.';return;}
 b.disabled=true;s.textContent='Finding you...';
 navigator.geolocation.getCurrentPosition(function(p){
  fetch(location.pathname.replace('/l/','/api/l/'),{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy_m:p.coords.accuracy})})
  .then(function(r){s.textContent=r.ok?'Done. Help can see where you are. You can close this page.':'This link has expired. Tell the person on the call where you are.';b.style.display='none';})
  .catch(function(){s.textContent='No connection. Tell the person on the call where you are.';b.disabled=false;});
 },function(){s.textContent='Location is turned off. That is okay, tell the person on the call where you are.';b.disabled=false;},
 {enableHighAccuracy:true,timeout:15000,maximumAge:0});
};
</script></body></html>"""

_EXPIRED_PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confirm</title></head><body style="font:18px -apple-system,system-ui,sans-serif;padding:28px 22px;background:#0e0e0e;color:#f7f1e4">
<p>This link has expired. If you still need help, call back and tell us where you are.</p></body></html>"""


@app.get("/l/{token}", response_class=HTMLResponse)
async def location_link_page(token: str):
    if not live_location.token_case_id(token):
        return HTMLResponse(_EXPIRED_PAGE, status_code=410, headers={"Cache-Control": "no-store"})
    return HTMLResponse(_LINK_PAGE, headers={"Cache-Control": "no-store"})


class GpsPayload(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float | None = None


@app.post("/api/cases/{case_id}/location-link")
async def caseworker_send_location_link(case_id: str):
    """Dashboard button: text the caller on a live call the one-tap GPS link.
    Case-data route, so it is refused through the public tunnel."""
    if not live_location.get_live_call(case_id):
        raise HTTPException(status_code=409, detail="Case is not on a live call")
    return await live_location.send_location_link(case_id)


@app.post("/api/l/{token}")
async def location_link_submit(token: str, body: GpsPayload):
    case = await live_location.record_gps(token, body.latitude, body.longitude, body.accuracy_m)
    if not case:
        raise HTTPException(status_code=410, detail="Link expired or already used")
    return {"ok": True}


@app.post("/api/eval/run")
async def run_eval_endpoint():
    from evals.run_eval import run_benchmark

    return await run_benchmark()

