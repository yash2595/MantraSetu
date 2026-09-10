# MantraSetu "Saarthi" Voice Assistant — PRD / Working Notes

## Original problem (2026-09-10)
Voice assistant stuck in an infinite reconnect loop. Frontend logs: WS connects →
CONNECTED + greeting AI_RESPONSE → ERROR {code:UPSTREAM_ERROR, message:"Upstream closed
connection"} → WS close (1006) → auto-reconnect → repeats forever. User also flagged
pre-existing STT accuracy + audio echo concerns. Upstream provider: Inworld.

## Architecture (3-tier, runs on user's local machine; NOT wired to this pod's supervisor)
- Frontend: `final frontend mantrasetu/MantraSetu-Saarthi-main` (React/Vite, `useSaarthiVoice.ts`)
- Proxy backend: `final backend mantrasetu/mantrasetu-saarthi-backend-main` (FastAPI, port 8000, `/ws/voice` → proxies to AI engine)
- AI intent engine: `FINAL ai Mantra setu/MantraSetu-Saarthi-feature-ai-intent-engine` (FastAPI, port 8002, Inworld STT/TTS, Groq LLM)
- Real API keys (Inworld/Groq/Gemini/Mongo) live only in the user's local `.env` files; absent in this pod.

## Fixed (2026-09-10)
- **Reconnect loop (P0) — ROOT CAUSE + FIX, verified.**
  - Cause: cached greeting TTS was sent as ONE ~1.28 MB base64 AUDIO_CHUNK. The proxy's
    `websockets.connect()` used the python-websockets default `max_size` (1 MiB) → upstream
    frame rejected (close 1009) → proxy emitted UPSTREAM_ERROR & closed → client reconnected
    → cache hit → same oversized frame → infinite loop.
  - Fix 1 (proxy): `app/services/voice_service.py` → `websockets.connect(ai_ws_url, max_size=None, ping_interval=20, ping_timeout=60)`.
  - Fix 2 (defense-in-depth, AI engine): `app/voice/tts/voice_response_pipeline.py` cache-hit
    path now yields ~48 KB sub-chunks instead of a single giant frame.
  - Verified via `test_voice_proxy_bigframe.py` (mock upstream, no keys). Without fix →
    reproduces exact UPSTREAM_ERROR; with fix → forwards 1,280,000-byte frame, PASS.

## Speaker echo — VERIFIED FIXED (2026-09-10) via echo_harness (no keys)
- Ran `/app/echo_harness/speaker_echo_test.mjs` (Playwright: real frontend + mock backend
  `mock_voice_server2.py` + simulated loudspeaker->mic room `room_sim2.js`) against the CURRENT
  `useSaarthiVoice.ts`. Testing agent report: /app/test_reports/iteration_4.json.
- Result: ECHO_DETECTED=false, ECHO_BUFFERS=0, frames_streamed_during_silent_greeting_phase=0,
  frames_arriving_while_tts_streaming=0, MIC_ALIVE=true (clean user buffer streamed). Saarthi does
  NOT transcribe her own greeting; real user speech still reaches STT.
- Working guards in `useSaarthiVoice.ts`: AUDIO_FRAME gated on `state==='listening' && !isPlayingRef`,
  muted mic sink during speaking, pre-roll cleared unless listening, ~450ms acoustic cooldown before re-arming mic.
- To re-run: start `uvicorn mock_voice_server2:app` on :8000 and `npx vite` on :3000, then
  `cd /app/echo_harness && PLAYWRIGHT_BROWSERS_PATH=/pw-browsers node speaker_echo_test.mjs`.
  Do NOT use run_echo_test.sh (it overwrites the hook with a snapshot).

## STT accuracy — still needs real Inworld keys
- STT transcription accuracy uses live Inworld and cannot be exercised in this pod (no keys).
  Retest on your local env.

## Backlog / next
- P1: Validate STT accuracy + echo end-to-end on the user's local env (needs Inworld keys).
- P1: Add `test_voice_proxy_bigframe.py` to CI to guard the max_size regression.
- P2: Consider capping/streaming all AUDIO_CHUNK sizes uniformly at the AI-engine source.
