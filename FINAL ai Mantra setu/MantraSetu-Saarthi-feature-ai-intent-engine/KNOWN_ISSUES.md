# Known Issues

## Voice & AI Intent Engine

### 1. InWorld STT Provider - Empty API Responses (Active Investigation)
* **Status:** Under active investigation | First observed: 2026-08-28 | Latest re-check: 2026-09-01
* **Mandated Provider:** Inworld STT is the required STT provider for the project.
* **Component:** `InWorldSTTAdapter` (via `/stt/v1/recognize` endpoint)
* **Symptom:** The endpoint `https://api.inworld.ai/stt/v1/recognize` repeatedly returns HTTP 200 OK with `content-length: 0` and an empty response body when multipart WAV audio is submitted with Basic Auth, instead of returning JSON transcriptions.
* **Verification:** Re-verified via isolated diagnostic script (`scratch/investigate_inworld_stt.py`) across multiple authentication and request permutations.
* **Next Steps:** Review diagnostic findings with Yash to verify whether InWorld requires account/project provisioning adjustments, API key permissions update, or specific upstream configuration.

## Pending Manual Verification Items

- **SUBMIT_FORM Voice Trigger (BUG-14 Fix)**: Verified via static code analysis (backend directive + frontend `useSaarthiVoice.ts` listener match). Actual end-to-end live browser click and form submit data persistence remain to be manually verified in a human walkthrough.

## Architecture & Scale-Out Notes

- **`onboarding_state` Single-Node Memory Scope**: `onboarding_state` (`AISessionManager`) is currently single-node in-memory only, NOT Redis-backed. This is intentional for single-node deployments. If/when we scale to multiple backend replicas, `onboarding_state` MUST be migrated to a Redis-backed store (similar pattern to `ProductionWebSocketManager`, which already exists but is not yet wired into `router.py`) — otherwise users will silently lose onboarding progress when requests land on a different node mid-flow.

