"""Mock MantraSetu voice backend that MEASURES whether Saarthi's own voice reaches STT.

Saarthi's TTS is broadband noise in the 2500-5000 Hz band.
The simulated user speaks broadband noise in the 200-1500 Hz band.
Both are broadband enough to drive the app's real VAD, and cleanly separable spectrally.

Every AUDIO_FRAME the frontend sends is accumulated; band energies tell us whose voice the
frontend streamed to STT. Saarthi transcribing her own replies == SAARTHI band energy present.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import random
import struct
import time
import wave

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TTS_SAMPLE_RATE = 24000
TTS_SECONDS = 3.0
TTS_CHUNKS = 12
MIC_SAMPLE_RATE = 16000

SAARTHI_BAND = [f for f in range(2500, 5001, 250)]
USER_BAND = [f for f in range(200, 1501, 130)]

EVENTS: list[dict] = []
TURNS: list[dict] = []
CURRENT: dict = {"frames": [], "pcm": bytearray(), "started": None}
T0 = time.monotonic()


def log(kind: str, **extra) -> None:
    EVENTS.append({"t": round(time.monotonic() - T0, 4), "kind": kind, **extra})


def build_tts_pcm() -> bytes:
    """3s of loud band-limited noise in Saarthi's band (sum of many tones, random phase)."""
    random.seed(7)
    n = int(TTS_SAMPLE_RATE * TTS_SECONDS)
    phases = [random.random() * 2 * math.pi for _ in SAARTHI_BAND]
    amp = 0.9 / len(SAARTHI_BAND)
    out = bytearray()
    for i in range(n):
        t = i / TTS_SAMPLE_RATE
        s = sum(amp * math.sin(2 * math.pi * f * t + p) for f, p in zip(SAARTHI_BAND, phases))
        out += struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000))
    return bytes(out)


TTS_PCM = build_tts_pcm()


def goertzel(samples, freq: float, rate: int) -> float:
    n = len(samples)
    if n == 0:
        return 0.0
    k = int(0.5 + (n * freq) / rate)
    w = 2 * math.pi * k / n
    coeff = 2 * math.cos(w)
    s_prev = s_prev2 = 0.0
    for x in samples:
        s = (x / 32768.0) + coeff * s_prev - s_prev2
        s_prev2, s_prev = s_prev, s
    power = s_prev2 * s_prev2 + s_prev * s_prev - coeff * s_prev * s_prev2
    return math.sqrt(max(0.0, power)) / n * 2


def band_energy(samples, band, rate: int) -> float:
    if not samples:
        return 0.0
    return round(math.sqrt(sum(goertzel(samples, f, rate) ** 2 for f in band)), 6)


def to_samples(pcm: bytes):
    n = len(pcm) // 2
    return list(struct.unpack(f"<{n}h", pcm[: n * 2])) if n else []


def analyse(pcm: bytes) -> dict:
    s = to_samples(pcm)
    if not s:
        return {"samples": 0, "duration_sec": 0.0, "rms": 0.0, "saarthi_band": 0.0, "user_band": 0.0,
                "head1s_saarthi_band": 0.0, "head1s_user_band": 0.0}
    head = s[:MIC_SAMPLE_RATE]
    rms = math.sqrt(sum(v * v for v in s) / len(s)) / 32768.0
    return {
        "samples": len(s),
        "duration_sec": round(len(s) / MIC_SAMPLE_RATE, 3),
        "rms": round(rms, 5),
        "saarthi_band": band_energy(s, SAARTHI_BAND, MIC_SAMPLE_RATE),
        "user_band": band_energy(s, USER_BAND, MIC_SAMPLE_RATE),
        "head1s_saarthi_band": band_energy(head, SAARTHI_BAND, MIC_SAMPLE_RATE),
        "head1s_user_band": band_energy(head, USER_BAND, MIC_SAMPLE_RATE),
    }


@app.post("/voice/ticket")
async def voice_ticket():
    return {"ticket": "harness-ticket", "type": "guest"}


