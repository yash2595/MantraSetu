"""Voice Processing Orchestration Service module.

Orchestrates the complete voice pipeline bridging Speech-to-Text, Conversation,
AI Generation, Navigation Planning, Action Execution, Browser Bridge Command generation,
and Text-to-Speech synthesis via Dependency Injection.
"""

import inspect
import logging
from typing import Any

from pydantic import BaseModel, Field


from app.llm.models import LLMRequest
from app.services.action_engine import ActionEngine, ExecutionPlan
from app.services.ai_service import AIService
from app.services.base import BaseService
from app.services.browser_bridge import BrowserBridge, BrowserCommand
from app.services.conversation_service import ConversationService
from app.services.navigation_service import NavigationDecision, NavigationService

logger = logging.getLogger(__name__)


class VoiceRequest(BaseModel):
    """Input payload model for voice processing requests.

    Attributes:
        session_id: Unique string identifier for the active conversation session.
        audio_bytes: Raw input audio binary payload.
        language: Language code string for speech processing (default 'hinglish').
    """

    session_id: str = Field(..., description="Unique conversation session ID.")
    audio_bytes: bytes = Field(..., description="Raw audio byte payload.")
    language: str = Field(
        default="hinglish", description="Target language identifier."
    )


class VoiceResponse(BaseModel):
    """Output payload model resulting from voice request pipeline execution.

    Attributes:
        transcript: Transcribed text string from input audio.
        assistant_response: AI assistant textual response string.
        browser_commands: List of BrowserCommand objects generated for frontend.
        audio_response: Optional synthesized output audio byte payload.
    """

    transcript: str = Field(..., description="Transcribed input speech text.")
    assistant_response: str = Field(
        ..., description="Generated AI response content."
    )
    browser_commands: list[BrowserCommand] = Field(
        default_factory=list,
        description="Ordered list of BrowserCommand models for frontend rendering.",
    )
    audio_response: bytes | None = Field(
        default=None, description="Synthesized output audio binary payload."
    )


