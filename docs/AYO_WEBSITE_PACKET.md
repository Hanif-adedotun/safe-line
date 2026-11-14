# Ayo Website — Build Packet

*For: the teammate building the Ayo landing page. From: Naomi Ivie (founder). Prepared 14 Nov 2026, HackPrinceton Fall '26.*

Everything you need is in this one file:
- what to build and in what order (§1–3)
- the facts about the product (§4–5), the problem (§6), and the organisation (§7)
- the claims you must not make (§8)
- design direction (§9), the codebase (§10), and open questions for Naomi (§11)

Where something is a draft or unconfirmed, it says so.

---

## 1. The job, in one paragraph

Build a clean, YC-style landing page for **Ayo** at `/` in the existing Next.js app (`frontend/src/app/page.tsx`).

**Hero:**
- The word **Ayo** in huge, bright white letters.
- The pronunciation beside it.
- The tagline **"A child's best friend."**

**Below the hero:**
1. What Ayo is and what it does.
2. The problem, with the researched stats below.

**Tone:** calm and confident, lots of whitespace, no hype. Think Linear or Vercel minimalism, not a hackathon dashboard. Don't touch the caseworker console at `/console`; it's a separate page and must keep working.

## 2. Hero spec (Naomi's exact ask)

```
AYO   /ˈɑː.joʊ/ · "AH-yo"            ← pronunciation beside the word, small, muted
A child's best friend.               ← tagline, under the wordmark

[ one line of plain-English description ]
[ primary CTA ]   [ secondary CTA ]
```

