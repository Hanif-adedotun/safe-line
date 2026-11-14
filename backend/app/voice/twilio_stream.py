"""Twilio Media Streams WebSocket handler.

Handles full-duplex streaming audio between a Twilio phone call and Gemini Live.
- Twilio sends: 8kHz mu-law audio frames (base64 encoded)
- Server decodes: mu-law -> 8kHz PCM16 -> Gemini Live
- Gemini Live yields: 24kHz PCM16 audio
- Server downsamples: 24kHz -> 8kHz PCM16 -> mu-law -> base64 -> Twilio
- Interruption handling: sends {"event": "clear"} to flush Twilio playback buffer.

Location: the voice webhook passes Twilio's caller geo data as <Parameter>
elements, which arrive here in `start.customParameters`. Gemini is only opened
after that event so the location briefing is in the system prompt from the
first word, and the live case exists before the caller says anything.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Awaitable, Callable, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.services import live_location
from app.voice.audio import Downsample24kTo8k, FrameChunker, mulaw_to_pcm16, pcm16_to_mulaw
from app.voice.caller_location import CallerLocation, build_location_briefing
from app.voice.gemini_live import GeminiLiveSession, LiveConfig
from app.voice.voice_id import CallVoiceID
from app.services.case_store import get_case, save_case

logger = logging.getLogger("safeline.voice.twilio")

PUBLIC_BASE_PARAM = "sl_public_base"
RETURNING_CALLER_CUE = (
    "[SYSTEM NOTE, not spoken by the caller] Voice ID: this caller's voice matches someone who "
    "has called this line before. You may warmly say it is good to hear from them again. Do not "
    "mention voices, recordings or matching, and do not repeat anything from earlier calls unless "
    "they bring it up."
)
CALL_STARTED_CUE = (
    "[SYSTEM NOTE, not spoken by the caller] The call has just connected. Greet the caller "
    "now, following your opening instructions."
)


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
        self.caller_location: Optional[CallerLocation] = None
        self.case_id: Optional[str] = None
        self.gemini_session: Optional[GeminiLiveSession] = None
        self.resampler = Downsample24kTo8k()
        self.chunker = FrameChunker(frame_bytes=160)  # 20ms of 8kHz mu-law = 160 bytes
        self._running = False
        self._outbound_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self.voice_id: Optional[CallVoiceID] = None

    async def run(self):
        self._running = True
        try:
            while self._running:
                data = json.loads(await self.ws.receive_text())
                event = data.get("event")

                if event == "start":
                    if not await self._on_start(data.get("start") or {}):
                        break

                elif event == "media":
                    payload = (data.get("media") or {}).get("payload")
                    if payload and self.gemini_session:
                        pcm16 = mulaw_to_pcm16(base64.b64decode(payload))
                        await self.gemini_session.send_audio(pcm16)
                        if self.voice_id:
                            self.voice_id.feed(pcm16)

                elif event == "stop":
                    logger.info("Twilio call stopped")
                    break

        except WebSocketDisconnect:
            logger.info("Twilio WebSocket disconnected")
        except Exception as e:
            logger.error(f"Twilio bridge loop error: {e}", exc_info=True)
        finally:
            self._running = False
            if self.case_id:
                live_location.attach_injector(self.case_id, None)
            if self.voice_id:
                try:
                    await self._on_voice_id(await self.voice_id.finish())
                except Exception:
                    logger.exception("Voice ID finish failed")
            if self.gemini_session:
                await self.gemini_session.close()
            for task in self._tasks:
                task.cancel()
            logger.info("Twilio Media Bridge closed.")

    async def _on_start(self, start: dict) -> bool:
        self.stream_sid = start.get("streamSid")
        self.call_sid = start.get("callSid")
        params = start.get("customParameters") or {}
        self.caller_location = CallerLocation.from_custom_parameters(params)
        public_base = (params.get(PUBLIC_BASE_PARAM) or "").strip() or None
        logger.info(
            "Twilio stream started call_sid=%s location=%s (%s)",
            self.call_sid,
            self.caller_location.describe(),
            self.caller_location.source,
        )

        live_call = live_location.start_call(
            caller_location=self.caller_location,
            call_sid=self.call_sid,
            public_base_url=public_base,
        )
        self.case_id = live_call.case_id
        self.voice_id = CallVoiceID(self.caller_location.number, on_result=self._on_voice_id)

        case_id = self.case_id

        async def on_tool(name: str, args: dict) -> dict:
            return await live_location.handle_tool_call(case_id, name, args)

        cfg = LiveConfig(
            system_prompt=self.system_prompt + build_location_briefing(self.caller_location),
            voice=self.voice_name,
            input_rate=8000,
            tools=live_location.TOOL_DECLARATIONS,
        )
        self.gemini_session = GeminiLiveSession(
            cfg,
            on_audio=self._on_gemini_audio_chunk,
            on_interrupted=self._on_interrupted,
            on_turn_complete=self._on_turn_complete,
            on_tool_call=on_tool,
        )
        try:
            await self.gemini_session.connect()
        except Exception as e:
            logger.error("Failed to connect to Gemini Live: %s", e)
            self.gemini_session = None
            await self.ws.close()
            return False

        live_location.attach_injector(self.case_id, self.gemini_session.send_realtime_text)
        self._tasks.append(asyncio.create_task(self.gemini_session.receive_forever()))
        self._tasks.append(asyncio.create_task(self._outbound_sender()))
        # Gemini Live does not speak until it hears something; make it greet first.
        await self.gemini_session.send_realtime_text(CALL_STARTED_CUE)
        return True

    async def _on_voice_id(self, result: dict) -> None:
        """Save the voice ID result on the case; tell Ayo (quietly) about a returning caller."""
        if self.case_id:
            case = await asyncio.to_thread(get_case, self.case_id)
            if case:
                case.voice_id = result
                await asyncio.to_thread(save_case, case)
        if result.get("status") == "recognised" and self.gemini_session and self._running:
            try:
                await self.gemini_session.send_realtime_text(RETURNING_CALLER_CUE)
            except Exception:
                logger.warning("Could not tell Ayo about the returning caller")

    def _on_gemini_audio_chunk(self, pcm24k_chunk: bytes):
        """Called synchronously when Gemini Live receives a 24kHz audio chunk."""
        if not self._running:
            return
        pcm8k = self.resampler.resample(pcm24k_chunk)
        if not pcm8k:
            return
        for frame in self.chunker.add_samples(pcm16_to_mulaw(pcm8k)):
            self._outbound_queue.put_nowait(frame)

    async def _outbound_sender(self):
        """Pumps 20ms audio frames downstream to Twilio."""
        while self._running:
            frame = await self._outbound_queue.get()
            if not self.stream_sid:
                continue
            try:
                await self.ws.send_text(
                    json.dumps(
                        {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": base64.b64encode(frame).decode("utf-8")},
                        }
                    )
                )
            except Exception:
                break

    async def _on_interrupted(self):
        """Caller barged in: clear downstream playback buffer immediately."""
        while not self._outbound_queue.empty():
            try:
                self._outbound_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        if self.stream_sid:
            try:
                await self.ws.send_text(json.dumps({"event": "clear", "streamSid": self.stream_sid}))
            except Exception:
                pass

    async def _on_turn_complete(self, user_text: str, model_text: str):
        logger.info(f"[CALLER]: {user_text}")
        logger.info(f"[SAFE-LINE]: {model_text}")
        if self.on_turn_complete:
            await self.on_turn_complete(user_text, model_text)
