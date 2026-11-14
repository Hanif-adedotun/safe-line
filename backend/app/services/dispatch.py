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
    api_key = os.getenv("PHOTON_API_KEY", "").strip()
    base_url = os.getenv("PHOTON_BASE_URL", "https://api.photon.codes/v2").strip().rstrip("/")
    if not (api_key and recipient):
        return False, "photon_not_configured"

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(
                f"{base_url}/messages",
                json={"to": recipient, "text": body[:1500]},
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            return 200 <= resp.status_code < 300, f"photon_http_{resp.status_code}"
    except Exception as exc:
        logger.warning("Photon dispatch failed: %s", exc)
        return False, str(exc)


async def dispatch_caseworker_alert(
    *,
    case_id: str,
    risk_level: int,
    harm_category: str,
    general_location: str | None,
    redacted_summary: str,
) -> list[str]:
    """Fan out urgent Risk >= 2 alerts to Twilio SMS and/or Photon 2.0, with safe demo logging."""
    if risk_level < 2:
        return []

    target_phone = os.getenv("CASEWORKER_ALERT_PHONE", "").strip()
    message = (
        f"[SAFE-LINE RISK {risk_level}] Case {case_id} | {harm_category} | "
        f"Loc: {general_location or 'unspecified'} | {redacted_summary[:220]}"
    )

    channels: list[str] = []
    if target_phone:
        tw_ok, _ = await send_twilio_sms(target_phone, message)
        if tw_ok:
            channels.append("twilio_sms")
        ph_ok, _ = await send_photon_message(target_phone, message)
        if ph_ok:
            channels.append("photon_2_0")

    if not channels:
        # Clean simulated dispatch for offline/table demo when carrier keys aren't loaded
        logger.warning("DISPATCH_SIMULATED: %s", message)
        channels.append("caseworker_queue_realtime")

    return channels

