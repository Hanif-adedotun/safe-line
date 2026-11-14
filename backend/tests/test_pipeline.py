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


def test_intake_scrubs_pii_and_queues_for_human(tmp_path, monkeypatch):
    import app.services.case_store as case_store

    monkeypatch.setattr(case_store, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("GEMINI_API_KEY", "")  # System 1 unavailable -> must still reach a human
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
        stored = " ".join(t["text_redacted"] for t in data["case"]["turns"])
        assert "08031234567" not in stored and "Adaobi" not in stored
        assert data["case"]["review_item_id"]
        assert data["case"]["decision"]["rule_id"] == "P4_ASSESSMENT_FAILED"
        reply = data["assistant_reply"].lower()
        assert "secret" not in reply and "on the way" not in reply


def test_forensics_query_returns_citations():
    with TestClient(app) as client:
        r = client.post("/api/forensics/query", json={"question": "Which cases mention Surulere Primary Annex?"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["citations"]) >= 1
        assert any(c["case_id"] == "SL-2026-0101" for c in data["citations"])


def test_eval_endpoint_runs_suite_without_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with TestClient(app) as client:
        r = client.post("/api/eval/run")
        assert r.status_code == 200
        summary = r.json()["summary"]
        assert summary["total_cases"] == 25
        # With no model every case falls back to human review: nothing is silently cleared.
        assert len(summary["fallbacks"]) == 25
        assert summary["concern_detection_recall_pct"] == 100.0
