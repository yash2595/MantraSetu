# Known Issues

## Voice & AI Intent Engine

### 1. InWorld STT Provider - Empty API Responses [RESOLVED]
* **Status:** Resolved | Resolved date: 2026-09-04
* **Root Cause:** Historical issue was caused by calling an incorrect endpoint (`/stt/v1/recognize` with multipart audio) rather than the documented synchronous REST endpoint `https://api.inworld.ai/stt/v1/transcribe` with JSON base64 LINEAR16 audio data. In addition, HTTP exceptions previously swallowed in the adapter masked underlying 400 Bad Request / 5xx failures as empty strings.
* **Resolution:** Synchronous `/stt/v1/transcribe` integration verified live on audio samples. Hindi filler words ("हम्म", "हम्म।") added to noise filter; adapter updated to distinguish HTTP status codes, retry transient 5xx/timeouts once, and bubble `stt_error` to gateway for honest technical error feedback rather than attributing failures to user silence.

## Pending Manual Verification Items

- **SUBMIT_FORM Voice Trigger (BUG-14 Fix)**: Verified via static code analysis (backend directive + frontend `useSaarthiVoice.ts` listener match). Actual end-to-end live browser click and form submit data persistence remain to be manually verified in a human walkthrough.

## Architecture & Scale-Out Notes

- **`onboarding_state` Single-Node Memory Scope**: `onboarding_state` (`AISessionManager`) is currently single-node in-memory only, NOT Redis-backed. This is intentional for single-node deployments. If/when we scale to multiple backend replicas, `onboarding_state` MUST be migrated to a Redis-backed store (similar pattern to `ProductionWebSocketManager`, which already exists but is not yet wired into `router.py`) — otherwise users will silently lose onboarding progress when requests land on a different node mid-flow.