@app.get("/_report")
async def report():
    pending = None
    if CURRENT["pcm"]:
        pending = {
            "started": CURRENT["started"],
            "frames": CURRENT["frames"],
            "analysis": analyse(bytes(CURRENT["pcm"])),
            "note": "frames streamed to STT that never ended in an AUDIO_END",
        }
    return JSONResponse({"events": EVENTS, "turns": TURNS, "pending": pending})


@app.post("/_reset")
async def reset():
    EVENTS.clear()
    TURNS.clear()
    CURRENT["frames"] = []
    CURRENT["pcm"] = bytearray()
    CURRENT["started"] = None
    return {"ok": True}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str):
    return JSONResponse({})


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    await ws.accept()
    log("ws_open")
    speaking = False

    async def stream_tts(turn_label: str):
        nonlocal speaking
        await ws.send_text(json.dumps({
            "type": "AI_RESPONSE",
            "request_id": "harness-req",
            "payload": {
                "content": "Namaste, main Saarthi hoon.",
                "navigation_directive": {"action": None, "target": None, "intent": "CHAT"},
            },
        }))
        speaking = True
        log("tts_send_start", turn=turn_label)
        step = len(TTS_PCM) // TTS_CHUNKS
        step -= step % 2
        for idx in range(TTS_CHUNKS):
            start = idx * step
            end = len(TTS_PCM) if idx == TTS_CHUNKS - 1 else start + step
            await ws.send_text(json.dumps({
                "type": "AUDIO_CHUNK",
                "request_id": "harness-req",
                "payload": {
                    "data": base64.b64encode(TTS_PCM[start:end]).decode(),
                    "sample_rate": TTS_SAMPLE_RATE,
                    "encoding": "LINEAR16",
                    "is_final": idx == TTS_CHUNKS - 1,
                },
            }))
            await asyncio.sleep(TTS_SECONDS / TTS_CHUNKS)
        speaking = False
        log("tts_send_end", turn=turn_label)

    tts_task: asyncio.Task | None = None
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "CONNECT":
                log("connect_received")
                await ws.send_text(json.dumps({
                    "type": "CONNECTED",
                    "payload": {"status": "connected", "sample_rate": 16000, "language": "hi"},
                }))
                tts_task = asyncio.create_task(stream_tts("greeting"))

            elif mtype == "AUDIO_FRAME":
                data = msg.get("payload", {}).get("data", "")
                pcm = base64.b64decode(data) if data else b""
                if CURRENT["started"] is None:
                    CURRENT["started"] = round(time.monotonic() - T0, 4)
                CURRENT["pcm"] += pcm
                s = to_samples(pcm)
                CURRENT["frames"].append({
                    "t": round(time.monotonic() - T0, 4),
                    "bytes": len(pcm),
                    "during_tts_send": speaking,
                    "saarthi_band": band_energy(s, SAARTHI_BAND, MIC_SAMPLE_RATE),
                    "user_band": band_energy(s, USER_BAND, MIC_SAMPLE_RATE),
                })
                log("audio_frame", bytes=len(pcm), during_tts_send=speaking)

            elif mtype == "AUDIO_END":
                log("audio_end", during_tts_send=speaking)
                pcm = bytes(CURRENT["pcm"])
                turn = {
                    "index": len(TURNS),
                    "started": CURRENT["started"],
                    "ended": round(time.monotonic() - T0, 4),
                    "frame_count": len(CURRENT["frames"]),
                    "frames": CURRENT["frames"],
                    "analysis": analyse(pcm),
                }
                TURNS.append(turn)
                with wave.open(f"/app/echo_harness/received_turn_{turn['index']}.wav", "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(MIC_SAMPLE_RATE)
                    w.writeframes(pcm)
                CURRENT["frames"] = []
                CURRENT["pcm"] = bytearray()
                CURRENT["started"] = None
                if tts_task and not tts_task.done():
                    continue
                tts_task = asyncio.create_task(stream_tts(f"reply{len(TURNS)}"))

            elif mtype == "PONG":
                pass
            else:
                log("other", type=mtype)
    except WebSocketDisconnect:
        log("ws_close")
    except Exception as exc:  # noqa: BLE001
        log("ws_error", error=repr(exc))
