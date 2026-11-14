from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.models import (
    AgentTraceStep,
    CaseRecord,
    ExtractedFields,
    HarmCategory,
    IntakeRequest,
    IntakeResponse,
    TurnRecord,
)
from app.services.case_store import find_linked_cases, get_case, save_case
from app.services.dispatch import dispatch_caseworker_alert
from app.services.pii_scrubber import scrub_pii

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:  # pragma: no cover
    ChatGoogleGenerativeAI = None  # type: ignore


HELPLINES = {
    "NG": ["Nigeria Emergency: 112", "Cece Yara Free Child Helpline: 0800 800 8001"],
    "US": ["Childhelp National Hotline: 1-800-422-4453 (Call/Text)", "988 Lifeline / 911 Emergency"],
}

_CITY_COORDS: dict[str, tuple[float, float]] = {
    "surulere": (6.4969, 3.3539),
    "yaba": (6.5095, 3.3711),
    "ikeja": (6.6018, 3.3515),
    "ajegunle": (6.4531, 3.3298),
    "mushin": (6.5280, 3.3541),
    "mile 12": (6.6046, 3.3958),
    "lagos": (6.5244, 3.3792),
    "abuja": (9.0765, 7.3986),
    "rivers": (4.8156, 7.0498),
    "port harcourt": (4.8156, 7.0498),
    "trenton": (40.2206, -74.7597),
    "princeton": (40.3573, -74.6672),
    "newark": (40.7357, -74.1724),
    "camden": (39.9259, -75.1196),
}


def resolve_location_coords(location: str | None, region: str) -> tuple[float, float]:
    low = (location or "").lower()
    for key, coords in _CITY_COORDS.items():
        if key in low:
            return coords
    return (6.5244, 3.3792) if region == "NG" else (40.3573, -74.6672)

# Trauma-informed rules: never ask for graphic details, never promise secrecy, minimal questions.
_SELF_HARM_RE = re.compile(
    r"\b(kill (myself|me)|want(?:s|ing)? to die|end (?:my|her|his|their) life|hurt(?:ing)? myself|no wan live|wan die|wan commot for this world|suicide)\b",
    re.I,
)
_IMMEDIATE_DANGER_RE = re.compile(
    r"\b(right now|outside the door|chasing (?:me|her|him)|bleeding|attack(?:ing|ed) (?:me|her|him)|locked (me|her|him) in|can'?t breathe|about to hit|coming now|in danger)\b",
    re.I,
)
_SEXUAL_RE = re.compile(
    r"\b(touch(?:es|ed|ing)? (?:me|her|him|[a-z ]+?) (?:down|there)|molest(?:s|ed|ing)?|raped?|sexual(?:ly)?|private parts?|defile)\b",
    re.I,
)
_PHYSICAL_RE = re.compile(
    r"\b(beat(?:s|en|ing)?|flog(?:s|ged|ging)?|cane|whip(?:s|ped)?|slap(?:s|ped)?|hit(?:s|ting)?|hurt(?:s|ing)? (?:me|her|him)|burn(?:s|t)?|threw me|lock(?:s|ed)? (?:am|her|him|me) (?:for|in)|knack)\b",
    re.I,
)
_NEGLECT_RE = re.compile(
    r"\b(no food|nobody (?:dey )?feeds?|dem no dey (?:feed|give (?:me|us|am) food)|starving|abandoned|sleeping outside|no shelter|without food)\b",
    re.I,
)
_EMOTIONAL_RE = re.compile(
    r"\b(threaten(?:s|ing)?|screaming|locking|don'?t tell anyone|our secret|scared to go home)\b",
    re.I,
)
_LOCATION_RE = re.compile(
    r"\b(?:in|at|near|from|for)\s+([A-Z][A-Za-z0-9\s-]{2,35}?(?:School|Primary|Secondary|Annex|Area|Road|Market|Lagos|Surulere|Yaba|Ikeja|Abuja|Trenton|Princeton|Newark|NJ))\b",
    re.I,
)


