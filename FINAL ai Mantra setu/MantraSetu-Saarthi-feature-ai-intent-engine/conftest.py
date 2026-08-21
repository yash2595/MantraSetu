"""
Root conftest.py — loads .env before any test module is imported,
so os.getenv('GEMINI_API_KEY') and friends resolve correctly in tests.
Also ensures LLMProviderFactory singleton has Gemini registered.
"""
import os
import pathlib


def pytest_configure(config):
    """Load .env and bootstrap provider registrations before tests run."""
    # Step 1: Load .env into os.environ BEFORE any app modules are imported
    env_path = pathlib.Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Only set if not already in environment (don't override CI secrets)
                if key and key not in os.environ:
                    os.environ[key] = value

    # Step 2: Import providers module to trigger LLMProviderFactory singleton registration
    # (GeminiProvider and others are registered here at module-import time).
    # This must happen AFTER env vars are set so GeminiProvider.__init__ picks up the key.
    try:
        import app.dependencies.providers  # noqa: F401 — side-effect import
    except Exception as e:
        print(f"[conftest] Warning: could not import providers for factory registration: {e}")


def pytest_ignore_collect(collection_path, config):
    """Python 3.14 compatibility: accept both old fspath and new collection_path."""
    return None
