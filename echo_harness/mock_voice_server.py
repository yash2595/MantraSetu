"""Mock MantraSetu voice backend used to measure microphone/TTS echo from the browser.

Speaks the exact WS protocol `useSaarthiVoice.ts` expects, records the timestamp of every
AUDIO_FRAME the frontend sends, and exposes the recording at GET /_report.

Echo definition used here: any AUDIO_FRAME (or AUDIO_END) that arrives while Saarthi's TTS is
being played back by the browser means the mic is feeding Saarthi's own voice to STT.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import struct
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EVENTS: list[dict] = []
T0 = time.monotonic()


def log(kind: str, **extra) -> None:
    EVENTS.append({"t": round(time.monotonic() - T0, 4), "kind": kind, **extra})


TTS_SAMPLE_RATE = 24000
TTS_SECONDS = 3.0
TTS_CHUNKS = 12


def build_tts_pcm() -> bytes:
    """Loud 24kHz LINEAR16 tone stack standing in for Saarthi's spoken reply."""
    n = int(TTS_SAMPLE_RATE * TTS_SECONDS)
    out = bytearray()
    for i in range(n):
        t = i / TTS_SAMPLE_RATE
        env = 0.6 + 0.4 * math.sin(2 * math.pi * 3.0 * t)
        s = env * (
            0.5 * math.sin(2 * math.pi * 180 * t)
            + 0.3 * math.sin(2 * math.pi * 520 * t)
            + 0.2 * math.sin(2 * math.pi * 1400 * t)
        )
        out += struct.pack("<h", int(max(-1.0, min(1.0, s)) * 30000))
    return bytes(out)


TTS_PCM = build_tts_pcm()


@app.post("/voice/ticket")
async def voice_ticket():
    return {"ticket": "harness-ticket", "type": "guest"}


@app.get("/_report")
async def report():
    return JSONResponse({"events": EVENTS, "tts_seconds": TTS_SECONDS})


@app.post("/_reset")
async def reset():
    EVENTS.clear()
    return {"ok": True}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str):
    return JSONResponse({})


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    await ws.accept()
    log("ws_open")
    speaking = False

    async def stream_tts():
        nonlocal speaking
        await ws.send_text(json.dumps({
            "type": "AI_RESPONSE",
            "request_id": "harness-req",
            "payload": {
                "content": "Namaste, main Saarthi hoon. Aapki kaise madad kar sakta hoon?",
                "navigation_directive": {"action": None, "target": None, "intent": "CHAT"},
            },
        }))
        speaking = True
        log("tts_playback_start")
        step = len(TTS_PCM) // TTS_CHUNKS
        # Byte-align to 16-bit sample boundaries
        step -= step % 2
        for idx in range(TTS_CHUNKS):
            start = idx * step
            end = len(TTS_PCM) if idx == TTS_CHUNKS - 1 else start + step
            is_final = idx == TTS_CHUNKS - 1
            await ws.send_text(json.dumps({
                "type": "AUDIO_CHUNK",
                "request_id": "harness-req",
                "payload": {
                    "data": base64.b64encode(TTS_PCM[start:end]).decode(),
                    "sample_rate": TTS_SAMPLE_RATE,
                    "encoding": "LINEAR16",
                    "is_final": is_final,
                },
            }))
            log("tts_chunk_sent", idx=idx, is_final=is_final)
            await asyncio.sleep(TTS_SECONDS / TTS_CHUNKS)
        # Browser is still draining its scheduled buffers for roughly one chunk more
        await asyncio.sleep(TTS_SECONDS / TTS_CHUNKS)
        speaking = False
        log("tts_playback_end")

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
                # Greeting turn: Saarthi speaks first, exactly like the real app
                tts_task = asyncio.create_task(stream_tts())

            elif mtype == "AUDIO_FRAME":
                data = msg.get("payload", {}).get("data", "")
                log("audio_frame", bytes=len(base64.b64decode(data)) if data else 0,
                    during_tts=speaking)

            elif mtype == "AUDIO_END":
                log("audio_end", during_tts=speaking)
                if tts_task and not tts_task.done():
                    continue
                tts_task = asyncio.create_task(stream_tts())

            elif mtype == "PONG":
                pass
            else:
                log("other", type=mtype)
    except WebSocketDisconnect:
        log("ws_close")
    except Exception as exc:  # noqa: BLE001
        log("ws_error", error=repr(exc))
