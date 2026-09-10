"""Generate the loud speech-like WAV that Chrome replays as the fake microphone.

This simulates the worst case for echo: the microphone constantly hears loud audio, as it
would when Saarthi's reply is coming out of a loudspeaker right next to the mic.
"""

import math
import struct
import wave

SR = 48000
SECONDS = 12.0

frames = bytearray()
for i in range(int(SR * SECONDS)):
    t = i / SR
    # Syllable-rate amplitude envelope (~4 Hz) over a voiced harmonic stack
    env = max(0.0, math.sin(2 * math.pi * 4.0 * t)) ** 0.5
    s = env * (
        0.45 * math.sin(2 * math.pi * 200 * t)
        + 0.30 * math.sin(2 * math.pi * 600 * t)
        + 0.20 * math.sin(2 * math.pi * 1800 * t)
        + 0.10 * math.sin(2 * math.pi * 3000 * t)
    )
    frames += struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000))

with wave.open("/app/echo_harness/fake_mic.wav", "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(bytes(frames))

print("wrote /app/echo_harness/fake_mic.wav")
