"""Tests must never message, call or text anyone for real.

The dev machine runs the real Photon bridge on :8001 and holds live Twilio credentials, so a test that reaches
dispatch (a live-call test, or a pipeline test that scores Risk >= 2) could otherwise send to a real phone or
register a made-up number with Photon. Everything outbound is replaced with a stub that reports failure.
Tests that need a specific outcome patch these again themselves, which wins over this default.
"""

import pytest


@pytest.fixture(autouse=True)
def no_real_outbound_messaging(monkeypatch):
    import app.services.dispatch as dispatch

    async def blocked(*args, **kwargs):
        return False, "blocked_in_tests"

    for name in ("send_photon_message", "send_twilio_sms", "send_twilio_voice_alert"):
        monkeypatch.setattr(dispatch, name, blocked)
