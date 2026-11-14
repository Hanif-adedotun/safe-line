from __future__ import annotations

import base64
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("safeline.dispatch")


async def send_twilio_sms(to_phone: str, body: str) -> tuple[bool, str]:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_phone = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    if not (sid and token and from_phone and to_phone):
        return False, "twilio_not_configured"

    auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data={"From": from_phone, "To": to_phone, "Body": body[:1500]},
                headers={"Authorization": f"Basic {auth}"},
            )
            return 200 <= resp.status_code < 300, f"twilio_http_{resp.status_code}"
    except Exception as exc:
        logger.warning("Twilio SMS dispatch failed: %s", exc)
        return False, str(exc)


async def send_photon_message(recipient: str, body: str) -> tuple[bool, str]:
    """Dispatch an outbound iMessage alert via the Photon 2.0 local bridge."""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                "http://localhost:8001/send",
                json={"recipient": recipient, "text": body[:1500]},
            )
            if resp.status_code == 200:
                return True, "photon_dispatched"
            return False, f"photon_http_{resp.status_code}"
    except Exception as exc:
        logger.warning("Photon bridge dispatch failed: %s", exc)
        return False, str(exc)


async def send_twilio_voice_alert(to_phone: str, speech_text: str) -> tuple[bool, str]:
    """Place an urgent automated outbound alert call to the caseworker."""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_phone = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    if not (sid and token and from_phone and to_phone):
        return False, "twilio_not_configured"

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        escaped = speech_text.replace("<", "&lt;").replace(">", "&gt;")
        twiml = f"<Response><Say voice='alice'>{escaped}</Say></Response>"
        call = client.calls.create(to=to_phone, from_=from_phone, twiml=twiml)
        return True, call.sid
    except Exception as exc:
        logger.warning("Twilio voice alert call failed: %s", exc)
        return False, str(exc)


async def dispatch_caseworker_alert(
    *,
    case_id: str,
    risk_level: int,
    harm_category: str,
    general_location: str | None,
    redacted_summary: str,
    location_detail: str | None = None,
) -> list[str]:
    """Fan out urgent Risk >= 2 alerts to phone voice call, SMS, and/or Photon 2.0."""
    if risk_level < 2:
        return []

    target_phone = os.getenv("CASEWORKER_ALERT_PHONE", "").strip()
    message = (
        f"[SAFE-LINE RISK {risk_level}] Case {case_id} | {harm_category} | "
        f"Loc: {general_location or 'unspecified'} | {redacted_summary[:220]}"
    )
    if location_detail:
        message += f" | {location_detail}"

    channels: list[str] = []
    if target_phone:
        # 1. Automated urgent voice call (bypasses US carrier SMS filters)
        speech = f"Attention: SafeLine Emergency Alert. Risk level {risk_level} detected in {general_location or 'an unspecified location'}. Category: {harm_category}."
        call_ok, _ = await send_twilio_voice_alert(target_phone, speech)
        if call_ok:
            channels.append("twilio_voice_call")

        # 2. Twilio SMS
        tw_ok, _ = await send_twilio_sms(target_phone, message)
        if tw_ok:
            channels.append("twilio_sms")

        # 3. Photon 2.0 silent message
        ph_ok, _ = await send_photon_message(target_phone, message)
        if ph_ok:
            channels.append("photon_2_0")

    if not channels:
        logger.warning("DISPATCH_SIMULATED: %s", message)
        channels.append("caseworker_queue_realtime")

    return channels

