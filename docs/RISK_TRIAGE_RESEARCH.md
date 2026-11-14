# How the world's best crisis and child-abuse lines triage risk

*Research for SafeLine, 14 Nov 2026. Written to decide what replaces the current regex + Gemini "Risk 0–3" score.*

## The short answer

No serious helpline triages with a single severity number produced by keywords. The gold standard has five features:

1. **They ask, they don't infer.** 988 requires two direct questions of *every* caller. Child-abuse hotlines walk the reporter through a fixed checklist. Risk comes from answers to specific questions, not from scanning a transcript for words.
2. **They separate the kinds of risk.** Suicide/self-harm uses one framework (Desire, Intent, Capability, Buffers). Child maltreatment uses another: is this abuse, and how fast must someone respond? "Danger right now" is its own branch.
3. **The output is a response priority, not a score.** Examples: "attempt in progress → act now", "respond within 24 hours", "respond within 10 days", "safety plan + referral". Each level maps to a specific action.
4. **A trained human makes the call, with a supervisor on overrides.** Any change to the tool's recommendation, and every emergency dispatch, gets supervisor review.
5. **AI, where used, only re-orders the queue.** Crisis Text Line and The Trevor Project use models to decide *who a human counsellor talks to first*, never to decide outcomes. Both learned that keyword lists fail.

---

## 1. Suicide and self-harm: the 988 Lifeline standard

The US 988 Suicide & Crisis Lifeline's **Suicide Safety Policy (2024)** replaced its 2007 Risk Assessment Standards and its 2011 imminent-risk policy. It is the most documented crisis-line triage standard in the world.

**Ask everyone, early.** Counsellors must ask about suicide with *all* contacts, within about the first 5 minutes (or 5–7 texts). The two required prompts are:
- "Have you had any thoughts of suicide in the past few days, including today?"
- "Have you taken any action to harm yourself today?"

They need not be verbatim, but they must cover recent past, current, and whether an attempt has already happened.

**Four Core Principles** (Joiner et al., 2007, built on the Interpersonal Theory of Suicide):

| Principle | What counsellors listen for |
|---|---|
| **Desire** | Psychological pain, hopelessness, helplessness, feeling a burden on others, feeling trapped, feeling intolerably alone |
| **Capability** | Past attempts, exposure to someone else's suicide, violence to others, access to means, current intoxication, acute mental-illness symptoms, dramatic mood change, extreme rage, agitation, not sleeping |
| **Intent** | Attempt in progress, a plan with a known method, preparatory behaviour, stated intent to die |
| **Buffers** | Immediate supports, other social supports, planning for the future, engagement with the helper, ambivalence about dying, core values/beliefs, sense of purpose |

**How they combine** (this is the key logic):
- Desire alone is common and does **not** mean imminent risk.
- **Imminent risk** = desire + intent + capability, with a close time link. When all three are present, buffers don't lower it.
- When desire pairs with intent *or* capability (not both), buffers can be decisive.
- An **attempt in progress** is acted on immediately.

**What they do about it: least invasive intervention.**
- Collaboration comes before coercion. Involuntary emergency dispatch is a last resort and needs a documented attempt to agree a safety plan first.
- Every dispatch gets a supervisory review, and the line must confirm that emergency services actually reached the person.
- In practice police or paramedic dispatch happens on roughly 1% of contacts (CBS News citing Vibrant data).

