"""Review queue + audit trail (demo, SQLite).

A session (CaseRecord) is not a case. A review item exists only when the
policy engine creates one. Every assessment, decision, review-item change,
mock notification and human review is written to the audit log.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

import app.services.case_store as case_store

ReviewStatus = Literal["open", "reviewed"]

DISPOSITIONS = [
    "escalated_per_protocol",
    "support_referral_offered",
    "no_safeguarding_concern_after_review",
    "needs_more_information",
    "duplicate_or_test",
]


class ReviewItem(BaseModel):
    id: str
    session_id: str
    created_at: str
    updated_at: str
    priority: str
    categories: list[str] = Field(default_factory=list)
    urgency: str
    immediate_danger: str
    rule_id: str
    policy_version: str
    explanation: str
    status: ReviewStatus = "open"
    notification_preview: Optional[str] = None
    reviewer_note: Optional[str] = None
    disposition: Optional[str] = None
    corrected_categories: Optional[list[str]] = None
    reviewed_at: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(case_store.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS review_items (id TEXT PRIMARY KEY, session_id TEXT, updated_at TEXT, data_json TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, session_id TEXT, "
        "review_item_id TEXT, kind TEXT, detail_json TEXT)"
    )
    return conn


def audit(kind: str, session_id: Optional[str], detail: dict[str, Any], review_item_id: Optional[str] = None) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO audit_events (at, session_id, review_item_id, kind, detail_json) VALUES (?,?,?,?,?)",
            (_now(), session_id, review_item_id, kind, json.dumps(detail, default=str)),
        )


def list_audit(session_id: Optional[str] = None, limit: int = 200) -> list[dict]:
    with _conn() as c:
        if session_id:
            rows = c.execute(
                "SELECT * FROM audit_events WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit)
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [
        {"at": r["at"], "session_id": r["session_id"], "review_item_id": r["review_item_id"], "kind": r["kind"],
         "detail": json.loads(r["detail_json"])}
        for r in rows
    ]


def save_review_item(item: ReviewItem) -> ReviewItem:
    with _conn() as c:
        c.execute(
            "INSERT INTO review_items (id, session_id, updated_at, data_json) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at, data_json=excluded.data_json",
            (item.id, item.session_id, item.updated_at, item.model_dump_json()),
        )
    return item


def get_review_item(item_id: str) -> Optional[ReviewItem]:
    with _conn() as c:
        row = c.execute("SELECT data_json FROM review_items WHERE id=?", (item_id,)).fetchone()
    return ReviewItem.model_validate_json(row["data_json"]) if row else None


_PRIORITY_ORDER = {"critical": 0, "high": 1, "standard": 2, "routine": 3}


def list_review_items() -> list[ReviewItem]:
    with _conn() as c:
        rows = c.execute("SELECT data_json FROM review_items").fetchall()
    items = [ReviewItem.model_validate_json(r["data_json"]) for r in rows]
    # Open first, then most urgent, then newest.
    items.sort(key=lambda i: i.created_at, reverse=True)
    items.sort(key=lambda i: (i.status != "open", _PRIORITY_ORDER.get(i.priority, 9)))
    return items


def new_review_item_id() -> str:
    return f"REV-{uuid.uuid4().hex[:5].upper()}"


def mark_reviewed(item_id: str, disposition: str, note: Optional[str], corrected_categories: Optional[list[str]]) -> Optional[ReviewItem]:
    item = get_review_item(item_id)
    if not item:
        return None
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown disposition")
    before = item.model_dump()
    item.status = "reviewed"
    item.disposition = disposition
    item.reviewer_note = (note or "")[:1000] or None
    item.corrected_categories = corrected_categories
    item.reviewed_at = item.updated_at = _now()
    save_review_item(item)
    audit(
        "human_review_recorded",
        item.session_id,
        {"disposition": disposition, "note": item.reviewer_note, "corrected_categories": corrected_categories,
         "model_categories": before["categories"]},
        review_item_id=item.id,
    )
    return item


def reset_demo_data() -> None:
    """Delete all sessions, review items and audit events (demo reset)."""
    with _conn() as c:
        c.execute("DELETE FROM review_items")
        c.execute("DELETE FROM audit_events")
    with case_store._conn() as c:  # noqa: SLF001
        c.execute("DELETE FROM cases")
