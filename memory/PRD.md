# MantraSetu Saarthi — Voice Assistant PRD

## Original problem statement
Fix Speech-to-Text (STT) issues in the MantraSetu project:
1. Inaccurate / garbled transcriptions.
2. Audio echo — the assistant hears and transcribes its own spoken replies during voice
   conversations with spoken replies.

Scope is strictly limited to the Mantrasetu project folders. No other features requested.

## Architecture
```
/app/
├── final frontend mantrasetu/MantraSetu-Saarthi-main/      (React + Vite)
│   └── src/hooks/useSaarthiVoice.ts   ~3280 lines — mic capture, VAD, WS, TTS playback
├── FINAL ai Mantra setu/MantraSetu-Saarthi-feature-ai-intent-engine/   (FastAPI)
│   ├── app/api/websocket/router.py    WS /ws/voice, session start (sample_rate default 16000)
│   ├── app/voice/gateway.py           per-turn AudioBuffer, pre-STT VAD gate
│   └── app/voice/stt/inworld_stt_adapter.py   default STT provider = inworld
└── echo_harness/                      voice echo measurement harness (added 2026-06)
```
Audio contract: frontend streams base64 PCM16 mono @ 16 kHz via `AUDIO_FRAME`; backend wraps in
WAV @ session.sample_rate (16000) and posts to InWorld STT. TTS returns LINEAR16 @ 24 kHz.

### Environment constraints (important for any future agent)
- This container has NO `/app/frontend` or `/app/backend`, so supervisor `frontend`/`backend` are
  permanently FATAL. Expected. The projects live in the named folders above.
- The REAL backend cannot run here: needs `INWORLD_API_KEY`, `GROQ_API_KEY` and a MongoDB Atlas
  URI that we do not have.
- Chromium in this container has NO audio input device. `getUserMedia` fails with
  `NotFoundError`, and Chrome's `--use-fake-device-for-media-capture` /
  `--use-file-for-fake-audio-capture` flags do NOT work here (verified across chromium and
  headless-shell channels, and after installing PulseAudio with a null sink). Don't retry them.

## Implemented

### 2026-06 — STT accuracy + speaker echo fix (`src/hooks/useSaarthiVoice.ts`)
Root causes found and fixed:
1. **Mic wired into the speaker graph.** The capture `ScriptProcessorNode` was connected to
   `audioContextRef.current.destination` — the *same* AudioContext used to play Saarthi's TTS.
   The mic now has its own isolated `micAudioCtxRef` context and the chain terminates in a
   `GainNode` with `gain = 0`.
2. **Crude 24 kHz → 16 kHz decimation.** The mic ran in the 24 kHz playback context and was
   decimated by a box-average of ~1.5 samples with no anti-alias filter. Measured: only ~14 dB
   SNR on a 3 kHz component (consonant band) vs ~42 dB for a native 16 kHz pass-through.
   The mic context is now requested at 16000 Hz so `downsampleTo16kHz` is a no-op; a 7 kHz
   lowpass biquad is inserted only when the browser refuses 16 kHz (Safari).
3. **Echo audio entering the pre-roll.** The 3-frame pre-roll ring was filled unconditionally,
   including while Saarthi was speaking, then flushed to STT at the start of the next utterance —
   gluing up to ~768 ms of Saarthi's voice in front of the user's words. It is now only filled
   while `stateRef.current === 'listening'`.
4. **Echo tail self-triggering the VAD.** A first attempt used a FIXED 600 ms elevated-threshold
   guard plus a 700 ms cooldown; the harness proved it still leaked 2 echo buffers because room
   reverb outlived the fixed window. Replaced with an **adaptive echo-tail hold**: after playback
   the mic stays gated until the measured input level actually decays back to the room noise
   floor (2 quiet ticks), hard-capped at `MAX_ECHO_TAIL_MS = 1500`. With this in place the
   acoustic cooldown was restored to **450 ms**, so responsiveness matches the original.
5. **Frame/VAD gating hardened.** `AUDIO_FRAME` streaming and VAD detection now also require
   `!isPlayingRef.current`.
6. **Barge-in / fallback hygiene.** `stopSpeaking()` and the 20 s fallback now reset `stateRef`,
   byte counters, pre-roll and VAD state instead of only calling `setSaarthiState`.
7. **Teardown.** `micAudioCtxRef` is closed in both `disableVoice()` and the mic effect cleanup;
   `vadAudioCtxRef` now aliases the single mic context (one capture graph instead of two).

Side benefit observed: VAD calibration no longer measures Saarthi's own echo as "room noise"
(baseline 3.5 instead of the clamped 10.0), so the speech threshold is 6.5 instead of 12.2 —
the VAD is now materially more sensitive to the actual user.

### Verification (2026-06)
`tsc -p tsconfig.app.json --noEmit` clean. Verified by `testing_agent` (report
`/app/test_reports/iteration_1.json`, frontend 100%) using a purpose-built harness in
`/app/echo_harness/`:

| | pre-fix (control) | fixed |
|---|---|---|
| frames streamed to STT | 52 | 15 |
| frames sent while Saarthi greeted a SILENT user | 13–15 | **0** |
| buffers containing Saarthi's own voice | **4 of 4** | **0** |
| clean user buffers | 0 | 1 |
| user utterance contamination | saarthi_band 0.0095 | saarthi_band 0.000016 |
| mic alive | false | true |

