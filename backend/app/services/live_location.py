"""Live caller-location routing for SafeLine phone calls.

Three location signals, from weakest to strongest:

1. network  - Twilio's FromCity/FromState on the voice webhook (plus the number
              prefix). For a mobile this is where the number was registered,
              not where the caller is standing.
2. spoken   - the address or landmark the caller gives when the voice agent
              asks. The agent saves it with the `record_caller_location` tool.
3. gps      - one-tap link sent by iMessage (Photon) after the caller agrees.
              Twilio is never used to text the caller: Twilio has no live
              device-location API (its From* fields are number lookups), and
              its own Flex geolocation guide uses this same link approach. The page reads navigator.geolocation and posts it
              back while the call is still live.

Every signal is written straight into the case record so the dashboard shows it
during the call, and GPS is also pushed into the live Gemini session so the
agent can tell the caller it arrived.

Nothing here sends the caller's address to a third-party geocoder. The
caseworker gets the raw text plus a maps link they open themselves.
"""

from __future__ import annotations

import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import quote_plus

from app.models import CaseRecord, GpsFix, LocationEvidence
from app.services.case_store import get_case, save_case
from app.voice.caller_location import CallerLocation

logger = logging.getLogger("safeline.live_location")

LINK_TTL_SECONDS = 30 * 60
MAX_ADDRESS_CHARS = 200

