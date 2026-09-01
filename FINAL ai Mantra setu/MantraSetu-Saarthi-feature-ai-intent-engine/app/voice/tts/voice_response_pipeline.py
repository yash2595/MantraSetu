"""VoiceResponsePipeline streaming coordinator converting OrchestratorResponse into audio streams."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import AsyncGenerator
from uuid import uuid4

from app.orchestrator.orchestrator_models import OrchestratorResponse
from app.voice.schemas import AudioEncoding
from app.voice.tts.base import ITTSProvider
from app.voice.tts.cache_manager import TTSCacheManager, get_tts_cache_manager
from app.voice.tts.schemas import AudioChunk, VoiceSynthesisRequest
from app.utils.identifier_speech import render_long_numeric_identifiers

logger = logging.getLogger(__name__)

# Comprehensive Unicode emoji regex pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002600-\U000026FF"  # Miscellaneous Symbols
    "\U00002700-\U000027BF"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "]+",
    flags=re.UNICODE,
)

HINGLISH_PHONETIC_REPLACEMENTS = [
    (r'(\d+)-digit', r'\1 digit'),
    (r'\b10-digit\b', 'दस अंकों का'),
    (r'\bNamaste\b', 'नमस्ते'),
    (r'\bMantraSetu\b', 'मंत्रसेतु'),
    (r'\bPanditji\b', 'पंडित जी'),
    (r'\bPandit\b', 'पंडित'),
    (r'\bSwagat\b', 'स्वागत'),
    (r'\bSeva\b', 'सेवा'),
    (r'\bDhanyawad\b', 'धन्यवाद'),
    (r'\bUttam\b', 'उत्तम'),
    (r'\bBahut\b', 'बहुत'),
    (r'\bSundar\b', 'सुंदर'),
    (r'\bBadhiya\b', 'बढ़िया'),
    (r'\bKripya\b', 'कृपया'),
    (r'\bBataiye\b', 'बताइए'),
    (r'\bDobara\b', 'दोबारा'),
    (r'\bSamajh\b', 'समझ'),
    (r'\bRoop\b', 'रूप'),
    (r'\bJudna\b', 'जुड़ना'),
    (r'\bChahte\b', 'चाहते'),
    (r'\bBhakt\b', 'भक्त'),
    (r'\bMobile\b', 'मोबाइल'),
    (r'\bNumber\b', 'नंबर'),
    (r'\bEmail\b', 'ईमेल'),
    (r'\bCity\b', 'शहर'),
    (r'\bState\b', 'राज्य'),
    (r'\bForm\b', 'फॉर्म'),
    (r'\bRecord\b', 'रिकॉर्ड'),
]


def clean_text_for_tts(text: str) -> str:
    """Sanitize text specifically for TTS audio generation.

    Preserves natural speech punctuation (!, ?, ., ,, :, ;) for natural intonation/pauses,
    while stripping emojis, markdown, and technical non-speech characters.
    """
    if not text:
        return "Namaste"

    # 1. Strip Markdown formatting symbols and technical non-speech characters
    cleaned = re.sub(r'[*_#`~>@$%^&+=/\\|<>{}\[\]]', '', text)

    # 2. Strip all emoji characters
    cleaned = EMOJI_PATTERN.sub('', cleaned)

    # 3. Identifier-like number sequences (phone/OTP/PIN) are rendered as
    # alphabetic digit words.  Spaces alone can be re-normalised by TTS as a
    # cardinal number; words cannot become lakh/crore place-value speech.
    cleaned = render_long_numeric_identifiers(cleaned)

    # 4. Normalize multiple consecutive punctuation marks
    cleaned = re.sub(r'!+', '!', cleaned)
    cleaned = re.sub(r'\?+', '?', cleaned)
    cleaned = re.sub(r'\.+', '.', cleaned)

    # 5. Apply Hinglish phonetic replacements for Indic TTS
    for pattern, replacement in HINGLISH_PHONETIC_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # 6. Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned if cleaned else "Namaste"


class VoiceResponsePipeline:
    """Stream coordinator converting normalized OrchestratorResponse into streamed AudioChunk sequence."""

    def __init__(
        self,
        tts_provider: ITTSProvider,
        cache_manager: TTSCacheManager | None = None,
    ) -> None:
        if tts_provider is None:
            raise ValueError("VoiceResponsePipeline requires a non-null ITTSProvider instance.")
        self._tts_provider = tts_provider
        self._cache_manager = cache_manager or get_tts_cache_manager()

    @property
    def tts_provider(self) -> ITTSProvider:
        """Expose injected ITTSProvider implementation."""
        return self._tts_provider

    @property
    def cache_manager(self) -> TTSCacheManager:
        """Expose injected TTSCacheManager implementation."""
        return self._cache_manager

    async def process_response(
        self,
        response: OrchestratorResponse,
        voice: str | None = None,
        language: str | None = None,
        encoding: AudioEncoding = AudioEncoding.MP3,
    ) -> AsyncGenerator[AudioChunk, None]:
        """Convert OrchestratorResponse content into streaming AudioChunk sequence."""
        
        raw_text = response.text if response.text else "Namaste"
        text_content = clean_text_for_tts(raw_text)

        resolved_voice = voice or "pandit"
        resolved_language = language or "hi"
        provider_name = self._tts_provider.provider_name

        def _get_valid_uuid(val, default):
            if not val:
                return default
            try:
                if isinstance(val, uuid.UUID):
                    return val
                return uuid.UUID(str(val))
            except ValueError:
                return default

        req_uuid = _get_valid_uuid(response.request_id, uuid4())
        conv_uuid = _get_valid_uuid(getattr(response, "conversation_id", None), uuid4())
        sess_uuid = getattr(response, "session_id", "default_sess")

        # ── Check TTS Cache First (0-2ms latency for static prompts) ──
        cache_start_time = time.time()
        cache_key = self._cache_manager.get_cache_key(text_content, resolved_voice, resolved_language, provider_name)
        cached_audio = self._cache_manager.get(cache_key)

        if cached_audio is not None and len(cached_audio) > 0:
            cache_elapsed_ms = int((time.time() - cache_start_time) * 1000)
            logger.info(
                f"[TIMING-TTS] TTS Cache HIT for key={cache_key[:8]} | text='{text_content[:35]}...' | Served in {cache_elapsed_ms}ms | size={len(cached_audio)} bytes"
            )
            yield AudioChunk(
                request_id=req_uuid,
                session_id=sess_uuid,
                conversation_id=conv_uuid,
                sequence_number=0,
                data=cached_audio,
                is_final=True,
                timestamp_ms=int(time.time() * 1000),
                metadata={"provider": provider_name, "cached": True, "cache_key": cache_key},
            )
            return

        # ── Cache Miss: Synthesize via TTS Provider ──
        synthesis_request = VoiceSynthesisRequest(
            request_id=req_uuid,
            session_id=sess_uuid,
            conversation_id=conv_uuid,
            text=text_content,
            language=resolved_language,
            voice=resolved_voice,
            encoding=encoding,
            metadata={},
        )

        logger.info(
            "VoiceResponsePipeline processing OrchestratorResponse for TTS (CACHE MISS)",
            extra={
                "request_id": str(synthesis_request.request_id),
                "session_id": getattr(response, "session_id", None),
                "conversation_id": str(getattr(response, "conversation_id", None)),
                "text_length": len(text_content),
                "provider": provider_name,
                "voice": resolved_voice,
                "language": resolved_language,
            },
        )

        tts_start_time = time.time()
        full_audio_bytes = b""
        async for chunk in self._tts_provider.stream(synthesis_request):
            tts_elapsed_ms = int((time.time() - tts_start_time) * 1000)
            if chunk.data:
                full_audio_bytes += chunk.data
            logger.info(f"[TIMING-TTS] TTS Audio stream chunk produced in {tts_elapsed_ms}ms | size={len(chunk.data)} bytes")
            yield chunk

        # Store complete synthesized audio in cache for future instant serving
        if full_audio_bytes:
            self._cache_manager.put(cache_key, full_audio_bytes)

    async def cancel(self, request_id: str) -> None:
        """Cancel an active TTS synthesis stream."""
        await self._tts_provider.cancel(request_id)
