"""Typed, loop-recoverable errors (AD1).

The MCP's caller is an AI agent. Generic exceptions stall its loop — the agent
cannot tell "log in again" from "wait 5 minutes" from "selectors broke." Every
failure carries a machine-readable `code`, optional `retry_after`, a
`requires_headful` flag, and a suggested next tool so the agent can recover.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    AUTH_REQUIRED = "AUTH_REQUIRED"              # no valid session — call login()
    CHECKPOINT_REQUIRED = "CHECKPOINT_REQUIRED"  # IG challenge/2FA — headful login(force=True)
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"          # session cap hit — wait retry_after
    EXTRACTION_DEGRADED = "EXTRACTION_DEGRADED"  # some fields missing, partial data returned
    SELECTOR_BROKEN = "SELECTOR_BROKEN"          # IG layout changed, DOM fallback failed
    NO_REELS_FOUND = "NO_REELS_FOUND"            # empty feed / no results
    BROWSER_UNAVAILABLE = "BROWSER_UNAVAILABLE"  # Playwright/Chromium not installed
    PROFILE_LOCKED = "PROFILE_LOCKED"            # another session holds the profile lock
    BAD_SORT = "BAD_SORT"                        # unknown sort_by value


@dataclass
class DoomScrollError(Exception):
    """Structured error an agent can branch on."""

    code: ErrorCode
    message: str
    retry_after: float | None = None         # seconds to wait before retrying
    requires_headful: bool = False           # human must complete a visible browser step
    suggested_tool: str | None = None        # next MCP tool the agent should call
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["code"] = self.code.value
        d["error"] = True
        return d
