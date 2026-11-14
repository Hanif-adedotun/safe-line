"""Caller voice ID with ReDimNet2+ (lab260/redimnet2-plus).

What it does, per phone call:
- Listens to the caller's side of the line (never Ayo's voice).
- If this phone number already has a registered voice, it checks the first
  ~8 seconds of the caller's speech against it: "recognised" or "not recognised".
- If not, it registers the voice. Children say little per call (median about 6 s
  of speech on Sabi's line), so registration builds up across calls: every 6 s of
  speech adds a sample, and the voice counts as registered at 15 s / 3 samples.

It never blocks the conversation and never ends a call. If the model is missing,
there is no caller ID, or the caller says too little, the call carries on as normal.

Measured on 8 kHz phone audio (Nov 14 2026, small sample - recalibrate as data grows):
- 15 synthetic voices + one real adult: same voice >= 0.80, different voice <= 0.54.
- Real Sabi calls: returning callers with 8+ s of speech scored 0.91-0.97 against
  their voiceprint; different callers scored median 0.10 (one outlier at 0.75).
- Real callers' own 6 s samples agree only at 0.44-0.72, hence the 0.40 consistency
  bar and the "unsure" band between 0.55 and 0.70.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import numpy as np

logger = logging.getLogger("safeline.voice_id")

THRESHOLD = float(os.getenv("VOICE_ID_THRESHOLD", "0.70"))
# Between REJECT and THRESHOLD the honest answer is "unsure".
REJECT_BELOW = float(os.getenv("VOICE_ID_REJECT_BELOW", "0.55"))
# A new sample must look like the voice already being registered, so a second
# person on a shared phone does not get mixed into someone else's voiceprint.
CONSISTENCY = float(os.getenv("VOICE_ID_CONSISTENCY", "0.40"))
SAMPLE_SECONDS = 6.0
REGISTER_SECONDS = 15.0  # ~15 s already separated every test voice perfectly
REGISTER_SAMPLES = 3
VERIFY_SECONDS = 8.0
MIN_VERIFY_SECONDS = 4.0
PHONE_RATE = 8000
MODEL_REPO = "lab260/redimnet2-plus"
MODEL_FILE = "pytorch_model_fsdp.bin"
MODEL_NAME = "redimnet2-plus-lmft"

_VENDOR = Path(__file__).resolve().parents[2] / "third_party" / "redimnet2plus"
_DB_PATH = Path(__file__).resolve().parents[2] / "safeline.db"

_model = None
_model_error: Optional[str] = None
_model_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
def _load_model():
    global _model, _model_error
    with _model_lock:
        if _model is not None or _model_error is not None:
            return _model
        try:
            import torch
            from huggingface_hub import hf_hub_download

            if str(_VENDOR) not in sys.path:
                sys.path.insert(0, str(_VENDOR))
            from asv.models.redimnet2 import ReDimNet2Encoder

            # return_2d_output=True matches the released checkpoint's shapes
            # (the model card's example says False, which does not load).
            enc = ReDimNet2Encoder(
                model_name="b6",
                pretrained=False,
                model_overrides={"out_channels": 224, "return_2d_output": True},
            )
            state = torch.load(hf_hub_download(MODEL_REPO, MODEL_FILE), map_location="cpu")
            state = {k.replace("_orig_mod.", "").replace("module.", ""): v for k, v in state.items()}
            state = {k[len("encoder."):]: v for k, v in state.items() if k.startswith("encoder.")}
            enc.load_state_dict(state, strict=True)
            enc.eval()
            _model = enc
            logger.info("Voice ID model loaded (%s)", MODEL_NAME)
        except Exception as exc:  # never take the line down over voice ID
            _model_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Voice ID unavailable: %s", _model_error)
        return _model


def preload_in_background() -> None:
    """Load the model at startup so the first caller does not wait for it."""
    threading.Thread(target=_load_model, name="voice-id-load", daemon=True).start()


def model_status() -> dict[str, Any]:
    return {
        "model": MODEL_NAME,
        "loaded": _model is not None,
        "error": _model_error,
        "threshold": THRESHOLD,
        "reject_below": REJECT_BELOW,
    }


def embed_phone_audio(pcm8k: bytes) -> Optional[np.ndarray]:
    """8 kHz 16-bit mono PCM -> L2-normalised 192-dim voiceprint (blocking)."""
    model = _load_model()
    if model is None or len(pcm8k) < PHONE_RATE * 2:
        return None
    import torch
    from scipy.signal import resample_poly

    samples = np.frombuffer(pcm8k[: len(pcm8k) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
    wav16 = resample_poly(samples, 2, 1).astype(np.float32)  # model expects 16 kHz
    with torch.inference_mode():
        emb = model(model.spec_frontend(torch.from_numpy(wav16).unsqueeze(0)))
        emb = torch.nn.functional.normalize(emb, dim=1)
    return emb[0].cpu().numpy().astype(np.float32)


# --------------------------------------------------------------------------- #
# Storage: one row per phone number, in the same SQLite file as cases
# --------------------------------------------------------------------------- #
def normalise_phone(number: Optional[str]) -> Optional[str]:
    """Return a usable caller ID, or None for withheld/blank numbers."""
    n = (number or "").strip()
    if not n or n.lower() in {"anonymous", "restricted", "unknown", "blocked", "unavailable", "private"}:
        return None
    digits = "".join(ch for ch in n if ch.isdigit())
    if len(digits) < 7 or digits in {"266696687", "86282452253", "8656696"}:  # keypad spellings of ANONYMOUS/UNAVAILABLE/UNKNOWN
        return None
    return ("+" if n.startswith("+") else "") + digits


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS voiceprints (
            phone TEXT PRIMARY KEY,
            status TEXT NOT NULL,              -- 'registering' | 'registered'
            vector_sum TEXT NOT NULL,          -- JSON list: sum of sample voiceprints
            samples INTEGER NOT NULL,
            seconds REAL NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    return conn


@dataclass
class Voiceprint:
    phone: str
    status: str
    vector: np.ndarray  # normalised mean
    vector_sum: np.ndarray
    samples: int
    seconds: float
    created_at: str


def get_voiceprint(phone: str) -> Optional[Voiceprint]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM voiceprints WHERE phone = ?", (phone,)).fetchone()
    if not row or row["model"] != MODEL_NAME:
        return None
    s = np.asarray(json.loads(row["vector_sum"]), dtype=np.float32)
    return Voiceprint(row["phone"], row["status"], s / (np.linalg.norm(s) or 1.0), s, row["samples"], row["seconds"], row["created_at"])


def add_sample(phone: str, emb: np.ndarray, seconds: float) -> tuple[str, Optional[float]]:
    """Add one speech sample towards registering this phone's voice.

    Returns (status, similarity_to_existing). Status is 'registering',
    'registered' (just completed), or 'inconsistent' (rejected: sounded like a
    different person from the samples so far).
    """
    vp = get_voiceprint(phone)
    now = _now()
    if vp and vp.status == "registered":
        return "registered", None
    sim = float(vp.vector @ emb) if vp and vp.samples else None
    if sim is not None and sim < CONSISTENCY:
        return "inconsistent", sim
    s = (vp.vector_sum if vp else np.zeros_like(emb)) + emb
    samples = (vp.samples if vp else 0) + 1
    secs = (vp.seconds if vp else 0.0) + seconds
    status = "registered" if (secs >= REGISTER_SECONDS and samples >= REGISTER_SAMPLES) else "registering"
    with _conn() as conn:
        conn.execute(
            """INSERT INTO voiceprints (phone,status,vector_sum,samples,seconds,model,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(phone) DO UPDATE SET status=excluded.status, vector_sum=excluded.vector_sum,
               samples=excluded.samples, seconds=excluded.seconds, model=excluded.model, updated_at=excluded.updated_at""",
            (phone, status, json.dumps([round(float(x), 6) for x in s]), samples, secs, MODEL_NAME,
             vp.created_at if vp else now, now),
        )
    return status, sim


def list_voiceprints() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT phone,status,samples,seconds,created_at,updated_at FROM voiceprints ORDER BY updated_at DESC").fetchall()
    return [
        {**dict(r), "phone": mask_phone(r["phone"]), "seconds": round(r["seconds"], 1)}
        for r in rows
    ]


def delete_voiceprint(phone: str) -> bool:
    p = normalise_phone(phone)
    if not p:
        return False
    with _conn() as conn:
        return conn.execute("DELETE FROM voiceprints WHERE phone = ?", (p,)).rowcount > 0


def mask_phone(phone: str) -> str:
    return f"…{phone[-4:]}" if phone else "unknown"


# --------------------------------------------------------------------------- #
# Per-call listener
# --------------------------------------------------------------------------- #
ResultHandler = Callable[[dict[str, Any]], Awaitable[None]]


class CallVoiceID:
    """Collects the caller's speech during one call and recognises or registers it."""

    FRAME = 160 * 2  # 20 ms of 8 kHz 16-bit PCM
    MIN_RMS = 350.0  # below this a 20 ms frame is treated as silence/line noise

    def __init__(self, phone: Optional[str], on_result: Optional[ResultHandler] = None):
        self.phone = normalise_phone(phone)
        self.on_result = on_result
        self._pending = bytearray()
        self._speech = bytearray()   # voiced audio not yet used
        self._verified = False
        self._registered_before = False
        self._busy = False
        self._tasks: set[asyncio.Task] = set()
        self.result: dict[str, Any] = {"status": "listening"}
        if not self.phone:
            self.result = {"status": "no_caller_id"}
        else:
            vp = get_voiceprint(self.phone)
            self._registered_before = bool(vp and vp.status == "registered")
            if vp:
                self.result = {"status": vp.status if vp.status == "registering" else "listening",
                               "registered_seconds": round(vp.seconds, 1)}

    @property
    def active(self) -> bool:
        return self.phone is not None and _model_error is None

    def feed(self, pcm8k: bytes) -> None:
        """Called for every inbound audio chunk. Cheap; heavy work runs in a thread."""
        if not self.active or (self._registered_before and self._verified):
            return  # nothing left to do on this call
        self._pending.extend(pcm8k)
        while len(self._pending) >= self.FRAME:
            frame = bytes(self._pending[: self.FRAME])
            del self._pending[: self.FRAME]
            x = np.frombuffer(frame, dtype="<i2").astype(np.float32)
            if float(np.sqrt(np.mean(x * x))) >= self.MIN_RMS:
                self._speech.extend(frame)
        need = VERIFY_SECONDS if (self._registered_before and not self._verified) else SAMPLE_SECONDS
        if not self._busy and len(self._speech) >= need * PHONE_RATE * 2:
            take = bytes(self._speech[: int(need * PHONE_RATE * 2)])
            del self._speech[: int(need * PHONE_RATE * 2)]
            self._spawn(self._process(take))

    async def finish(self, timeout: float = 8.0) -> dict[str, Any]:
        """At hang-up: wait for running checks, then use whatever speech is left."""
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)
        if self.active:
            sample = int(SAMPLE_SECONDS * PHONE_RATE * 2)
            if not self._registered_before:
                while len(self._speech) >= sample and not self._registered_before:
                    chunk = bytes(self._speech[:sample]); del self._speech[:sample]
                    await asyncio.wait_for(self._process(chunk), timeout=timeout)
                # Callers say little: a shorter final sample still counts.
                if not self._registered_before and len(self._speech) >= MIN_VERIFY_SECONDS * PHONE_RATE * 2:
                    chunk = bytes(self._speech); self._speech.clear()
                    await asyncio.wait_for(self._process(chunk), timeout=timeout)
            if self._registered_before and not self._verified and len(self._speech) >= MIN_VERIFY_SECONDS * PHONE_RATE * 2:
                chunk = bytes(self._speech[: int(VERIFY_SECONDS * PHONE_RATE * 2)])
                await asyncio.wait_for(self._process(chunk), timeout=timeout)
            self._speech.clear()
        if self.result.get("status") in ("listening", "registering") and self.phone and "at" not in self.result:
            self.result = {**self.result, "status": "too_little_speech"}
        return self.result

    def _spawn(self, coro) -> None:
        self._busy = True
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _process(self, pcm: bytes) -> None:
        try:
            seconds = len(pcm) / (PHONE_RATE * 2)
            emb = await asyncio.to_thread(embed_phone_audio, pcm)
            if emb is None:
                return
            if self._registered_before and not self._verified:
                vp = await asyncio.to_thread(get_voiceprint, self.phone)
                score = float(vp.vector @ emb) if vp else None
                self._verified = True
                ok = score is not None and score >= THRESHOLD
                # A low score from a few seconds of speech is not evidence of a
                # different person; only call it "not recognised" with enough audio.
                status = ("recognised" if ok else
                          "not_recognised" if (score is not None and score < REJECT_BELOW and seconds >= VERIFY_SECONDS) else
                          "unsure")
                await self._emit({
                    "status": status,
                    "seconds_checked": round(seconds, 1),
                    "score": round(score, 3) if score is not None else None,
                    "threshold": THRESHOLD,
                    "registered_seconds": round(vp.seconds, 1) if vp else None,
                    "registered_at": vp.created_at if vp else None,
                })
            elif not self._registered_before:
                status, sim = await asyncio.to_thread(add_sample, self.phone, emb, seconds)
                vp = await asyncio.to_thread(get_voiceprint, self.phone)
                await self._emit({
                    "status": "registered" if status == "registered" else status,
                    "registered_seconds": round(vp.seconds, 1) if vp else 0.0,
                    "needed_seconds": REGISTER_SECONDS,
                    "sample_similarity": round(sim, 3) if sim is not None else None,
                })
                if status == "registered":
                    self._registered_before = True
                    self._verified = True  # registered on this call; nothing to check against yet
        except Exception:
            logger.exception("Voice ID processing failed")
        finally:
            self._busy = False

    async def _emit(self, result: dict[str, Any]) -> None:
        self.result = {**result, "phone": mask_phone(self.phone or ""), "at": _now()}
        logger.info("Voice ID %s: %s", mask_phone(self.phone or ""), self.result)
        if self.on_result:
            try:
                await self.on_result(self.result)
            except Exception:
                logger.exception("Voice ID result handler failed")
