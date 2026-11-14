# SafeLine

**24/7 Toll-Free Voice & Photon 2.0 Silent-Text Child Safety Triage**

Built for **HackPrinceton Fall '26** (Nov 13–15, 2026).

## Why SafeLine
- **1B+ children** experience violence annually (WHO/UNICEF); **500,000+ child helpline contacts/yr** go unanswered (Child Helpline International).
- In Nigeria, **6 in 10 children** experience violence before 18, yet **<5% receive help**—and **88% of child sexual abuse victims know their abuser**, making speaking aloud unsafe.
- **71% of US 988 crisis centers** report understaffing (*JAMA Network Open*).

## Architecture
1. **Dual-Modality Intake:** Toll-free voice call (Twilio + Groq Whisper) + silent text/iMessage (**Photon 2.0**) + web mic fallback.
2. **LangGraph Triage Agent:** Deterministic PII scrubber (`pii_scrubber.py`) → trauma-informed minimal-questioning intake & Risk 0–3 scorer (`Gemini 2.5 Flash` + deterministic safety floor) → caseworker SMS/Photon dispatch.
3. **Cross-Case Forensics (Arlequin Track):** Links recurring locations/actors across anonymized reports and supports cited investigator Q&A.
4. **40-Case Synthetic Eval Harness:** `100.0%` escalation recall, `0.0%` false-positive rate, `0` raw PII leaks.

## Run Locally
```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
```
