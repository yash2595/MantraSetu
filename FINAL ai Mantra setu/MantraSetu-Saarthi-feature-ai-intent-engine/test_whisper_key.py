"""Inspect WAV audio to determine if it contains actual speech or silence."""
import wave
import struct
import math

f = wave.open("debug_last.wav", "rb")
frames = f.readframes(f.getnframes())
f.close()

samples = struct.unpack(f"<{len(frames)//2}h", frames)
n = len(samples)

# Calculate RMS (volume level)
rms = math.sqrt(sum(s*s for s in samples) / n)
max_val = max(abs(s) for s in samples)
min_val = min(samples)

# Count non-silent samples (above threshold)
threshold = 500
non_silent = sum(1 for s in samples if abs(s) > threshold)

print(f"Total samples: {n}")
print(f"Duration: {n/16000:.2f}s")
print(f"RMS level: {rms:.1f}")
print(f"Max amplitude: {max_val}")
print(f"Min amplitude: {min_val}")
print(f"Non-silent samples (>{threshold}): {non_silent} ({100*non_silent/n:.1f}%)")

# Print first 100 samples to see if it's all zeros
first_100 = samples[:100]
print(f"First 100 samples: {first_100}")

if rms < 100:
    print("\n=== AUDIO IS MOSTLY SILENCE ===")
elif non_silent / n < 0.05:
    print("\n=== VERY LOW SPEECH CONTENT ===")
else:
    print(f"\n=== AUDIO HAS CONTENT (RMS={rms:.0f}) ===")
