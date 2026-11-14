"""System 2: Intervention and Escalation Engine (DEMO POLICY).

Deterministic, versioned rules over the SafeguardingAssessment from System 1.
No LLM here. Every decision records the rule that produced it.

DEMO ONLY: these thresholds are illustrative (from the product brief, section
5.3). They are not a real reporting protocol and must be replaced by rules
written and approved by child-protection professionals for a jurisdiction.
All notifications are previews. Nothing is sent anywhere.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.safeguarding.schema import CATEGORY_LABELS, ConcernCategory, SafeguardingAssessment, Urgency

POLICY_VERSION = "demo-2026-11-14.1"


class Action(str, Enum):
    emergency_protocol = "emergency_protocol"
    priority_review = "priority_review"
    standard_review = "standard_review"
    routine_review = "routine_review"
    no_action = "no_action"


class Priority(str, Enum):
    critical = "critical"
    high = "high"
    standard = "standard"
    routine = "routine"
    none = "none"


_RANK = {Priority.none: 0, Priority.routine: 1, Priority.standard: 2, Priority.high: 3, Priority.critical: 4}

# Categories that never drop below priority review, whatever urgency the model gave.
PRIORITY_FLOOR_CATEGORIES = {
    ConcernCategory.sexual_abuse_or_exploitation,
    ConcernCategory.self_harm_or_suicide,
    ConcernCategory.online_exploitation,
}

RULES: dict[str, str] = {
    "P1_IMMEDIATE_DANGER": "Immediate danger indicated, or urgency critical → emergency protocol (demo simulation).",
    "P2_HIGH_URGENCY": "Urgency high → priority human review + mock urgent notification.",
    "P3_CATEGORY_FLOOR": "Sexual abuse/exploitation, self-harm, or online exploitation → never below priority review.",
    "P4_ASSESSMENT_FAILED": "System 1 could not produce a valid assessment → human review (never treated as 'no concern').",
    "P5_CONCERN_MODERATE_OR_UNKNOWN": "A concern with moderate or unknown urgency → standard human review.",
    "P6_UNVERIFIED_EVIDENCE": "Evidence could not be matched to the child's words → standard human review.",
    "P7_CONCERN_LOW": "A concern with low urgency → routine review (low urgency is not low importance).",
    "P8_MODEL_ASKED_FOR_REVIEW": "No concern classified, but uncertainty flagged → standard human review.",
    "P9_NO_CONCERN": "No concern identified → no review item; ordinary supportive conversation.",
    "MONOTONIC": "Within one session, priority can rise but never fall; an open review item is never auto-closed.",
}


class Decision(BaseModel):
    policy_version: str = POLICY_VERSION
    rule_id: str
    rule_text: str
    action: Action
    priority: Priority
    create_review_item: bool
    notify: bool
    notification_preview: Optional[str] = None
    in_call_instruction: Optional[str] = None
    explanation: str
    held_from_previous: bool = False


def _decide(a: SafeguardingAssessment) -> tuple[str, Action, Priority]:
    cats = {c.category for c in a.concerns}
    if a.immediate_danger == "yes" or a.urgency == Urgency.critical:
        return "P1_IMMEDIATE_DANGER", Action.emergency_protocol, Priority.critical
    if a.urgency == Urgency.high:
        return "P2_HIGH_URGENCY", Action.priority_review, Priority.high
    if cats & PRIORITY_FLOOR_CATEGORIES:
        return "P3_CATEGORY_FLOOR", Action.priority_review, Priority.high
    if a.fallback:
        return "P4_ASSESSMENT_FAILED", Action.standard_review, Priority.standard
    if a.concerns and a.urgency in (Urgency.moderate, Urgency.unknown):
        return "P5_CONCERN_MODERATE_OR_UNKNOWN", Action.standard_review, Priority.standard
    if any(not c.evidence_verified for c in a.concerns):
        return "P6_UNVERIFIED_EVIDENCE", Action.standard_review, Priority.standard
    if a.concerns:
        return "P7_CONCERN_LOW", Action.routine_review, Priority.routine
    if a.human_review_recommended:
        return "P8_MODEL_ASKED_FOR_REVIEW", Action.standard_review, Priority.standard
    return "P9_NO_CONCERN", Action.no_action, Priority.none


def mock_notification(reference: str, a: SafeguardingAssessment, priority: Priority, rule_id: str) -> str:
    cats = ", ".join(CATEGORY_LABELS[c.category] for c in a.concerns) or "Unclassified (human review)"
    excerpt = next((q for c in a.concerns for q in c.evidence_quotes), None)
    excerpt_line = f'"{excerpt[:120]}"' if excerpt else "None (see console)"
    return (
        "MOCK SAFEGUARDING ALERT — DEMO ONLY\n\n"
        f"Reference: {reference}\n"
        f"Priority: {priority.value.upper()}\n"
        f"Concern categories: {cats}\n"
        f"Immediate danger: {a.immediate_danger.capitalize()}\n"
        f"Reason for review: {RULES[rule_id]}\n"
        f"Evidence (redacted excerpt): {excerpt_line}\n"
        "Location: held in the access-controlled console, not in this message.\n"
        "Action: Human safeguarding review required.\n\n"
        "This is a simulated notification. No external authority has been contacted."
    )


EMERGENCY_IN_CALL_INSTRUCTION = (
    "[SYSTEM NOTE, not spoken by the caller] The safeguarding check indicates the caller may be in danger "
    "right now. Gently and briefly: ask if they are safe right now and whether the person is near them; if "
    "they can safely do so, tell them to call the emergency number from your CALLER CONTEXT; tell them what "
    "they shared is going to a person whose job is to help keep them safe. Do not say anyone is on the way."
)


def decide(a: SafeguardingAssessment, reference: str, previous: Optional[Decision] = None) -> Decision:
    rule_id, action, priority = _decide(a)
    held = False
    # MONOTONIC: never downgrade within a session.
    if previous and _RANK[previous.priority] > _RANK[priority]:
        rule_id, action, priority, held = previous.rule_id, previous.action, previous.priority, True

    create = priority != Priority.none
    notify = priority in (Priority.critical, Priority.high)
    explanation = RULES[rule_id] + (" (held from an earlier assessment in this session: " + RULES["MONOTONIC"] + ")" if held else "")
    return Decision(
        rule_id=rule_id,
        rule_text=RULES[rule_id],
        action=action,
        priority=priority,
        create_review_item=create,
        notify=notify,
        notification_preview=mock_notification(reference, a, priority, rule_id) if notify else None,
        in_call_instruction=EMERGENCY_IN_CALL_INSTRUCTION if action == Action.emergency_protocol else None,
        explanation=explanation,
        held_from_previous=held,
    )
