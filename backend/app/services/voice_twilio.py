from __future__ import annotations

import logging
import os
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, Request, Response

from app.agent.triage_agent import run_intake_pipeline
from app.models import IntakeRequest

logger = logging.getLogger("safeline.voice")
router = APIRouter(prefix="/api/twilio", tags=["twilio"])


def _twiml(body: str) -> Response:
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>{body}</Response>',
        media_type="application/xml",
    )


async def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "speech.wav") -> str:
    """Transcribe caller audio using Groq Whisper (fast, accent-tolerant) when key is set."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key or not audio_bytes:
        return ""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_key}"},
                files={"file": (filename, audio_bytes, "audio/wav")},
                data={
                    "model": "whisper-large-v3-turbo",
                    "prompt": "Child safety helpline caller in Nigeria or US. Terms: Surulere, Lagos, Pidgin, dey, teacher, uncle, school, beat, safe.",
                },
            )
            resp.raise_for_status()
            return (resp.json().get("text") or "").strip()
    except Exception as exc:
        logger.warning("Groq STT failed: %s", exc)
        return ""


@router.post("/incoming")
async def twilio_incoming(request: Request) -> Response:
    server_url = os.getenv("SERVER_URL", str(request.base_url).rstrip("/"))
    greeting = (
        "You have reached SafeLine. You are safe to speak here. "
        "Please tell me briefly what happened and where the child is, without sharing any graphic details."
    )
    return _twiml(
        f"""
        <Say voice="alice">{escape(greeting)}</Say>
        <Record action="{escape(server_url)}/api/twilio/recording" maxLength="25" playBeep="true" trim="trim-silence" timeout="3" />
        <Say voice="alice">I did not hear anything. Goodbye.</Say>
        """
    )


@router.post("/recording")
async def twilio_recording(request: Request) -> Response:
    form = await request.form()
    recording_url = str(form.get("RecordingUrl", "")).strip()
    case_id = request.query_params.get("case_id") or None
    server_url = os.getenv("SERVER_URL", str(request.base_url).rstrip("/"))

    transcript = ""
    if recording_url:
        sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        auth = (sid, token) if (sid and token) else None
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(f"{recording_url}.wav", auth=auth)
                if r.is_success:
                    transcript = await transcribe_audio_bytes(r.content, "twilio.wav")
        except Exception as exc:
            logger.warning("Twilio recording fetch failed: %s", exc)

    if not transcript:
        return _twiml(
            f"""
            <Say voice="alice">Sorry, the line was noisy. Please say again briefly where the child is and what happened.</Say>
            <Record action="{escape(server_url)}/api/twilio/recording" maxLength="25" playBeep="true" trim="trim-silence" timeout="3" />
            """
        )

    result = await run_intake_pipeline(
        IntakeRequest(case_id=case_id, message=transcript, channel="voice_call", region="NG")
    )
    return _twiml(
        f"""
        <Say voice="alice">{escape(result.assistant_reply)}</Say>
        <Record action="{escape(server_url)}/api/twilio/recording?case_id={escape(result.case.id)}" maxLength="20" playBeep="true" trim="trim-silence" timeout="3" />
        """
    )

