"""Interactive CLI helpers (run by a human, not the agent)."""

from __future__ import annotations

import asyncio
import json
import sys

from .browser import BrowserSession
from .config import Settings
from .errors import DoomScrollError


def login_main() -> None:
    """Headful login: opens a visible browser, you sign in, the profile persists."""
    force = "--force" in sys.argv
    settings = Settings.from_env()
    print("⚠️  Automating Instagram violates its ToS — account ban/lock risk is yours.")
    print(f"Profile will persist at: {settings.profile_dir}")
    print("A browser window will open. Sign in, then leave it — it closes itself.\n")
    session = BrowserSession(settings)
    try:
        result = asyncio.run(session.login(force=force))
        print(json.dumps(result, indent=2))
    except DoomScrollError as e:
        print(json.dumps(e.to_dict(), indent=2))
        sys.exit(1)


def status_main() -> None:
    settings = Settings.from_env()
    print(json.dumps(asyncio.run(BrowserSession(settings).login_status()), indent=2))