- **"Ayo":** the largest thing on the page, pure white (`#FFFFFF`) on near-black, heavy weight, tight tracking. Roughly `text-[clamp(5rem,18vw,14rem)]`.
- **Pronunciation:** set beside the word on desktop and under it on mobile, ~1/8 the size, in pale gold `#E2C88E`.
  - Ayo is Yoruba (**Ayọ̀**), meaning **"joy"**.
  - The Yoruba tones are mid-low: roughly **"AH-yaw"**, with the second syllable lower in pitch.
  - Most English speakers say **"AH-yo"**.
  - ⚠️ **Confirm the exact pronunciation line with Naomi** (she's Nigerian). A safe display: `Ayọ̀ · ah-yaw · "joy" in Yoruba`.
- **Tagline:** "A child's best friend." Medium size, white at ~85%.
- **One-liner under the tagline (draft, pick one):**
  - "A free phone line any child can call, to talk, to be heard, and to get help from a real person when something is wrong."
  - "Ayo listens when a child has no one else to tell, and makes sure what they share reaches someone who can help."
- **CTAs (drafts):**
  - Primary: "How Ayo works" (scrolls down).
  - Secondary: "For caseworkers →" (links to `/console`).
  - Don't make "Call Ayo" the primary CTA until Naomi confirms which number is public (see §8).

## 3. Page structure (top to bottom)

| # | Section | Purpose | Content source |
|---|---|---|---|
| 1 | Hero | Name, pronunciation, tagline | §2 |
| 2 | What Ayo is | 3–4 sentence explanation | §4.1 |
| 3 | How it works | 3–4 steps with simple icons | §4.2 |
| 4 | What Ayo does | Feature grid (6 tiles max) | §4.3 |
| 5 | Built safe | Safety principles (trust section) | §4.4 |
| 6 | The problem | Big verified stats + short text | §6 |
| 7 | Why us | E4E, Sabi, Nigeria context | §7 |
| 8 | Status | Honest "prototype" line | §5 |
| 9 | Footer | Emergency numbers, E4E, links | §9.5 |

Naomi asked for **product first, then problem**. Keep that order.

---

## 4. The product: what's true today

### 4.1 What Ayo is (draft copy)

> Ayo is a free phone line that children can call. A warm AI voice answers straight away, any time. It listens without judging, never rushes, and never asks "why". When a child shares that someone is hurting them, Ayo makes sure it isn't lost: their words go to a trained person whose job is to keep children safe. Ayo works on any phone, with no app, no internet, and no smartphone needed.

Ayo is the "little sister" of **Sabi**, E4E's AI voice tutor that teaches Nigerian children maths and reading over ordinary phone calls. Ayo uses the same phone technology, pointed at listening instead of teaching.

### 4.2 How it works (4 steps)

1. **A child calls.** On any phone, even a basic one. A warm, calm voice answers.
2. **Ayo listens.** It talks like a kind older sister. Short sentences, never rushing, never blaming. A child can talk about anything; they don't have to be in crisis.
3. **Ayo understands.** In the background, Ayo recognises when something may be wrong, even when a child says it indirectly. Examples: "I don't like going home", "sometimes I don't get dinner".
4. **A human follows up.** Anything concerning goes to a trained person to review. In an emergency, Ayo tells the child the local emergency number.

### 4.3 What Ayo does (feature tiles — pick up to 6)

- **Answers instantly, 24/7.** No queue, no hold music.
- **Works on any phone.** An ordinary voice call: no smartphone, app, or data. This matters where most children don't have smartphones.
- **Listens like a person, not a form.** Trauma-informed:
  - believes the child
  - never asks "why" or for graphic details
  - lets the child set the pace
  - is honest that it's an AI
- **Hears what isn't said outright.** Recognises many kinds of harm, not just physical: emotional abuse, neglect, sexual abuse, threats, bullying, online exploitation, and "I'm scared but I don't know how to say it".
- **Knows where to send help.** Asks gently where the child is. If it's safe, it can send a one-tap link so the child's phone shares its location.
- **Gets it to a human.** Concerns become review items for a trained caseworker, with the child's own words as evidence and a clear reason why.
- **Silent text option.** For children who can't speak out loud, a texting channel (iMessage via Photon) is being built.

### 4.4 Built safe (trust section — important for judges and partners)

- **A person decides, not the AI.** Ayo's AI only *understands* the conversation. Separate fixed rules, plus a trained human reviewer, decide what happens. The AI can't close a case or decide a child is fine.
- **Nothing slips through.** If Ayo isn't sure, it sends the conversation to a human rather than ignoring it. "Not sure" never means "nothing happened".
- **The child's words, not guesses.** Every concern shown to a reviewer quotes what the child actually said.
- **Honest with children.** Ayo never promises total secrecy. It tells children what they share goes to someone whose job is to keep them safe, and never to the person hurting them.
- **Minimal data.** Names, phone numbers and emails are removed from transcripts before they're saved. Location stays in the secure console, not in alert messages.
- **Never promises rescue.** Ayo won't say "help is on the way" unless that's true. In danger it gives the child the real local emergency number.

---

## 5. Honest status (put a small line on the page)

Ayo is a **working prototype built at HackPrinceton (Nov 13–15, 2026)**. It is not yet a live service for children.

- Concern detection and escalation rules are a **demo policy**; they need review by child-protection professionals before real use.
- Suggested page line: *"Ayo is in development. If you are a child in danger right now, call 112 in Nigeria or 911 in the US."*

What actually works today (verified by Claude in testing on Nov 14):

| Works | Detail |
|---|---|
| Live phone calls | US Twilio test number → Gemini Live voice agent; greets first, follows the trauma-informed prompt |
| Asking for location in the call | Saves the address or landmark the child gives |
| One-tap GPS link | Sent by iMessage, tapped on a real iPhone; location landed within ~13 m and the agent acknowledged it mid-call |
| Concern detection (separate branch) | 25 synthetic test conversations: all 21 concerning ones flagged, every evidence quote verified as the child's own words. **Developer-labelled test cases, not expert-reviewed — don't quote these as accuracy numbers.** |
| Caseworker console | `/console` (main demo) and `/safeguarding` (new engine, branch `feat/safeguarding-engine`) |

---

## 6. The problem (verified stats, with sources)

Use **3–4 big numbers max**, each with a one-line label and a source link in small text. Every number below was checked against its source on 14 Nov 2026.

### Recommended headline stats

| Big number | Label (draft) | Source |
|---|---|---|
| **Up to 1 billion** | children aged 2–17 experienced physical, sexual or emotional violence or neglect in the past year | [WHO fact sheet, *Violence against children*](https://www.who.int/news-room/fact-sheets/detail/violence-against-children) (Hillis et al., *Pediatrics* 2016) |
| **6 in 10** | Nigerian children experience physical, sexual or emotional violence before age 18 | [UNICEF Nigeria / NPopC, *Violence Against Children in Nigeria: Findings from a National Survey 2014*](https://www.unicef.org/nigeria/reports/ending-violence-against-children-nigeria) |
| **Fewer than 5%** | of Nigerian children who experienced violence ever received help | Same 2014 survey ([summary](https://www.healthnews.ng/ending-violence-children-nigeria)). ⚠️ The exact "<5% received help" figure is from secondary reporting; cite the UNICEF report and confirm wording in it. |
| **500,000** | contacts to child helplines worldwide went unanswered in 2024, usually because there weren't enough staff | [Child Helpline International, *Global Voices of Children and Young People 2024* factsheet](https://childhelplineinternational.org/wp-content/uploads/2025/11/Global-Voices-of-Children-and-Young-People-2024-Factsheet_Final.pdf) (6.1M contacts total) |

### Supporting stats (body text or a second row)

- **1 in 8 girls and women** alive today (370M+) experienced rape or sexual assault before 18; about 1 in 11 boys and men (240–310M). Sub-Saharan Africa has the most victims: 79M girls and women. Source: [UNICEF, Oct 2024](https://www.unicef.org/lac/en/press-releases/over-370-million-girls-women-globally-subjected-to-rape-sexual-assault-as-children).
- **1 in 4 girls and 1 in 10 boys** in Nigeria experience sexual violence before 18 (Nigeria VACS 2014, as above).
- **71% of US 988 crisis centres** that answered said they were understaffed (102 of 144), and 89% struggled to get resources to hire. Source: [Matthews et al., *JAMA Network Open*, May 2026](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2848613). Word it as "of centres surveyed", not "of all".
- **Children are usually hurt by someone they know.** Of child sexual assault victims reported to US police, 93% knew the perpetrator: 59% acquaintances, 34% family. Source: [US BJS, Snyder 2000, via RAINN](https://rainn.org/2025/06/16/statistics-perpetrators-of-sexual-violence/). This is why speaking out at home is dangerous, and why a line a child can reach on their own matters.
- **AI chatbots aren't safe substitutes.** Common Sense Media and Stanford found the major AI chatbots unsafe for teen mental-health support. The standard should be fast handoff to human care. Source: [Common Sense Media, Nov 2025](https://www.commonsensemedia.org/press-releases/common-sense-media-finds-major-ai-chatbots-unsafe-for-teen-mental-health-support). Use carefully: it supports Ayo's "AI listens, humans decide" design.

### Problem copy (draft, ~80 words)

> Most children who are hurt never tell anyone. Many are hurt by someone at home, so speaking up isn't safe. Helplines are overstretched: half a million calls to child helplines went unanswered last year. In Nigeria, 6 in 10 children face violence before they turn 18, and fewer than 1 in 20 ever get help. Many have no smartphone, no data, and no trusted adult. A child should only need a phone call.

### ❌ Do NOT use these (unverified or wrong)

- **"88% of child sexual abuse victims know their abuser"** — no traceable source; the only one found was a blog crediting UNICEF with no report. Use the 93% BJS figure above, with its source.
- **"1 billion children a year"** without "up to" — WHO says "up to 1 billion".
- **"71% of 988 centres are understaffed"** with no qualifier — it's 71% *of centres that answered*.
- **"1 child killed by violence every 4 minutes"**, **"$7 trillion per year"** — not re-verified today; leave out unless you check the UNICEF source yourself.

---

## 7. Who's behind it (for an "About" or "Why us" strip)

- **Education for Equality (E4E):** nonprofit, US 501(c)(3) with EIN issued Oct 2026, registered with Nigeria's CAC.
- **Founder:** Naomi Ivie, Wesleyan University (Economics & CS). Grew up in Lagos.
- **Sabi:** E4E's AI voice tutor teaching foundational maths and literacy to Nigerian children over ordinary phone calls. Ayo uses the same telephony stack: phone line → audio bridge → real-time voice model.
- **Built at HackPrinceton Fall '26** by Naomi and team (confirm teammate names and credits with Naomi before listing anyone).

---

## 8. Rules: claims and things that must NOT appear

The current `/` page has claims the product doesn't support. **Remove or don't carry these over:**

| Current claim | Why it has to go |
|---|---|
| "Cryptographic audit preservation", "SHA-256 ledger", "tamper-evident", "forensic admissibility" | There's no hashing or cryptographic ledger anywhere in the code |
| "40-case synthetic validation", "100% escalation recall", "0% false positives" | That eval tested a keyword list against cases written to pass it; it caught 0 of 10 realistic phrasings. It's being replaced. |
| "Acute triage safety floor" | Same keyword system |
| "Acoustic Listener Sidecar", "translate raw telephony acoustics into steering guidance" | Exists only as test scripts in `eval/`, not in the product |
| "Guaranteed abuser-safe confidentiality", "Safe-Protector Guarantee" | We can't guarantee outcomes. Say "Ayo never contacts the person you're worried about." |
| "High-risk disclosures immediately route to trained caseworkers via SMS" | Today alerts go to a test phone; carrier SMS is blocked (unregistered number). Say "go to a trained reviewer". |
| **"+234 201 700 1459" (Africa's Talking)** | ⚠️ **That's Sabi's live production tutoring line, not Ayo.** A child calling it reaches a maths tutor. Never list it for Ayo. |
| "world's first", "zero latency", "<800 ms", "1.2 s" | Unmeasured |

**Phone number:**
- The US test number (+1 715 312 2345) is a **Twilio trial** that's being temporarily routed to Ayo for the hackathon.
- Don't publish it as "Ayo's number" unless Naomi says so.
- If shown, label it "Demo line (HackPrinceton)".

**Emergency numbers, exact:**

| Country | Emergency | Child helpline | Self-harm / suicide |
|---|---|---|---|
| Nigeria | **112** | **Cece Yara, 0800 800 8001** (free, 24/7) | — |
| US | **911** | **Childhelp, 1-800-422-4453** (call or text) | **988** (Suicide & Crisis Lifeline) |

Don't list 988 as a child-abuse line.

**Children may land on this page.** Keep the language readable by a 10-year-old where possible, and keep emergency numbers visible in the footer (and ideally a slim top bar).

---

## 9. Design direction

### 9.1 Feel
"YC clean": confident, sparse, typographic.
- One idea per section, generous vertical space (`py-24`–`py-32`), a max ~3 colours, no gradients-everywhere, no glassmorphism, no stock photos of crying children.
- References for the feeling: linear.app, vercel.com, YC company homepages.

### 9.2 Colour — Naomi's direction: **"Ayo" in white, different gold accents**

The wordmark is pure white. Everything accented uses a family of golds (from the E4E/Sabi brand guide), not one flat gold.

| Use | Value | Where |
|---|---|---|
| Background | `#0B0B0C` (near-black) | Whole page (console uses `#0B0D12`) |
| **"Ayo" wordmark + headings** | **`#FFFFFF`** | Always pure white; never gold, never a gradient |
| Body text | `rgba(255,255,255,0.72)` | |
| Muted (sources, captions) | `rgba(255,255,255,0.45)` | |
| **Pale gold** | `#E2C88E` | Pronunciation next to "Ayo", tagline highlight, small labels |
| **Classic gold** | `#CBA868` | Primary buttons (black text on gold), step numbers, link underlines |
| **Warm amber** | `#F5B642` | Sparing pops: the big problem stats, the hover state of primary buttons |
| **Deep bronze** | `#9A7536` | Borders and hairline rules on cards, secondary button outline, icon strokes |
| Neutral hairlines | `rgba(255,255,255,0.08)` | Section dividers |

Guidance:
- Gold is for accents, not fills: no gold paragraphs, no gold backgrounds behind text blocks.
- Golds on near-black all pass contrast for large text. For small text use pale gold `#E2C88E`, which has the highest contrast.
- A very soft gold glow is fine behind the hero wordmark, if it stays subtle: e.g. a radial `#CBA868` at ~8% opacity behind "Ayo".

### 9.3 Type
- One sans family: **Inter**, **Geist**, or **Manrope** via `next/font/google`.
- "Ayo" at 800–900 weight with tight letter-spacing (`tracking-tighter`).
- Body 18–20px, line-height 1.6.
- Stats: big numerals (`text-6xl`+) with tiny labels.

### 9.4 Layout notes
- **Hero:** full viewport height, content centred or left-aligned. Nothing else competes with "Ayo".
- **How it works:** 4 numbered steps in a row on desktop, stacked on mobile.
- **Stats:** a 2×2 or 4-across grid of big numbers, with source links in small muted text under each.
- **Mobile first:** must look right at 375px wide, with no horizontal scroll.
- **Accessibility:** contrast ≥ 4.5:1 for body text, real `<h1>`–`<h3>` order, focus states on links, `prefers-reduced-motion` respected.
- **Motion:** at most a subtle fade-up on scroll.

### 9.5 Footer
- Emergency numbers (§8 table).
- "Ayo is an initiative of Education for Equality".
- Links: "For caseworkers" (`/console`), GitHub repo, contact (ask Naomi which email).
- Small line: "Prototype. Not a substitute for emergency services."

---

## 10. Codebase: how to work on it

- **Repo:** `github.com/thegirwhocodes/safe-line` (public). Branch off `main`: `git checkout -b website/landing`.
- **App:** `frontend/` — Next.js **16.4**, React 19, Tailwind CSS **4** (`@import "tailwindcss"` in `globals.css`), TypeScript, `lucide-react` icons.
- ⚠️ `frontend/AGENTS.md`: *"This is NOT the Next.js you know"*. Next 16 has breaking changes; read `frontend/node_modules/next/dist/docs/` before using unfamiliar APIs.
- **Files:**
  - `frontend/src/app/page.tsx` — the landing page (currently a 1,350-line page with simulator widgets; you can replace it wholesale).
  - `frontend/src/app/console/page.tsx` — caseworker console. **Don't modify.**
  - `frontend/src/app/layout.tsx`, `globals.css` — fonts and global styles. Changes here affect `/console` too, so test both.
- **Run:**
  ```bash
  cd frontend && npm install && npm run dev     # http://localhost:3000  (console at /console)
  npx tsc --noEmit -p .                          # typecheck before pushing
  ```
- The landing page should be **static**: no API calls needed. Don't add fetches to the backend (`localhost:8000`). It won't exist for site visitors, and the backend refuses case data over the public tunnel by design.
- **Deploy:** not deployed anywhere yet. Ask Naomi before creating a Vercel project or domain.
- **Other sessions are actively committing to `main`.** Pull often, keep your changes to the landing page files, and open a PR rather than pushing straight to `main`.

---

## 11. Open questions for Naomi (get answers before final copy)

1. Exact **pronunciation line** next to "Ayo" (IPA, phonetic spelling, or both? include "joy" in Yoruba?).
2. ~~Accent colour~~ — decided: "Ayo" in white with a family of gold accents (§9.2).
3. Is any **phone number** public on the site? If yes, which, and how is it labelled?
4. Who goes in **credits** (teammates' names and roles)?
5. Primary audience: judges and funders, or children and parents? This decides how much the copy speaks to a child directly.
6. Is the "silent text / iMessage" channel shown as available or "coming soon"?
7. Contact email for the footer.

---

## Appendix A: Background reading in this repo

- `docs/RISK_TRIAGE_RESEARCH.md` — how 988, child-protection hotlines and Childline triage. Background for the "Built safe" section; not page copy.
- `docs/DEVPOST_SUBMISSION.md`, `docs/PITCH_SCRIPT_2_MINUTES.md` — hackathon pitch. ⚠️ Contains several claims listed in §8; don't copy them.
- Branch `feat/safeguarding-engine` → `docs/SAFEGUARDING_LANE.md` — the new System 1/System 2 safeguarding engine, the basis for §4.4.
- `eval/prompts/ayo_brief_for_openai.md` — Naomi's own words on what Ayo must feel like (persona, secrecy, probing, location).