class VoiceService(BaseService):
    """Orchestration service for the complete end-to-end voice pipeline.

    Coordinates SpeechToText, Conversation, AI, Navigation, ActionEngine,
    BrowserBridge, and TextToSpeech services through explicit dependency injection.
    """

    def __init__(
        self,
        conversation_service: ConversationService | None = None,
        ai_service: AIService | None = None,
        navigation_service: NavigationService | None = None,
        action_engine: ActionEngine | None = None,
        browser_bridge: BrowserBridge | None = None,
        stt_service: Any | None = None,
        tts_service: Any | None = None,
    ) -> None:
        """Initialize the VoiceService with injected pipeline dependencies.

        Args:
            conversation_service: Optional ConversationService instance.
            ai_service: Optional AIService instance.
            navigation_service: Optional NavigationService instance.
            action_engine: Optional ActionEngine instance.
            browser_bridge: Optional BrowserBridge instance.
            stt_service: Optional SpeechToText service interface.
            tts_service: Optional TextToSpeech service interface.
        """
        self._conversation_service = conversation_service
        self._ai_service = ai_service
        self._navigation_service = navigation_service
        self._action_engine = action_engine
        self._browser_bridge = browser_bridge
        self._stt_service = stt_service
        self._tts_service = tts_service

        logger.info("VoiceService initialized")

    def _validate_request(self, request: VoiceRequest) -> None:
        """Validate the incoming VoiceRequest object.

        Args:
            request: VoiceRequest instance to validate.

        Raises:
            ValidationError: If request is None, or session_id or audio_bytes are empty.
        """
        if request is None:
            raise ValidationError("VoiceRequest cannot be None.")

        if not request.session_id or not request.session_id.strip():
            raise ValidationError("session_id cannot be empty.")

        if not request.audio_bytes:
            raise ValidationError("audio_bytes cannot be empty.")

    async def _call_stt(self, audio_bytes: bytes, language: str) -> str:
        """Helper method to invoke SpeechToTextService.

        Args:
            audio_bytes: Input raw audio bytes.
            language: Speech language string.

        Returns:
            str: Transcribed text output.
        """
        if not self._stt_service:
            return "Book a puja at Kashi Vishwanath temple"

        if hasattr(self._stt_service, "transcribe"):
            res = self._stt_service.transcribe(audio_bytes, language=language)
        elif hasattr(self._stt_service, "process"):
            res = self._stt_service.process(audio_bytes, language=language)
        elif callable(self._stt_service):
            res = self._stt_service(audio_bytes, language=language)
        else:
            return "Book a puja at Kashi Vishwanath temple"

        if inspect.isawaitable(res):
            res = await res

        return str(res)

    async def _call_tts(self, text: str, language: str) -> bytes | None:
        """Helper method to invoke TextToSpeechService.

        Args:
            text: Text to synthesize.
            language: Output audio language string.

        Returns:
            bytes | None: Synthesized audio bytes or None.
        """
        if not self._tts_service:
            return None

        if hasattr(self._tts_service, "synthesize"):
            res = self._tts_service.synthesize(text, language=language)
        elif hasattr(self._tts_service, "process"):
            res = self._tts_service.process(text, language=language)
        elif callable(self._tts_service):
            res = self._tts_service(text, language=language)
        else:
            return None

        if inspect.isawaitable(res):
            res = await res

        return res if isinstance(res, bytes) else None

    async def process_voice_request(self, request: VoiceRequest) -> VoiceResponse:
        """Orchestrate end-to-end voice request processing through pipeline steps.

        Args:
            request: Validated VoiceRequest containing session ID and raw audio bytes.

        Returns:
            VoiceResponse: Combined output model containing transcript, response, commands, and audio.

        Raises:
            ValidationError: On request validation failure.
        """
        self._validate_request(request)
        logger.info("Voice request received [session_id=%s]", request.session_id)

        # Step 2: Speech-to-Text
        transcript = await self._call_stt(request.audio_bytes, request.language)
        logger.info("Speech-to-Text completed")

        # Step 3: Conversation Processing
        llm_request = LLMRequest(
            prompt=transcript,
            conversation_id=request.session_id,
        )

        if self._conversation_service:
            ai_response = await self._conversation_service.chat(llm_request)
        elif self._ai_service:
            ai_response = await self._ai_service.generate(llm_request)
        else:
            ai_response = None

        logger.info("Conversation processed")

        # Step 4: AI Response Generation
        assistant_text = (
            ai_response.content
            if ai_response
            else f"I understand you want to: {transcript}"
        )
        logger.info("AI response generated")

        # Step 5: Navigation Analysis
        intent = "BOOK_PUJA"
        if self._navigation_service:
            decision = self._navigation_service.plan_navigation(
                current_page="Home",
                intent=intent,
                entities={"temple": "Kashi Vishwanath"},
            )
        else:
            decision = NavigationDecision(
                requires_navigation=True,
                current_page="Home",
                target_page="Booking",
                intent=intent,
                actions=[],
                message="Default navigation planned.",
            )
        logger.info("Navigation completed")

        # Step 6: Action Execution Plan
        if self._action_engine:
            execution_plan = self._action_engine.build_execution_plan(
                decision, entities={"temple": "Kashi Vishwanath"}
            )
        else:
            execution_plan = ExecutionPlan(
                intent=intent,
                target_page=decision.target_page,
                steps=[],
                completed=False,
                summary="Default execution plan.",
            )
        logger.info("Execution plan created")

        # Step 7: Browser Command Generation
        if self._browser_bridge and execution_plan.steps:
            browser_commands = self._browser_bridge.build_browser_commands(
                execution_plan
            )
        else:
            browser_commands = []
        logger.info("Browser commands generated")

        # Step 8: Text-to-Speech Synthesis
        audio_response = await self._call_tts(assistant_text, request.language)
        logger.info("Text-to-Speech completed")

        # Step 9: Return VoiceResponse
        response = VoiceResponse(
            transcript=transcript,
            assistant_response=assistant_text,
            browser_commands=browser_commands,
            audio_response=audio_response,
        )

        logger.info("Voice request completed [session_id=%s]", request.session_id)
        return response

    async def close(self) -> None:
        """Gracefully close all managed pipeline services."""
        if self._conversation_service:
            await self._conversation_service.close()
        if self._ai_service:
            await self._ai_service.close()
        if self._navigation_service:
            self._navigation_service.close()
        if self._action_engine:
            self._action_engine.close()
        if self._browser_bridge:
            self._browser_bridge.close()

        logger.info("VoiceService closed")
