"""Wires System 1 -> System 2 -> review queue -> audit, for text and live calls."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from app.models import CaseRecord, IntakeRequest, IntakeResponse, TurnRecord
from app.safeguarding import store
from app.safeguarding.assess import Turn, assess_conversation
from app.safeguarding.policy import Action, Decision, decide
from app.safeguarding.schema import SafeguardingAssessment
from app.services.case_store import get_case, save_case
from app.services.pii_scrubber import scrub_pii

logger = logging.getLogger("safeline.safeguarding.pipeline")

HELPLINES = {
    "NG": {"emergency": "112", "child": "Cece Yara child helpline, 0800 800 8001"},
    "US": {"emergency": "911", "child": "Childhelp, 1-800-422-4453"},
}

_locks: dict[str, asyncio.Lock] = {}

# Injected so tests can run System 1 against a fake model.
ModelCaller = Optional[Callable[[str], Awaitable[str]]]
_model_caller: ModelCaller = None


def set_model_caller(caller: ModelCaller) -> None:
    global _model_caller
    _model_caller = caller


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def case_turns(case: CaseRecord) -> list[Turn]:
    return [("child" if t.role == "reporter" else "agent", t.text_redacted) for t in case.turns]


async def assess_and_route(case_id: str) -> tuple[Optional[SafeguardingAssessment], Optional[Decision]]:
    lock = _locks.setdefault(case_id, asyncio.Lock())
    async with lock:
        case = get_case(case_id)
        if not case:
            return None, None
        turns = case_turns(case)
        assessment = await assess_conversation(case_id, turns, caller=_model_caller)
        previous = Decision.model_validate(case.decision) if case.decision else None
        reference = case.review_item_id or store.new_review_item_id()
        decision = decide(assessment, reference, previous)

        store.audit(
            "assessment_run",
            case_id,
            {"engine": assessment.engine, "fallback": assessment.fallback, "urgency": assessment.urgency.value,
             "immediate_danger": assessment.immediate_danger,
             "categories": [c.category.value for c in assessment.concerns], "turns": assessment.turns_assessed},
        )
        store.audit(
            "policy_decision",
            case_id,
            {"policy_version": decision.policy_version, "rule_id": decision.rule_id, "action": decision.action.value,
             "priority": decision.priority.value, "held_from_previous": decision.held_from_previous},
        )

        # Re-read: location tools may have written to the case while System 1 ran.
        case = get_case(case_id) or case
        case.assessment = assessment.model_dump(mode="json")
        case.decision = decision.model_dump(mode="json")

        if decision.create_review_item:
            existing = store.get_review_item(case.review_item_id) if case.review_item_id else None
            categories = sorted({c.category.value for c in assessment.concerns} | set(existing.categories if existing else []))
            if existing is None:
                item = store.ReviewItem(
                    id=reference,
                    session_id=case_id,
                    created_at=_now(),
                    updated_at=_now(),
                    priority=decision.priority.value,
                    categories=categories,
                    urgency=assessment.urgency.value,
                    immediate_danger=assessment.immediate_danger,
                    rule_id=decision.rule_id,
                    policy_version=decision.policy_version,
                    explanation=decision.explanation,
                    notification_preview=decision.notification_preview,
                )
                store.save_review_item(item)
                case.review_item_id = item.id
                store.audit("review_item_created", case_id, {"priority": item.priority, "rule_id": item.rule_id}, item.id)
            else:
                changed = (existing.priority != decision.priority.value) or (existing.categories != categories)
                existing.priority = decision.priority.value
                existing.categories = categories
                existing.urgency = assessment.urgency.value
                existing.immediate_danger = assessment.immediate_danger
                existing.rule_id = decision.rule_id
                existing.explanation = decision.explanation
                if decision.notification_preview:
                    existing.notification_preview = decision.notification_preview
                if existing.status == "reviewed" and changed:
                    # New information after a human review re-opens it; nothing is silently closed.
                    existing.status = "open"
                    store.audit("review_item_reopened", case_id, {"reason": "new information"}, existing.id)
                existing.updated_at = _now()
                store.save_review_item(existing)
                if changed:
                    store.audit("review_item_updated", case_id, {"priority": existing.priority, "categories": categories}, existing.id)
            if decision.notify:
                store.audit(
                    "mock_notification_recorded",
                    case_id,
                    {"priority": decision.priority.value, "sent": False, "note": "Preview only. Nothing was sent."},
                    case.review_item_id,
                )

        case.updated_at = _now()
        save_case(case)
        return assessment, decision


# --------------------------------------------------------------------------- #
# Text channel (dashboard simulator, iMessage)
# --------------------------------------------------------------------------- #
# Replies to the child only ever use these approved, non-leading prompts (brief
# section 4.5). The model's own suggested_follow_up is shown to reviewers in the
# console but never sent to a child: in testing it produced a "why" question.
APPROVED_PROMPTS = {
    "safe_now": "Are you safe right now?",
    "person_near": "Is the person you're worried about with you right now?",
    "trusted_adult": "Is there an adult you trust who you feel safe talking to?",
    "connect": "Would you like help connecting with someone who can support you?",
    "tell_more": "You can tell me a little more if you want to, as much or as little as you like.",
}

# Categories where "it is not your fault" fits. For an ambiguous statement
# ("I don't like my uncle") it would be premature and leading.
_HARM_CATEGORIES = {
    "physical_abuse", "emotional_abuse", "sexual_abuse_or_exploitation", "neglect", "domestic_violence_exposure",
    "bullying", "threats_intimidation", "coercion_control", "unsafe_living_environment", "online_exploitation",
    "self_harm_or_suicide",
}


def _reply_for(decision: Decision, assessment: SafeguardingAssessment, region: str) -> str:
    lines = HELPLINES.get(region, HELPLINES["US"])
    cats = {c.category.value for c in assessment.concerns}
    harm = bool(cats & _HARM_CATEGORIES)
    if decision.action == Action.emergency_protocol:
        return (
            "Thank you for telling me. It is not your fault. If you are in danger right now and can do it safely, "
            f"call {lines['emergency']}. What you told me is going to a person whose job is to help keep you safe. "
            + APPROVED_PROMPTS["safe_now"]
        )
    if decision.action == Action.no_action:
        return "Hi, I'm Ayo. I'm here and I'm listening. You can tell me as much or as little as you want."
    if not harm:
        # Something may be wrong but it is not clear what: listen, don't label.
        return "Thank you for telling me. I'm listening. " + APPROVED_PROMPTS["tell_more"]
    msg = (
        "Thank you for telling me. It is not your fault. A person whose job is to help keep children safe will read "
        "what you shared, and we will not contact the person you're worried about."
    )
    if decision.action == Action.priority_review:
        msg += f" You can also reach {lines['child']}."
    if assessment.immediate_danger == "unknown":
        msg += " " + APPROVED_PROMPTS["safe_now"]
    else:
        msg += " " + APPROVED_PROMPTS["trusted_adult"]
    return msg


async def run_text_intake(req: IntakeRequest) -> IntakeResponse:
    t0 = time.perf_counter()
    scrub = scrub_pii(req.message)
    now = _now()
    case = get_case(req.case_id) if req.case_id else None
    if case is None:
        import uuid

        case = CaseRecord(
            id=req.case_id or f"SL-2026-{uuid.uuid4().hex[:4].upper()}",
            created_at=now,
            updated_at=now,
            channel=req.channel,
            region=req.region,
            redacted_summary=scrub.redacted_text[:280],
        )
    case.turns.append(TurnRecord(role="reporter", text_redacted=scrub.redacted_text, timestamp=now))
    save_case(case)

    assessment, decision = await assess_and_route(case.id)
    reply = _reply_for(decision, assessment, req.region)

    case = get_case(case.id)
    case.turns.append(TurnRecord(role="safeline", text_redacted=reply, timestamp=_now()))
    save_case(case)
    return IntakeResponse(
        case=case,
        assistant_reply=reply,
        helpline_resources=list(HELPLINES.get(req.region, HELPLINES["US"]).values()),
        missing_fields=assessment.missing_information,
        pii_redacted_count=scrub.redaction_count,
        total_latency_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


# --------------------------------------------------------------------------- #
# Live voice calls: re-assess after each caller turn, without blocking audio
# --------------------------------------------------------------------------- #
class LiveAssessor:
    """One per call. Coalesces turns so at most one assessment runs at a time
    and the latest conversation is always assessed last."""

    def __init__(self, case_id: str, inject: Optional[Callable[[str], Awaitable[None]]] = None):
        self.case_id = case_id
        self.inject = inject
        self._dirty = False
        self._task: Optional[asyncio.Task] = None
        self._emergency_cue_sent = False

    def add_turn(self, caller_text: str, agent_text: str) -> None:
        case = get_case(self.case_id)
        if not case:
            return
        now = _now()
        if caller_text:
            case.turns.append(TurnRecord(role="reporter", text_redacted=scrub_pii(caller_text).redacted_text, timestamp=now))
        if agent_text:
            case.turns.append(TurnRecord(role="safeline", text_redacted=agent_text, timestamp=now))
        save_case(case)
        if caller_text:
            self._dirty = True
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while self._dirty:
            self._dirty = False
            try:
                _, decision = await assess_and_route(self.case_id)
            except Exception:
                logger.exception("Live assessment failed case=%s", self.case_id)
                continue
            if decision and decision.in_call_instruction and not self._emergency_cue_sent and self.inject:
                self._emergency_cue_sent = True
                try:
                    await self.inject(decision.in_call_instruction)
                    store.audit("in_call_emergency_cue_sent", self.case_id, {"rule_id": decision.rule_id})
                except Exception as exc:
                    logger.warning("Could not inject emergency cue: %s", exc)

    async def finish(self) -> None:
        """Wait for the last assessment so the final state reflects the whole call."""
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=30)
            except asyncio.TimeoutError:
                logger.warning("Final live assessment timed out case=%s", self.case_id)
