"""Voice ID logic tests. A fake embedder stands in for ReDimNet2+, so these run fast and offline."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.voice import voice_id as V  # noqa: E402

LOUD = (np.ones(160, dtype="<i2") * 3000).tobytes()  # 20 ms of "speech"
QUIET = (np.zeros(160, dtype="<i2")).tobytes()        # 20 ms of silence


def unit(seed: int) -> np.ndarray:
    v = np.random.default_rng(seed).normal(size=192).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture()
def voices(tmp_path, monkeypatch):
    """Each 'speaker' gets a fixed voiceprint; the fake model returns it (plus a little noise)."""
    monkeypatch.setattr(V, "_DB_PATH", tmp_path / "voice.db")
    current = {"vec": unit(1)}

    calls = {"n": 0}

    def fake_embed(pcm: bytes):
        calls["n"] += 1  # small, independent noise per sample, like real recordings
        noise = np.random.default_rng(calls["n"]).normal(scale=0.01, size=192).astype(np.float32)
        v = current["vec"] + noise
        return v / np.linalg.norm(v)

    monkeypatch.setattr(V, "embed_phone_audio", fake_embed)
    monkeypatch.setattr(V, "_model_error", None)
    return current


def run_call(phone, seconds_of_speech: float, silence_seconds: float = 2.0):
    async def go():
        v = V.CallVoiceID(phone)
        for _ in range(int(silence_seconds * 50)):
            v.feed(QUIET)
        for _ in range(int(seconds_of_speech * 50)):
            v.feed(LOUD)
            await asyncio.sleep(0)
        return await v.finish(timeout=5)

    return asyncio.run(go())


def test_withheld_number_is_never_identified(voices):
    for number in ("anonymous", "266696687", "", None, "Restricted"):
        assert run_call(number, 20)["status"] == "no_caller_id"


def test_registers_then_recognises(voices):
    assert run_call("+2348011112222", 16)["status"] == "registered"
    r = run_call("+2348011112222", 9)
    assert r["status"] == "recognised" and r["score"] >= V.THRESHOLD


def test_registration_builds_up_across_short_calls(voices):
    assert run_call("+2348011113333", 6.5)["status"] == "registering"
    assert run_call("+2348011113333", 6.5)["status"] == "registering"
    assert run_call("+2348011113333", 6.5)["status"] == "registered"


def test_different_person_on_registered_number(voices):
    run_call("+2348011114444", 16)
    voices["vec"] = unit(2)  # someone else picks up the phone
    r = run_call("+2348011114444", 9)
    assert r["status"] == "not_recognised" and r["score"] < V.REJECT_BELOW


def test_short_check_is_unsure_not_a_false_rejection(voices):
    run_call("+2348011115555", 16)
    voices["vec"] = unit(3)
    assert run_call("+2348011115555", 5)["status"] == "unsure"


def test_second_voice_is_not_mixed_into_registration(voices):
    run_call("+2348011116666", 6.5)
    voices["vec"] = unit(4)
    assert run_call("+2348011116666", 6.5)["status"] == "inconsistent"
    assert V.get_voiceprint("+2348011116666").samples == 1


def test_forget_my_voice(voices):
    run_call("+2348011117777", 16)
    assert V.delete_voiceprint("+2348011117777") is True
    assert V.get_voiceprint("+2348011117777") is None
