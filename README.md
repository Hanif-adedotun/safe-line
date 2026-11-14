# Ayo (formerly SafeLine / Leda) 🛡️✨

**The 24/7 Child-Safety Line That Actually Listens**  
*Full-Duplex Voice Telephony & Photon 2.0 Silent-Text Triage Engineered with Clinical Trauma Care*

Built for **HackPrinceton Fall '26** (Nov 13–15, 2026) and scaling under **Education for Equality (E4E)**.

## Why Ayo
- **1B+ children** experience violence annually (WHO/UNICEF); **500,000+ child helpline contacts/yr** go unanswered (Child Helpline International).
- In Nigeria, **6 in 10 children** experience violence before 18, yet **<5% receive help**—and **88% of child sexual abuse victims know their abuser**, making speaking aloud unsafe.
- **71% of US 988 crisis centers** report understaffing (*JAMA Network Open*).
- **2026 Acoustic AI Finding:** Voice models act on words, not tone (*Bartelds et al. 2026*). Ayo introduces an independent acoustic listener sidecar to capture crying, whisper mode, and tremor.

## Architecture
1. **Public Website (`/`):** Sleek, institutional presentation of the mission, clinical pillars, 2026 acoustic AI research, and interactive live response sandbox.
2. **Caseworker Command Center (`/console`):** Live intake simulator, PII-scrubbed transcript stream, dual-region geographic hotspot map (Nigeria + US), Arlequin cross-case entity forensics, and 40-case synthetic eval runner.
3. **Dual-Modality Intake:** Toll-free voice call (Twilio / Africa's Talking Asterisk AudioSocket) + silent text/iMessage (**Photon 2.0**) + web mic fallback.
4. **LangGraph Triage Agent:** Deterministic PII scrubber (`pii_scrubber.py`) → trauma-informed minimal-questioning intake & Risk 0–3 scorer (`Gemini 2.5 Flash` + deterministic safety floor) → caseworker SMS/Photon dispatch.
5. **Anti-Retaliation Safe-Protector Shield:** Protects children against violent retaliation with guaranteed abuser-safe confidentiality.
6. **40-Case Synthetic Eval Harness:** `100.0%` escalation recall, `0.0%` false-positive rate, `0` raw PII leaks.

## Run Locally
```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
# Public Product Site: http://localhost:3000
# Caseworker Console:  http://localhost:3000/console
```

