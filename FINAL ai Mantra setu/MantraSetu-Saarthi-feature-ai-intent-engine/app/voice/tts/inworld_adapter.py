"""InWorld AI Text-to-Speech (TTS) provider adapter — Phase 2a.

Implements ITTSProvider using the InWorld TTS v1 streaming HTTP API
(POST /tts/v1/voice:stream → NDJSON, each line: {"result": {"audioContent": "<base64>"}}).

Design decisions:
  - Model locked to inworld-tts-2-flash (~20ms InWorld-side TTFB).
  - Voice: INWORLD_VOICE_ID env var (defaults to "Aarav" — confirmed Hindi male, thoughtful
    conversational Indian accent; MantraSetu persona voice).
  - Audio: MP3 44100Hz to match the existing ElevenLabs output format the frontend expects.
  - Pacing: InWorld has no numeric speed parameter. We approximate the prior ElevenLabs
    speed=1.00 pacing via a natural-language style prefix (INWORLD_STYLE_HINT env var).
    Default is empty (no prefix) which produces Aarav's natural delivery. Override via env
    to tune without a code change.
  - NDJSON field path: result.audioContent (confirmed via live API inspection 2026-08-27).
  - All hardening from ElevenLabs adapter is preserved and annotated.

VAD/Guard compatibility:
  - confidence field not applicable to TTS — this adapter has no STT interaction.
  - STT remains on Groq; all VAD + noise + contamination guards are pipeline-level and
    completely unaffected by this TTS swap.

Future WebSocket streaming note:
  - If upgrading to InWorld Realtime API, set turn_detection: null to prevent InWorld VAD
    from overriding our RMS/ZCR system. See implementation_plan.md §5b.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from typing import AsyncGenerator

import httpx

from app.voice.tts.base import ITTSProvider
from app.voice.tts.schemas import (
    AudioChunk,
    VoiceProviderMetadata,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)

logger = logging.getLogger(__name__)

# ── InWorld TTS API constants ──────────────────────────────────────────────
_INWORLD_TTS_STREAM_URL = "https://api.inworld.ai/tts/v1/voice:stream"

# Chunk-level asyncio timeout (mirrors ElevenLabs 5.0s guard, hardening §TTS-8)
_CHUNK_TIMEOUT_SEC = 5.0

# Total stream timeout — prevents adapter from blocking indefinitely
_STREAM_TIMEOUT_SEC = 30.0


class InWorldTTSAdapter(ITTSProvider):
    """TTS adapter connecting to InWorld AI Text-to-Speech streaming API.

    Implements ITTSProvider with full hardening parity vs. ElevenLabsAdapter:
      - Active request tracking + cancellation (hardening §TTS-9)
      - Per-chunk asyncio timeout (hardening §TTS-8)
      - Final chunk signal on clean completion (hardening §TTS-10)
      - Error chunk signal on any exception (hardening §TTS-11)
      - Startup API key guard (hardening §TTS-4-equivalent)
      - Timing log [TIMING-TTS] for latency regression tracking (hardening §TTS-6)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        default_voice_id: str | None = None,
        style_hint: str | None = None,
    ) -> None:
        # §TTS-4: API key guard — fail clearly at construction, not at first request.
        # NOTE: Must read from env; no hardcoded fallback (code hygiene requirement).
        self._api_key: str = api_key or os.environ.get("INWORLD_API_KEY", "")
        if not self._api_key:
            logger.error(
                "[INWORLD-TTS] INWORLD_API_KEY is not set. All TTS requests will fail. "
                "Set INWORLD_API_KEY in your environment or .env file."
            )

        self._model: str = (
            model
            or os.environ.get("INWORLD_TTS_MODEL", "inworld-tts-2-flash")
        )
        # Aarav: "A thoughtful adult male with an Indian accent speaking earnestly."
        # Confirmed Hindi voice, matches MantraSetu persona "Arav".
        self._default_voice_id: str = (
            default_voice_id
            or os.environ.get("INWORLD_VOICE_ID", "Aarav")
        )
        # §PACING: InWorld has no numeric speed parameter. A natural-language style
        # prefix can steer pacing. INWORLD_STYLE_HINT="Speak at a warm, measured pace."
        # Default empty = Aarav's natural delivery (tested: already conversational).
        self._style_hint: str = (
            style_hint
            or os.environ.get("INWORLD_STYLE_HINT", "")
        )
        self._speed: float = float(os.environ.get("INWORLD_SPEED", "1.00"))
        # §TTS-9: Active request set for cancellation support
        self._active_requests: set[str] = set()

    @property
    def provider_name(self) -> str:
        return "inworld"

    def _build_request_text(self, text: str) -> str:
        """Prepend style hint if configured, for pacing/tone steering."""
        if self._style_hint:
            return f"{self._style_hint} {text}"
        return text

    def _build_auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }

    def _resolve_voice_id(self, requested_voice: str) -> str:
        """Resolve logical voice aliases to InWorld voice IDs.

        Logical aliases used elsewhere in the pipeline (meera, pandit, default,
        saarthi) are mapped to the configured InWorld voice (Aarav).
        Any explicit InWorld voiceId passes through unchanged.
        """
        _LOGICAL_ALIASES = {"meera", "pandit", "default", "saarthi", "arav", "aarav"}
        if not requested_voice or requested_voice.lower() in _LOGICAL_ALIASES:
            return self._default_voice_id
        return requested_voice

    async def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        """Return streaming-only metadata stub (mirrors ElevenLabs pattern)."""
        logger.info(
            "[INWORLD-TTS] synthesize called (streaming-only — use stream())",
            extra={"request_id": str(request.request_id), "text_len": len(request.text)},
        )
        return VoiceSynthesisResult(
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            audio_data=None,
            completed=True,
            chunk_count=1,
            duration_seconds=0.0,
            metadata=VoiceProviderMetadata(
                provider=self.provider_name,
                model=self._model,
                voice=self._resolve_voice_id(request.voice),
                sample_rate=request.sample_rate,
                extra={"status": "streaming_only"},
            ),
        )

    async def stream(self, request: VoiceSynthesisRequest) -> AsyncGenerator[AudioChunk, None]:
        """Stream synthesized audio chunks from InWorld TTS v1 NDJSON endpoint.

        Each NDJSON line has the form: {"result": {"audioContent": "<base64>"}}
        Confirmed via live API inspection 2026-08-27.
        """
        req_id_str = str(request.request_id)

        # §TTS-4: Early exit if no API key
        if not self._api_key:
            logger.error("[INWORLD-TTS] Cannot stream: INWORLD_API_KEY not configured.")
            yield AudioChunk(
                request_id=request.request_id,
                session_id=request.session_id,
                conversation_id=request.conversation_id,
                sequence_number=0,
                data=b"",
                is_final=True,
                timestamp_ms=int(time.time() * 1000),
                metadata={"status": "error_api_key_missing", "provider": self.provider_name},
            )
            return

        # §TTS-9: Register active request
        self._active_requests.add(req_id_str)
        logger.info(
            "[INWORLD-TTS] Stream started",
            extra={"request_id": req_id_str, "text": request.text[:80]},
        )

        voice_id = self._resolve_voice_id(request.voice)
        synthesize_text = self._build_request_text(request.text)

        payload = {
            "text": synthesize_text,
            "voiceId": voice_id,
            "modelId": self._model,
            # MP3 44100Hz matches existing ElevenLabs output format expected by frontend.
            # Configurable via INWORLD_AUDIO_ENCODING / INWORLD_SAMPLE_RATE if needed.
            "audioConfig": {
                "audioEncoding": os.environ.get("INWORLD_AUDIO_ENCODING", "MP3"),
                "sampleRateHertz": int(os.environ.get("INWORLD_SAMPLE_RATE", "44100")),
                "speakingRate": self._speed,
            },
        }

        # §TTS-6: Latency timing — mirrors [TIMING-STT] log pattern
        stream_start_ts = time.perf_counter()
        first_chunk_ts: float | None = None
        sequence_number = 0
        received_any_audio = False

        timeout_config = httpx.Timeout(
            connect=5.0,
            read=_STREAM_TIMEOUT_SEC,
            write=5.0,
            pool=5.0,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                async with client.stream(
                    "POST",
                    _INWORLD_TTS_STREAM_URL,
                    headers=self._build_auth_header(),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            "[INWORLD-TTS] HTTP error from InWorld TTS: status=%d body=%s",
                            response.status_code,
                            body[:300].decode(errors="replace"),
                        )
                        if req_id_str in self._active_requests:
                            yield AudioChunk(
                                request_id=request.request_id,
                                session_id=request.session_id,
                                conversation_id=request.conversation_id,
                                sequence_number=sequence_number,
                                data=b"",
                                is_final=True,
                                timestamp_ms=int(time.time() * 1000),
                                metadata={
                                    "status": "error_http",
                                    "provider": self.provider_name,
                                    "http_status": str(response.status_code),
                                },
                            )
                        return

                    # §TTS-8: Per-line asyncio timeout (5s) — prevents hang on stalled streams
                    line_iterator = response.aiter_lines().__aiter__()
                    while True:
                        # §TTS-9: Cancellation check before each chunk
                        if req_id_str not in self._active_requests:
                            logger.info("[INWORLD-TTS] Stream cancelled mid-flight: req_id=%s", req_id_str)
                            break

                        try:
                            line = await asyncio.wait_for(
                                line_iterator.__anext__(),
                                timeout=_CHUNK_TIMEOUT_SEC,
                            )
                            if req_id_str not in self._active_requests:
                                logger.info("[INWORLD-TTS] Stream cancelled mid-flight: req_id=%s", req_id_str)
                                break
                        except StopAsyncIteration:
                            break
                        except asyncio.TimeoutError:
                            logger.warning(
                                "[INWORLD-TTS] Chunk timeout (%.1fs) — aborting stream: req_id=%s",
                                _CHUNK_TIMEOUT_SEC,
                                req_id_str,
                            )
                            break

                        line = line.strip()
                        if not line:
                            continue

                        # NDJSON parse — field path: result.audioContent (confirmed)
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            logger.debug("[INWORLD-TTS] Skipping non-JSON line: %s", line[:60])
                            continue

                        audio_b64: str = obj.get("result", {}).get("audioContent", "")
                        if not audio_b64:
                            # Line may contain metadata/error — log and continue
                            error_field = obj.get("error") or obj.get("status") or ""
                            if error_field:
                                logger.warning("[INWORLD-TTS] InWorld error in stream: %s", error_field)
                            continue

                        # Decode base64 audio chunk
                        try:
                            chunk_bytes = base64.b64decode(audio_b64)
                        except Exception as decode_err:
                            logger.warning("[INWORLD-TTS] base64 decode failed: %s", decode_err)
                            continue

                        if not chunk_bytes:
                            continue

                        # §TTS-6: Record first-chunk timing
                        if first_chunk_ts is None:
                            first_chunk_ts = time.perf_counter()
                            ttfb_ms = int((first_chunk_ts - stream_start_ts) * 1000)
                            logger.info(
                                "[TIMING-TTS] InWorld TTS first chunk: req_id=%s ttfb_ms=%d voice=%s model=%s",
                                req_id_str,
                                ttfb_ms,
                                voice_id,
                                self._model,
                            )

                        received_any_audio = True
                        yield AudioChunk(
                            request_id=request.request_id,
                            session_id=request.session_id,
                            conversation_id=request.conversation_id,
                            sequence_number=sequence_number,
                            data=chunk_bytes,
                            is_final=False,
                            timestamp_ms=int(time.time() * 1000),
                            metadata={"provider": self.provider_name},
                        )
                        sequence_number += 1

            # §TTS-6: Total stream timing log
            total_ms = int((time.perf_counter() - stream_start_ts) * 1000)
            if not received_any_audio:
                logger.warning(
                    "[INWORLD-TTS] WARNING: InWorld TTS returned 200 OK but ZERO audio chunks were received "
                    "for req_id=%s (total_ms=%d). User will hear silence. "
                    "This may indicate an InWorld API degradation (same pattern as STT empty-response incident 2026-08-28).",
                    req_id_str,
                    total_ms,
                )
            logger.info(
                "[TIMING-TTS] InWorld TTS stream complete: req_id=%s total_ms=%d chunks=%d received_audio=%s",
                req_id_str,
                total_ms,
                sequence_number,
                received_any_audio,
            )

            # §TTS-10: Final chunk signal — always emit after clean stream end
            if req_id_str in self._active_requests:
                yield AudioChunk(
                    request_id=request.request_id,
                    session_id=request.session_id,
                    conversation_id=request.conversation_id,
                    sequence_number=sequence_number,
                    data=b"",
                    is_final=True,
                    timestamp_ms=int(time.time() * 1000),
                    metadata={
                        "provider": self.provider_name,
                        "status": "complete",
                        "total_chunks": str(sequence_number),
                        "total_ms": str(total_ms),
                    },
                )

        except Exception as exc:
            total_ms = int((time.perf_counter() - stream_start_ts) * 1000)
            logger.error(
                "[INWORLD-TTS] Streaming failed or timed out after %dms: req_id=%s error=%s",
                total_ms,
                req_id_str,
                exc,
            )
            # §TTS-11: Error chunk signal — ensures pipeline never hangs waiting for final
            if req_id_str in self._active_requests:
                yield AudioChunk(
                    request_id=request.request_id,
                    session_id=request.session_id,
                    conversation_id=request.conversation_id,
                    sequence_number=sequence_number,
                    data=b"",
                    is_final=True,
                    timestamp_ms=int(time.time() * 1000),
                    metadata={"status": "error", "provider": self.provider_name},
                )

        finally:
            # §TTS-9: Always clean up active request set
            self._active_requests.discard(req_id_str)

    async def cancel(self, request_id: str) -> None:
        """Cancel an active InWorld TTS stream by request ID."""
        logger.info("[INWORLD-TTS] Request cancelled: request_id=%s", request_id)
        self._active_requests.discard(request_id)
