"""Speech-to-Text canonical Pydantic models.

Defines request and response schemas shared across SpeechToTextService, STT providers,
and Voice Conversation Pipelines.
"""

from pydantic import BaseModel, Field


class SpeechToTextRequest(BaseModel):
    """Input payload model for speech-to-text transcription requests.

    Attributes:
        audio_bytes: Raw binary audio data bytes.
        language: Target speech language identifier string.
    """

    audio_bytes: bytes = Field(
        ...,
        description="Raw binary audio data bytes for transcription.",
    )
    language: str = Field(
        default="hinglish",
        description="Target speech language identifier string.",
    )


class SpeechToTextResponse(BaseModel):
    """Output response model from speech-to-text transcription execution.

    Attributes:
        transcript: Transcribed textual content output string.
        language: Language code string of the transcribed output.
        confidence: Transcription confidence score floating point between 0.0 and 1.0.
    """

    transcript: str = Field(
        ...,
        description="Transcribed textual content output string.",
    )
    language: str = Field(
        ...,
        description="Language code string of the transcribed output.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Transcription confidence score floating point between 0.0 and 1.0.",
    )


class VoiceChatRequest(BaseModel):
    """Unified request model for text and voice conversation pipeline.

    Attributes:
        prompt: Optional text prompt input string for direct text chat.
        audio_bytes: Optional raw binary audio input bytes for speech pipeline.
        language: Target spoken language identifier string.
        voice: Optional target TTS voice speaker identifier string.
    """

    prompt: str | None = Field(
        default=None,
        description="Optional text prompt input string for direct text chat.",
    )
    audio_bytes: bytes | None = Field(
        default=None,
        description="Optional raw binary audio input bytes for speech pipeline.",
    )
    language: str = Field(
        default="hinglish",
        description="Target spoken language identifier string.",
    )
    voice: str | None = Field(
        default=None,
        description="Optional target TTS voice speaker identifier string.",
    )


class VoiceChatResponse(BaseModel):
    """Unified response model for end-to-end voice conversation pipeline.

    Attributes:
        transcription: Transcribed user speech text output.
        assistant_text: Generated AI assistant text response completion.
        audio_bytes: Synthesized binary audio output payload bytes.
        audio_format: Audio container format string (e.g. 'mp3', 'wav').
        sample_rate: Audio sampling frequency in Hertz (Hz).
        total_latency_ms: Total end-to-end pipeline latency in milliseconds.
        stt_latency_ms: Latency of Speech-to-Text transcription phase in ms.
        llm_latency_ms: Latency of AI text generation phase in ms.
        tts_latency_ms: Latency of Text-to-Speech synthesis phase in ms.
    """

    transcription: str = Field(
        default="",
        description="Transcribed user speech text output.",
    )
    assistant_text: str = Field(
        ...,
        description="Generated AI assistant text response completion.",
    )
    audio_bytes: bytes = Field(
        default=b"",
        description="Synthesized binary audio output payload bytes.",
    )
    audio_format: str = Field(
        default="mp3",
        description="Audio container format string (e.g. 'mp3', 'wav').",
    )
    sample_rate: int = Field(
        default=24000,
        description="Audio sampling frequency in Hertz (Hz).",
    )
    total_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total end-to-end pipeline latency in milliseconds.",
    )
    stt_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latency of Speech-to-Text transcription phase in ms.",
    )
    llm_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latency of AI text generation phase in ms.",
    )
    tts_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latency of Text-to-Speech synthesis phase in ms.",
    )
