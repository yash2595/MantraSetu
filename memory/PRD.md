# MantraSetu Saarthi — Voice Assistant PRD

## Original problem statement
Fix Speech-to-Text (STT) issues in the MantraSetu project:
1. Inaccurate / garbled transcriptions.
2. Audio echo — the assistant hears its own spoken replies during voice conversations.

Scope is strictly limited to the Mantrasetu project folders. No other features requested.

## Architecture
```
/app/
├── final frontend mantrasetu/MantraSetu-Saarthi-main/      (React + Vite)
│   └── src/hooks/useSaarthiVoice.ts   ~3200 lines — mic capture, VAD, WS, TTS playback
├── FINAL ai Mantra setu/MantraSetu-Saarthi-feature-ai-intent-engine/   (FastAPI)
│   ├── app/api/websocket/router.py    WS /ws/voice, session start (sample_rate default 16000)
│   ├── app/voice/gateway.py           per-turn AudioBuffer, pre-STT VAD gate
│   └── app/voice/stt/inworld_stt_adapter.py   default STT provider = inworld
└── (root) assorted ad-hoc test scripts
```
Audio contract: frontend streams base64 PCM16 mono @ 16 kHz via `AUDIO_FRAME`; backend wraps in
WAV @ session.sample_rate (16000) and posts to InWorld STT. TTS returns LINEAR16 @ 24 kHz.

**Environment note:** this container has NO `/app/frontend` or `/app/backend`, so supervisor
`frontend`/`backend` are FATAL. The app cannot be run here; verification is type-check + unit
math only. Live audio testing must be done in the user's browser.

## Implemented

### 2026-06 — STT accuracy + echo fix (`src/hooks/useSaarthiVoice.ts`)
Root causes found and fixed:
1. **Mic wired into the speaker graph.** The capture `ScriptProcessorNode` was connected to
   `audioContextRef.current.destination` — the *same* AudioContext used to play Saarthi's TTS.
   Now the mic has its own isolated `micAudioCtxRef` context and the chain terminates in a
   `GainNode` with `gain = 0`.
2. **Crude 24 kHz → 16 kHz decimation.** The mic ran in the 24 kHz playback context and was
   decimated by a box-average of ~1.5 samples with no anti-alias filter. Measured: only ~14 dB
   SNR on a 3 kHz component (consonant band) vs ~42 dB for a native 16 kHz pass-through.
   Now the mic context is requested at 16000 Hz so `downsampleTo16kHz` is a no-op; a 7 kHz
   lowpass biquad is inserted only when the browser refuses 16 kHz (Safari).
3. **Echo tail self-triggering.** Acoustic cooldown raised 450 ms → 700 ms
   (`ACOUSTIC_COOLDOWN_MS`) and a 600 ms `ECHO_GUARD_MS` window added after re-arming during
   which the VAD threshold is raised by +8.0, so the reverb tail of Saarthi's reply cannot set
   `userHasSpoken`.
4. **Echo audio entering the pre-roll.** The 3-frame pre-roll buffer was filled unconditionally,
   including while Saarthi was speaking, then flushed to STT at the start of the next utterance.
   It is now only filled while `stateRef.current === 'listening'`.
5. **Frame/VAD gating hardened.** `AUDIO_FRAME` streaming and VAD speech detection now also
   require `!isPlayingRef.current`.
6. **Barge-in / fallback hygiene.** `stopSpeaking()` and the 20 s fallback timeout now reset
   `stateRef`, byte counters, pre-roll and VAD state instead of only calling `setSaarthiState`.
7. **Teardown.** `micAudioCtxRef` is closed in both `disableVoice()` and the mic effect cleanup;
   `vadAudioCtxRef` now aliases the single mic context (one capture graph instead of two).

Verification: `npx tsc -p tsconfig.app.json --noEmit` clean; resampler SNR measured numerically.
Live browser verification PENDING with user.

## Backlog
- P1: Live browser validation of echo + transcription accuracy (needs user's mic/speakers).
- P2: Backend passes `language: "hi"` to InWorld while the adapter expects `hi-IN` style codes
  (`inworld_stt_adapter.py`) — worth confirming against InWorld docs.
- P2: `useSaarthiVoice.ts` is ~3200 lines; split mic/VAD, WS transport and TTS playback.
- P2: Migrate deprecated `ScriptProcessorNode` to `AudioWorkletNode`.
