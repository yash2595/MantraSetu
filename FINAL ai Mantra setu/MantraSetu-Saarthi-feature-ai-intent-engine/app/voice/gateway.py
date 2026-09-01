"""Lightweight VoiceGateway coordinator integrating STT stream processing with AIOrchestrator."""

from __future__ import annotations

from dataclasses import replace
import logging
import time
from typing import Any
from uuid import UUID

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.orchestrator_models import OrchestratorRequest
from app.voice.audio_buffer import AudioBuffer
from app.voice.exceptions import InvalidAudioChunk, VoiceGatewayError
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession, VoiceSessionStatus
from app.voice.session_manager import VoiceSessionManager
from app.voice.stt.base import ISpeechRecognizer
from app.voice.transcript import TranscriptAggregator

logger = logging.getLogger(__name__)

# Keep server-side capture capacity aligned with the browser's long-answer
# window.  Free-text onboarding answers must not be finalised at 12 seconds.
MAX_VOICE_TURN_SECONDS = 20.0


class VoiceGateway:
    """Lightweight coordinator for voice streams, speech-to-text, and AIOrchestrator.

    Responsibilities:
        - Delegate session lifecycle to VoiceSessionManager.
        - Delegate audio chunk buffering to AudioBuffer.
        - Delegate speech recognition to ISpeechRecognizer.
        - Delegate transcript aggregation to TranscriptAggregator.
        - Normalize final transcript into InteractionRequest and invoke AIOrchestrator.process().
        - Maintain zero domain or business logic.
    """

    def __init__(
        self,
        ai_orchestrator: AIOrchestrator,
        session_manager: VoiceSessionManager,
        speech_recognizer: ISpeechRecognizer,
    ) -> None:
        if ai_orchestrator is None:
            raise ValueError("VoiceGateway requires a non-null AIOrchestrator instance.")
        if session_manager is None:
            raise ValueError("VoiceGateway requires a non-null VoiceSessionManager instance.")
        if speech_recognizer is None:
            raise ValueError("VoiceGateway requires a non-null ISpeechRecognizer instance.")

        self._ai_orchestrator = ai_orchestrator
        self._session_manager = session_manager
        self._speech_recognizer = speech_recognizer
        self._buffers: dict[str, AudioBuffer] = {}
        self._aggregators: dict[str, TranscriptAggregator] = {}
        self._vads: dict[str, Any] = {}
        self._cached_pujas = None
        self._fetching_pujas_task = None

    @property
    def session_manager(self) -> VoiceSessionManager:
        return self._session_manager

    @property
    def speech_recognizer(self) -> ISpeechRecognizer:
        return self._speech_recognizer

    async def _fetch_puja_list(self) -> None:
        try:
            import httpx
            import os
            backend_url = os.getenv("MAIN_BACKEND_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000"
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{backend_url}/puja/list")
                if resp.status_code == 200:
                    pujas = resp.json()
                    puja_names = [p.get("title") for p in pujas if p.get("title")]
                    self._cached_pujas = puja_names
                    logger.info(f"Successfully cached {len(puja_names)} pujas from main backend")
        except Exception as e:
            logger.warning(f"Could not fetch dynamic puja list in background: {e}")

    async def start_voice_session(
        self,
        connection_id: str,
        conversation_id: UUID | None = None,
        language: str = "hi",
        sample_rate: int = 16000,
        audio_encoding: Any = "pcm16",
        session_id: str | None = None,
    ) -> VoiceSession:
        """Initialize and register a new live voice streaming session."""
        session = await self._session_manager.create_session(
            connection_id=connection_id,
            conversation_id=conversation_id,
            language=language,
            sample_rate=sample_rate,
            audio_encoding=audio_encoding,
            session_id=session_id,
        )
        
        # Use cached puja names if available, and trigger non-blocking background fetch if empty
        import asyncio
        if self._cached_pujas is not None:
            session.context_data["pujas"] = self._cached_pujas
        else:
            session.context_data["pujas"] = []
            if not self._fetching_pujas_task or self._fetching_pujas_task.done():
                self._fetching_pujas_task = asyncio.create_task(self._fetch_puja_list())

        self._buffers[session.session_id] = AudioBuffer()
        self._aggregators[session.session_id] = TranscriptAggregator()
        from app.voice.vad import VoiceActivityDetector
        self._vads[session.session_id] = VoiceActivityDetector(min_speech_duration_sec=0.15, sample_rate=sample_rate, safety_cap_sec=MAX_VOICE_TURN_SECONDS)
        await self._speech_recognizer.start_session(session)
        return session

    async def process_audio_chunk(
        self,
        session_id: str,
        chunk: bytes,
    ) -> TranscriptChunk | None:
        """Ingest raw audio chunk, buffer, and process via speech recognizer."""
        session = await self._session_manager.get_session(session_id)
        if not session or session.status in (VoiceSessionStatus.CLOSED, VoiceSessionStatus.COMPLETED):
            raise InvalidAudioChunk(f"Voice session '{session_id}' is closed or invalid.")

        session.status = VoiceSessionStatus.STREAMING
        session.touch()

        if session_id not in self._buffers:
            self._buffers[session_id] = AudioBuffer()
        if session_id not in self._aggregators:
            self._aggregators[session_id] = TranscriptAggregator()
        if session_id not in self._vads:
            from app.voice.vad import VoiceActivityDetector
            self._vads[session_id] = VoiceActivityDetector(min_speech_duration_sec=0.15, sample_rate=session.sample_rate or 16000, safety_cap_sec=MAX_VOICE_TURN_SECONDS)

        buffer = self._buffers.get(session_id)
        if buffer:
            buffer.append(chunk)
            
        vad = self._vads.get(session_id)
        if vad:
            safety_cap_hit = vad.process_chunk(chunk)
            if safety_cap_hit:
                from app.voice.exceptions import SafetyCapExceededError
                logger.warning(f"[VAD-SAFETY] Session {session_id} exceeded max duration of {vad.safety_cap_sec}s! Raising exception to force finalization.")
                raise SafetyCapExceededError(f"Session {session_id} exceeded maximum allowed duration.")

        partial_chunk = await self._speech_recognizer.stream_audio(session, chunk)
        if partial_chunk and partial_chunk.text:
            aggregator = self._aggregators.get(session_id)
            if aggregator:
                aggregator.add_chunk(partial_chunk)

        return partial_chunk

    async def finish_voice_session(
        self,
        session_id: str,
        current_page: str | None = None,
        user_parameters: dict | None = None,
        request_id: str | None = None,
    ) -> tuple[Any, str]:
        """Finalize voice stream, generate final transcript, and invoke AIOrchestrator.process()."""
        session = await self._session_manager.get_session(session_id)
        if not session:
            raise VoiceGatewayError(f"Voice session '{session_id}' not found.")

        session.status = VoiceSessionStatus.PROCESSING
        session.touch()
        # A WebSocket session spans many turns; diagnostics must use the turn ID.
        turn_request_id = request_id or session_id
        session.context_data["voice_turn_request_id"] = turn_request_id

        buffer = self._buffers.pop(session_id, None) or AudioBuffer()
        self._aggregators.pop(session_id, None)

        # ── Pre-STT VAD Gate: Verify minimum 0.25s active human speech ──
        pre_flush_bytes = buffer.size
        raw_pcm_bytes = buffer.flush()
        logger.info(
            "[AUDIO-BUFFER] request_id=%s session_id=%s pre_flush_bytes=%d detached_from_live_buffer=true",
            turn_request_id, session_id, pre_flush_bytes,
        )
        vad = self._vads.pop(session_id, None)
        if not vad:
            from app.voice.vad import VoiceActivityDetector
            vad = VoiceActivityDetector(min_speech_duration_sec=0.15, sample_rate=session.sample_rate or 16000, safety_cap_sec=MAX_VOICE_TURN_SECONDS)
            vad.process_chunk(raw_pcm_bytes)
        
        vad_analysis = vad.get_analysis()
        vad_valid = bool(vad_analysis["is_valid_speech"])

        # ── [DIAG-INVESTIGATION] VAD Gate Decision ──
        logger.info(
            "[DIAG-INVESTIGATION][VAD] request_id=%s session_id=%s provider=%s pcm_bytes=%d | wav_would_be=%d | "
            "speech_dur=%.3fs | total_dur=%.3fs | min_required=0.15s | "
            "vad_valid=%s | reason=%s",
            turn_request_id,
            session_id,
            self._speech_recognizer.provider_name,
            len(raw_pcm_bytes),
            len(raw_pcm_bytes) + 44,   # WAV header is 44 bytes
            vad_analysis["speech_duration_sec"],
            vad_analysis["total_duration_sec"],
            vad_valid,
            vad_analysis["reason"],
        )

        if not vad_valid:
            logger.warning(
                "[VAD-GATE-DISCARD] Pre-STT VAD Gate rejected audio buffer for session %s (speech_duration=%.2fs, total=%.2fs, reason=%s). Discarding buffer without calling STT/LLM.",
                session.session_id, vad_analysis["speech_duration_sec"], vad_analysis["total_duration_sec"], vad_analysis["reason"]
            )
            from app.orchestrator.orchestrator_models import OrchestratorResponse, ResponseType
            current_field = None
            if hasattr(session, "onboarding_state") and session.onboarding_state:
                idx = session.onboarding_state.get("current_field_index", 0)
                fields = session.onboarding_state.get("fields", [])
                if idx < len(fields):
                    current_field = fields[idx]

            repeat_msg = "Kshama karein, main sun nahi paya. Kripya apna jawab dobara boliye."
            vad_discard_response = OrchestratorResponse(
                response_id=f"resp_vad_discard_{session_id[:8]}",
                request_id=turn_request_id,
                text=repeat_msg,
                response_type=ResponseType.CHAT,
                navigation_directive={
                    "action": None,
                    "target": None,
                    "query": None,
                    "active_field": current_field,
                    "intent": "REPEAT_PROMPT",
                    "recognition_status": "no_speech",
                    "vad_valid": vad_valid,
                }
            )
            buffer.clear()
            logger.info(
                "[AUDIO-BUFFER] request_id=%s session_id=%s post_flush_bytes=%d",
                turn_request_id, session_id, buffer.size,
            )
            return vad_discard_response, ""

        buffer_size_bytes = buffer.size
        session.context_data["client_active_field"] = user_parameters.get("active_field") if user_parameters else None
        stt_result = await self._speech_recognizer.finish_session(session, buffer)
        # This object was detached before STT.  Clearing it after the provider has
        # consumed it proves it cannot leak PCM into a later voice turn.
        buffer.clear()
        logger.info(
            "[AUDIO-BUFFER] request_id=%s session_id=%s post_flush_bytes=%d",
            turn_request_id, session_id, buffer.size,
        )
        logger.info(f"[DIAGNOSTIC] RAW STT TRANSCRIPT before LLM extraction: {stt_result.text!r}")

        final_text = (stt_result.text or "").strip()
        stt_status = stt_result.metadata.get("status", "success")
        recognition_status = "ok" if final_text else ("stt_error" if stt_status not in {"success", "empty", "skipped"} else "no_speech")
        stt_engine_model = stt_result.metadata.get("model", stt_result.provider)
        
        if "gemini" in stt_engine_model.lower():
            stt_tier_label = "Tier 1 (Gemini Audio API)"
        elif "google_web_speech" in stt_engine_model.lower():
            stt_tier_label = "Tier 2 (Google WebSpeech fallback)"
        else:
            stt_tier_label = f"Unknown ({stt_engine_model})"

        # ── Noise & Low Confidence Guard ──
        is_noise = False
        msg_lower = final_text.lower().strip()
        
        # 1. Strip standard noise/non-speech markers
        import re
        clean_marker = re.sub(r'<[^>]+>', '', msg_lower).strip()
        clean_marker = re.sub(r'\[[^\]]+\]', '', clean_marker).strip()
        clean_marker = re.sub(r'\([^\)]+\)', '', clean_marker).strip()
        
        # 2. Filler words check
        fillers = {
            "uh", "um", "ah", "eh", "oh", "hm", "hmm", "hmmm", "oops", "mhm", "uh-huh",
            "ummm", "ehh", "err", "uhh", "like", "actually", "basically"
        }
        words = [w.strip(".,?!;:") for w in clean_marker.split() if w.strip(".,?!;:")]
        remaining_words = [w for w in words if w not in fillers]
        
        # 3. Confidence threshold
        confidence_available = bool(stt_result.metadata.get("confidence_available", False))
        is_low_confidence = confidence_available and stt_result.confidence < 0.40

        # ── [DIAG-INVESTIGATION] Full STT gate breakdown ──
        logger.info(
            "[DIAG-INVESTIGATION][STT-GATE] request_id=%s session_id=%s | raw_transcript=%r | "
            "confidence=%.4f | confidence_available=%s | threshold=0.40 | is_low_conf=%s | "
            "tier=%s | model=%s | audio_dur=%.3fs | buffer_bytes=%d | "
            "words_after_filler_strip=%r | remaining_word_count=%d | "
            "clean_marker_empty=%s | noise_markers_removed=%s",
            turn_request_id,
            session.session_id,
            final_text,
            stt_result.confidence if stt_result.confidence is not None else -1.0,
            confidence_available,
            is_low_confidence,
            stt_tier_label,
            stt_engine_model,
            stt_result.duration_seconds,
            buffer_size_bytes,
            remaining_words,
            len(remaining_words),
            clean_marker == "",
            msg_lower != clean_marker,   # True means markers/brackets were stripped
        )
        # ── [DIAG-INVESTIGATION] Legacy alias kept for backward grep ──
        logger.info(
            "[STT-INVESTIGATION-LOG] Session: %s | Raw Transcript: %r | Exact Confidence: %.4f | STT Tier Used: %s | Model: %s | Audio Duration: %.2fs (Buffer: %d bytes) | Low Confidence (<0.40): %s | Remaining Words: %r",
            session.session_id,
            final_text,
            stt_result.confidence if stt_result.confidence is not None else -1.0,
            stt_tier_label,
            stt_engine_model,
            stt_result.duration_seconds,
            buffer_size_bytes,
            is_low_confidence,
            remaining_words
        )

        
        if not remaining_words or is_low_confidence or clean_marker == "":
            is_noise = True
            # ── [DIAG-INVESTIGATION] Log which exact sub-condition triggered noise gate ──
            logger.warning(
                "[DIAG-INVESTIGATION][NOISE-GATE] session=%s | IS_NOISE=True | "
                "trigger_no_remaining_words=%s | trigger_low_confidence=%s | trigger_empty_marker=%s | "
                "raw=%r | confidence=%.4f",
                session.session_id,
                not remaining_words,
                is_low_confidence,
                clean_marker == "",
                final_text,
                stt_result.confidence if stt_result.confidence is not None else -1.0,
            )
            
        current_field = None
        if hasattr(session, "onboarding_state") and session.onboarding_state:
            idx = session.onboarding_state.get("current_field_index", 0)
            fields = session.onboarding_state.get("fields", [])
            if idx < len(fields):
                current_field = fields[idx]
        
        is_name_field = current_field in ["pandit-first-name", "pandit-last-name", "pandit-name"]

        if is_noise:
            recognition_status = "low_confidence" if is_low_confidence else "no_speech"
            stt_fail_count = getattr(session, "stt_fail_count", 0) + 1
            session.stt_fail_count = stt_fail_count
            
            if is_name_field and hasattr(session, "onboarding_state") and session.onboarding_state:
                name_fails = session.onboarding_state.get("name_stt_fail_count", 0) + 1
                session.onboarding_state["name_stt_fail_count"] = name_fails

            from app.orchestrator.orchestrator_models import OrchestratorResponse, ResponseType

            if is_name_field and session.onboarding_state.get("name_stt_fail_count", 0) >= 2:
                logger.info(
                    "[STT-FALLBACK] STT failed 2+ times on name field (%s). Asking user to type name manually.",
                    current_field
                )
                repeat_msg = "Kripya apna naam type karein"
                repeat_response = OrchestratorResponse(
                    response_id=f"resp_type_name_{session_id[:8]}",
                    request_id=session_id,
                    text=repeat_msg,
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive={
                        "action": "FILL_FORM", 
                        "target": current_field or "pandit-first-name", 
                        "query": None,
                        "recognition_status": recognition_status,
                        "active_field": current_field or "pandit-first-name", 
                        "intent": "PANDIT_ONBOARDING"
                    }
                )
            elif stt_fail_count == 1:
                logger.info(
                    "[STT-GUARD] First STT noise/empty failure for session %s. Retrying ONCE silently without prompting user.",
                    session_id
                )
                repeat_response = OrchestratorResponse(
                    response_id=f"resp_silent_{session_id[:8]}",
                    request_id=session_id,
                    text="",  # Empty text stays silent!
                    response_type=ResponseType.CHAT,
                    navigation_directive={
                        "action": None, 
                        "target": None, 
                        "query": None, 
                        "active_field": current_field, 
                        "intent": "SILENT_RETRY"
                    }
                )
            elif stt_fail_count == 2:
                logger.info(
                    "[STT-GUARD] 2nd STT noise failure for session %s. Prompting user to repeat.", session_id
                )
                session.stt_fail_count = 0  # Reset counter
                repeat_msg = "Kshama karein, main sun nahi paya. Kripya apna jawab dobara boliye."
                repeat_response = OrchestratorResponse(
                    response_id=f"resp_repeat_{session_id[:8]}",
                    request_id=session_id,
                    text=repeat_msg,
                    response_type=ResponseType.CHAT,
                    navigation_directive={
                        "action": None, 
                        "target": None, 
                        "query": None, 
                        "active_field": current_field, 
                        "intent": "RETRY"
                    }
                )
            else:
                logger.info(
                    "[STT-GUARD] 3rd+ STT noise failure for session %s. Suggesting typing.", session_id
                )
                repeat_msg = "Kshama karein, lagta hai mic se aawaz nahi aa rahi. Kripya apna mic check karein, ya screen par apna jawab type kar dein."
                repeat_response = OrchestratorResponse(
                    response_id=f"resp_repeat_type_{session_id[:8]}",
                    request_id=session_id,
                    text=repeat_msg,
                    response_type=ResponseType.CHAT,
                    navigation_directive={
                        "action": None, 
                        "target": None, 
                        "query": None, 
                        "active_field": current_field, 
                        "intent": "REPEAT_PROMPT"
                    }
                )
            self._buffers.pop(session_id, None)
            self._aggregators.pop(session_id, None)
            self._vads.pop(session_id, None)
            updated_directive = dict(repeat_response.navigation_directive or {})
            updated_directive.update({
                "recognition_status": "low_confidence" if is_low_confidence else "no_speech",
                "transcript": final_text,
                "stt_provider": stt_result.provider,
                "stt_confidence": stt_result.confidence,
                "audio_bytes_received": buffer_size_bytes,
                "vad_valid": vad_valid,
                "stt_confidence_available": confidence_available,
            })
            repeat_response = replace(repeat_response, navigation_directive=updated_directive)
            logger.warning("[DIAG-INVESTIGATION][STT] request_id=%s session_id=%s provider=%s pcm_bytes=%d transcript_length=%d confidence=%.3f confidence_available=%s status=%s provider_error=%s", turn_request_id, session_id, stt_result.provider, buffer_size_bytes, len(final_text), stt_result.confidence or 0.0, confidence_available, repeat_response.navigation_directive["recognition_status"], stt_result.metadata.get("error"))
            return repeat_response, ""
        else:
            session.stt_fail_count = 0  # Reset fail count on clean transcript


        if is_name_field and hasattr(session, "onboarding_state") and session.onboarding_state:
            session.onboarding_state["name_stt_fail_count"] = 0


        if not final_text:
            logger.info("[STT-DIAGNOSTIC] Session %s | Empty transcript detected (silence/background noise). Suppressing AI response.", session.session_id)
            self._buffers.pop(session_id, None)
            self._aggregators.pop(session_id, None)
            self._vads.pop(session_id, None)
            await self._session_manager.close_session(session_id, status=VoiceSessionStatus.COMPLETED)
            
            from app.orchestrator.orchestrator_models import OrchestratorResponse, ResponseType
            empty_response = OrchestratorResponse(
                response_id=f"resp_empty_{session_id[:8]}",
                request_id=session_id,
                text="",
                response_type=ResponseType.CHAT
            )
            return empty_response, ""

        merged_user_params = {
            "transport": "voice_websocket",
            "connection_id": session.connection_id,
            "language": session.language,
            "stt_provider": stt_result.provider,
            "confidence": stt_result.confidence,
            "duration_seconds": stt_result.duration_seconds,
            "pujas": session.context_data.get("pujas", []),
        }
        if isinstance(user_parameters, dict):
            merged_user_params.update(user_parameters)

        # Create normalized OrchestratorRequest for AIOrchestrator (Module 1)
        interaction_request = OrchestratorRequest(
            conversation_id=session.conversation_id or "default_conv",
            session_id=session.session_id,
            user_message=final_text,
            current_page=current_page,  # Pass real page from frontend; orchestrator calls session.update_location()
            user_parameters=merged_user_params,
        )

        logger.info(
            "VoiceGateway forwarding final transcript to AIOrchestrator [page=%r]",
            current_page,
            extra={
                "session_id": session.session_id,
                "connection_id": session.connection_id,
                "final_transcript": final_text,
            },
        )

        # Delegate execution to frozen Module 1 AIOrchestrator
        response = await self._ai_orchestrator.process(interaction_request)
        # STT facts are transport metadata, deliberately independent of intent/action.
        updated_directive = dict(response.navigation_directive or {})
        updated_directive.update({
            "recognition_status": recognition_status,
            "transcript": final_text,
            "stt_provider": stt_result.provider,
            "stt_confidence": stt_result.confidence,
            "stt_confidence_available": confidence_available,
            "audio_bytes_received": buffer_size_bytes,
            "vad_valid": vad_valid,
        })
        response = replace(response, navigation_directive=updated_directive)
        logger.info(
            "[DIAG-INVESTIGATION][STT] request_id=%s session_id=%s provider=%s pcm_bytes=%d transcript_length=%d confidence=%.3f confidence_available=%s status=%s provider_error=%s",
            turn_request_id, session_id, stt_result.provider, buffer_size_bytes, len(final_text), stt_result.confidence or 0.0, confidence_available, recognition_status, stt_result.metadata.get("error"),
        )

        # Keep session alive for multi-turn voice interaction
        session.status = VoiceSessionStatus.CONNECTED
        if session_id not in self._buffers:
            self._buffers[session_id] = AudioBuffer()
        if session_id not in self._aggregators:
            self._aggregators[session_id] = TranscriptAggregator()
        if session_id not in self._vads:
            from app.voice.vad import VoiceActivityDetector
            self._vads[session_id] = VoiceActivityDetector(min_speech_duration_sec=0.15, sample_rate=session.sample_rate or 16000, safety_cap_sec=MAX_VOICE_TURN_SECONDS)

        return response, final_text

    async def cancel_voice_session(self, session_id: str) -> None:
        """Cancel an active voice session gracefully."""
        session = await self._session_manager.get_session(session_id)
        if session:
            await self._speech_recognizer.cancel_session(session)
            self._buffers.pop(session_id, None)
            self._aggregators.pop(session_id, None)
            self._vads.pop(session_id, None)
            await self._session_manager.close_session(session_id, status=VoiceSessionStatus.CANCELLED)
