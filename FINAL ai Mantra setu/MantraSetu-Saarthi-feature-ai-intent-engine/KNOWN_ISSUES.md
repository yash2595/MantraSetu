# Known Issues

## Voice & AI Intent Engine

### 1. InWorld STT Provider - Empty API Responses [RESOLVED]
* **Status:** Resolved | Resolved date: 2026-09-04
* **Root Cause:** Historical issue was caused by calling an incorrect endpoint (`/stt/v1/recognize` with multipart audio) rather than the documented synchronous REST endpoint `https://api.inworld.ai/stt/v1/transcribe` with JSON base64 LINEAR16 audio data. In addition, HTTP exceptions previously swallowed in the adapter masked underlying 400 Bad Request / 5xx failures as empty strings.
* **Resolution:** Synchronous `/stt/v1/transcribe` integration verified live on audio samples. Hindi filler words ("हम्म", "हम्म।") added to noise filter; adapter updated to distinguish HTTP status codes, retry transient 5xx/timeouts once, and bubble `stt_error` to gateway for honest technical error feedback rather than attributing failures to user silence.

### 2. Proper Name Mistranscriptions & Infinite Confirmation Loops [RESOLVED]
* **Status:** Resolved | Resolved date: 2026-09-04
* **Root Cause:** InWorld STT `transcribeConfig.language` was hardcoded to `"hi-IN"`. When transcribing consonant-ending English/Hinglish names, the Hindi ASR model applied inherent schwa vowel prolongation (e.g. "Utkarsh" -> "Utkarsha", "Navneet" -> "Navaneeta"). Additionally, rejecting a tentative confirmation ("Nahi, galat hai") repeatedly re-prompted the user to speak their name again, trapping them in an infinite voice loop.
* **Resolution:** Dynamic language switching implemented in `inworld_stt_adapter.py` (`"en-IN"` for name fields, `"hi-IN"` for conversational turns). Rejection circuit breaker added to `pandit_onboarding.py` (immediate typing fallback on 1st rejection for name fields, 2nd rejection for non-name fields) emitting `FILL_FORM` directive with `suggest_keyboard: True`. Fully covered by 16 automated tests.

### 3. Groq 1000 OTPM Rate Limit on Consecutive Turns [RESOLVED]
* **Status:** Resolved | Resolved date: 2026-09-04
* **Root Cause:** Groq free-tier limits cumulative output tokens to 1000 tokens per rolling minute. Multi-turn voice interactions where intent detection and response generation both emitted tokens exhausted this quota with HTTP 429.
* **Resolution:** Intent detection output capped at `max_tokens=150`, response generator capped at `max_tokens=512`. Resilient fallback chain configured with `Groq` -> `Gemini` (`gemini-3.6-flash`) -> `gpt-oss-20b` fallback failover.

### 4. Spoken Email Address Number Normalization & Hindi Transliteration [RESOLVED]
* **Status:** Resolved | Resolved date: 2026-09-04
* **Root Cause:** Spoken email addresses with compound numbers (e.g. "twelve thirty four"), multipliers (e.g. "double two double three"), or custom domain numbers remained as words, corrupting the email syntax. Additionally, InWorld STT operated in `hi-IN` mode during email collection, transcribing Latin email addresses into Devanagari Hindi text.
* **Resolution:** Dynamic STT language switching extended to email collection turns via `ALPHANUMERIC_FIELDS` (`"en-IN"` mode). Shared DRY helper `normalize_spoken_numbers()` implemented in `pandit_onboarding.py`, handling multipliers, compound numbers (teens and tens), tens+units combination with noisy punctuation/conjunctions (`twenty, one` -> `21`), and single digits. Refactored phone number normalization to share the same helper, covered with 18 unit tests (0 regressions).


## Pending Manual Verification Items

- **SUBMIT_FORM Voice Trigger (BUG-14 Fix)**: Verified via static code analysis (backend directive + frontend `useSaarthiVoice.ts` listener match). Actual end-to-end live browser click and form submit data persistence remain to be manually verified in a human walkthrough.

## Architecture & Scale-Out Notes

- **`onboarding_state` Single-Node Memory Scope**: `onboarding_state` (`AISessionManager`) is currently single-node in-memory only, NOT Redis-backed. This is intentional for single-node deployments. If/when we scale to multiple backend replicas, `onboarding_state` MUST be migrated to a Redis-backed store (similar pattern to `ProductionWebSocketManager`, which already exists but is not yet wired into `router.py`) — otherwise users will silently lose onboarding progress when requests land on a different node mid-flow.

## Engineering Backlog & Follow-Up Items

1. **Provider Sliding-Window Rate Limiter**:
   - Add a centralized token-bucket / sliding-window tracking mechanism for external LLM providers (e.g. Groq 1000 OTPM on-demand limit) across concurrent requests and turns to proactively queue or route requests before encountering HTTP 429s.
2. **Gemini Model Periodic Verification**:
   - Periodically monitor `gemini-3.6-flash` against Google GenAI API release lifecycle / deprecation notices to ensure long-term stability and migrate to designated GA versions as announced.
3. **`VoiceGatewayIntegration` Dead-Code Resolution**:
   - Clean up or deprecate orphaned `VoiceGatewayIntegration` in `app/orchestrator/voice_gateway.py` once live voice testing confirms the primary `VoiceGateway` (`app/voice/gateway.py`) flow is fully solidified.