**Third-party callers** (someone reporting another person, which is most of SafeLine's text reports):
- Gather what they know and get contact details for the person at risk and for themselves.
- Allow anonymity when revealing the reporter could endanger them, for example interpersonal violence.
- Try a three-way connection with the person at risk.

**Youth screen: NIMH ASQ.** This validated screen takes about 20 seconds and is meant for youth, asked without a parent present. It found 97% of at-risk youth in NIMH's emergency-department study. The four core items cover:
- wishing they were dead
- feeling they or their family would be better off if they were dead
- thoughts of killing themselves
- any past attempt

Any "yes" means a 5th question: "Are you having thoughts of killing yourself right now?" Yes is an **acute positive** (imminent); no is a **non-acute positive** (needs a brief safety assessment). It is free and public domain.

The **Columbia Suicide Severity Rating Scale (C-SSRS) screener** is the other widely used tool. It is a short gated question set with Low / Moderate / High triage colours.

## 2. Child abuse reports: the child-protection hotline standard

The most concrete published standard for "how urgent is this abuse report" is the **Structured Decision Making (SDM) Hotline Tool** (Evident Change). Many US child-protection agencies use it; the California 2023 version is quoted here. It has two steps.

**Step 1: screening.** Does the report meet a threshold in any category? If any criterion is met, an in-person response is required.
- **Physical abuse:** non-accidental or suspicious injury (severe injury or a child's death is an automatic 24-hour response); caregiver action likely to cause injury.
- **Sexual abuse:** any sexual act by an adult caregiver or other adult in the household; indicators consistent with abuse; acts among children in the home; exploitation or trafficking; threat (a known perpetrator lives with the child).
- **Emotional abuse:** caregiver actions causing or likely to cause severe anxiety, withdrawal, or aggression; emotional harm related to domestic violence.
- **Neglect:** severe (malnutrition, health or safety endangered); general (food, shelter, supervision, medical care, abandonment, failure to protect); threat of neglect.

**Step 2: response priority (24 hours or 10 days).** A short decision tree per category:
- **Physical abuse:** 24 hours if medical care is needed now, the caregiver's behaviour is dangerous or threatening, or the child is under 2. Otherwise, 10 days if a *non-offending caregiver is aware and acting protectively*. Otherwise, 24 hours if the child is **vulnerable or fearful**, there is prior abuse, or domestic violence will affect them within 10 days.
- **Sexual abuse:** is there **current** abuse shown by disclosure, a credible witness or medical evidence? If yes and no protective caregiver is acting, 24 hours.
- **Neglect:** 24 hours if the child needs care now, living conditions are immediately hazardous, or the child is currently unsupervised.
- **Overrides:**
  - Raise to 24 hours if police request it, if evidence would be lost by waiting, or if the family may flee.
  - Lower to 10 days if the child is in an alternative safe place or the incident was over six months ago with nothing since.
  - Any override needs supervisor approval.

**What this teaches SafeLine:** the questions that matter for a child disclosing abuse are:
- Is the child hurt now and needing care?
- Is the abuse ongoing?
- Does the abuser have access to the child now?
- Is there a protective adult who knows and is acting?
- Is the child under 2 (or otherwise especially vulnerable) or afraid?

Not "did they say a scary word".

**Childhelp (US National Child Abuse Hotline)** is explicitly *not* a reporting line. Counsellors give crisis intervention, safety planning, and a warm transfer to the right local agency (CPS or police), and 911 for emergencies.

**Childline UK (NSPCC)** promises confidentiality but must break it when a child is at **serious or immediate risk**. It aims to get the child's consent before involving emergency services, and it distinguishes feeling suicidal from planning to act. Its internal thresholds are not public. **Cautionary 2026 case:** the NSPCC self-reported to the Charity Commission after **37 contacts categorised as high-risk were not passed to police or councils** over six months. The failure was the *handoff*, not the detection.

**Kids Help Phone (Canada):**
- Responders must report when someone is at immediate risk or discloses abuse.
- Trained volunteers are supervised by professional staff.
- Around 2019, counsellors had directed police or paramedics to a texter's location in 761 "active rescues".

**WHO (2017 guideline / 2022 handbook):** first-line response to a child's disclosure of sexual abuse is the "LIVES" approach. It is child-centred and gender-sensitive, offers choices, respects the child's wishes, and avoids causing further distress.

**Child Helpline International** (the global network, 160+ helplines) has Core Quality Standards and a shared data framework. Concerns are categorised (violence → physical, emotional, sexual, neglect, bullying, online exploitation), not scored. The full framework is available on request, not public.

## 3. How AI is actually used at real helplines

- **Crisis Text Line:**
  - First system, "Code Orange V1": a hand-picked list of about 50 words. It **produced false alarms** ("I'm not suicidal, just depressed" was flagged) and **missed real ones** ("I am walking towards the bridge"). That is SafeLine's regex problem exactly.
  - Replacement: a model trained on counsellor post-conversation risk labels. It reportedly cut false alarms 52% and misses 13%, finds 86% of severe-imminent-risk texters in their first conversation, and gets 94% of high-risk texters to a counsellor in under 5 minutes. These figures are self-reported.
  - Its only job is moving people **up the queue** to a human.
- **The Trevor Project:**
  - A model reads the intake form and chat, then puts the young person in a **standard or priority queue**; counsellors take the priority queue first. Labels come from counsellors' clinical risk assessments.
  - It was tuned on *how long high-risk youth wait*, and error rates were checked across 20+ demographic groups.
  - It found the labels noisy: near-identical intake answers got opposite risk ratings from different counsellors.
- **Allegheny Family Screening Tool:** a statistical model at a US child-abuse hotline. It is the cautionary tale: accuracy was disputed, there were racial-bias concerns, and the DOJ took an interest. Workers can override it, and investigators disagreed with it about a third of the time.
- **LLM research (2025):**
  - PsyCrisisBench, 540 real Chinese hotline transcripts: LLMs scored F1 0.88 on suicidal ideation, 0.78 on detecting a plan, and 0.91 on risk level. They improved with examples and fine-tuning. Humans still did better on ideation and mood.
  - Other 2025 audits found every model struggles with **indirect or implicit** signals.
- **Youth AI safety consensus (2025–26):**
  - Common Sense Media / Stanford: major chatbots are unsafe for teen mental-health support. The standard should be **rapid handoff to human care, not extended AI conversation**, and safeguards weaken in long chats.
  - Jed Foundation: detect acute distress, warm-hand-off to 988 or Crisis Text Line, publish youth-safety metrics, accept independent audits.

## 4. Nigeria specifically

I found no published intake triage standard for Nigerian child helplines.
- **Cece Yara:** 24-hour toll-free line (0800 800 8001) offering counselling, referral, and emergency intervention, plus child advocacy centres in Lagos and Abuja.
- **Mirabel Centre** (LASUTH, Ikeja): Nigeria's first sexual-assault referral centre, doing forensic exams.
- **Lagos DSVA:** the state's domestic and sexual violence agency, a structured framework.
- **Police Family Support Units:** handle domestic violence, sexual assault and child abuse cases.

Investigative reporting (TheCable / Pulitzer, 2025) documents **police extorting families of abused children** in Lagos. Any "alert the authorities" design for Nigeria has to route through trusted partners (Cece Yara, Mirabel, DSVA), not straight to police. I couldn't confirm a mandatory-reporting duty in the Child Rights Act text; verify with the statute or a lawyer.

## 5. What this means for SafeLine

**Why the current system has to go:**
- It is a ~50-word keyword list in disguise, which is exactly what Crisis Text Line abandoned.
- It merges suicide, abuse and danger into one number.
- Its "100% recall" was measured on cases written alongside the rules. On 10 realistic sentences it hadn't seen, it caught 0 of 10.

**What a gold-standard-shaped replacement looks like (proposal, not yet built):**

1. **Ask, through the voice agent, in plain child language,** and record answers with a tool rather than inferring from the transcript:
   - **Safety right now** (first, like 988 phase 1): "Are you safe right now? Is the person who hurt you near you?" and "Are you hurt and need a doctor?"
   - **Suicide/self-harm** (ASQ-style, only when distress signals appear, or always if Naomi wants the 988 approach of asking everyone): wish to be dead / thoughts of killing yourself → "right now?"
   - **Abuse** (SDM-style): is it still happening; does that person live with you or can reach you; is there a grown-up who knows and is keeping you safe.
2. **Output = a response priority, not a score:**
   - **Act now:** attempt in progress, attacker present or injury needing care, or "yes, right now" to suicide.
   - **Same day / 24 hours:** ongoing abuse with the abuser having access and no protective adult, a fearful child, or under-2 injury.
   - **Follow-up:** past or contained abuse with a protective adult.
   - **Support and referral:** no disclosure.

   Each level has a fixed action: emergency number + warm transfer, caseworker alert, case queue, or resources.
3. **A human confirms every alert.** The caseworker sees the answers, not a black-box number. Overrides and emergency escalations get logged and reviewed (988 Section 5).
4. **Track the handoff:** confirm the caseworker actually received and acted on the alert (988 Section 8). That is where Childline failed.
5. **Least invasive, with the child's consent where possible.** For Nigeria, route through Cece Yara, Mirabel or DSVA, not police.
6. **If a model is used, it only prioritises.** It ranks the caseworker's queue, trained and evaluated on held-out cases labelled by a safeguarding professional. It is judged on missed high-priority cases and their wait time, broken down by language (English, Pidgin) and age.
7. **Pitch honesty:** drop "100% recall" until a held-out, professionally labelled evaluation exists.

**Open decisions for Naomi:**
- Ask every caller about suicide (988's approach) or only on distress signals?
- Who is the human caseworker for the demo, and for real deployment in Nigeria?
- Which partner receives Nigerian escalations?

## Sources

- [988 Lifeline Suicide Safety Policy 2024 — Supplemental Guide](https://988lifeline.org/wp-content/uploads/2026/04/Lifeline-Suicide-Safety-Policy-2024-Supplemental-Guide.pdf) · [Policy](https://988lifeline.org/wp-content/uploads/2024/09/988-Suicide-and-Crisis-Lifeline-Suicide-Safety-Policy-2024.pdf)
- [Joiner et al. 2007, Establishing standards for the assessment of suicide risk among callers to the NSPL](https://988lifeline.org/wp-content/uploads/2016/09/Joiner-et-al-2007.pdf)
- [Draper et al., Helping callers to the Lifeline who are at imminent risk (PMC4491352)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4491352)
- [CBS News: Will 988 call the police? Data suggests rarely](https://www.cbsnews.com/news/will-988-call-the-police-data-suggests-rarely)
- [NIMH ASQ screening tool](https://www.nimh.nih.gov/sites/default/files/documents/research/research-conducted-at-nimh/asq-toolkit-materials/asq-tool/screening_tool_asq_nimh_toolkit_1.pdf) · [NIMH validation news](https://www.nimh.nih.gov/news/science-updates/2013/emergency-department-suicide-screening-tool-accurately-predicts-at-risk-youth)
- [C-SSRS Screener with triage points (2026)](https://cssrs.columbia.edu/wp-content/uploads/C-SSRS-Screener-with-triage-points-2026.pdf)
- [Evident Change / California SDM Hotline Tools](https://docs.evidentchange.org/Pages/California/Content/General/CA_SDM%20Hotline%20Tools.pdf) · [Oregon screening & response time manual](https://www.oregon.gov/oha/HSD/BH-Child-Family/SOCAC/OR%20Screening%20and%20Response%20Time%20PP%20Manual%20(8).pdf)
- [Childhelp Hotline — How it works](https://www.childhelphotline.org/how-it-works/)
- [Childline legal / confidentiality](https://www.childline.org.uk/legal/) · [NSPCC failed to report high-risk contacts (LocalGov, 2026)](https://www.localgov.co.uk/NSPCC-admits-failing-to-report-high-risk-child-contacts-to-councils/64555) · [NSPCC: young people in crisis](https://www.corra.scot/wp-content/uploads/2023/06/Young-people-in-crisis-how-we-support-them_NSPCC.pdf)
- [Kids Help Phone crisis responder Q&A](https://kidshelpphone.ca/get-info/text-support-qa-with-a-black-crisis-responder/) · [Globe and Mail on KHP active rescues](https://www.theglobeandmail.com/amp/canada/article-how-kids-help-phone-counsellors-aid-teens-with-gut-wrenching-problems/)
- [WHO: Responding to children and adolescents who have been sexually abused (2017)](https://www.who.int/publications/i/item/9789241550147) · [WHO clinical handbook 2022](https://abuseincare.org.nz/assets/Evidence-library/Part-4/World-Health-Organisation-Responding-to-child-maltreatment-a-clinical-handbook-for-health-professionals-2022.pdf)
- [Child Helpline International quality standards](https://childhelplineinternational.org/standards-for-child-helplines/) · [Africa best-practice guidelines 2026](https://childhelplineinternational.org/wp-content/uploads/2026/02/Best-Practice-Guidelines-Final-Report-ENG.pdf)
- [Crisis Text Line: Embracing AI to save lives](https://www.crisistextline.org/blog/2017/07/19/embracing-ai-to-save-lives/) · [Detecting crisis: an AI solution](https://www.crisistextline.org/product/detecting-crisis-an-ai-solution/)
- [The Trevor Project on TensorFlow](https://blog.tensorflow.org/2020/12/how-trevor-project-assesses-lgbtq-youth-suicide-risk-with-tensorflow.html) · [Google blog](https://blog.google/outreach-initiatives/google-org/trevor-project)
- [Allegheny Family Screening Tool coverage (MuckRock)](https://www.muckrock.com/news/archives/2019/jul/10/algorithms-family-screening-Pennsylvania/) · [UMN CASCW 2025](https://cascw.umn.edu/cw360deg-spring-2025/how-child-welfare-workers-reduce-racial-disparities-algorithmic-decisions)
- [PsyCrisisBench (arXiv 2506.01329)](https://arxiv.org/abs/2506.01329v2) · [Implicit suicidal ideation (arXiv 2502.17899)](https://www.alphaxiv.org/abs/2502.17899.md) · [Between Help and Harm (arXiv 2509.24857)](https://arxiv.org/abs/2509.24857v2)
- [Common Sense Media: AI chatbots unsafe for teen mental health](https://www.commonsensemedia.org/press-releases/common-sense-media-finds-major-ai-chatbots-unsafe-for-teen-mental-health-support) · [Jed Foundation open letter](https://jedfoundation.org/open-letter-to-the-ai-and-technology-industry/) · [AIES 2026: how child-safety experts evaluate chatbots](https://ojs.aaai.org/index.php/AIES/article/view/43168)
- [Cece Yara Child Helpline (CHI profile)](https://childhelplineinternational.org/nigeria-cece-yara-child-helpline/?amp=1) · [Guardian NG interview](https://guardian.ng/guardian-woman/we-have-provided-the-first-free-child-helpline-in-nigeria/) · [Mirabel Centre](https://rapeisacrime.org/portal/location-based-help-support/name/mirabel-centre) · [TheCable investigation on police extortion](https://www.thecable.ng/investigation-ii-in-lagos-police-extort-families-of-sexually-abused-children-in-search-of-justice) · [UK gov: Nigeria info for victims](https://www.gov.uk/government/publications/nigeria-information-for-victims-of-rape-and-sexual-assault/nigeria-information-for-victims-of-rape-and-sexual-assault)
