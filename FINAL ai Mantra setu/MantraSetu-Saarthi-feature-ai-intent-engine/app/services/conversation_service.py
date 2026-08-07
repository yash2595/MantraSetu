"""Conversation Orchestration Service module.

Main service coordinating SpeechToText, AI Generation, and TextToSpeech services.
"""

import logging
import time

from app.core.exceptions import InternalServerError
from app.llm.models import LLMRequest, LLMResponse
from app.services.ai_service import AIService
from app.services.base import BaseService
from app.services.speech_to_text_service import SpeechToTextService
from app.services.text_to_speech_service import TextToSpeechService
from app.speech.models import (
    SpeechToTextRequest,
    SpeechToTextResponse,
    VoiceChatRequest,
    VoiceChatResponse,
)
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse

logger = logging.getLogger(__name__)

MS_PER_SECOND: float = 1000.0


class ConversationService(BaseService):
    """Main orchestration service delegating to speech, AI, and TTS services."""

    def __init__(
        self,
        speech_service: SpeechToTextService,
        ai_service: AIService,
        tts_service: TextToSpeechService,
    ) -> None:
        """Initialize ConversationService with injected service dependencies.

        Args:
            speech_service: Injected SpeechToTextService instance.
            ai_service: Injected AIService instance.
            tts_service: Injected TextToSpeechService instance.
        """
        self._speech_service = speech_service
        self._ai_service = ai_service
        self._tts_service = tts_service

    async def speech_to_text(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Delegate speech transcription request to the SpeechToTextService.

        Args:
            request: Standardized SpeechToTextRequest model.

        Returns:
            SpeechToTextResponse: Standardized transcript output response model.
        """
        return await self._speech_service.transcribe(request)

    async def generate_response(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Delegate text response generation request to the AIService.

        Args:
            request: Standardized LLMRequest model.

        Returns:
            LLMResponse: Standardized AI completion response model.
        """
        return await self._ai_service.generate(request)

    async def text_to_speech(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        """Delegate speech synthesis request to the TextToSpeechService.

        Args:
            request: Standardized TextToSpeechRequest model.

        Returns:
            TextToSpeechResponse: Standardized audio output response model.
        """
        return await self._tts_service.synthesize(request)

    async def process_voice_chat(
        self,
        request: VoiceChatRequest,
    ) -> VoiceChatResponse:
        """Process an end-to-end voice conversation pipeline.

        Orchestrates: Audio/Prompt -> STT -> LLM -> TTS -> Audio/Text output with latency tracking.

        Args:
            request: VoiceChatRequest containing prompt or audio_bytes.

        Returns:
            VoiceChatResponse: Standardized response containing transcript, assistant_text, audio, and latencies.

        Raises:
            ValueError: If neither prompt nor audio_bytes is provided.
        """
        if request is None:
            raise ValueError("VoiceChatRequest cannot be None.")

        if not request.prompt and not request.audio_bytes:
            raise ValueError(
                "VoiceChatRequest must contain either a text prompt or audio_bytes payload."
            )

        start_total = time.perf_counter()
        stt_latency_ms = 0.0
        llm_latency_ms = 0.0
        tts_latency_ms = 0.0

        user_text = ""
        transcription = ""

        # 1. Speech-to-Text Phase (if audio_bytes provided)
        if request.audio_bytes:
            logger.info("Voice pipeline started [mode=voice]")
            start_stt = time.perf_counter()
            stt_request = SpeechToTextRequest(
                audio_bytes=request.audio_bytes,
                language=request.language,
            )
            stt_response = await self.speech_to_text(stt_request)
            stt_latency_ms = (time.perf_counter() - start_stt) * MS_PER_SECOND
            transcription = stt_response.transcript
            user_text = transcription
        else:
            logger.info("Voice pipeline started [mode=text]")
            user_text = request.prompt.strip() if request.prompt else ""

        # 2. AI Response Generation Phase
        start_llm = time.perf_counter()
        llm_request = LLMRequest(prompt=user_text)
        llm_response = await self.generate_response(llm_request)
        llm_latency_ms = (time.perf_counter() - start_llm) * MS_PER_SECOND
        assistant_text = llm_response.content

        # 3. Text-to-Speech Synthesis Phase
        audio_bytes = b""
        audio_format = "mp3"
        sample_rate = 24000

        if assistant_text:
            start_tts = time.perf_counter()
            try:
                tts_request = TextToSpeechRequest(
                    text=assistant_text,
                    language=request.language,
                    voice=request.voice,
                )
                tts_response = await self.text_to_speech(tts_request)
                audio_bytes = tts_response.audio_bytes
                audio_format = tts_response.format
                sample_rate = tts_response.sample_rate
                tts_latency_ms = (time.perf_counter() - start_tts) * MS_PER_SECOND
            except InternalServerError as exc:
                if exc.error_code == "TTS_KEY_MISSING":
                    logger.warning(
                        "TTS synthesis skipped during pipeline execution: TTS_API_KEY unconfigured."
                    )
                    tts_latency_ms = (time.perf_counter() - start_tts) * MS_PER_SECOND
                else:
                    raise exc

        total_latency_ms = (time.perf_counter() - start_total) * MS_PER_SECOND

        logger.info(
            "Voice conversation pipeline completed [stt=%.2fms, llm=%.2fms, tts=%.2fms, total=%.2fms]",
            stt_latency_ms,
            llm_latency_ms,
            tts_latency_ms,
            total_latency_ms,
        )

        return VoiceChatResponse(
            transcription=transcription,
            assistant_text=assistant_text,
            audio_bytes=audio_bytes,
            audio_format=audio_format,
            sample_rate=sample_rate,
            total_latency_ms=total_latency_ms,
            stt_latency_ms=stt_latency_ms,
            llm_latency_ms=llm_latency_ms,
            tts_latency_ms=tts_latency_ms,
        )

    async def health_check(self) -> bool:
        """Check operational health across all underlying services.

        Returns:
            bool: True if speech, AI, and TTS services are healthy, False otherwise.
        """
        try:
            speech_healthy = await self._speech_service.health_check()
        except Exception as exc:
            logger.warning("SpeechService health check failed: %s", exc)
            speech_healthy = False

        try:
            ai_status = await self._ai_service.health_check()
            ai_healthy = (
                getattr(ai_status, "healthy", bool(ai_status))
                if ai_status is not None
                else False
            )
        except Exception as exc:
            logger.warning("AIService health check failed: %s", exc)
            ai_healthy = False

        try:
            tts_status = await self._tts_service.health_check()
            tts_healthy = (
                getattr(tts_status, "healthy", bool(tts_status))
                if tts_status is not None
                else False
            )
        except Exception as exc:
            logger.warning("TTSService health check failed: %s", exc)
            tts_healthy = False

        return bool(speech_healthy and ai_healthy and tts_healthy)


    async def close(self) -> None:
        """Gracefully release all underlying service resources."""
        await self._speech_service.close()
        await self._ai_service.close()
        await self._tts_service.close()