class TriageState(TypedDict):
    req: IntakeRequest
    raw_message: str
    redacted_message: str
    pii_count: int
    extracted: dict[str, Any]
    risk_level: int
    missing_fields: list[str]
    assistant_reply: str
    case: Optional[CaseRecord]
    trace: list[dict[str, Any]]


def _heuristic_extract(text: str) -> tuple[ExtractedFields, int]:
    t = text or ""
    immediate = bool(_IMMEDIATE_DANGER_RE.search(t))
    harm: HarmCategory = "other_concern"
    risk = 1

    if _SELF_HARM_RE.search(t):
        harm = "self_harm"
        risk = 3
    elif _SEXUAL_RE.search(t):
        harm = "sexual_abuse"
        risk = 3
    elif immediate:
        harm = "immediate_danger"
        risk = 3
    elif _PHYSICAL_RE.search(t):
        harm = "physical_abuse"
        risk = 3 if immediate or any(k in t.lower() for k in ("bleeding", "store room", "lock", "every day", "burn")) else 2
    elif _NEGLECT_RE.search(t):
        harm = "neglect"
        risk = 2
    elif _EMOTIONAL_RE.search(t):
        harm = "emotional_abuse"
        risk = 2
    elif any(k in t.lower() for k in ("hello", "test", "weather", "homework", "math", "just checking")):
        harm = "non_crisis"
        risk = 0

    who = None
    low = t.lower()
    for pat, label in (
        (r"\b(my (?:small |little )?sister)\b", "younger sister"),
        (r"\b(my (?:small |little )?brother)\b", "younger brother"),
        (r"\b(my friend|classmate|neighbor|neighbour)\b", "peer/neighbor child"),
        (r"\b(pupil|student|child|kid|daughter|son)\b", "child/student"),
        (r"\b(i am|i'm|me|myself)\b", "caller (self)"),
    ):
        if re.search(pat, low):
            who = label
            break

    loc_match = _LOCATION_RE.search(t)
    loc = loc_match.group(1).strip() if loc_match else None

    entities: list[str] = []
    if loc:
        entities.append(loc)
    for role_word in ("teacher", "uncle", "stepdad", "guardian", "neighbor", "pastor", "coach", "store room"):
        if role_word in low:
            entities.append(role_word)

    return (
        ExtractedFields(
            who_at_risk=who,
            harm_category=harm,
            general_location=loc,
            immediate_danger=immediate,
            entities=entities,
        ),
        risk,
    )


async def _llm_extract(text: str, heuristic: ExtractedFields, heuristic_risk: int) -> tuple[ExtractedFields, int, str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or ChatGoogleGenerativeAI is None:
        return heuristic, heuristic_risk, "deterministic_guard"

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.0,
            timeout=6.0,
        )
        prompt = (
            "You are a trauma-informed child-safety triage classifier. "
            "Extract ONLY high-level protective fields from the redacted report below. "
            "NEVER ask for or output graphic details. Return strict JSON with keys: "
            "who_at_risk (string|null), harm_category (one of physical_abuse, sexual_abuse, emotional_abuse, "
            "neglect, self_harm, immediate_danger, other_concern, non_crisis), "
            "general_location (string|null), immediate_danger (bool), risk_level (0..3), entities (list of short strings).\n\n"
            f"Report: {text}"
        )
        resp = await llm.ainvoke(prompt)
        raw = str(resp.content).strip()
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return heuristic, heuristic_risk, "deterministic_fallback"
        data = json.loads(m.group(0))
        ext = ExtractedFields(
            who_at_risk=data.get("who_at_risk") or heuristic.who_at_risk,
            harm_category=data.get("harm_category") or heuristic.harm_category,
            general_location=data.get("general_location") or heuristic.general_location,
            immediate_danger=bool(data.get("immediate_danger")) or heuristic.immediate_danger,
            entities=list({*(data.get("entities") or []), *heuristic.entities})[:8],
        )
        # Safety floor: never let the LLM downgrade a heuristic crisis detection
        risk = max(int(data.get("risk_level", heuristic_risk)), heuristic_risk)
        return ext, min(max(risk, 0), 3), "gemini-2.5-flash"
    except Exception:
        return heuristic, heuristic_risk, "deterministic_fallback"


