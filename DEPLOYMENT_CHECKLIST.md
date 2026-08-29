# MantraSetu Production Deployment Checklist

## Environment Files Setup
- [ ] Create `.env.production` files in Frontend, Backend, and AI Service using the provided templates.
- [ ] Fill in actual values for all `<PLACEHOLDERS>` in `.env.production` files.

## Secrets and Security
- [ ] **JWT_SECRET_KEY**: Generated a NEW, strong secret (e.g. `openssl rand -hex 32`) for the backend. (Do NOT use the local/dev secret).
- [ ] **VOICE_TICKET_SECRET**: Generated a secure ticket secret and confirmed it is an **EXACT MATCH** in both Backend and AI Service `.env.production` files.
- [ ] **API Keys**: Verified that Groq, Gemini, OpenAI, and ElevenLabs keys are for production accounts, not test/dev limits.

## Network and CORS
- [ ] **CORS_ORIGINS**: Set to real production domains only in Backend and AI Service (e.g. `https://mantrasetu.com,https://www.mantrasetu.com`). No `localhost` unless conditionally kept for a specific reason.
- [ ] **URLs**: Frontend points to production Backend and AI Service URLs. Backend points to production AI Service URL. AI Service points to production Backend URL.

## Database
- [ ] **MONGODB_URI**: Points to the production MongoDB cluster, not local database.

## Build and Version Control
- [ ] Checked that `.env.production` is NOT committed to git (verify `.gitignore` works).
- [ ] Built frontend (`npm run build`) and verified that the `dist/` output has the production API URLs baked in.
