# SafeLine — Technical Build Plan

**Goal:** 24/7 toll-free voice & Photon 2.0 silent-text child-safety reporting line with trauma-informed LangGraph triage, deterministic PII scrubbing, instant caseworker dispatch, and cross-case forensics.  
**Repo:** `~/dev/safe-line`

---

## 1. Architecture Overview

```text
[Toll-Free Voice (Twilio)] ──► Groq Whisper STT ──┐
[Silent Text (Photon 2.0)] ──────────────────────┼──► LangGraph Triage Agent (Vultr NJ)
[Browser Mic / Text Demo] ───────────────────────┘        │
                                                          ├──► 1. Deterministic PII Scrubber
                                                          ├──► 2. Gemini 2.5 Flash + Safety Floor (Risk 0–3)
                                                          ├──► 3. Trauma-Informed Responder (NICHD + PFA)
                                                          ├──► 4. Location Resolver + Cross-Case Linker
                                                          └──► 5. Caseworker Dispatch (Twilio SMS + Photon)
                                                                     │
                                                                     ▼
                                                       Next.js Command Center (Zoom-Out → Zoom-In → Zoom-Out)
```

---

## 2. Build Tiers

### Tier 1 — Unbreakable Core *(Built & Passing)*
- **FastAPI Backend (`backend/app/main.py`):** CORS, health check, macro stats, intake endpoints, SQLite persistence (`case_store.py`).
- **Deterministic PII Scrubber (`backend/app/services/pii_scrubber.py`):** Masks phone numbers, emails, street addresses, and self-reported names before storage.
- **LangGraph Triage Pipeline (`backend/app/agent/triage_agent.py`):** Stateful 4-node graph (`pii_scrubber` → `extract_and_score` → `generate_reply` → `persist_and_dispatch`) with Gemini 2.5 Flash + deterministic Nigerian Pidgin/English/US safety floor.
- **Location Intelligence (`resolve_location_coords`):** Maps Nigerian & US community/school locations to `(lat, lng)` coordinates.
- **Next.js Command Center (`frontend/src/app/page.tsx`):**
  1. **Zoom Out (Blind Spot):** Verified macro stats + dual-region live hotspot map.
  2. **Zoom In (Live Triage):** Voice mic / Photon silent text / 1-click presets + PII-redacted transcript + live LangGraph trace.
  3. **Zoom Out (Forensics & Eval):** Evidence-cited investigator Q&A + live 40-case eval runner.

### Tier 2 — Live Channels & Clinical Felt Safety *(Next)*
- **Live Toll-Free Voice (`backend/app/services/voice_twilio.py`):** Wire `TWILIO_*` and `GROQ_API_KEY` in `.env`; point toll-free Twilio Voice webhook to `/api/twilio/incoming`.
- **Live Photon 2.0 Silent Text (`backend/app/services/dispatch.py`, `/api/photon/webhook`):** Wire `PHOTON_API_KEY` for inbound silent reporting + outbound Risk ≥ 2 caseworker alerts.
- **Clinical Felt-Safety Upgrade (`triage_agent.py` + UI):** Enforce and surface the 5 NICHD / Psychological First Aid guarantees on every response (*Believed & De-blamed*, *Zero "Why?" / Leading Questions*, *Micro-Agency*, *Transparent Handoff*, *Non-Human Clarity*).
- **Vultr NJ Deployment:** Deploy `backend/` on a Vultr New Jersey instance for low-latency telephony + **MLH Best Use of Vultr**.

### Tier 3 — Bonus Stack & Submission
- **40-Case Synthetic Eval (`backend/evals/run_eval.py`):** Already at `100.0%` escalation recall, `0.0%` FPR, `0` raw PII leaks.
- **Peri Forward Deployed:** Include partner consultation screenshot + quote on Devpost.
- **Backup Demo Video:** ≤2-min screen recording of Zoom-Out → Live Call/Text → Caseworker Alert → Cross-Case Forensics.

---

## 3. Target HackPrinceton Tracks
- **Main Track:** Healthcare *(auto-entered for Best Overall)*
- **Special Tracks:** Photon 2.0 (Messaging + Best Voice Agent) · LangChain `deepagents` · Amazon Practical AI · Arlequin AI Track 1 (Forensics) · Peri Forward Deployed · MLH Gemini API · MLH Vultr · ChatOverflow
