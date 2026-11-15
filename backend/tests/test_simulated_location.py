"""Device-location demo feed, place gazetteer, cross-check and nearest help.

The device-location feed is seeded demo data. These tests pin down what it does and that the cross-check never
guesses: when sources disagree the responder is shown all of them.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

import app.services.case_store as case_store
from app.services import geo, live_location
from app.services import simulated_device_location as sim
from app.voice import caller_location as cl
from app.voice import twilio_stream
from test_live_location import FakeGemini, FakeWS


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(case_store, "DB_PATH", tmp_path / "sim.db")
    for var in ("CASEWORKER_ALERT_PHONE", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "GEMINI_API_KEY", "PUBLIC_BASE_URL",
                "LINK_BASE_URL", "DASHBOARD_KEY", "SIM_DEMO_NUMBERS", "SIM_PRINCETON_LATLNG", "SIM_LOCATION_AUTO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SIM_LOCATION_DELAY_S", "0")
    live_location.reset_for_tests()
    yield
    live_location.reset_for_tests()


def open_call(number="+16095551234", country="US", city="PRINCETON", state="NJ"):
    loc = cl.CallerLocation(number=number, city=city, state=state, country=country, source="twilio")
    return live_location.start_call(caller_location=loc, call_sid="CA1", public_base_url="https://demo.example")


def evidence(case_id):
    return case_store.get_case(case_id).location


# --------------------------------------------------------------------------- #
# geometry and the gazetteer
# --------------------------------------------------------------------------- #
def test_distance_between_princeton_and_trenton_is_about_17_km():
    assert 15 < geo.haversine_km(40.3573, -74.6672, 40.2206, -74.7597) < 19


@pytest.mark.parametrize("said,expected", [
    ("I'm near Ojuelegba bus stop", "Ojuelegba, Lagos"),
    ("Surulere, Lagos", "Surulere, Lagos"),                         # the specific area beats the city
    ("by the big market at Mile 12", "Mile 12, Lagos"),
    ("mile 1 market in Port Harcourt", "Mile 1 Market, Port Harcourt"),  # the market beats the whole city
    ("somewhere off Nassau Street", "Nassau Street, Princeton"),
    ("V.I.", "Victoria Island, Lagos"),
    ("we are in trenton", "Trenton, NJ"),
])
def test_places_are_found_from_the_callers_own_words(said, expected):
    assert geo.resolve_place(said).name == expected


@pytest.mark.parametrize("said", ["", "   ", "my house", "a place with a red gate", None])
def test_unknown_places_resolve_to_nothing_rather_than_a_guess(said):
    assert geo.resolve_place(said) is None


def test_mile_12_is_not_confused_with_mile_1():
    assert geo.resolve_place("mile 12 market").name == "Mile 12, Lagos"


def test_nearest_help_in_lagos_and_new_jersey():
    ikeja = geo.nearest_help(6.6018, 3.3515, "NG")
    assert ikeja[0]["distance_km"] == 0.0 and "Mirabel" in ikeja[0]["name"]
    assert any(h["phone"] == "112" for h in ikeja) and any(h["phone"] == "0800 800 8001" for h in ikeja)
    princeton = geo.nearest_help(40.3430, -74.6514, "US")
    assert "Princeton Medical Center" in princeton[0]["name"]
    assert any(h["phone"] == "911" for h in princeton) and any(h["phone"] == "1-800-422-4453" for h in princeton)
    assert all(h["distance_km"] is None for h in princeton if h["phone"] in ("911", "1-800-422-4453"))


def test_where_the_child_is_decides_the_emergency_numbers_not_where_the_sim_is_registered():
    in_lagos_on_a_us_sim = geo.nearest_help(6.5001, 3.3530, "US")
    phones = {h["phone"] for h in in_lagos_on_a_us_sim}
    assert {"112", "0800 800 8001"} <= phones and not ({"911", "1-800-422-4453"} & phones)
    in_princeton_on_a_nigerian_sim = geo.nearest_help(40.3430, -74.6514, "NG")
    phones = {h["phone"] for h in in_princeton_on_a_nigerian_sim}
    assert {"911", "1-800-422-4453"} <= phones and not ({"112"} & phones)


def test_nothing_is_offered_far_from_every_known_centre():
    assert geo.nearest_help(0.0, -30.0) == []  # mid-Atlantic: no centre, no country, no guess


def test_nearest_help_is_sorted_by_distance():
    out = [h for h in geo.nearest_help(6.4600, 3.4200, "NG") if h["distance_km"] is not None]
    assert [h["distance_km"] for h in out] == sorted(h["distance_km"] for h in out)


# --------------------------------------------------------------------------- #
# the cross-check
# --------------------------------------------------------------------------- #
def S(label, lat, lng, radius):
    return geo.Source(label, lat, lng, radius)


def test_cross_check_needs_two_sources():
    assert geo.cross_check([])["status"] == "insufficient"
    assert geo.cross_check([S("GPS", 6.5, 3.3, 20)])["status"] == "insufficient"


def test_cross_check_agrees_when_the_gap_is_within_the_combined_uncertainty():
    out = geo.cross_check([S("GPS", 40.3466, -74.6559, 12), S("Device", 40.3430, -74.6514, 600)])
    assert out["status"] == "agree" and out["pairs"][0]["agree"]


def test_cross_check_disagrees_and_says_to_show_every_source():
    out = geo.cross_check([S("GPS", 6.5001, 3.3530, 15), S("Said", 6.5981, 3.3511, 3000)])
    assert out["status"] == "disagree"
    assert "DISAGREE" in out["summary"] and "do not pick one" in out["summary"]
    assert out["pairs"][0]["distance_km"] > 10


def test_one_disagreeing_pair_makes_the_whole_check_disagree():
    out = geo.cross_check([S("A", 6.5, 3.35, 100), S("B", 6.5, 3.351, 100), S("C", 6.9, 3.9, 100)])
    assert out["status"] == "disagree" and sum(not p["agree"] for p in out["pairs"]) == 2


# --------------------------------------------------------------------------- #
# the seeded device-location feed
# --------------------------------------------------------------------------- #
def test_seeded_and_env_numbers_map_to_profiles(monkeypatch):
    assert sim.profile_for_number("+16095550101") == "princeton_demo"
    assert sim.profile_for_number("+16095559999") is None and sim.profile_for_number(None) is None
    monkeypatch.setenv("SIM_DEMO_NUMBERS", "+15557654321=lagos_yaba, +15551112222=not_a_profile")
    assert sim.profile_for_number("+15557654321") == "lagos_yaba"
    assert sim.profile_for_number("+15551112222") is None  # unknown profile ids are ignored


def test_no_real_phone_number_is_hardcoded_in_the_seed():
    source = (Path(sim.__file__)).read_text()
    assert "860" not in source and "7048" not in source  # real demo phones live in the environment only


def test_lookup_returns_a_fictional_fix_marked_simulated_in_the_data():
    fix = asyncio.run(sim.lookup(profile_id="lagos_surulere"))
    assert fix["simulated"] is True and fix["country"] == "NG" and 6.4 < fix["lat"] < 6.6
    assert asyncio.run(sim.lookup(profile_id="nope")) is None and asyncio.run(sim.lookup(phone="+1555")) is None


def test_princeton_profile_can_be_moved_to_where_you_are_rehearsing(monkeypatch):
    monkeypatch.setenv("SIM_PRINCETON_LATLNG", "40.3466,-74.6559")
    fix = asyncio.run(sim.lookup(profile_id="princeton_demo"))
    assert (fix["lat"], fix["lng"]) == (40.3466, -74.6559)
    monkeypatch.setenv("SIM_PRINCETON_LATLNG", "not,numbers")
    assert asyncio.run(sim.lookup(profile_id="princeton_demo"))["lat"] == 40.3430  # bad input falls back
    monkeypatch.setenv("SIM_PRINCETON_LATLNG", "999,5")
    assert asyncio.run(sim.lookup(profile_id="princeton_demo"))["lat"] == 40.3430  # out of range falls back


def test_attaching_the_feed_updates_the_case_and_best_signal():
    call = open_call()
    out = asyncio.run(live_location.attach_simulated_device_location(call.case_id, "lagos_surulere"))
    assert out == {"attached": True, "profile": "lagos_surulere"}
    loc = evidence(call.case_id)
    assert loc.device_service.simulated is True and loc.best == "device_service"
    assert loc.cross_check.status == "insufficient"
    assert loc.nearest_help and any(h.phone == "112" for h in loc.nearest_help)


def test_the_map_pin_follows_the_feed_but_a_real_gps_fix_still_wins():
    call = open_call()
    asyncio.run(live_location.attach_simulated_device_location(call.case_id, "princeton_demo"))
    case = case_store.get_case(call.case_id)
    assert (case.latitude, case.longitude) == (40.3430, -74.6514)
    token = live_location.issue_link_token(call.case_id)
    asyncio.run(live_location.record_gps(token, 40.3466, -74.6559, 12.0))
    asyncio.run(live_location.attach_simulated_device_location(call.case_id, "princeton_demo"))  # looked up again
    case = case_store.get_case(call.case_id)
    assert (case.latitude, case.longitude) == (40.3466, -74.6559)


def test_the_callers_words_become_a_map_point_and_are_cross_checked_against_the_feed():
    call = open_call(country="NG", city="LAGOS", state="")
    asyncio.run(live_location.attach_simulated_device_location(call.case_id, "lagos_surulere"))
    live_location.record_spoken_address(call.case_id, "I am near Surulere")
    loc = evidence(call.case_id)
    assert loc.spoken_point.name == "Surulere, Lagos"
    assert loc.cross_check.status == "agree" and set(loc.cross_check.sources_used) == {"Device location service", "What the caller said"}


def test_disagreeing_sources_are_shown_not_resolved_and_reach_the_alert_text():
    call = open_call(country="NG", city="LAGOS", state="")
    asyncio.run(live_location.attach_simulated_device_location(call.case_id, "mismatch_demo"))  # device says Ikeja
    live_location.record_spoken_address(call.case_id, "I'm in Surulere")                         # caller says Surulere
    loc = evidence(call.case_id)
    assert loc.cross_check.status == "disagree" and loc.cross_check.pairs[0].distance_km > 10
    assert loc.device_service is not None and loc.spoken_address == "I'm in Surulere"  # both kept, neither dropped
    alert = live_location.describe_best_location(loc)
    assert "Device location" in alert and "DISAGREE" in alert


def test_real_gps_outranks_the_feed_and_agrees_within_uncertainty():
    call = open_call()
    asyncio.run(live_location.attach_simulated_device_location(call.case_id, "princeton_demo"))
    token = live_location.issue_link_token(call.case_id)
    asyncio.run(live_location.record_gps(token, 40.3466, -74.6559, 12.0))
    loc = evidence(call.case_id)
    assert loc.best == "gps" and loc.cross_check.status == "agree"
    assert live_location.describe_best_location(loc).startswith("GPS")


def test_a_gps_fix_far_from_the_feed_is_flagged():
    call = open_call()
    asyncio.run(live_location.attach_simulated_device_location(call.case_id, "princeton_demo"))
    token = live_location.issue_link_token(call.case_id)
    asyncio.run(live_location.record_gps(token, 40.2206, -74.7597, 10.0))  # Trenton, ~17 km away
    assert evidence(call.case_id).cross_check.status == "disagree"


def test_unseeded_case_without_a_profile_id_attaches_nothing():
    call = open_call()
    assert asyncio.run(live_location.attach_simulated_device_location(call.case_id)) == {"attached": False, "reason": "no_profile"}
    assert evidence(call.case_id).device_service is None


# --------------------------------------------------------------------------- #
# automatic lookup on a call from a seeded number
# --------------------------------------------------------------------------- #
def test_a_seeded_number_gets_the_lookup_automatically_when_the_call_connects():
    call = open_call(number="+16095550101")

    async def go():
        live_location.start_simulated_lookup(call.case_id)
        assert call.sim_task is not None
        return await call.sim_task

    assert asyncio.run(go())["profile"] == "princeton_demo"
    assert evidence(call.case_id).device_service is not None


def test_an_unseeded_number_or_the_off_switch_starts_nothing(monkeypatch):
    plain = open_call(number="+16095551234")
    live_location.start_simulated_lookup(plain.case_id)
    assert plain.sim_task is None
    monkeypatch.setenv("SIM_LOCATION_AUTO", "0")
    seeded = open_call(number="+16095550101")
    live_location.start_simulated_lookup(seeded.case_id)
    assert seeded.sim_task is None


def test_call_start_runs_the_feed_for_a_seeded_number(monkeypatch):
    monkeypatch.setattr(twilio_stream, "GeminiLiveSession", FakeGemini)
    params = cl.CallerLocation(number="+2348012345001", country="NG", source="twilio").to_custom_parameters()
    ws = FakeWS([{"event": "start", "start": {"streamSid": "MZ1", "callSid": "CA1", "customParameters": params}}, {"event": "stop"}])
    bridge = twilio_stream.TwilioMediaBridge(ws, system_prompt="BASE", voice_name="Kore")

    async def go():
        await bridge.run()
        call = live_location.get_live_call(bridge.case_id)
        await call.sim_task

    asyncio.run(go())
    assert evidence(bridge.case_id).device_service.profile_id == "lagos_surulere"


# --------------------------------------------------------------------------- #
# dashboard API
# --------------------------------------------------------------------------- #
def test_api_lists_profiles_and_attaches_the_feed():
    from app.main import app

    with TestClient(app) as client:
        profiles = client.get("/api/sim/profiles").json()
        assert {"princeton_demo", "lagos_surulere", "mismatch_demo"} <= {p["id"] for p in profiles}
        call = open_call()
        r = client.post(f"/api/cases/{call.case_id}/simulate-device-location", json={"profile_id": "lagos_yaba"})
        assert r.status_code == 200 and r.json() == {"attached": True, "profile": "lagos_yaba"}
        case = next(c for c in client.get("/api/cases").json() if c["id"] == call.case_id)
        assert case["location"]["device_service"]["area_label"] == "Yaba, Lagos"
        assert case["location"]["best"] == "device_service" and case["location"]["nearest_help"]


def test_api_errors_are_clear():
    from app.main import app

    with TestClient(app) as client:
        call = open_call()
        assert client.post(f"/api/cases/{call.case_id}/simulate-device-location", json={}).status_code == 409
        assert client.post(f"/api/cases/{call.case_id}/simulate-device-location", json={"profile_id": "nope"}).status_code == 409


def test_these_routes_are_not_reachable_through_the_public_tunnel():
    from app.main import app

    with TestClient(app) as client:
        tunnel = {"x-forwarded-for": "1.2.3.4"}
        assert client.get("/api/sim/profiles", headers=tunnel).status_code == 403
        assert client.post("/api/cases/SL-X/simulate-device-location", json={}, headers=tunnel).status_code == 403
