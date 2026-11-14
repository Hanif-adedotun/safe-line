"""Offline tests for the safeguarding lane. System 1's model is faked; System 2,
validation, fallbacks, review queue and audit are real."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.case_store as case_store
from app.models import IntakeRequest
from app.safeguarding import pipeline, store
from app.safeguarding.assess import assess_conversation, fallback_assessment, quote_in_child_turns
from app.safeguarding.policy import Action, Priority, decide
from app.safeguarding.schema import SafeguardingAssessment, Urgency


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(case_store, "DB_PATH", tmp_path / "sg.db")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    pipeline.set_model_caller(None)
    yield
    pipeline.set_model_caller(None)


def fake_model(payload: dict):
    async def call(_transcript: str) -> str:
        return json.dumps(payload)

    return call


def A(**kw) -> SafeguardingAssessment:
    base = dict(session_id="S1", urgency=Urgency.low, immediate_danger="unknown",
                human_review_recommended=False, follow_up_appropriate=False)
    base.update(kw)
    return SafeguardingAssessment(**base)


def concern(cat, quote="x", verified=True):
    return {"category": cat, "status": "stated", "evidence_quotes": [quote], "interpretation": "i", "evidence_verified": verified}


# --------------------------------------------------------------------------- #
# System 1: validation, evidence, fallback
# --------------------------------------------------------------------------- #
def test_valid_output_with_verbatim_evidence():
    out = asyncio.run(assess_conversation("S1", [("child", "My mum says I'm worthless every day.")], caller=fake_model({
        "concerns": [{"category": "emotional_abuse", "status": "stated", "evidence_quotes": ["I'm worthless every day"], "interpretation": "repeated humiliation"}],
        "urgency": "moderate", "immediate_danger": "unknown", "model_uncertainty": [], "missing_information": ["Is the child safe now"],
        "human_review_recommended": False, "follow_up_appropriate": True, "suggested_follow_up": "Are you safe right now?"})))
    assert not out.fallback
    assert out.concerns[0].evidence_verified is True
    assert out.human_review_recommended is True  # forced on when there is a concern


def test_fabricated_quote_is_flagged_not_dropped():
    out = asyncio.run(assess_conversation("S1", [("child", "I don't like going home.")], caller=fake_model({
        "concerns": [{"category": "physical_abuse", "status": "potential", "evidence_quotes": ["he beats me"], "interpretation": "?"}],
        "urgency": "unknown", "immediate_danger": "unknown", "model_uncertainty": [], "missing_information": [],
        "human_review_recommended": False, "follow_up_appropriate": False})))
    assert len(out.concerns) == 1 and out.concerns[0].evidence_verified is False
    assert any("not found verbatim" in u for u in out.model_uncertainty)


def test_quotes_from_agent_turns_do_not_count():
    turns = [("agent", "Is someone hurting you?"), ("child", "yes")]
    assert not quote_in_child_turns("Is someone hurting you", turns)
    assert quote_in_child_turns("yes", turns)


@pytest.mark.parametrize("raw", ["not json", "[]", json.dumps({"concerns": [], "urgency": "very bad"})])
def test_malformed_output_falls_back_to_human_review(raw):
    async def call(_):
        return raw

    out = asyncio.run(assess_conversation("S1", [("child", "help")], caller=call))
    assert out.fallback and out.human_review_recommended and out.urgency == Urgency.unknown


def test_no_api_key_falls_back():
    out = asyncio.run(assess_conversation("S1", [("child", "help me")]))
    assert out.fallback and "GEMINI_API_KEY" in out.fallback_reason


def test_no_child_words_yet_is_not_a_fallback():
    out = asyncio.run(assess_conversation("S1", [("agent", "Hi, I'm Ayo.")]))
    assert not out.fallback and not out.human_review_recommended


# --------------------------------------------------------------------------- #
# System 2: every rule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("assessment, rule, action, priority, notify", [
    (A(immediate_danger="yes", concerns=[concern("physical_abuse")]), "P1_IMMEDIATE_DANGER", Action.emergency_protocol, Priority.critical, True),
    (A(urgency=Urgency.critical), "P1_IMMEDIATE_DANGER", Action.emergency_protocol, Priority.critical, True),
    (A(urgency=Urgency.high, concerns=[concern("neglect")]), "P2_HIGH_URGENCY", Action.priority_review, Priority.high, True),
    (A(urgency=Urgency.low, concerns=[concern("sexual_abuse_or_exploitation")]), "P3_CATEGORY_FLOOR", Action.priority_review, Priority.high, True),
    (A(urgency=Urgency.moderate, concerns=[concern("self_harm_or_suicide")]), "P3_CATEGORY_FLOOR", Action.priority_review, Priority.high, True),
    (fallback_assessment("S1", "x"), "P4_ASSESSMENT_FAILED", Action.standard_review, Priority.standard, False),
    (A(urgency=Urgency.moderate, concerns=[concern("emotional_abuse")]), "P5_CONCERN_MODERATE_OR_UNKNOWN", Action.standard_review, Priority.standard, False),
    (A(urgency=Urgency.unknown, concerns=[concern("fear_unclear_cause")]), "P5_CONCERN_MODERATE_OR_UNKNOWN", Action.standard_review, Priority.standard, False),
    (A(urgency=Urgency.low, concerns=[concern("bullying", verified=False)]), "P6_UNVERIFIED_EVIDENCE", Action.standard_review, Priority.standard, False),
    (A(urgency=Urgency.low, concerns=[concern("bullying")]), "P7_CONCERN_LOW", Action.routine_review, Priority.routine, False),
    (A(human_review_recommended=True, model_uncertainty=["?"]), "P8_MODEL_ASKED_FOR_REVIEW", Action.standard_review, Priority.standard, False),
    (A(), "P9_NO_CONCERN", Action.no_action, Priority.none, False),
])
def test_policy_rules(assessment, rule, action, priority, notify):
    d = decide(assessment, "REV-TEST")
    assert (d.rule_id, d.action, d.priority, d.notify) == (rule, action, priority, notify)
    assert d.create_review_item == (priority != Priority.none)
    if notify:
        assert "DEMO ONLY" in d.notification_preview and "No external authority has been contacted" in d.notification_preview
    else:
        assert d.notification_preview is None


def test_emotional_abuse_is_not_lost_behind_physical_threshold():
    """The brief's core worry: verbal abuse must not fall through a physical-harm-only threshold."""
    d = decide(A(urgency=Urgency.moderate, concerns=[concern("emotional_abuse")]), "R")
    assert d.create_review_item


