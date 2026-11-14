from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.models import (
    AgentTraceStep,
    CaseRecord,
    CaseStatus,
    CitationSpan,
    ForensicQueryResponse,
    TurnRecord,
)

DB_PATH = Path(__file__).resolve().parents[2] / "safeline.db"


def _now_iso(offset_minutes: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data_json TEXT NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        if count == 0:
            for case in _seed_synthetic_cases():
                conn.execute(
                    "INSERT INTO cases (id, created_at, updated_at, data_json) VALUES (?, ?, ?, ?)",
                    (case.id, case.created_at, case.updated_at, case.model_dump_json()),
                )


def _seed_synthetic_cases() -> list[CaseRecord]:
    """Synthetic demo cases so cross-case forensics linking works immediately on boot."""
    return [
        CaseRecord(
            id="SL-2026-0101",
            created_at=_now_iso(-190),
            updated_at=_now_iso(-185),
            channel="photon_sms",
            region="NG",
            status="reviewing",
            risk_level=3,
            harm_category="physical_abuse",
            general_location="Surulere Primary Annex, Lagos",
            who_at_risk="10-year-old female pupil",
            immediate_danger=True,
            redacted_summary="Silent text from older sibling: teacher at Surulere Primary Annex locks pupil in store room after closing and beats her with cane.",
            entities=["Surulere", "Surulere Primary Annex", "teacher", "store room"],
            linked_case_ids=["SL-2026-0102"],
            alert_dispatched=True,
            alert_channels=["photon_2_0", "caseworker_queue_realtime"],
            turns=[
                TurnRecord(
                    role="reporter",
                    text_redacted="My small sister dey cry every day. One teacher for Surulere Primary Annex dey lock am for store room beat am after school.",
                    timestamp=_now_iso(-190),
                ),
                TurnRecord(
                    role="safeline",
                    text_redacted="Thank you for telling me—you did the right thing and your sister deserves to be safe. Is she in danger right now or still at the school?",
                    timestamp=_now_iso(-189),
                ),
            ],
            trace=[
                AgentTraceStep(node="intake_guard", status="flagged", latency_ms=14.2, detail="Risk 3 physical_abuse detected (Pidgin)"),
                AgentTraceStep(node="pii_scrubber", status="ok", latency_ms=2.1, detail="0 contact PII leaked"),
                AgentTraceStep(node="dispatch_alert", status="alert_sent", latency_ms=92.4, detail="Dispatched to Lagos focal point"),
            ],
        ),
        CaseRecord(
            id="SL-2026-0102",
            created_at=_now_iso(-95),
            updated_at=_now_iso(-90),
            channel="voice_call",
            region="NG",
            status="open",
            risk_level=2,
            harm_category="emotional_abuse",
            general_location="Surulere Primary Annex, Lagos",
            who_at_risk="Multiple primary pupils",
            immediate_danger=False,
            redacted_summary="Anonymous parent called about repeated verbal threats and forced labor after hours near Surulere Primary Annex.",
            entities=["Surulere", "Surulere Primary Annex", "teacher"],
            linked_case_ids=["SL-2026-0101"],
            alert_dispatched=True,
            alert_channels=["twilio_sms"],
            turns=[
                TurnRecord(
                    role="reporter",
                    text_redacted="I am calling from Surulere. A teacher near Surulere Primary Annex has been threatening children not to tell their parents.",
                    timestamp=_now_iso(-95),
                ),
            ],
            trace=[
                AgentTraceStep(node="case_linker", status="flagged", latency_ms=8.7, detail="Linked to SL-2026-0101 via Surulere Primary Annex"),
            ],
        ),
        CaseRecord(
            id="SL-2026-0103",
            created_at=_now_iso(-45),
            updated_at=_now_iso(-42),
            channel="photon_sms",
            region="US",
            status="actioned",
            risk_level=3,
            harm_category="immediate_danger",
            general_location="Trenton Central High area, NJ",
            who_at_risk="15-year-old student",
            immediate_danger=True,
            redacted_summary="Silent text: teen unsafe to speak aloud because guardian is outside bedroom door after physical altercation.",
            entities=["Trenton", "guardian", "bedroom"],
            linked_case_ids=[],
            alert_dispatched=True,
            alert_channels=["photon_2_0", "twilio_sms"],
            turns=[
                TurnRecord(
                    role="reporter",
                    text_redacted="Cant talk out loud my stepdad is outside the door he just threw me into the wall in Trenton",
                    timestamp=_now_iso(-45),
                ),
            ],
            trace=[
                AgentTraceStep(node="intake_guard", status="flagged", latency_ms=11.0, detail="Risk 3 immediate_danger (silent mode)"),
            ],
        ),
    ]


def list_cases() -> list[CaseRecord]:
    init_db()
    with _conn() as conn:
        rows = conn.execute("SELECT data_json FROM cases ORDER BY updated_at DESC").fetchall()
    return [CaseRecord.model_validate_json(r["data_json"]) for r in rows]


def get_case(case_id: str) -> Optional[CaseRecord]:
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT data_json FROM cases WHERE id = ?", (case_id,)).fetchone()
    return CaseRecord.model_validate_json(row["data_json"]) if row else None


def save_case(case: CaseRecord) -> CaseRecord:
    init_db()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO cases (id, created_at, updated_at, data_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at, data_json = excluded.data_json
            """,
            (case.id, case.created_at, case.updated_at, case.model_dump_json()),
        )
    return case


def update_case_status(case_id: str, status: CaseStatus) -> Optional[CaseRecord]:
    case = get_case(case_id)
    if not case:
        return None
    case.status = status
    case.updated_at = _now_iso()
    return save_case(case)


def find_linked_cases(case: CaseRecord) -> list[str]:
    """Link cases that share normalized location or key actor/facility entities."""
    all_cases = list_cases()
    my_tokens = {e.lower().strip() for e in case.entities if len(e.strip()) >= 4}
    if case.general_location:
        for tok in case.general_location.lower().replace(",", " ").split():
            if len(tok) >= 4 and tok not in {"lagos", "area", "near", "road", "street"}:
                my_tokens.add(tok)

    linked: list[str] = []
    for other in all_cases:
        if other.id == case.id:
            continue
        other_tokens = {e.lower().strip() for e in other.entities if len(e.strip()) >= 4}
        if other.general_location:
            for tok in other.general_location.lower().replace(",", " ").split():
                if len(tok) >= 4 and tok not in {"lagos", "area", "near", "road", "street"}:
                    other_tokens.add(tok)
        if my_tokens & other_tokens:
            linked.append(other.id)
    return linked


def query_forensics(question: str) -> ForensicQueryResponse:
    """Evidence-backed investigator Q&A over redacted case records and spans."""
    cases = list_cases()
    q_words = [
        w.strip("?,.'\"").lower()
        for w in question.split()
        if len(w.strip("?,.'\"")) >= 3
        and w.lower() not in {"what", "which", "where", "when", "have", "there", "about", "cases", "reports", "show"}
    ]

    scored: list[tuple[int, CaseRecord, str]] = []
    matched_entities: set[str] = set()

    for c in cases:
        blob = " ".join(
            [
                c.general_location or "",
                c.redacted_summary,
                c.harm_category,
                " ".join(c.entities),
                " ".join(t.text_redacted for t in c.turns if t.role == "reporter"),
            ]
        ).lower()
        hits = sum(1 for w in q_words if w in blob)
        if hits > 0 or not q_words:
            for e in c.entities:
                if any(w in e.lower() for w in q_words):
                    matched_entities.add(e)
            excerpt = next(
                (t.text_redacted for t in c.turns if t.role == "reporter"),
                c.redacted_summary,
            )
            scored.append((hits, c, excerpt[:220]))

    scored.sort(key=lambda item: (item[0], item[1].risk_level), reverse=True)
    top = scored[:4]

    if not top:
        return ForensicQueryResponse(
            answer="No matching anonymized reports were found for that query.",
            citations=[],
            matched_entities=[],
        )

    citations = [
        CitationSpan(
            case_id=c.id,
            location=c.general_location,
            risk_level=c.risk_level,
            excerpt=excerpt,
        )
        for _, c, excerpt in top
    ]
    ids_str = ", ".join(f"{c.case_id} (Risk {c.risk_level})" for c in citations)
    locs = sorted({c.location for c in citations if c.location})
    answer = (
        f"Found {len(citations)} evidence-backed report(s): {ids_str}. "
        f"Locations referenced: {', '.join(locs) if locs else 'unspecified'}. "
        f"All excerpts below are PII-redacted."
    )
    return ForensicQueryResponse(
        answer=answer,
        citations=citations,
        matched_entities=sorted(matched_entities),
    )

