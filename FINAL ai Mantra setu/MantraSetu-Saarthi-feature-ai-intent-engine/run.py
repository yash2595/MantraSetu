"""MantraSetu AI Backend — production/development server launcher.

Use this script instead of invoking ``uvicorn`` directly when running on Windows
so that the asyncio ProactorEventLoop (required by Playwright) is active for the
full process lifetime.

Usage:
    python run.py            # production (no reload)
    python run.py --reload   # development with auto-reload
"""

from __future__ import annotations

import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Step 1: Set the Windows ProactorEventLoop policy FIRST.
# This must happen before any asyncio machinery (including uvicorn internals)
# creates or touches an event loop.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ---------------------------------------------------------------------------
# Step 2: Import uvicorn AFTER the policy is installed.
# ---------------------------------------------------------------------------
import uvicorn

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MantraSetu AI Backend server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        # ---------------------------------------------------------------
        # loop="none" tells uvicorn to skip its own loop factory entirely.
        # This means uvicorn will call asyncio.run() which respects the
        # WindowsProactorEventLoopPolicy we set above, giving Playwright
        # a ProactorEventLoop that supports create_subprocess_exec.
        # ---------------------------------------------------------------
        loop="none",
    )
