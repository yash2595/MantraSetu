# MantraSetu-Saarthi AI Backend

FastAPI backend skeleton for the MantraSetu AI Assistant.

## Tech Stack

- Python 3.11
- FastAPI
- Pydantic
- Pydantic Settings
- Uvicorn

## Project Structure

- `app/api`: HTTP layer, routers, and versioned endpoints.
- `app/services`: Business services and use-case orchestration.
- `app/planner`: Planning and workflow orchestration abstractions.
- `app/prompts`: Prompt templates and system instructions.
- `app/tools`: External tool adapters and integrations.
- `app/rag`: Retrieval-augmented generation components.
- `app/memory`: Memory and persistence abstractions.
- `app/models`: Pydantic models shared across layers.
- `app/utils`: Cross-cutting helpers, utilities, and exceptions.

## Current Scope
This scaffold does not implement business logic yet. It provides the application structure, configuration, and a health endpoint so the codebase is ready for feature development.

## LLM Layer

- `app/llm`: Provider-independent LLM boundary with factory-based provider selection.
- `app/llm/base.py` defines the abstract LLM contract.
- `app/llm/factory.py` resolves the provider from environment settings.
- `app/llm/providers/qwen.py` contains the current async Qwen implementation.
- The only public provider method is `generate()` so business logic stays provider-agnostic.

## Setup

1. Create a Python 3.11 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
copy .env.example .env
```

4. Run the API:

```bash
uvicorn app.main:app --reload
```

## Notes

- The application uses a factory-based FastAPI setup.
- Settings are centralized in `app/core/config.py`.
- Logging is configured through `app/core/logging.py`.
- A `/api/v1/health` endpoint is included for readiness checks.
- The LLM layer is ready for future OpenAI and Claude providers without changing callers.
