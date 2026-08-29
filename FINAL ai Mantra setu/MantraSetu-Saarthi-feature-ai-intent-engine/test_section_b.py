import struct
from app.voice.vad import VoiceActivityDetector

print("--- SECTION B: Mic & VAD Lifecycle ---")
vad = VoiceActivityDetector(min_speech_duration_sec=0.15, sample_rate=16000)

def generate_pcm_buffer(duration_sec, rms_target, zcr_target=0.1):
    num_samples = int(duration_sec * 16000)
    samples = []
    # simple sine wave approximation for rms and zcr
    for i in range(num_samples):
        # We need rms > 450, so amplitude should be around 450 * sqrt(2) ~ 636
        if rms_target > 0:
            val = int(rms_target * 1.414 * (1 if (i // 100) % 2 == 0 else -1))
        else:
            val = 0
        samples.append(val)
    return struct.pack(f"<{num_samples}h", *samples)

# Check 1: Short Burst (< 0.15s, RMS 500)
print("Check 1 | Input: 0.10s audio, RMS 500 | Expected: reason INSUFFICIENT_HUMAN_SPEECH")
buf = generate_pcm_buffer(0.10, 500)
res = vad.analyze_audio_buffer(buf)
print(f"Actual: is_valid_speech={res['is_valid_speech']}, reason={res['reason']}, duration={res['speech_duration_sec']}")
print(f"Result: {'PASS' if res['reason'] == 'AUDIO_TOO_SHORT' or res['reason'] == 'INSUFFICIENT_HUMAN_SPEECH' else 'FAIL'}")

# Check 2: Background Noise (RMS 300)
print("\nCheck 2 | Input: 0.5s audio, RMS 300 | Expected: reason INSUFFICIENT_HUMAN_SPEECH")
buf2 = generate_pcm_buffer(0.5, 300)
res2 = vad.analyze_audio_buffer(buf2)
print(f"Actual: is_valid_speech={res2['is_valid_speech']}, reason={res2['reason']}, duration={res2['speech_duration_sec']}")
print(f"Result: {'PASS' if res2['reason'] == 'INSUFFICIENT_HUMAN_SPEECH' else 'FAIL'}")

# Check 3: Valid Speech (RMS 500)
print("\nCheck 3 | Input: 0.5s audio, RMS 500 | Expected: OK / Valid Speech")
buf3 = generate_pcm_buffer(0.5, 500)
res3 = vad.analyze_audio_buffer(buf3)
print(f"Actual: is_valid_speech={res3['is_valid_speech']}, reason={res3['reason']}, duration={res3['speech_duration_sec']}")
print(f"Result: {'PASS' if res3['is_valid_speech'] else 'FAIL'}")