def test_priority_never_drops_within_a_session():
    first = decide(A(urgency=Urgency.high, concerns=[concern("physical_abuse")]), "R")
    later = decide(A(), "R", previous=first)
    assert later.priority == Priority.high and later.held_from_previous


def test_notification_holds_no_location():
    d = decide(A(immediate_danger="yes", concerns=[concern("physical_abuse", "he is at the door")]), "R")
    assert "Location: held in the access-controlled console" in d.notification_preview


# --------------------------------------------------------------------------- #
# Pipeline: sessions, review queue, audit
# --------------------------------------------------------------------------- #
def _model_for(urgency, cats, danger="unknown"):
    async def call(transcript: str) -> str:
        last_child = [l for l in transcript.splitlines() if "] CHILD: " in l][-1].split("] CHILD: ", 1)[1]
        return json.dumps({
            "concerns": [{"category": c, "status": "stated", "evidence_quotes": [last_child[:30]], "interpretation": "i"} for c in cats],
            "urgency": urgency, "immediate_danger": danger, "model_uncertainty": [], "missing_information": [],
            "human_review_recommended": bool(cats), "follow_up_appropriate": False})
    return call


def test_ordinary_message_creates_session_but_no_review_item():
    pipeline.set_model_caller(_model_for("low", []))
    res = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="can you help with homework", channel="web_text", region="US")))
    assert res.case.review_item_id is None
    assert store.list_review_items() == []
    assert res.case.decision["rule_id"] == "P9_NO_CONCERN"


