"""Pure Python Acoustic Voice Activity Detector (VAD) Gate for Voice AI v1.0."""

import logging
import math
import struct
from typing import Any

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    """Pre-STT Acoustic Voice Activity Detector (VAD) Gate."""

    def __init__(self, min_speech_duration_sec: float = 0.8, sample_rate: int = 16000) -> None:
        self.min_speech_duration_sec = min_speech_duration_sec
        self.sample_rate = sample_rate

    def analyze_audio_buffer(self, pcm_bytes: bytes) -> dict[str, Any]:
        """Analyze raw PCM16 audio buffer and classify active human speech duration & validity."""
        if not pcm_bytes or len(pcm_bytes) < 960:
            return {
                "is_valid_speech": False,
                "speech_duration_sec": 0.0,
                "total_duration_sec": 0.0,
                "reason": "AUDIO_TOO_SHORT"
            }

        sample_count = len(pcm_bytes) // 2
        total_duration_sec = round(sample_count / self.sample_rate, 2)
        
        # Analyze in 30ms frames (480 samples @ 16kHz = 960 bytes)
        frame_samples = int(self.sample_rate * 0.03)  # 480 samples
        frame_bytes = frame_samples * 2  # 960 bytes
        
        speech_frames = 0
        total_frames = len(pcm_bytes) // frame_bytes

        if total_frames == 0:
            return {
                "is_valid_speech": False,
                "speech_duration_sec": 0.0,
                "total_duration_sec": total_duration_sec,
                "reason": "INSUFFICIENT_FRAMES"
            }

        for i in range(total_frames):
            frame = pcm_bytes[i * frame_bytes : (i + 1) * frame_bytes]
            samples = struct.unpack(f"<{frame_samples}h", frame)
            
            # Calculate RMS Energy
            sum_sq = sum(s * s for s in samples)
            rms = math.sqrt(sum_sq / frame_samples)
            
            # Calculate Zero-Crossing Rate (ZCR)
            zcr = sum(1 for j in range(1, frame_samples) if (samples[j] >= 0) != (samples[j-1] >= 0)) / frame_samples
            
            # Speech frame classification (Voiced / Unvoiced human speech envelope)
            if rms >= 450 and zcr < 0.45:
                speech_frames += 1

        speech_duration_sec = round(speech_frames * 0.03, 2)
        is_valid = speech_duration_sec >= self.min_speech_duration_sec

        logger.info(
            "[VAD-GATE] Total Duration: %.2fs | Verified Speech Duration: %.2fs (min req: %.2fs) | Valid Speech: %s",
            total_duration_sec, speech_duration_sec, self.min_speech_duration_sec, is_valid
        )

        return {
            "is_valid_speech": is_valid,
            "speech_duration_sec": speech_duration_sec,
            "total_duration_sec": total_duration_sec,
            "reason": "OK" if is_valid else "INSUFFICIENT_HUMAN_SPEECH"
        }
