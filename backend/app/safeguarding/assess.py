"""System 1: Safeguarding Intelligence Engine.

Reads the conversation and returns a validated SafeguardingAssessment. It
interprets; it does not decide what happens next (that is policy.py).

Safety properties:
- Multi-label: any number of concern categories, including other_or_unknown.
- Urgency is a separate field from category.
- Every concern must quote the child's own words. Quotes are checked against
  the child's turns; an unverifiable quote keeps the concern but marks it
  unverified, so a human looks at it. Nothing is silently dropped.
- Any failure (no key, timeout, malformed JSON, schema violation) returns a
  fallback assessment that demands human review instead of "no concern".
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Iterable, Literal, Optional

import httpx
from pydantic import ValidationError

from app.safeguarding.schema import (
    CATEGORY_LABELS,
    GEMINI_RESPONSE_SCHEMA,
    SafeguardingAssessment,
    Urgency,
)

logger = logging.getLogger("safeline.safeguarding.assess")

Role = Literal["child", "agent"]
Turn = tuple[Role, str]

DEFAULT_MODEL = "gemini-2.5-flash"
TIMEOUT_S = 20.0

_taxonomy = "\n".join(f"- {c.value}: {label}" for c, label in CATEGORY_LABELS.items())

SYSTEM_INSTRUCTION = f"""You are the assessment component of a child-safeguarding voice line (DEMO, synthetic conversations).
You read a conversation between a CHILD and the line's voice agent (AYO) and describe, in structured form, what the child may be communicating. You do not decide what happens next; a separate policy engine and human reviewers do.

Concern categories (use as many as apply; a conversation can raise several at once):
{_taxonomy}

Rules:
1. Understand meaning, not keywords. Indirect or partial statements count ("I don't like going home", "sometimes I don't get dinner", "my uncle comes in my room at night"). Combine statements made across different turns.
2. Physical harm is not the only concern. Verbal humiliation, threats, being locked in, not being fed, being made to keep secrets, unwanted touching, scary adults online, self-harm thoughts all matter.
3. If something seems wrong but does not fit a category, use other_or_unknown or fear_unclear_cause. Never leave a possible concern out because it is ambiguous.
4. evidence_quotes must be copied EXACTLY from the CHILD's lines (not AYO's), short (a few words to one sentence). Do not paraphrase inside quotes.
5. status: "stated" if the child said it directly, "potential" if inferred from indirect words, "unclear" if you are not sure what they meant.
6. Do not invent facts, names, ages, places, or who did what. Put unknowns in missing_information.
7. urgency is separate from category:
   - critical: possible immediate danger right now (being hurt now, attacker present or coming, attempt to self-harm in progress, cannot get away).
   - high: serious or ongoing harm needing urgent human assessment (ongoing sexual abuse, ongoing violence, abuser has access, self-harm thoughts).
   - moderate: a safeguarding concern needing timely review (persistent emotional abuse, neglect, bullying with threats).
   - low: the child may benefit from support but nothing indicates an urgent safeguarding response.
   - unknown: not enough information to judge urgency.
   Low urgency never means unimportant. Something in the past can still be ongoing; something serious with unclear timing is "unknown" or "high", not "low".
