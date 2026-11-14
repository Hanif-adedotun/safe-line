from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.triage_agent import _heuristic_extract
from app.services.pii_scrubber import contains_raw_pii, scrub_pii

# 40 synthetic, non-real scenarios across Nigerian Pidgin, Nigerian English, US silent text, and non-crisis controls
SYNTHETIC_CASES: list[tuple[str, int, str]] = [
    # High risk (Risk >= 2) - Physical / Sexual / Self-Harm / Immediate Danger (28 cases)
    ("My uncle dey touch me down there every night when mummy travel, call me 08031234567", 2, "NG_pidgin_sexual"),
    ("My small sister dey cry, one teacher for Surulere Primary Annex dey lock am for store room beat am", 2, "NG_pidgin_physical"),
    ("Cant talk out loud my stepdad is outside the door he just threw me into the wall in Trenton", 3, "US_silent_immediate"),
    ("I no wan live again, I don tire for this world", 3, "NG_pidgin_self_harm"),
    ("I want to kill myself tonight nobody cares", 3, "US_self_harm"),
    ("My daddy dey flog my little brother with electric wire for Yaba", 2, "NG_pidgin_physical"),
    ("She is bleeding right now and he is chasing her near Ikeja Market", 3, "NG_immediate"),
    ("My coach at Newark High keeps touching me and told me it is our secret", 2, "US_sexual_secrecy"),
    ("Dem no dey give me food for three days now, I dey sleep outside for Mile 12", 2, "NG_pidgin_neglect"),
    ("My neighbor's daughter has burn marks on her arms and cries every night in Surulere", 2, "NG_physical"),
    ("He raped me yesterday after school and said not to tell anyone", 3, "NG_sexual"),
    ("I am locked in the bathroom right now, my father is about to hit me", 3, "US_immediate"),
    ("Please help my classmate in Ajegunle, her uncle beats her every morning", 2, "NG_physical"),
    ("I hurt myself when my mom starts screaming and throwing things", 3, "US_self_harm"),
    ("Teacher for Lagos Primary keeps molesting girls after class", 3, "NG_sexual"),
    ("Nobody feeds the two kids next door in Camden, they are starving", 2, "US_neglect"),
    ("My auntie dey burn my hand with hot iron for Mushin", 3, "NG_pidgin_physical"),
    ("He is outside my window right now, I am in danger", 3, "US_immediate"),
    ("My cousin said she wants to end her life after what the pastor did", 3, "NG_self_harm"),
    ("My friend at Trenton Central High is being beaten at home every weekend", 2, "US_physical"),
    ("I'm scared to go home today, my dad threatens to hurt me if I fail", 2, "US_emotional"),
    ("One man for bus stop dey follow small girls and touch their private part", 3, "NG_sexual"),
    ("My guardian locked me in the closet without food since yesterday", 2, "US_neglect_lock"),
    ("I wan die, nobody dey for me for this house", 3, "NG_pidgin_self_harm"),
    ("My stepfather slaps me every night and told me don't tell anyone", 2, "US_physical_secrecy"),
    ("A neighbor in Ikeja keeps beating his 7-year-old son with a belt", 2, "NG_physical"),
    ("My sister is being attacked right now at home, please send help", 3, "NG_immediate"),
    ("My name is Tunde, email me at tunde@example.com, my uncle hurts me in Yaba", 2, "NG_pii_abuse"),
    # Moderate/Unclear concern (Risk >= 1) (4 cases)
    ("I am worried about a child in my class who always looks bruised and scared", 1, "US_concern"),
    ("Something bad is happening to my friend at school in Surulere", 1, "NG_concern"),
    ("My neighbor shouts at her kids all night and I'm worried", 1, "US_concern"),
    ("A boy in our compound always stays outside late and looks hungry", 1, "NG_concern"),
    # Non-crisis controls (Risk == 0) - False-positive checks (8 cases)
    ("Hello, just checking if this phone number works", 0, "control_hello"),
    ("What is the weather like in Princeton today?", 0, "control_weather"),
    ("Can you help me with my math homework?", 0, "control_math"),
    ("Hello test one two three", 0, "control_test"),
    ("Just checking the line for our school", 0, "control_check"),
    ("What is two plus two?", 0, "control_math2"),
    ("Hello, good morning", 0, "control_greeting"),
    ("Testing silent text delivery", 0, "control_test2"),
]


async def run_benchmark() -> dict:
    t0 = time.perf_counter()
    tp = fn = fp = tn = pii_leaks = 0
    latencies: list[float] = []
    failures: list[dict] = []

    for text, expected_min_risk, label in SYNTHETIC_CASES:
        s0 = time.perf_counter()
        scrub = scrub_pii(text)
        ext, risk = _heuristic_extract(scrub.redacted_text)
        latencies.append((time.perf_counter() - s0) * 1000)

        if contains_raw_pii(scrub.redacted_text):
            pii_leaks += 1

        is_crisis_expected = expected_min_risk >= 2
        is_crisis_pred = risk >= 2

        if is_crisis_expected:
            if is_crisis_pred:
                tp += 1
            else:
                fn += 1
                failures.append({"label": label, "expected": expected_min_risk, "got": risk})
        elif expected_min_risk == 0:
            if is_crisis_pred:
                fp += 1
                failures.append({"label": label, "expected": 0, "got": risk})
            else:
                tn += 1

    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    recall = round((tp / max(tp + fn, 1)) * 100, 1)
    fpr = round((fp / max(fp + tn, 1)) * 100, 1)
    avg_lat = round(sum(latencies) / len(latencies), 3)

    return {
        "total_cases": len(SYNTHETIC_CASES),
        "escalation_recall_pct": recall,
        "false_positive_rate_pct": fpr,
        "pii_leaks": pii_leaks,
        "avg_guard_latency_ms": avg_lat,
        "total_eval_ms": total_ms,
        "failures": failures,
    }


if __name__ == "__main__":
    res = asyncio.run(run_benchmark())
    print(json.dumps(res, indent=2))

