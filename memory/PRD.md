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

## Notes on echo/STT (already present in code, NOT E2E-verified here)
- Frontend already gates mic streaming to `state==='listening' && !isPlayingRef` and uses a
  muted mic sink + pre-roll guard (recent "Echo Fix" commits) so Saarthi should not transcribe
  her own TTS. Could not run the full Inworld pipeline in this pod (no keys), so accuracy/echo
  were not exercised end-to-end.

## Backlog / next
- P1: Validate STT accuracy + echo end-to-end on the user's local env (needs Inworld keys).
- P1: Add `test_voice_proxy_bigframe.py` to CI to guard the max_size regression.
- P2: Consider capping/streaming all AUDIO_CHUNK sizes uniformly at the AI-engine source.
