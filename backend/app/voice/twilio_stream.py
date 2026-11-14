"""Twilio Media Streams WebSocket handler.

Handles full-duplex streaming audio between a Twilio phone call and Gemini Live.
- Twilio sends: 8kHz mu-law audio frames (base64 encoded)
- Server decodes: mu-law -> 8kHz PCM16 -> Gemini Live
- Gemini Live yields: 24kHz PCM16 audio
- Server downsamples: 24kHz -> 8kHz PCM16 -> mu-law -> base64 -> Twilio
- Interruption handling: sends {"event": "clear"} to flush Twilio playback buffer.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Optional, Callable, Awaitable

from fastapi import WebSocket, WebSocketDisconnect

from app.voice.audio import (
    mulaw_to_pcm16,
    pcm16_to_mulaw,
    Downsample24kTo8k,
    FrameChunker,
)
from app.voice.gemini_live import GeminiLiveSession, LiveConfig

logger = logging.getLogger("safeline.voice.twilio")


class TwilioMediaBridge:
    def __init__(
        self,
        websocket: WebSocket,
        system_prompt: str,
        voice_name: str = "Puck",
        on_turn_complete: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ):
        self.ws = websocket
        self.system_prompt = system_prompt
        self.voice_name = voice_name
        self.on_turn_complete = on_turn_complete

        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.gemini_session: Optional[GeminiLiveSession] = None
        self.resampler = Downsample24kTo8k()
        self.chunker = FrameChunker(frame_bytes=160)  # 20ms of 8kHz mu-law = 160 bytes
        self._running = False
        self._outbound_queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def run(self):
        self._running = True
        logger.info("Starting Twilio Media Bridge...")

        cfg = LiveConfig(
            system_prompt=self.system_prompt,
            voice=self.voice_name,
            input_rate=8000,
        )

        # Create Gemini Live session
        self.gemini_session = GeminiLiveSession(
            cfg,
            on_audio=self._on_gemini_audio_chunk,
            on_interrupted=self._on_interrupted,
            on_turn_complete=self._on_turn_complete,
        )

        try:
            await self.gemini_session.connect()
            logger.info("Connected to Gemini Live successfully!")
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live: {e}")
            await self.ws.close()
            return

        gemini_loop_task = asyncio.create_task(self.gemini_session.receive_forever())
        sender_task = asyncio.create_task(self._outbound_sender())

        try:
            while self._running:
                raw_text = await self.ws.receive_text()
                data = json.loads(raw_text)
                event = data.get("event")

                if event == "connected":
                    logger.info("Twilio connected event received")

                elif event == "start":
                    start_data = data.get("start", {})
                    self.stream_sid = start_data.get("streamSid")
                    self.call_sid = start_data.get("callSid")
                    logger.info(f"Twilio stream started: stream_sid={self.stream_sid} call_sid={self.call_sid}")

                elif event == "media":
                    media_payload = data.get("media", {}).get("payload")
                    if media_payload and self.gemini_session:
                        # 1. Base64 decode Twilio mu-law
                        mulaw_bytes = base64.b64decode(media_payload)
                        # 2. Decode mu-law to 8kHz PCM16
                        pcm16_bytes = mulaw_to_pcm16(mulaw_bytes)
                        # 3. Stream to Gemini Live
                        await self.gemini_session.send_audio(pcm16_bytes)

                elif event == "stop":
                    logger.info("Twilio call stopped event received")
                    break

        except WebSocketDisconnect:
            logger.info("Twilio WebSocket disconnected")
        except Exception as e:
            logger.error(f"Twilio bridge loop error: {e}", exc_info=True)
        finally:
            self._running = False
            if self.gemini_session:
                await self.gemini_session.close()
            gemini_loop_task.cancel()
            sender_task.cancel()
            logger.info("Twilio Media Bridge closed.")

    def _on_gemini_audio_chunk(self, pcm24k_chunk: bytes):
        """Called synchronously when Gemini Live receives a 24kHz audio chunk."""
        if not self._running:
            return
        pcm8k = self.resampler.resample(pcm24k_chunk)
        if not pcm8k:
            return
        mulaw = pcm16_to_mulaw(pcm8k)
        frames = self.chunker.add_samples(mulaw)
        for frame in frames:
            self._outbound_queue.put_nowait(frame)

    async def _outbound_sender(self):
        """Pumps 20ms audio frames downstream to Twilio."""
        while self._running:
            frame = await self._outbound_queue.get()
            if not self.stream_sid:
                continue
            b64_audio = base64.b64encode(frame).decode("utf-8")
            media_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": b64_audio,
                },
            }
            try:
                await self.ws.send_text(json.dumps(media_message))
            except Exception:
                break

    async def _on_interrupted(self):
        """Twilio user barged in: clear downstream playback buffer immediately."""
        # Empty local outbound queue
        while not self._outbound_queue.empty():
            try:
                self._outbound_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        if self.stream_sid:
            logger.info("Barge-in: clearing Twilio audio buffer")
            clear_message = {
                "event": "clear",
                "streamSid": self.stream_sid,
            }
            try:
                await self.ws.send_text(json.dumps(clear_message))
            except Exception:
                pass

    async def _on_turn_complete(self, user_text: str, model_text: str):
        logger.info(f"[CALLER]: {user_text}")
        logger.info(f"[SAFE-LINE]: {model_text}")
        if self.on_turn_complete:
            await self.on_turn_complete(user_text, model_text)