8. immediate_danger: "yes" only if the child indicates danger right now; "no" only if the child indicates they are safe right now; otherwise "unknown".
9. Speech-to-text may garble words. If a key phrase looks mis-transcribed, say so in model_uncertainty rather than guessing.
10. human_review_recommended: true whenever there is any concern, any uncertainty about a possible concern, or anything you cannot classify.
11. follow_up_appropriate: true if one gentle, non-leading question would help (e.g. whether they are safe right now). suggested_follow_up: that one question in simple child-friendly words, or null. Never a "why" question, never leading, never asking for graphic detail.
12. If the conversation is ordinary (homework, chatting, testing the line) return no concerns, urgency low, immediate_danger unknown or no.
"""


def _model() -> str:
    return os.getenv("SAFEGUARDING_MODEL", DEFAULT_MODEL)


def format_transcript(turns: Iterable[Turn]) -> str:
    lines = []
    for i, (role, text) in enumerate(turns, 1):
        who = "CHILD" if role == "child" else "AYO"
        lines.append(f"[{i}] {who}: {text.strip()}")
    return "\n".join(lines)


_norm_re = re.compile(r"[^a-z0-9\[\] ]+")


def _norm(s: str) -> str:
    return " ".join(_norm_re.sub(" ", s.lower()).split())


def quote_in_child_turns(quote: str, turns: list[Turn]) -> bool:
    q = _norm(quote)
    if len(q) < 2:
        return False
    child_text = " ".join(_norm(t) for r, t in turns if r == "child")
    return q in child_text


def fallback_assessment(session_id: str, reason: str, turns_assessed: int = 0) -> SafeguardingAssessment:
    """What System 1 returns when it cannot produce a valid assessment.
    It never claims 'no concern'; it hands the session to a human."""
    return SafeguardingAssessment(
        session_id=session_id,
        concerns=[],
        urgency=Urgency.unknown,
        immediate_danger="unknown",
        model_uncertainty=[f"Automated assessment unavailable: {reason}"],
        missing_information=["Whole conversation needs human reading."],
        human_review_recommended=True,
        follow_up_appropriate=False,
        limitations=["Assessment failed; no automated interpretation is available. A human must review."],
        engine="fallback",
        fallback=True,
        fallback_reason=reason,
        assessed_at=datetime.now(timezone.utc).isoformat(),
        turns_assessed=turns_assessed,
    )


def parse_and_validate(session_id: str, raw: str, turns: list[Turn], engine: str) -> SafeguardingAssessment:
    """Strict validation of model output + evidence check. Raises on malformed output."""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("assessment is not a JSON object")
    data = {k: v for k, v in data.items() if k in GEMINI_RESPONSE_SCHEMA["properties"]}
    data["session_id"] = session_id
    assessment = SafeguardingAssessment.model_validate(data)

    unverified = []
    for c in assessment.concerns:
        c.evidence_verified = all(quote_in_child_turns(q, turns) for q in c.evidence_quotes)
        if not c.evidence_verified:
            unverified.append(c.category.value)
    if unverified:
        assessment.model_uncertainty.append(
            "Evidence quotes not found verbatim in the child's words for: " + ", ".join(unverified)
        )
        assessment.human_review_recommended = True

    # A concern always needs a human; the model may not opt out of that.
    if assessment.concerns:
        assessment.human_review_recommended = True

    assessment.engine = engine
    assessment.assessed_at = datetime.now(timezone.utc).isoformat()
    assessment.turns_assessed = len(turns)
    return assessment


async def _call_gemini(transcript: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{_model()}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": "Conversation:\n" + transcript}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": GEMINI_RESPONSE_SCHEMA,
        },
    }
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        r = await client.post(url, params={"key": api_key}, json=body)
    if r.status_code != 200:
        raise RuntimeError(f"gemini_http_{r.status_code}")
    payload = r.json()
    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        finish = (payload.get("candidates") or [{}])[0].get("finishReason")
        raise RuntimeError(f"gemini_no_content finish={finish}") from exc


async def assess_conversation(session_id: str, turns: list[Turn], *, caller: Optional[object] = None) -> SafeguardingAssessment:
    """System 1 entry point. `caller` lets tests inject a fake model:
    an async function (transcript) -> raw JSON string."""
    turns = [(r, t) for r, t in turns if t and t.strip()]
    if not any(r == "child" for r, _ in turns):
        return SafeguardingAssessment(
            session_id=session_id,
            urgency=Urgency.unknown,
            immediate_danger="unknown",
            human_review_recommended=False,
            follow_up_appropriate=False,
            model_uncertainty=["The child has not said anything yet."],
            engine="none",
            assessed_at=datetime.now(timezone.utc).isoformat(),
        )

    transcript = format_transcript(turns)
    t0 = time.perf_counter()
    try:
        if caller is not None:
            raw = await caller(transcript)  # type: ignore[misc]
            engine = "injected"
        else:
            key = os.getenv("GEMINI_API_KEY", "").strip()
            if not key:
                return fallback_assessment(session_id, "GEMINI_API_KEY not configured", len(turns))
            raw = await _call_gemini(transcript, key)
            engine = _model()
        assessment = parse_and_validate(session_id, raw, turns, engine)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Assessment failed validation: %s", type(exc).__name__)
        return fallback_assessment(session_id, f"malformed model output ({type(exc).__name__})", len(turns))
    except Exception as exc:
        logger.warning("Assessment call failed: %s", exc)
        return fallback_assessment(session_id, f"model call failed ({str(exc)[:80]})", len(turns))
    logger.info(
        "Assessment session=%s concerns=%s urgency=%s in %.0fms",
        session_id,
        [c.category.value for c in assessment.concerns],
        assessment.urgency.value,
        (time.perf_counter() - t0) * 1000,
    )
    return assessment
