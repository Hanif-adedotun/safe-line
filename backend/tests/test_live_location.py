"""Live caller-location flow: Twilio geo -> stream params -> live case ->
spoken address -> one-tap GPS link -> injected into the call -> survives triage.

No real Twilio, Gemini, or Photon calls: those are faked.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import app.services.case_store as case_store
from app.services import live_location
from app.voice import caller_location as cl
from app.voice import twilio_stream


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(case_store, "DB_PATH", tmp_path / "test.db")
    for var in ("CASEWORKER_ALERT_PHONE", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "GEMINI_API_KEY", "PUBLIC_BASE_URL", "DASHBOARD_KEY"):
        monkeypatch.setenv(var, "")
    live_location.reset_for_tests()
    yield
    live_location.reset_for_tests()


def _client():
    from app.main import app

    return TestClient(app)


# --------------------------------------------------------------------------- #
# Twilio hooks -> <Parameter> round trip
# --------------------------------------------------------------------------- #
def test_twilio_geo_round_trips_through_stream_parameters():
    loc = cl.from_twilio_webhook(
        {"From": "+16095551234", "FromCity": "PRINCETON", "FromState": "NJ", "FromZip": "08540", "FromCountry": "US"}
    )
    assert loc.city == "PRINCETON" and loc.state == "NJ" and loc.country == "US"
    back = cl.CallerLocation.from_custom_parameters(loc.to_custom_parameters())
    assert back == loc
    assert "1-800-422-4453" in loc.child_helpline  # Childhelp, not 988
    assert loc.crisis_line.startswith("988")


def test_nigerian_number_falls_back_to_prefix():
    loc = cl.from_twilio_webhook({"From": "+2348031234567"})
    assert loc.country == "NG"
    assert loc.source in ("number_prefix", "mixed")
    assert loc.emergency_number == "112"


def test_voice_webhook_emits_parameters_and_wss_url():
    with _client() as c:
        r = c.post(
            "/voice/incoming",
            data={"From": "+16095551234", "FromCity": "PRINCETON", "FromState": "NJ", "FromCountry": "US"},
            headers={"host": "demo.ngrok-free.dev", "x-forwarded-proto": "https"},
        )
    assert r.status_code == 200
    xml = r.text
    assert 'url="wss://demo.ngrok-free.dev/ws/twilio"' in xml
    assert 'name="sl_city" value="PRINCETON"' in xml
    assert 'name="sl_state" value="NJ"' in xml
    assert 'name="sl_public_base" value="https://demo.ngrok-free.dev"' in xml


# --------------------------------------------------------------------------- #
# Media stream: location reaches Gemini before the first word
# --------------------------------------------------------------------------- #
class FakeWS:
    def __init__(self, events):
        self._events = [json.dumps(e) for e in events]
        self.sent = []
        self.closed = False

    async def receive_text(self):
        if not self._events:
            await asyncio.sleep(3600)
        return self._events.pop(0)

    async def send_text(self, text):
        self.sent.append(text)

    async def close(self):
        self.closed = True


class FakeGemini:
    instances: list["FakeGemini"] = []

    def __init__(self, cfg, *, on_audio, on_interrupted, on_turn_complete, on_tool_call=None):
        self.cfg = cfg
        self.on_tool_call = on_tool_call
        self.texts: list[str] = []
        FakeGemini.instances.append(self)

    async def connect(self):
        return None

    async def send_realtime_text(self, text):
        self.texts.append(text)

    async def send_audio(self, pcm):
        return None

    async def receive_forever(self):
        await asyncio.sleep(3600)

    async def close(self):
        return None


def test_stream_start_opens_live_case_with_location_and_greets(monkeypatch):
    FakeGemini.instances.clear()
    monkeypatch.setattr(twilio_stream, "GeminiLiveSession", FakeGemini)
    params = cl.CallerLocation(number="+16095551234", city="PRINCETON", state="NJ", country="US", source="twilio").to_custom_parameters()
    params["sl_public_base"] = "https://demo.ngrok-free.dev"
    ws = FakeWS(
        [
            {"event": "connected"},
            {"event": "start", "start": {"streamSid": "MZ1", "callSid": "CA1", "customParameters": params}},
            {"event": "stop"},
        ]
    )
    bridge = twilio_stream.TwilioMediaBridge(ws, system_prompt="BASE PROMPT", voice_name="Kore")
    asyncio.run(bridge.run())

    gem = FakeGemini.instances[-1]
    assert "CALLER CONTEXT" in gem.cfg.system_prompt and "PRINCETON" in gem.cfg.system_prompt
    assert {t["name"] for t in gem.cfg.tools} == {"record_caller_location", "send_location_link"}
    assert gem.texts and "call has just connected" in gem.texts[0]

    case = case_store.get_case(bridge.case_id)
    assert case.live_call is True
    assert case.location.network == "PRINCETON, NJ, US"
    assert case.location.best == "network"


# --------------------------------------------------------------------------- #
# Spoken address + GPS link, end to end
# --------------------------------------------------------------------------- #
def _open_call():
    loc = cl.CallerLocation(number="+16095551234", city="PRINCETON", state="NJ", country="US", source="twilio")
    return live_location.start_call(caller_location=loc, call_sid="CA1", public_base_url="https://demo.ngrok-free.dev")


def test_spoken_address_tool_updates_case():
    call = _open_call()
    out = asyncio.run(live_location.handle_tool_call(call.case_id, "record_caller_location", {"address": "near Nassau Street by the library"}))
    assert out == {"saved": True}
    case = case_store.get_case(call.case_id)
    assert case.location.spoken_address == "near Nassau Street by the library"
    assert case.location.best == "spoken"
    assert case.general_location == "near Nassau Street by the library"


def test_link_is_sent_by_imessage_then_gps_flows_into_case_and_call(monkeypatch):
    sent = []

    async def fake_photon(recipient, body):
        sent.append((recipient, body))
        return True, "photon_dispatched"

    async def fake_sms(recipient, body):
        raise AssertionError("SMS should not be used when iMessage succeeds")

    import app.services.dispatch as dispatch

    monkeypatch.setattr(dispatch, "send_photon_message", fake_photon)
    monkeypatch.setattr(dispatch, "send_twilio_sms", fake_sms)

    call = _open_call()
    injected = []

    async def inject(text):
        injected.append(text)

    live_location.attach_injector(call.case_id, inject)

    out = asyncio.run(live_location.handle_tool_call(call.case_id, "send_location_link", {}))
    assert out == {"sent": True, "via": ["imessage"]}
    recipient, body = sent[0]
    assert recipient == "+16095551234"
    url = body.split()[-1]
    assert url.startswith("https://demo.ngrok-free.dev/l/")
    token = url.rsplit("/", 1)[1]

    with _client() as c:
        page = c.get(f"/l/{token}")
        assert page.status_code == 200 and "Share my location" in page.text
        r = c.post(f"/api/l/{token}", json={"latitude": 40.3487, "longitude": -74.6593, "accuracy_m": 12.4})
        assert r.status_code == 200
        # single use
        assert c.post(f"/api/l/{token}", json={"latitude": 1, "longitude": 1}).status_code == 410
        assert c.get(f"/l/{token}").status_code == 410

    case = case_store.get_case(call.case_id)
    assert case.location.gps.latitude == pytest.approx(40.3487)
    assert case.location.best == "gps"
    assert case.location.link_sent_via == ["imessage"]
    assert (case.latitude, case.longitude) == (pytest.approx(40.3487), pytest.approx(-74.6593))
    assert injected and "shared its location" in injected[0] and "40.34" not in injected[0]


def test_no_twilio_sms_when_imessage_fails(monkeypatch):
    import app.services.dispatch as dispatch

    async def fail_photon(recipient, body):
        return False, "photon_http_502"

    async def forbidden_sms(recipient, body):
        raise AssertionError("Twilio must never text the caller")

    monkeypatch.setattr(dispatch, "send_photon_message", fail_photon)
    monkeypatch.setattr(dispatch, "send_twilio_sms", forbidden_sms)
    call = _open_call()
    assert asyncio.run(live_location.send_location_link(call.case_id)) == {"sent": False, "reason": "imessage_unavailable"}
    assert case_store.get_case(call.case_id).location.link_sent_via == []


def test_link_refused_without_https_base():
    loc = cl.CallerLocation(number="+16095551234", country="US")
    call = live_location.start_call(caller_location=loc, call_sid="CA2", public_base_url="http://localhost:8000")
    out = asyncio.run(live_location.send_location_link(call.case_id))
    assert out == {"sent": False, "reason": "no_public_https_url"}


def test_bad_or_unknown_token_rejected():
    with _client() as c:
        assert c.post("/api/l/nope", json={"latitude": 1, "longitude": 1}).status_code == 410
        assert c.get("/l/nope").status_code == 410


def test_post_call_triage_keeps_gps_and_puts_it_in_alert(monkeypatch):
    import app.agent.triage_agent as ta
    from app.models import IntakeRequest

    alerts = []

    async def capture_alert(**kw):
        alerts.append(kw)
        return ["caseworker_queue_realtime"]

    monkeypatch.setattr(ta, "dispatch_caseworker_alert", capture_alert)
    call = _open_call()
    token = live_location.issue_link_token(call.case_id)
    asyncio.run(live_location.record_gps(token, 40.3487, -74.6593, 10.0))
    live_location.end_call(call.case_id)

    res = asyncio.run(
        ta.run_intake_pipeline(
            IntakeRequest(
                case_id=call.case_id,
                message="Caller: my stepdad is beating me right now in Trenton",
                channel="twilio_voice",
                region="US",
            )
        )
    )
    case = res.case
    assert case.id == call.case_id
    assert case.risk_level >= 2
    assert (case.latitude, case.longitude) == (pytest.approx(40.3487), pytest.approx(-74.6593))
    assert case.location.gps is not None and case.live_call is False
    assert "GPS" in alerts[0]["location_detail"] and "google.com/maps" in alerts[0]["location_detail"]


# --------------------------------------------------------------------------- #
# Case data is not reachable through the public tunnel
# --------------------------------------------------------------------------- #
def test_case_data_blocked_through_tunnel_but_public_routes_open():
    with _client() as c:
        tunnel = {"x-forwarded-for": "1.2.3.4"}
        assert c.get("/api/cases", headers=tunnel).status_code == 403
        assert c.post("/api/forensics/query", json={"question": "Surulere"}, headers=tunnel).status_code == 403
        assert c.get("/api/health", headers=tunnel).status_code == 200
        assert c.post("/voice/incoming", data={"From": "+16095551234"}, headers=tunnel).status_code == 200
        assert c.get("/api/cases").status_code == 200  # local dashboard
