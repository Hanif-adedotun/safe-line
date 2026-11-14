from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
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
from app.services.case_store import init_db, list_cases, query_forensics, update_case_status
from app.services.voice_twilio import router as twilio_router, transcribe_audio_bytes
from app.voice.twilio_stream import TwilioMediaBridge

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompts" / "sabi_safe_prompt.md"
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


@app.post("/api/photon/webhook", response_model=IntakeResponse)
async def photon_webhook(payload: PhotonInbound):
    """Photon 2.0 silent text/iMessage inbound webhook."""
    return await run_intake_pipeline(
        IntakeRequest(
            case_id=payload.case_id,
            message=payload.text,
            channel="photon_sms",
            region=payload.region,
        )
    )


@app.post("/api/forensics/query", response_model=ForensicQueryResponse)
async def forensics_query(body: ForensicQueryRequest):
    return query_forensics(body.question)


@app.api_route("/voice/incoming", methods=["GET", "POST"])
async def voice_incoming(request: Request):
    """Twilio Inbound Voice Webhook for real-time full-duplex calls."""
    host = request.headers.get("host", "localhost:8000")
    protocol = "wss" if "https" in str(request.base_url) else "ws"
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{protocol}://{host}/ws/twilio" />
    </Connect>
</Response>"""
    return Response(content=twiml_response, media_type="application/xml")


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

    # When call finishes, automatically process through the triage pipeline
    if transcript_accumulator:
        full_transcript = "\n".join(transcript_accumulator)
        try:
            await run_intake_pipeline(
                IntakeRequest(
                    message=full_transcript,
                    channel="twilio_voice",
                    region="US" if bridge.call_sid else "NG",
                )
            )
        except Exception as e:
            pass


@app.post("/api/eval/run")
async def run_eval_endpoint():
    from evals.run_eval import run_benchmark

    return await run_benchmark()

