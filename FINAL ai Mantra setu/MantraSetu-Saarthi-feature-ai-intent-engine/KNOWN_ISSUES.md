# Known Issues

## Voice & AI Intent Engine

### 1. InWorld STT Provider - Empty API Responses (2026-08-28 & 2026-08-29)
* **Date:** 2026-08-28 (First observed) | Re-checked: 2026-08-29
* **Component:** `InWorldSTTAdapter` (via `/stt/v1/recognize` endpoint)
* **Symptom:** The API repeatedly returns HTTP 200 OK with `Content-Length: 0` and an empty response body instead of valid JSON transcriptions. Latency has also severely degraded, with average Time to First Byte (TTFB) hitting **2046ms** (compared to ~220ms previously).
* **Verification:** Confirmed via fresh isolated live validation test (`test_inworld_stt_live_validation.py`) on 4 real human WAV files. All 4 requests failed with the same `Empty-200` bug.
* **Current Mitigation:** The system has been switched to use Groq as the default STT provider. `DEFAULT_STT_PROVIDER=groq` is set in `.env` and is the permanent active default.
* **Next Steps:** STT migration to InWorld is **PAUSED indefinitely**. Do not retry InWorld STT tests automatically or toggle the environment variable. Report this issue with reproducible parameters (multipart WAV files,Basic Auth headers, `/stt/v1/recognize` endpoint) to InWorld support channels/Discord. We will only revisit if/when InWorld confirms a fix.

## Pending Manual Verification Items

- **SUBMIT_FORM Voice Trigger (BUG-14 Fix)**: Verified via static code analysis (backend directive + frontend `useSaarthiVoice.ts` listener match). Actual end-to-end live browser click and form submit data persistence remain to be manually verified in a human walkthrough.

## Architecture & Scale-Out Notes

- **`onboarding_state` Single-Node Memory Scope**: `onboarding_state` (`AISessionManager`) is currently single-node in-memory only, NOT Redis-backed. This is intentional for single-node deployments. If/when we scale to multiple backend replicas, `onboarding_state` MUST be migrated to a Redis-backed store (similar pattern to `ProductionWebSocketManager`, which already exists but is not yet wired into `router.py`) — otherwise users will silently lose onboarding progress when requests land on a different node mid-flow.

