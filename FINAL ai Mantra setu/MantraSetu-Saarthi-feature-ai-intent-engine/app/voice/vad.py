"""Pure Python Acoustic Voice Activity Detector (VAD) Gate for Voice AI v1.0."""

import logging
import math
import struct
from typing import Any

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    """Pre-STT Acoustic Voice Activity Detector (VAD) Gate with Dynamic SNR and Hysteresis."""

    def __init__(self, min_speech_duration_sec: float = 0.15, sample_rate: int = 16000, safety_cap_sec: float = 12.0) -> None:
        self.min_speech_duration_sec = min_speech_duration_sec
        self.sample_rate = sample_rate
        self.safety_cap_sec = safety_cap_sec
        
        # Buffer for incomplete frames
        self._residual_bytes = b""
        
        # State
        self.total_frames = 0
        self.speech_frames = 0
        self.max_rms = 0.0
        
        # Calibration state
        self.is_calibrated = False
        self.calibration_frames = 0
        # Calibrate over first 500ms (0.5s / 0.03s per frame)
        self.required_calibration_frames = int((self.sample_rate * 0.5) / (self.sample_rate * 0.03))
        self.noise_floor_rms = 0.0
        self.calibration_rms_sum = 0.0
        
        # Hysteresis state
        self.is_speaking = False
        
        # Default starting fallback threshold (calibrated for standard PC/laptop mics)
        self.base_threshold = 100.0

    def process_chunk(self, pcm_bytes: bytes) -> bool:
        """Process incoming chunk. Returns True if safety cap is exceeded."""
        full_bytes = self._residual_bytes + pcm_bytes
        frame_samples = int(self.sample_rate * 0.03)  # 480 samples @ 16kHz
        frame_bytes = frame_samples * 2
        
        total_full_frames = len(full_bytes) // frame_bytes
        
        for i in range(total_full_frames):
            frame = full_bytes[i * frame_bytes : (i + 1) * frame_bytes]
            self._process_frame(frame, frame_samples)
            
        self._residual_bytes = full_bytes[total_full_frames * frame_bytes:]
        return self.get_total_duration_sec() >= self.safety_cap_sec

    def _process_frame(self, frame: bytes, frame_samples: int) -> None:
        samples = struct.unpack(f"<{frame_samples}h", frame)
        
        # RMS Energy
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / frame_samples) if sum_sq > 0 else 0.0
        if rms > self.max_rms:
            self.max_rms = rms
            
        # ZCR
        zcr = sum(1 for j in range(1, frame_samples) if (samples[j] >= 0) != (samples[j-1] >= 0)) / frame_samples
        
        # Calibration phase (First 500ms)
        if not self.is_calibrated:
            self.calibration_rms_sum += rms
            self.calibration_frames += 1
            if self.calibration_frames >= self.required_calibration_frames:
                self.noise_floor_rms = self.calibration_rms_sum / self.calibration_frames
                self.is_calibrated = True
                logger.info("[VAD-CALIBRATION] Noise floor calibrated at RMS: %.2f", self.noise_floor_rms)
                
        # Hysteresis thresholds
        noise_baseline = self.noise_floor_rms if self.is_calibrated else 40.0
        
        # Start threshold: Exceed noise baseline by +50 RMS or minimum 100 RMS
        start_threshold = max(self.base_threshold, noise_baseline + 50.0)
        
        # Continuation threshold (hysteresis): Lower bar to maintain active speech
        continuation_threshold = max(60.0, noise_baseline + 20.0)
        
        active_threshold = continuation_threshold if self.is_speaking else start_threshold
        
        # Speech classification
        is_frame_speech = rms >= active_threshold and zcr < 0.50
        
        if is_frame_speech:
            self.is_speaking = True
            self.speech_frames += 1
        else:
            self.is_speaking = False
            
        self.total_frames += 1

    def get_total_duration_sec(self) -> float:
        return self.total_frames * 0.03
        
    def get_speech_duration_sec(self) -> float:
        return self.speech_frames * 0.03

    def get_analysis(self) -> dict[str, Any]:
        """Return final analysis for the utterance."""
        speech_dur = self.get_speech_duration_sec()
        total_dur = self.get_total_duration_sec()
        is_valid = (speech_dur >= self.min_speech_duration_sec) or (self.max_rms >= 120.0 and total_dur >= 0.25)
        
        logger.info(
            "[VAD-GATE] Total Duration: %.2fs | Verified Speech Duration: %.2fs (min req: %.2fs) | Valid Speech: %s | Max RMS: %.2f | Calibrated Noise: %.2f",
            total_dur, speech_dur, self.min_speech_duration_sec, is_valid, self.max_rms, self.noise_floor_rms
        )

        if not is_valid:
            logger.info("[DIAG-INVESTIGATION][VAD-REJECTED] utterance rejected. Max RMS computed: %.2f", self.max_rms)
            
        return {
            "is_valid_speech": is_valid,
            "speech_duration_sec": speech_dur,
            "total_duration_sec": total_dur,
            "reason": "OK" if is_valid else "INSUFFICIENT_HUMAN_SPEECH",
            "max_rms": self.max_rms,
            "noise_floor_rms": self.noise_floor_rms
        }

    def analyze_audio_buffer(self, pcm_bytes: bytes) -> dict[str, Any]:
        """Backward compatibility for one-shot buffer analysis."""
        self.process_chunk(pcm_bytes)
        return self.get_analysis()
