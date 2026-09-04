"""InWorld Speech-to-Text provider adapter implementation."""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import time
import wave

import httpx

from app.voice.audio_buffer import AudioBuffer
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.vocab import STT_CUSTOM_VOCABULARY

logger = logging.getLogger(__name__)


class InWorldSTTAdapter(ISpeechRecognizer):
    """Speech-to-Text adapter connecting to InWorld STT API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("INWORLD_API_KEY", "")
        if not self._api_key:
            raise ValueError("INWORLD_API_KEY environment variable is missing")
        self._model = model or os.environ.get("INWORLD_STT_MODEL", "inworld/inworld-stt-1")
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return or lazily initialize shared persistent httpx.AsyncClient with connection pooling."""
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=30.0)
            timeout = httpx.Timeout(25.0, connect=5.0)
            self._client = httpx.AsyncClient(limits=limits, timeout=timeout)
        return self._client

    async def aclose(self) -> None:
        """Close shared HTTP client connection pool on teardown."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def provider_name(self) -> str:
        return "inworld"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info(
            "InWorld STT session initialized",
            extra={"session_id": session.session_id, "model": self._model},
        )

    async def stream_audio(self, session: VoiceSession, chunk: bytes) -> TranscriptChunk | None:
        if not chunk:
            return None
        return TranscriptChunk(
            session_id=session.session_id,
            text="",
            is_final=False,
            confidence=0.0,
            timestamp_ms=int(time.time() * 1000),
        )

    async def finish_session(self, session: VoiceSession, buffer: AudioBuffer) -> TranscriptResult:
        request_id = session.context_data.get("voice_turn_request_id", session.session_id)
        logger.info(
            "InWorld STT finish_session called",
            extra={"session_id": session.session_id, "size_bytes": buffer.size},
        )

        sample_rate = session.sample_rate or 16000
        duration_sec = round(buffer.size / (sample_rate * 2), 2) if sample_rate else 0.0

        try:
            # Convert raw PCM16 to WAV in memory
            raw_pcm = buffer.flush()
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(raw_pcm)

            wav_data = wav_io.getvalue()

            # Short-audio gate (<6000 bytes raw wave ~ 0.18s)
            if len(wav_data) < 6000:
                logger.warning(
                    "[INWORLD-STT] Audio too short (%d bytes < 6000), skipping processing",
                    len(wav_data),
                )
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={"model": self._model, "status": "skipped"},
                )

            if not self._api_key:
                logger.warning("[INWORLD-STT] INWORLD_API_KEY is missing or empty")
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={"model": self._model, "status": "error", "error": "api_key_missing", "confidence_available": False},
                )

            stt_start_time = time.time()
            text = ""
            # Inworld's documented synchronous transcription schema has no
            # transcript-confidence field. Keep this unavailable unless a future
            # provider response actually supplies a numeric value.
            stt_confidence = 0.0
            confidence_available = False

            import httpx
            
            lang_code = "hi-IN"
            
            audio_b64 = base64.b64encode(wav_data).decode('utf-8')
            payload = {
                "transcribeConfig": {
                    "modelId": self._model,
                    "audioEncoding": "LINEAR16",
                    "language": lang_code,
                    "sampleRateHertz": 16000,
                    "numberOfChannels": 1
                },
                "audioData": {
                    "content": audio_b64
                }
            }

            client = self._get_client()
            headers = {
                "Authorization": f"Basic {self._api_key}",
                "Content-Type": "application/json",
            }
            
            try:
                # Retry transient 5xx / timeout once before failing
                max_attempts = 2
                last_error: Exception | None = None
                response = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        response = await client.post(
                            'https://api.inworld.ai/stt/v1/transcribe',
                            headers=headers,
                            json=payload,
                            timeout=25.0
                        )
                        response_body = response.text
                        logger.info(
                            "[DIAG-INVESTIGATION][STT] request_id=%s session_id=%s provider=inworld attempt=%d http_status=%d pcm_bytes=%d response_body=%r",
                            request_id, session.session_id, attempt, response.status_code, len(raw_pcm), response_body[:2048]
                        )
                        if response.status_code >= 500 and attempt < max_attempts:
                            logger.warning(
                                "[INWORLD-STT-RETRY] Transient HTTP %d from Inworld STT. Retrying once (attempt %d/%d)...",
                                response.status_code, attempt, max_attempts
                            )
                            await asyncio.sleep(0.3)
                            continue

                        response.raise_for_status()
                        last_error = None
                        break
                    except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                        last_error = net_err
                        if attempt < max_attempts:
                            logger.warning(
                                "[INWORLD-STT-RETRY] Network/Timeout error (%s). Retrying once (attempt %d/%d)...",
                                net_err, attempt, max_attempts
                            )
                            await asyncio.sleep(0.3)
                            continue
                        raise net_err
                    except httpx.HTTPStatusError as status_err:
                        last_error = status_err
                        raise status_err

                if last_error is not None:
                    raise last_error

                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"[INWORLD-STT-ERROR] JSON Parse Error. Status: {response.status_code}, Response body: {response.text}")
                    raise e
                
                transcription = data.get("transcription", {})
                text = data.get("text", "") or data.get("transcript", "") or transcription.get("transcript", "")
                candidate_confidence = transcription.get("confidence", data.get("confidence"))
                if isinstance(candidate_confidence, (int, float)) and 0.0 <= float(candidate_confidence) <= 1.0:
                    stt_confidence = float(candidate_confidence)
                    confidence_available = True
            except httpx.HTTPStatusError as http_err:
                status_code = http_err.response.status_code
                error_category = "client_error" if 400 <= status_code < 500 else "provider_error"
                body = http_err.response.text[:500] if http_err.response is not None else ''
                logger.error(
                    "[DIAG-INVESTIGATION][STT] request_id=%s session_id=%s provider=inworld status=error category=%s http_status=%d error=%s body=%r",
                    request_id, session.session_id, error_category, status_code, http_err, body
                )
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={
                        "model": self._model,
                        "status": "error",
                        "error_type": error_category,
                        "http_status": status_code,
                        "error": f"HTTP {status_code}: {http_err}",
                        "confidence_available": False,
                    },
                )
            except (httpx.TimeoutException, asyncio.TimeoutError) as timeout_err:
                logger.error(
                    "[DIAG-INVESTIGATION][STT] request_id=%s session_id=%s provider=inworld status=error category=timeout error=%s",
                    request_id, session.session_id, timeout_err
                )
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={
                        "model": self._model,
                        "status": "error",
                        "error_type": "timeout",
                        "error": "STT request timed out after retries",
                        "confidence_available": False,
                    },
                )
            except Exception as e:
                body = response.text[:500] if 'response' in locals() and response is not None else ''
                logger.error(f"[DIAG-INVESTIGATION][STT] request_id={request_id} session_id={session.session_id} provider=inworld status=error error={type(e).__name__}:{e} body={body!r}")
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={
                        "model": self._model,
                        "status": "error",
                        "error_type": "unknown_error",
                        "error": f"{type(e).__name__}: {e}",
                        "confidence_available": False,
                    },
                )

            stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
            logger.info(
                f"[TIMING-STT] InWorld STT ({self._model}) completed in {stt_elapsed_ms}ms | Transcribed: '{text}'"
            )
            logger.info("[DIAG-INVESTIGATION][STT] request_id=%s session_id=%s provider=inworld transcript_length=%d confidence=%.3f confidence_available=%s", request_id, session.session_id, len(text.strip()), stt_confidence, confidence_available)

            # Hallucination Filter: Reject repetitive garbled Whisper tokens
            clean_text = text.strip()
            if clean_text:
                words = clean_text.split()
                if len(words) >= 6 and len(set(words)) <= 2:
                    logger.warning(
                        f"[INWORLD-STT-HALLUCINATION-FILTER] Rejected repetitive garbled transcript: '{clean_text}'"
                    )
                    clean_text = ""

            if not clean_text:
                stt_confidence = 0.0
                confidence_available = False

            return TranscriptResult(
                text=clean_text,
                confidence=stt_confidence,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={
                    "model": self._model,
                    "status": "success" if clean_text else "empty",
                    "latency_ms": stt_elapsed_ms,
                    "confidence_available": confidence_available,
                },
            )

        except asyncio.TimeoutError:
            logger.error("[INWORLD-STT-TIMEOUT] InWorld STT API timed out after 10.0s")
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={"model": self._model, "status": "error", "error": "timeout", "confidence_available": False},
            )
        except Exception as e:
            logger.error(f"[INWORLD-STT-ERROR] InWorld STT failed: {e}", exc_info=True)
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={"model": self._model, "status": "error", "error": str(e), "confidence_available": False},
            )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("InWorld STT session cancelled", extra={"session_id": session.session_id})
