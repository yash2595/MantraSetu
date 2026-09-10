"""Regression test: proxy must forward oversized upstream AUDIO_CHUNK frames.

Reproduces the "UPSTREAM_ERROR: Upstream closed connection" reconnect loop.
The cached greeting TTS audio is delivered as a single ~1.3 MB base64 frame. The
proxy's websockets client used the library default max_size (1 MiB), so that frame
tripped a 1009 close on the upstream leg -> client saw UPSTREAM_ERROR -> reconnect loop.

With the fix (max_size=None on websockets.connect), the big frame flows through.
No external API keys required: a local mock upstream stands in for the AI engine.
"""
import asyncio
import base64
import json
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ["AI_SERVICE_URL"] = "http://localhost:9902/api/v1"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"

import uvicorn
import websockets

BIG_AUDIO_BYTES = 960_000  # ~20s of 24kHz LINEAR16 mono -> ~1.28 MB once base64 encoded
BIG_B64 = base64.b64encode(b"\x01\x02" * (BIG_AUDIO_BYTES // 2)).decode()


async def mock_upstream(websocket):
    """Stand-in for the AI engine /ws/voice endpoint."""
    async for _msg in websocket:  # wait for the client's CONNECT frame
        await websocket.send(json.dumps({"type": "CONNECTED", "payload": {"status": "connected"}}))
        await websocket.send(json.dumps({
            "type": "AUDIO_CHUNK",
            "payload": {"sequence_number": 0, "is_final": True, "data": BIG_B64},
        }))
        # keep the connection open so the proxy does not close on its own
        await asyncio.sleep(5)
        break


async def run():
    # 1. start mock upstream (the AI engine)
    upstream = await websockets.serve(mock_upstream, "localhost", 9902)

    # 2. start the real proxy app
    from app.main import app
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.1)

    # 3. connect a client through the proxy and drive a CONNECT
    result = {"got_big": False, "got_error": False, "big_len": 0}
    try:
        async with websockets.connect("ws://127.0.0.1:8000/ws/voice?ticket=dummy", max_size=None) as ws:
            await ws.send(json.dumps({"type": "CONNECT", "payload": {"language": "hi"}}))
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                frame = json.loads(raw)
                if frame.get("type") == "AUDIO_CHUNK":
                    result["got_big"] = True
                    result["big_len"] = len(frame["payload"]["data"])
                    break
                if frame.get("type") == "ERROR":
                    result["got_error"] = True
                    result["error"] = frame.get("payload")
                    break
    except Exception as e:  # a connection drop here is the bug
        result["exception"] = repr(e)
    finally:
        server.should_exit = True
        await server_task
        upstream.close()
        await upstream.wait_closed()

    print("RESULT:", json.dumps(result))
    assert result["got_big"], f"Proxy failed to forward oversized frame: {result}"
    assert not result["got_error"], f"Proxy emitted UPSTREAM_ERROR (loop bug present): {result}"
    assert result["big_len"] > 1_048_576, f"Frame not actually oversized: {result['big_len']}"
    print("PASS: proxy forwarded a", result["big_len"], "byte frame (> 1 MiB) without dropping the connection.")


if __name__ == "__main__":
    asyncio.run(run())
