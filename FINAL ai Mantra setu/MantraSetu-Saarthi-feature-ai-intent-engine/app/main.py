"""Application entrypoint for MantraSetu AI Assistant."""

import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Windows asyncio ProactorEventLoop policy
# ---------------------------------------------------------------------------
# Set the WindowsProactorEventLoopPolicy so that every event loop created in
# this process (including uvicorn's internal asyncio.run() call) is a
# ProactorEventLoop — required by Playwright's asyncio.create_subprocess_exec.
#
# NOTE: We set only the *policy* here, not the loop instance.
# The loop instance is created by uvicorn via asyncio.run(); setting the
# policy guarantees that loop will be a ProactorEventLoop.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.core.app import create_app

app = create_app()

