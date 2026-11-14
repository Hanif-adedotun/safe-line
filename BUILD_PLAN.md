# SafeLine — HackPrinceton Fall '26 Build Plan (Sat 3:30 AM → Sun 8:00 AM)

**Deadline:** Sunday, Nov 15, 2026 @ **8:00 AM EST** (Devpost + GitHub repo created Nov 13–15)  
**Judging:** Sunday **9:30 AM – 2:30 PM** (2-min max table pitch, ≥3 general judges + Special Track judges)  
**Repo:** `~/dev/safe-line` (commits `e421276`, `b17d1c0`)

---

## 1. Track & Prize Stack
- **Main Track (Required — pick 1):** **Healthcare** (Apple Watch SE 3 / member + auto-entered for **Best Overall — PS5**)
- **Special Tracks (Stackable):**
  1. **Photon 2.0:** Messaging + Voice Agent ($400 Winner / $300 Best Voice Agent)
  2. **LangChain:** `deepagents` (Nintendo Switch 2)
  3. **Amazon:** Best Practical AI Innovation ($125/person gift card)
  4. **Arlequin AI (Track 1):** AI-Driven Forensics (AirPods 5)
  5. **Peri:** Forward Deployed Challenge (hiring fast-track — requires partner consultation screenshot + quote)
  6. **MLH:** Best Use of Gemini API + Best Use of Vultr
  7. **ChatOverflow:** Coding agent leaderboard ($500/$250/$150 + raffle)

---

## 2. What Is Already Built & Verified
- [x] **FastAPI Backend (`backend/app/main.py`)** + SQLite persistence (`case_store.py`)
- [x] **LangGraph Triage Agent (`backend/app/agent/triage_agent.py`)** — `pii_scrubber` → `extract_and_score` (Gemini 2.5 Flash + deterministic safety floor) → `trauma_informed_responder` → `case_linker_and_dispatch`
- [x] **Location Intelligence (`resolve_location_coords`)** — auto-pins NG & US locations (`lat, lng`)
- [x] **Twilio Voice Webhook (`voice_twilio.py`)** + **Photon 2.0 Webhook (`/api/photon/webhook`)** + **Caseworker Dispatch (`dispatch.py`)**
- [x] **40-Case Synthetic Eval (`evals/run_eval.py`)** — `100.0%` escalation recall, `0.0%` FPR, `0` raw PII leaks
- [x] **Next.js Zoom-Out → Zoom-In → Zoom-Out UI (`frontend/src/app/page.tsx`)** — Dual-region hotspot map, live intake, LangGraph trace, Arlequin cited Q&A, live eval panel (`next build` passing, `4/4` pytest passing)

---

## 3. Remaining Execution Schedule

| Window | Task | Done Criteria |
| :--- | :--- | :--- |
| **Sat 3:30 AM – 4:30 AM** | **Sleep / Rest or Quick Wire** | *Recommended:* Push `~/dev/safe-line` to a new public GitHub repo first, then get 4–5 hrs sleep so Sunday energy stays sharp. |
| **Sat Morning (10:00 AM – 1:00 PM)** | **Wire Live Keys & Phone/Photon** | Add `GEMINI_API_KEY`, `GROQ_API_KEY`, `TWILIO_*`, `PHOTON_API_KEY`, `CASEWORKER_ALERT_PHONE` to `.env`. Test 1 live call on your toll-free number + 1 live Photon 2.0 silent text. |
| **Sat Afternoon (1:00 PM – 4:00 PM)** | **Clinical Felt-Safety + Vultr Deploy** | Add the 5 NICHD / Psychological First Aid guarantees to `triage_agent.py` + UI badge. Deploy backend to **Vultr NJ** (`MLH Vultr` prize) and point Twilio webhook to it. |
| **Sat Afternoon (4:00 PM – 6:00 PM)** | **Peri Partner Consultation** | Message/call your child-safety partner; ask where their intake workflow breaks down; save screenshot + quote for **Peri Forward Deployed** submission. |
| **Sat Evening (6:00 PM – 9:00 PM)** | **Polish + Backup Video** | Freeze features at 6 PM. Record ≤2-min 1080p backup video showing Zoom-Out → Live Call/Text → Caseworker Phone Buzz → Cross-Case Forensics. Upload to YouTube. |
| **Sat Night (9:00 PM – 11:00 PM)** | **Devpost Draft + Sleep** | Fill Devpost using stat-first hook, architecture diagram, `100%` eval table, partner quote, Discord handle, and all selected Special Tracks. Sleep before midnight. |
| **Sun 7:00 AM – 8:00 AM** | **Submit Early** | Finalize Devpost **before 7:45 AM** (hard cutoff 8:00 AM). Test live demo on `puvisitor` Wi-Fi + hotspot backup. |
| **Sun 9:30 AM – 2:30 PM** | **Judging** | Deliver the 2:00 stopwatch pitch (0:00–0:20 Hook → 0:20–1:15 Live Demo → 1:15–1:40 Tech + Eval → 1:40–2:00 E4E Scale). |