def _node_pii(state: TriageState) -> dict[str, Any]:
    t0 = time.perf_counter()
    scrub = scrub_pii(state["raw_message"])
    ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "redacted_message": scrub.redacted_text,
        "pii_count": scrub.redaction_count,
        "trace": [
            *state["trace"],
            {
                "node": "pii_scrubber",
                "status": "ok",
                "latency_ms": ms,
                "detail": f"Masked {scrub.redaction_count} contact/identity PII token(s)",
            },
        ],
    }


async def _node_extract_and_score(state: TriageState) -> dict[str, Any]:
    t0 = time.perf_counter()
    heur, heur_risk = _heuristic_extract(state["redacted_message"])
    ext, risk, engine = await _llm_extract(state["redacted_message"], heur, heur_risk)
    ms = round((time.perf_counter() - t0) * 1000, 2)

    missing: list[str] = []
    if risk > 0:
        if not ext.who_at_risk:
            missing.append("who_at_risk")
        if not ext.general_location:
            missing.append("general_location")

    return {
        "extracted": ext.model_dump(),
        "risk_level": risk,
        "missing_fields": missing,
        "trace": [
            *state["trace"],
            {
                "node": "intake_guard_and_scorer",
                "status": "flagged" if risk >= 2 else "ok",
                "latency_ms": ms,
                "detail": f"Risk {risk} ({ext.harm_category}) via {engine}",
            },
        ],
    }


def _node_generate_reply(state: TriageState) -> dict[str, Any]:
    t0 = time.perf_counter()
    risk = state["risk_level"]
    ext = ExtractedFields.model_validate(state["extracted"])
    region = state["req"].region
    helplines = HELPLINES[region]
    missing = state["missing_fields"]

    if risk == 0:
        reply = (
            "Thank you for reaching SafeLine. If you or a child you know is unsafe or being hurt, "
            "you can tell me what is happening—by voice or silently by text—and I will connect a trained caseworker."
        )
    else:
        opener = (
            "Thank you for telling me—you did the right thing, and this is not your fault. "
            "I cannot keep secrets about someone being hurt, because your safety comes first."
        )
        if ext.immediate_danger or risk == 3:
            action = (
                f" If you can move to a safe place right now, please do. "
                f"I have flagged this as urgent for a caseworker, and you can also reach {helplines[0]} or {helplines[1]}."
            )
        else:
            action = f" I am alerting a trained caseworker now. Free confidential help is also at {helplines[1]}."

        if "general_location" in missing:
            follow = " Without sharing an exact home address, what neighborhood, school, or town is this in?"
        elif "who_at_risk" in missing:
            follow = " Is the child safe right this moment, and who needs help?"
        else:
            follow = " You do not need to share any graphic details—we have enough to alert a caseworker right now."
        reply = opener + action + follow

    ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "assistant_reply": reply,
        "trace": [
            *state["trace"],
            {
                "node": "trauma_informed_responder",
                "status": "ok",
                "latency_ms": ms,
                "detail": "Generated minimal-questioning response (no graphic probe, no secrecy)",
            },
        ],
    }


