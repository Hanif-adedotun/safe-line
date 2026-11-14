# Safeguarding lane: System 1 + System 2 (demo)

Built to `child_safeguarding_voice_agent_brief.md` on branch `feat/safeguarding-engine`. It is separate from the main SafeLine/Ayo demo and runs on its own ports and database.

**Demo only.** Synthetic conversations, a demo policy, and mock notifications. Nothing is sent to anyone.

## Run it

```bash
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8010     # API (own safeline.db)
cd frontend && NEXT_PUBLIC_API_URL=http://127.0.0.1:8010 npx next dev -p 3010
open http://localhost:3010/safeguarding        # ?session=SL-2026-XXXX deep-links a session
cd backend && .venv/bin/python -m evals.safeguarding_eval   # 25 synthetic cases, real model
```

## How it fits together

```
child turn ──► System 1: app/safeguarding/assess.py  (Gemini 2.5 Flash, JSON schema, temp 0)
                 │  multi-label concerns + separate urgency + immediate_danger
                 │  evidence quotes checked against the CHILD's own words
                 │  any failure → fallback assessment that demands human review
                 ▼
             schema.py  (strict Pydantic contract; extra fields rejected)
                 ▼
             System 2: app/safeguarding/policy.py  (no LLM; rules P1–P9, versioned)
                 │  rule_id + explanation on every decision
                 │  priority can only rise within a session
                 ▼
             pipeline.py → review item (store.py) + audit log + mock notification preview
```

- **Session vs review item:** every call or text thread is a session (`CaseRecord`). A review item exists only when policy creates one. A human disposition is recorded with an audit entry. New information re-opens a reviewed item; nothing auto-closes.
- **Live calls:** `LiveAssessor` re-runs System 1 and 2 after each caller turn, without blocking audio. On P1 it injects one emergency cue into the call: check safety, give the local emergency number, never say help is coming.
- **Text replies** (console and iMessage) only use the brief's approved, non-leading prompts. The model's own suggested follow-up is shown to reviewers only; in testing it produced a "why" question.
- **Kept, unused:** the legacy Risk 0–3 scorer in `app/agent/triage_agent.py` and `evals/run_eval.py`.

## Policy (demo-2026-11-14.1)

| Rule | When | Result |
|---|---|---|
| P1 | immediate_danger = yes, or urgency critical | emergency protocol, critical, mock urgent alert |
| P2 | urgency high | priority review, mock alert |
| P3 | sexual abuse/exploitation, self-harm, online exploitation | never below priority review |
| P4 | System 1 failed | standard review (never "no concern") |
| P5 | concern with moderate/unknown urgency | standard review |
| P6 | evidence not found in the child's words | standard review |
| P7 | concern with low urgency | routine review (low urgency ≠ unimportant) |
| P8 | no concern, but model flagged uncertainty | standard review |
| P9 | no concern | no review item |

## First real run (14 Nov 2026, gemini-2.5-flash, 25 synthetic cases)

| Metric | Result |
|---|---|
| Concern cases caught (21) | **100%**, 0 missed (including indirect, multi-turn, Pidgin, garbled STT) |
| Expected categories found | 100% |
| Evidence quotes verbatim from the child | 100% |
| Urgency matched label | 92% |
| False positives (4 ordinary cases) | 1: "My mum is going to kill me if I fail this test haha" → emotional abuse, standard review |
| Assessment failures | 0 |

**Main weakness: over-escalation.**
- 15 of 25 cases came out "high". Bullying and "I'm scared to go home" were rated high.
- "I haven't eaten since yesterday" was marked immediate danger, which fired P1.

A queue that is mostly "high" stops meaning anything. I did not tune the prompt to pass these tests, since the labels are mine and not expert-reviewed. Calibrating urgency needs professionally labelled cases.

## Assumptions and limits (needs professional review before any real use)

- Taxonomy, urgency definitions, policy thresholds, approved prompts and dispositions are all drafts. They need child-protection professionals for a specific jurisdiction (Nigeria and the US differ).
- I added `self_harm_or_suicide` to the brief's taxonomy; confirm.
- The test labels are a developer's, written before running. They are not evidence of real-world performance.
- Notifications are previews only. Real recipients, legal basis, channel security and data minimisation must be approved before enabling anything (brief 5.4).
- Never notify a parent or guardian automatically; they may be the person causing harm.
- Data: transcripts are PII-scrubbed (regex, imperfect: third-party names leak) and kept in local SQLite with no encryption or retention policy. Demo reset deletes everything.
- The text channel's reply is a fixed template, not a conversation. Voice calls use the Gemini Live agent with the existing prompt.
