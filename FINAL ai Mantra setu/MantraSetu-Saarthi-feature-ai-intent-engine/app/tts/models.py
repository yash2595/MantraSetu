"""Text-to-Speech canonical Pydantic models.

Defines request and response schemas shared across TextToSpeechService and TTS providers.
"""

from pydantic import BaseModel, Field


class TextToSpeechRequest(BaseModel):
    """Input request model for text-to-speech synthesis.

    Attributes:
        text: Textual content input to synthesize into speech.
        language: Target spoken language identifier string.
        voice: Optional target voice name or speaker identifier.
    """

    text: str = Field(
        ...,
        description="Textual content input to synthesize into speech.",
    )
    language: str = Field(
        default="hinglish",
        description="Target spoken language identifier string.",
    )
    voice: str | None = Field(
        default=None,
        description="Optional target voice name or speaker identifier.",
    )


class TextToSpeechResponse(BaseModel):
    """Output response model from text-to-speech synthesis execution.

    Attributes:
        audio_bytes: Synthesized binary audio data payload.
        sample_rate: Audio sampling frequency in Hertz (Hz). Must be > 0.
        format: Audio container/codec format identifier string.
    """

    audio_bytes: bytes = Field(
        ...,
        description="Synthesized binary audio data payload.",
    )
    sample_rate: int = Field(
        ...,
        gt=0,
        description="Audio sampling frequency in Hertz (Hz). Must be > 0.",
    )
    format: str = Field(
        ...,
        description="Audio container/codec format identifier string (e.g., 'mp3', 'wav').",
    )