Injector = Callable[[str], Awaitable[None]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LiveCall:
    case_id: str
    call_sid: Optional[str]
    caller_number: Optional[str]
    caller_location: CallerLocation
    public_base_url: Optional[str]
    inject: Optional[Injector] = None
    tokens: set[str] = field(default_factory=set)


@dataclass
class _Token:
    case_id: str
    expires_at: float
    used: bool = False


_calls: dict[str, LiveCall] = {}
_tokens: dict[str, _Token] = {}


# --------------------------------------------------------------------------- #
# Map links
# --------------------------------------------------------------------------- #
def gps_maps_url(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lng:.6f}"


def address_maps_url(address: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"


def describe_best_location(loc: Optional[LocationEvidence]) -> Optional[str]:
    """One line for alerts: the most precise signal, with a maps link."""
    if not loc:
        return None
    if loc.gps:
        acc = f" ±{round(loc.gps.accuracy_m)}m" if loc.gps.accuracy_m else ""
        return f"GPS{acc}: {gps_maps_url(loc.gps.latitude, loc.gps.longitude)}"
    if loc.spoken_address:
        return f"Caller said: {loc.spoken_address} ({address_maps_url(loc.spoken_address)})"
    if loc.network:
        return f"Phone network area: {loc.network} (registered area, not live)"
    return None


def _best(loc: LocationEvidence) -> str:
    if loc.gps:
        return "gps"
    if loc.spoken_address:
        return "spoken"
    if loc.network:
        return "network"
    return "none"


# --------------------------------------------------------------------------- #
# Call lifecycle
# --------------------------------------------------------------------------- #
def start_call(
    *,
    caller_location: CallerLocation,
    call_sid: Optional[str],
    public_base_url: Optional[str],
) -> LiveCall:
    """Open a case the moment the call connects so the dashboard shows it live."""
    from app.agent.triage_agent import resolve_location_coords  # avoid import cycle

    region = "NG" if caller_location.country == "NG" else "US"
    network = caller_location.describe() if caller_location.is_known else None
    lat, lng = resolve_location_coords(network, region)
    now = _now()
    case_id = f"SL-2026-{uuid.uuid4().hex[:4].upper()}"

    evidence = LocationEvidence(
        network=network,
        network_source=caller_location.source,
        country=caller_location.country,
    )
    evidence.best = _best(evidence)

    case = CaseRecord(
        id=case_id,
        created_at=now,
        updated_at=now,
        channel="twilio_voice",
        region=region,
        status="open",
        risk_level=0,
        harm_category="other_concern",
        general_location=network,
        latitude=lat,
        longitude=lng,
        redacted_summary="Live call in progress. Triage runs when the call ends.",
        location=evidence,
        live_call=True,
    )
    save_case(case)

    call = LiveCall(
        case_id=case_id,
        call_sid=call_sid,
        caller_number=caller_location.number,
        caller_location=caller_location,
        public_base_url=public_base_url,
    )
    _calls[case_id] = call
    logger.info("Live call opened case=%s network=%s", case_id, network or "unknown")
    return call


def attach_injector(case_id: str, inject: Optional[Injector]) -> None:
    call = _calls.get(case_id)
    if call:
        call.inject = inject


def end_call(case_id: str) -> None:
    """Call hung up. Links stay valid until they expire, since a GPS fix that
    lands after hangup is still useful to the caseworker."""
    call = _calls.pop(case_id, None)
    if call:
        call.inject = None
    case = get_case(case_id)
    if case and case.live_call:
        case.live_call = False
        case.updated_at = _now()
        save_case(case)


def get_live_call(case_id: str) -> Optional[LiveCall]:
    return _calls.get(case_id)


def _update_location(case_id: str, mutate: Callable[[LocationEvidence, CaseRecord], None]) -> Optional[CaseRecord]:
    case = get_case(case_id)
    if not case:
        return None
    loc = case.location or LocationEvidence()
    mutate(loc, case)
    loc.best = _best(loc)
    case.location = loc
    case.updated_at = _now()
    save_case(case)
    return case


# --------------------------------------------------------------------------- #
# Signal 2: spoken address
# --------------------------------------------------------------------------- #
def record_spoken_address(case_id: str, address: str) -> dict[str, Any]:
    text = " ".join((address or "").split())[:MAX_ADDRESS_CHARS]
    if not text:
        return {"saved": False, "reason": "empty_address"}

    def mutate(loc: LocationEvidence, case: CaseRecord) -> None:
        loc.spoken_address = text
        loc.spoken_at = _now()
        if not loc.gps:
            case.general_location = text

    case = _update_location(case_id, mutate)
    if not case:
        return {"saved": False, "reason": "case_not_found"}
    logger.info("Spoken location saved case=%s", case_id)
    return {"saved": True}


# --------------------------------------------------------------------------- #
# Signal 3: one-tap GPS link
# --------------------------------------------------------------------------- #
def issue_link_token(case_id: str) -> str:
    token = secrets.token_urlsafe(16)
    _tokens[token] = _Token(case_id=case_id, expires_at=time.time() + LINK_TTL_SECONDS)
    call = _calls.get(case_id)
    if call:
        call.tokens.add(token)
    return token


def token_case_id(token: str) -> Optional[str]:
    """Case id for a link that is still usable, or None."""
    entry = _tokens.get(token)
    if not entry or entry.used or entry.expires_at < time.time():
        return None
    return entry.case_id


def _public_base(call: Optional[LiveCall]) -> Optional[str]:
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    return call.public_base_url if call else None


async def send_location_link(case_id: str) -> dict[str, Any]:
    """iMessage the caller a one-tap link via Photon. No Twilio SMS fallback.
    The agent must have the caller's agreement before calling this."""
    from app.services.dispatch import send_photon_message

    call = _calls.get(case_id)
    if not call or not call.caller_number:
        return {"sent": False, "reason": "no_caller_number"}
    base = _public_base(call)
    if not base or not base.startswith("https://"):
        return {"sent": False, "reason": "no_public_https_url"}

    token = issue_link_token(case_id)
    url = f"{base}/l/{token}"
    body = f"SafeLine: here is the link we talked about. Tap it, then tap Share. {url}"

    ok, detail = await send_photon_message(call.caller_number, body)
    if not ok:
        # Usually: the caller's phone is not an iPhone / iMessage is off.
        logger.warning("Location link via Photon failed: %s", detail)
        return {"sent": False, "reason": "imessage_unavailable"}
    channels = ["imessage"]

    def mutate(loc: LocationEvidence, _case: CaseRecord) -> None:
        loc.link_sent_via = sorted(set(loc.link_sent_via + channels))
        loc.link_sent_at = _now()

    _update_location(case_id, mutate)
    return {"sent": True, "via": channels}


async def record_gps(token: str, latitude: float, longitude: float, accuracy_m: Optional[float]) -> Optional[CaseRecord]:
    case_id = token_case_id(token)
    if not case_id:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    _tokens[token].used = True

    fix = GpsFix(
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m if accuracy_m and accuracy_m > 0 else None,
        captured_at=_now(),
    )

    def mutate(loc: LocationEvidence, case: CaseRecord) -> None:
        loc.gps = fix
        case.latitude = latitude
        case.longitude = longitude
        if not loc.spoken_address:
            case.general_location = f"GPS {latitude:.4f}, {longitude:.4f}"

    case = _update_location(case_id, mutate)
    logger.info("GPS fix saved case=%s accuracy=%s", case_id, fix.accuracy_m)

    call = _calls.get(case_id)
    if case and call and call.inject:
        acc = f" (accurate to about {round(fix.accuracy_m)} metres)" if fix.accuracy_m else ""
        try:
            await call.inject(
                "[SYSTEM NOTE, not spoken by the caller] The caller's phone just shared its "
                f"location{acc} and it has been passed to the caseworker. In one short, calm "
                "sentence, let them know you received it, then continue supporting them. "
                "Do not read out coordinates, and do not say anyone is on the way or coming; "
                "you do not know that."
            )
        except Exception as exc:  # the call may have just ended
            logger.warning("Could not inject GPS note into live call: %s", exc)
    return case


# --------------------------------------------------------------------------- #
# Gemini Live tools
# --------------------------------------------------------------------------- #
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "record_caller_location",
        "description": (
            "Save where the caller is so a caseworker can reach them. Call this as soon as the "
            "caller tells you an address, street, school, landmark, bus stop, or neighbourhood. "
            "Pass their words as closely as you can. Call it again if they add detail."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "address": {
                    "type": "STRING",
                    "description": "The address or landmark in the caller's own words.",
                }
            },
            "required": ["address"],
        },
    },
    {
        "name": "send_location_link",
        "description": (
            "Send the caller an iMessage with a one-tap link that shares their exact location. Only call "
            "this after the caller clearly says yes to receiving a text AND says it is safe for "
            "a text to arrive on this phone. Never call it without that agreement."
        ),
        "parameters": {"type": "OBJECT", "properties": {}},
    },
]


async def handle_tool_call(case_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "record_caller_location":
        return record_spoken_address(case_id, str(args.get("address") or ""))
    if name == "send_location_link":
        return await send_location_link(case_id)
    return {"error": "unknown_tool"}


def reset_for_tests() -> None:
    _calls.clear()
    _tokens.clear()
