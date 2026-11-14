"""Run the synthetic safeguarding suite through System 1 (real model) + System 2.

    backend/.venv/bin/python -m evals.safeguarding_eval      (from backend/)

Expected labels live in safeguarding_cases.json and were written before any run.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.safeguarding.assess import assess_conversation  # noqa: E402
from app.safeguarding.policy import _RANK, Priority, decide  # noqa: E402

CASES_PATH = Path(__file__).with_name("safeguarding_cases.json")
RESULTS_DIR = Path(__file__).with_name("results")


def _rank(p: str) -> int:
    return _RANK[Priority(p)]


async def _run_case(case: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        turns = [(r, t) for r, t in case["turns"]]
        a = await assess_conversation(case["id"], turns)
    d = decide(a, f"EVAL-{case['id']}")
    exp = case["expect"]
    got_cats = {c.category.value for c in a.concerns}

    matched_sets = [any(c in got_cats for c in s) for s in exp["categories"]]
    concern_expected = bool(exp["categories"])
    pr = _rank(d.priority.value)
    priority_ok = pr >= _rank(exp["min_priority"]) and pr <= _rank(exp.get("max_priority", "critical"))
    return {
        "id": case["id"],
        "type": case["type"],
        "expected_categories": exp["categories"],
        "got_categories": sorted(got_cats),
        "category_sets_matched": matched_sets,
        "concern_expected": concern_expected,
        "concern_detected": bool(got_cats) or (a.fallback and concern_expected),
        "urgency": a.urgency.value,
        "urgency_ok": a.urgency.value in exp["urgency"],
        "immediate_danger": a.immediate_danger,
        "priority": d.priority.value,
        "rule_id": d.rule_id,
        "priority_ok": priority_ok,
        "evidence_verified": all(c.evidence_verified for c in a.concerns) if a.concerns else None,
        "human_review": d.create_review_item,
        "fallback": a.fallback,
        "fallback_reason": a.fallback_reason,
        "evidence": {c.category.value: c.evidence_quotes for c in a.concerns},
    }


async def run_suite(concurrency: int = 5) -> dict:
    cases = json.loads(CASES_PATH.read_text())["cases"]
    t0 = time.perf_counter()
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*[_run_case(c, sem) for c in cases])

    concern_cases = [r for r in results if r["concern_expected"]]
    clear_cases = [r for r in results if not r["concern_expected"]]
    sets_total = sum(len(r["expected_categories"]) for r in concern_cases)
    sets_hit = sum(sum(r["category_sets_matched"]) for r in concern_cases)

    misses_by_category: dict[str, int] = defaultdict(int)
    for r in concern_cases:
        for s, ok in zip(r["expected_categories"], r["category_sets_matched"]):
            if not ok:
                misses_by_category[s[0]] += 1

    with_evidence = [r for r in results if r["evidence_verified"] is not None]
    summary = {
        "model_note": "System 1 = Gemini structured output; System 2 = deterministic demo policy",
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(results),
        "concern_cases": len(concern_cases),
        "no_concern_cases": len(clear_cases),
        "concern_detection_recall_pct": round(100 * sum(r["concern_detected"] for r in concern_cases) / max(len(concern_cases), 1), 1),
        "missed_concern_cases": [r["id"] for r in concern_cases if not r["concern_detected"]],
        "category_recall_pct": round(100 * sets_hit / max(sets_total, 1), 1),
        "misses_by_category": dict(misses_by_category),
        "urgency_agreement_pct": round(100 * sum(r["urgency_ok"] for r in results) / len(results), 1),
        "priority_within_expected_pct": round(100 * sum(r["priority_ok"] for r in results) / len(results), 1),
        "under_escalated": [r["id"] for r in results if not r["priority_ok"] and r["concern_expected"]],
        "false_positives_on_no_concern": [r["id"] for r in clear_cases if not r["priority_ok"]],
        "evidence_verbatim_pct": round(100 * sum(bool(r["evidence_verified"]) for r in with_evidence) / max(len(with_evidence), 1), 1),
        "human_review_rate_pct": round(100 * sum(r["human_review"] for r in results) / len(results), 1),
        "fallbacks": [r["id"] for r in results if r["fallback"]],
        "priority_counts": dict(Counter(r["priority"] for r in results)),
        "seconds": round(time.perf_counter() - t0, 1),
        "caveat": "Synthetic cases with developer-written labels; not expert-reviewed. Not evidence of real-world performance.",
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    out = {"summary": summary, "results": results}
    (RESULTS_DIR / "safeguarding_eval_latest.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    out = asyncio.run(run_suite())
    print(json.dumps(out["summary"], indent=2))
    for r in out["results"]:
        flag = "" if (r["priority_ok"] and all(r["category_sets_matched"])) else "   <-- CHECK"
        print(f"{r['id']:28} got={r['got_categories']} urg={r['urgency']} pri={r['priority']} rule={r['rule_id']}{flag}")