Harness design: real frontend + mock voice backend (`mock_voice_server2.py`) + an in-page
virtual loudspeaker room (`room_sim2.js`) that bridges every AudioContext destination back into
a synthetic microphone through 0.18 s playout latency and a ~1 s reverb tail at full gain.
Saarthi's TTS is broadband noise at 2500–5000 Hz, the simulated user at 200–1500 Hz, so the
backend's Goertzel band-energy filter identifies whose voice reached STT.
Run with `bash /app/echo_harness/run_echo_test.sh fixed|prefix|restore`.

**Caveat:** the synthetic mic bypasses the browser's hardware echo canceller, so the harness
measures the worst case (full-gain coupling, no AEC) — harsher than any real device. Real-device
confirmation on a loudspeaker is still worth doing.

## Backlog
- P0 (BLOCKED on user): complexity refactor of `app/api/websocket/router.py`
  `voice_websocket_endpoint()` — genuinely 738 lines, cyclomatic complexity 162, 79 locals,
  11 nesting levels; `_handle_audio_end()` 218 lines / complexity 46. Deliberately NOT started:
  this is the same voice path as the echo fix above and the backend cannot be executed in this
  container, so a blind refactor would very likely silently reintroduce the echo bug. The user's
  answer on whether to proceed was self-contradictory (selected both "do it" and "skip it") and
  is being re-clarified. Also deferred with it: `apply_pandit()` (17 args → Pydantic model),
  `conversation_chat()`, `health_check()`, `browser_executor.execute_action()` (8 nesting levels).
- P1: Real-device confirmation of the echo fix on loudspeaker + headphones (needs user hardware).
- P2: Backend passes `language: "hi"` to InWorld while the adapter expects `hi-IN` style codes
  (`inworld_stt_adapter.py`) — worth confirming against InWorld docs.
- P2: `useSaarthiVoice.ts` is ~3280 lines; split into capture / playback / VAD / WS transport.
- P2: Migrate deprecated `ScriptProcessorNode` to `AudioWorkletNode` (capture currently runs on
  the main thread, so React re-renders can jitter audio frames).
- P2: `pydantic_settings` is not installed in this environment, so several `app/` modules cannot
  be imported for runtime testing (only static analysis works).
- P3: Pre-existing dev-only React warning: "props object containing a key prop is being spread
  into JSX" on `Link` components (2 occurrences). Not related to the voice path.
- P3: Emit echo-tail release times as telemetry to catch tail regressions in the field.
- P3: `/app/echo_harness/` is untracked and will be lost on pod restart. Move to
  `tools/echo-harness/` inside the frontend repo if it should be preserved.

## Changelog

### 2026-06 — Code quality report remediation (verified, `iteration_2.json`, 100% both sides)
Applied only the findings that survived verification. **7 of the report's "critical" items were
scanner false positives** and were deliberately not "fixed":
- The 7 claimed `eval()` code-injection vulnerabilities do not exist. There is zero raw `eval(`
  in the codebase. `pandit_onboarding.py:377` is already `ast.literal_eval`; two test hits
  matched the substring `eval` inside the word *retri**eval*** (`test_..._hybrid_retrieval`,
  `test_semantic_ranking_and_retrieval`).
- Several "hardcoded secrets" are mock literals (`api_key="mock_inworld_key"`), i.e. exactly the
  mocking the report recommends. `user_service.py:169` `hashed_password="oauth2_google"` is an
  OAuth shadow-user placeholder; `verify_password` uses `bcrypt.checkpw`, so a non-bcrypt hash
  cannot authenticate.
- "Insecure random" at `echo_harness/mock_voice_server2.py:51` is the test harness using
  `random.seed(7)` to generate a deterministic test tone — non-security by design.

Real fixes applied:
| Fix | Detail |
|---|---|
| Deleted 3 null-byte-corrupted orphans | `old_ai_orchestrator.py` (7272), `old_pandit_onboarding.py` (26932), `test_asyncmock.py` (175); confirmed imported nowhere |
| Stripped UTF-8 BOM | `final backend mantrasetu/.../app/database/verification_db.py` |
| Fixed 2 real `SyntaxError`s | f-string backslashes in `auth_browser_verification.py:79`, `auth_verification_test.py:98` (extracted `root_div` var); also narrowed 4 bare `except:` to `json.JSONDecodeError` |
| MD5 → SHA-256 | `app/tools/tool_cache.py` `_hash_key()` + docstring |
| Undefined names: 48 → 0 | added missing `Any`/`Optional` imports across 10 files; added `ValidationError` import to `app/archive/voice_service.py` (3 real `NameError` raise sites) |
| 3 methods missing `self` | `ConfigurationManager.reload_configuration`, `DashboardManager.get_dashboard_snapshot`, `SystemDiagnostics.generate_diagnostics_report` (now delegates to `generate_diagnostics`) |
| Removed dead expression | `cache_manager.py:281` `text=cleaned_prompt if "cleaned_prompt" in locals() else cleaned_text` → `text=cleaned_text` (condition was always false) |
| Real hardcoded secret | `test_rate_limiting.py:6` `VOICE_TICKET_SECRET` → `os.environ` |

Verification: `compileall` exit 0 on both backends; `pyflakes app/` undefined names 0 (was 48);
zero null-byte/BOM `.py` files remain; `app/api/websocket/router.py` byte-unchanged; echo-fix
regression harness re-run clean (ECHO_DETECTED=false, MIC_ALIVE=true).

