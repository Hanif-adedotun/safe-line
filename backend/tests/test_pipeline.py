from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_macro_stats():
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        m = client.get("/api/macro-stats")
        assert m.status_code == 200
        assert m.json()["live_cases_total"] >= 3


def test_intake_scrubs_pii_and_links_surulere():
    with TestClient(app) as client:
        r = client.post(
            "/api/intake",
            json={
                "message": "My name is Adaobi, call me 08031234567. A teacher at Surulere Primary Annex keeps beating my cousin.",
                "channel": "photon_sms",
                "region": "NG",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["pii_redacted_count"] >= 2
        assert "08031234567" not in data["case"]["redacted_summary"]
        assert "Adaobi" not in data["case"]["redacted_summary"]
        assert data["case"]["risk_level"] >= 2
        assert data["case"]["alert_dispatched"] is True
        assert "SL-2026-0101" in data["case"]["linked_case_ids"]
        # Trauma-informed check: never promise secrecy, never ask for graphic detail
        reply = data["assistant_reply"].lower()
        assert "cannot keep secrets" in reply or "safety comes first" in reply


def test_forensics_query_returns_citations():
    with TestClient(app) as client:
        r = client.post("/api/forensics/query", json={"question": "Which cases mention Surulere Primary Annex?"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["citations"]) >= 1
        assert any(c["case_id"] == "SL-2026-0101" for c in data["citations"])


def test_eval_endpoint():
    with TestClient(app) as client:
        r = client.post("/api/eval/run")
        assert r.status_code == 200
        data = r.json()
        assert data["total_cases"] == 40
        assert data["pii_leaks"] == 0
        assert data["escalation_recall_pct"] >= 95.0