async def _node_persist_and_dispatch(state: TriageState) -> dict[str, Any]:
    t0 = time.perf_counter()
    req = state["req"]
    ext = ExtractedFields.model_validate(state["extracted"])
    risk = state["risk_level"]
    now = datetime.now(timezone.utc).isoformat()

    existing = get_case(req.case_id) if req.case_id else None
    case_id = existing.id if existing else f"SL-2026-{uuid.uuid4().hex[:4].upper()}"

    turns = list(existing.turns) if existing else []
    turns.append(TurnRecord(role="reporter", text_redacted=state["redacted_message"], timestamp=now))
    turns.append(TurnRecord(role="safeline", text_redacted=state["assistant_reply"], timestamp=now))

    # Merge with existing case context on multi-turn follow-up
    merged_risk = max(risk, existing.risk_level) if existing else risk
    merged_loc = ext.general_location or (existing.general_location if existing else None)
    merged_who = ext.who_at_risk or (existing.who_at_risk if existing else None)
    merged_entities = sorted(set((existing.entities if existing else []) + ext.entities))
    merged_danger = ext.immediate_danger or (existing.immediate_danger if existing else False)
    merged_harm = ext.harm_category if ext.harm_category != "other_concern" else (existing.harm_category if existing else ext.harm_category)
    lat, lng = resolve_location_coords(merged_loc, req.region)

    draft = CaseRecord(
        id=case_id,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        channel=req.channel,
        region=req.region,
        status=existing.status if existing else "open",
        risk_level=merged_risk,
        harm_category=merged_harm,
        general_location=merged_loc,
        latitude=lat,
        longitude=lng,
        who_at_risk=merged_who,
        immediate_danger=merged_danger,
        redacted_summary=state["redacted_message"][:280],
        entities=merged_entities,
        linked_case_ids=[],
        alert_dispatched=existing.alert_dispatched if existing else False,
        alert_channels=list(existing.alert_channels) if existing else [],
        turns=turns,
        trace=[],
    )

    linked = find_linked_cases(draft)
    draft.linked_case_ids = linked

    channels = await dispatch_caseworker_alert(
        case_id=draft.id,
        risk_level=draft.risk_level,
        harm_category=draft.harm_category,
        general_location=draft.general_location,
        redacted_summary=draft.redacted_summary,
    )
    if channels:
        draft.alert_dispatched = True
        draft.alert_channels = sorted(set(draft.alert_channels + channels))

    ms = round((time.perf_counter() - t0) * 1000, 2)
    final_trace = [
        *[AgentTraceStep(**s) for s in state["trace"]],
        AgentTraceStep(
            node="case_linker_and_dispatch",
            status="alert_sent" if draft.alert_dispatched else "ok",
            latency_ms=ms,
            detail=f"Linked {len(linked)} prior case(s); alerts={draft.alert_channels or ['none']}",
        ),
    ]
    draft.trace = final_trace
    save_case(draft)
    return {"case": draft}


def _build_graph():
    g = StateGraph(TriageState)
    g.add_node("pii_scrubber", _node_pii)
    g.add_node("extract_and_score", _node_extract_and_score)
    g.add_node("generate_reply", _node_generate_reply)
    g.add_node("persist_and_dispatch", _node_persist_and_dispatch)

    g.set_entry_point("pii_scrubber")
    g.add_edge("pii_scrubber", "extract_and_score")
    g.add_edge("extract_and_score", "generate_reply")
    g.add_edge("generate_reply", "persist_and_dispatch")
    g.add_edge("persist_and_dispatch", END)
    return g.compile()


TRIAGE_GRAPH = _build_graph()


async def run_intake_pipeline(req: IntakeRequest) -> IntakeResponse:
    t0 = time.perf_counter()
    out = await TRIAGE_GRAPH.ainvoke(
        {
            "req": req,
            "raw_message": req.message,
            "redacted_message": "",
            "pii_count": 0,
            "extracted": {},
            "risk_level": 0,
            "missing_fields": [],
            "assistant_reply": "",
            "case": None,
            "trace": [],
        }
    )
    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    case: CaseRecord = out["case"]
    return IntakeResponse(
        case=case,
        assistant_reply=out["assistant_reply"],
        helpline_resources=HELPLINES[req.region],
        missing_fields=out["missing_fields"],
        pii_redacted_count=out["pii_count"],
        total_latency_ms=total_ms,
    )