def test_concern_creates_review_item_then_new_info_upgrades_it():
    pipeline.set_model_caller(_model_for("moderate", ["emotional_abuse"]))
    r1 = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="my mum calls me worthless", channel="web_text", region="US")))
    item = store.get_review_item(r1.case.review_item_id)
    assert item.priority == "standard" and item.categories == ["emotional_abuse"]

    pipeline.set_model_caller(_model_for("high", ["physical_abuse"]))
    asyncio.run(pipeline.run_text_intake(IntakeRequest(case_id=r1.case.id, message="and she hits me", channel="web_text", region="US")))
    item = store.get_review_item(r1.case.review_item_id)
    assert item.priority == "high"
    assert item.categories == ["emotional_abuse", "physical_abuse"]  # categories accumulate
    assert item.notification_preview and "MOCK SAFEGUARDING ALERT" in item.notification_preview
    kinds = [e["kind"] for e in store.list_audit(r1.case.id)]
    assert {"assessment_run", "policy_decision", "review_item_created", "review_item_updated", "mock_notification_recorded"} <= set(kinds)


def test_reviewed_item_reopens_on_new_information():
    pipeline.set_model_caller(_model_for("moderate", ["neglect"]))
    r1 = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="no food at home", channel="web_text", region="US")))
    store.mark_reviewed(r1.case.review_item_id, "support_referral_offered", "spoke to school", None)
    pipeline.set_model_caller(_model_for("moderate", ["neglect", "physical_abuse"]))
    asyncio.run(pipeline.run_text_intake(IntakeRequest(case_id=r1.case.id, message="and he hit me", channel="web_text", region="US")))
    assert store.get_review_item(r1.case.review_item_id).status == "open"


def test_model_failure_still_queues_for_human():
    res = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="something bad happened", channel="web_text", region="US")))
    item = store.get_review_item(res.case.review_item_id)
    assert item.rule_id == "P4_ASSESSMENT_FAILED" and item.status == "open"


def test_emergency_reply_gives_local_number_and_never_promises_rescue():
    pipeline.set_model_caller(_model_for("critical", ["physical_abuse"], danger="yes"))
    res = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="he is at my door now", channel="photon_imessage", region="NG")))
    assert "112" in res.assistant_reply
    assert "on the way" not in res.assistant_reply.lower()


def test_review_requires_known_disposition():
    pipeline.set_model_caller(_model_for("moderate", ["bullying"]))
    r = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="they push me at school", channel="web_text", region="US")))
    with pytest.raises(ValueError):
        store.mark_reviewed(r.case.review_item_id, "closed_by_ai", None, None)


def test_live_call_emergency_cue_injected_once():
    from app.models import CaseRecord

    case_store.save_case(CaseRecord(id="LIVE1", created_at="t", updated_at="t", channel="twilio_voice", region="US", redacted_summary="live"))
    pipeline.set_model_caller(_model_for("critical", ["physical_abuse"], danger="yes"))
    injected = []

    async def inject(text):
        injected.append(text)

    async def run():
        la = pipeline.LiveAssessor("LIVE1", inject=inject)
        la.add_turn("he is breaking the door", "I'm here with you.")
        await la.finish()
        la.add_turn("he's still here", "")
        await la.finish()

    asyncio.run(run())
    assert len(injected) == 1 and "may be in danger right now" in injected[0]
    case = case_store.get_case("LIVE1")
    assert case.decision["action"] == "emergency_protocol"
    assert [t.role for t in case.turns] == ["reporter", "safeline", "reporter"]


def test_ambiguous_reply_does_not_label_or_use_model_followup():
    async def call(_):
        return json.dumps({
            "concerns": [{"category": "fear_unclear_cause", "status": "unclear", "evidence_quotes": ["I don't like my uncle"], "interpretation": "?"}],
            "urgency": "low", "immediate_danger": "unknown", "model_uncertainty": [], "missing_information": [],
            "human_review_recommended": True, "follow_up_appropriate": True,
            "suggested_follow_up": "Why don't you like your uncle?"})
    pipeline.set_model_caller(call)
    res = asyncio.run(pipeline.run_text_intake(IntakeRequest(message="I don't like my uncle", channel="web_text", region="US")))
    reply = res.assistant_reply.lower()
    assert "why" not in reply and "not your fault" not in reply
    assert res.case.review_item_id  # still reaches a human
