"""VoiceResponsePipeline streaming coordinator converting InteractionResponse into audio streams."""

from __future__ import annotations

import logging
from typing import AsyncGenerator
from uuid import uuid4

from app.orchestrator.orchestrator_models import OrchestratorResponse
from app.voice.schemas import AudioEncoding
from app.voice.tts.base import ITTSProvider
from app.voice.tts.schemas import AudioChunk, VoiceSynthesisRequest

logger = logging.getLogger(__name__)


import re

# Comprehensive Unicode emoji regex pattern covering emoticons, symbols, pictographs, dingbats, and variation selectors
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
    (r'!', '.'),
    (r'\?', '.'),
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

    Strips emojis, markdown symbols, exclamation marks, and applies Hinglish
    phonetic normalization so gTTS (hi-IN) does not mispronounce symbols as 'flag'.
    """
    if not text:
        return "Namaste"

    # 1. Strip Markdown formatting characters
    cleaned = re.sub(r'[*_#`~>]', '', text)

    # 2. Strip all emoji characters
    cleaned = EMOJI_PATTERN.sub('', cleaned)

    # 3. Format continuous 10-digit mobile numbers into spaced digit groups for TTS
    cleaned = re.sub(r'\b([56789]\d{2})(\d{3})(\d{4})\b', r'\1 \2 \3', cleaned)

    # 4. Replace exclamation marks and symbols that cause gTTS to read 'flag' or punctuation names
    cleaned = re.sub(r'[!#\*\_~`^]', '.', cleaned)

    # 5. Apply Hinglish phonetic replacements for gTTS (hi-IN)
    for pattern, replacement in HINGLISH_PHONETIC_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # 6. Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned if cleaned else "Namaste"



class VoiceResponsePipeline:
    """Stream coordinator converting normalized InteractionResponse into streamed AudioChunk frames."""

    def __init__(self, tts_provider: ITTSProvider) -> None:
        if tts_provider is None:
            raise ValueError("VoiceResponsePipeline requires a non-null ITTSProvider instance.")
        self._tts_provider = tts_provider

    @property
    def tts_provider(self) -> ITTSProvider:
        """Expose injected ITTSProvider implementation."""
        return self._tts_provider

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

        resolved_voice = voice or "meera"
        resolved_language = language or "hi"

        import uuid

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
            "VoiceResponsePipeline processing InteractionResponse for TTS",
            extra={
                "request_id": str(synthesis_request.request_id),
                "session_id": getattr(response, "session_id", None),
                "conversation_id": str(getattr(response, "conversation_id", None)),
                "text_length": len(text_content),
                "provider": self._tts_provider.provider_name,
                "voice": resolved_voice,
                "language": resolved_language,
            },
        )

        async for chunk in self._tts_provider.stream(synthesis_request):
            yield chunk

    async def cancel(self, request_id: str) -> None:
        """Cancel an active TTS synthesis stream."""
        await self._tts_provider.cancel(request_id)
