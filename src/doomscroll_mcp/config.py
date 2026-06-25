"""Configuration: humanization + browsing modes.

Passive humanization is always on (no account side effects). Active engagement
(likes) is opt-in, off by default, and rate-limited — it mutates the user's
account and is a primary Instagram spam-detection trigger.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

# Browsing modes (AD5). Agents pick a mode; tests use fast_test to avoid 6s/reel.
MODES = ("fast_test", "normal_passive", "conservative")


@dataclass(frozen=True)
class HumanizeConfig:
    # passive — always on, no account side effects
    scroll_delay_range: tuple[float, float] = (2.0, 6.0)     # seconds between scrolls
    watch_duration_range: tuple[float, float] = (1.0, 5.0)   # "watch" pause per reel
    scroll_jitter: bool = True
    session_max_reels: int = 200                             # hard per-session cap
    cooldown_after_session: float = 0.0                      # seconds before next session
    # active — opt-in, risky, mutates the account
    enable_likes: bool = False
    like_probability: float = 0.0                            # 0..1

    @classmethod
    def for_mode(cls, mode: str) -> HumanizeConfig:
        """Preset configs per browsing mode."""
        if mode == "fast_test":
            # near-instant; for tests and dev only, NOT bot-safe
            return cls(
                scroll_delay_range=(0.0, 0.05),
                watch_duration_range=(0.0, 0.05),
                scroll_jitter=False,
                cooldown_after_session=0.0,
            )
        if mode == "conservative":
            return cls(
                scroll_delay_range=(4.0, 10.0),
                watch_duration_range=(3.0, 9.0),
                session_max_reels=80,
                cooldown_after_session=300.0,
            )
        # normal_passive — the default
        return cls()


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Profile dir persists the Playwright login between runs."""

    profile_dir: Path
    fixtures_dir: Path
    mode: str = "normal_passive"
    humanize: HumanizeConfig = field(default_factory=HumanizeConfig)
    # Dump raw IG network JSON for replay/debug (AD4). OFF by default: the
    # payloads are unbounded and carry a logged-in session's feed data. Opt in
    # with DOOMSCROLL_CAPTURE_FIXTURES=1.
    capture_fixtures: bool = False
    # The X-IG-App-ID header IG's own web client sends; required by the internal
    # search API. This is the *public* web app id (same for every visitor, not a
    # secret, stable for years) — not your account. Hardcoded as the default but
    # overridable via DOOMSCROLL_IG_APP_ID in case Instagram ever rotates it, so
    # a change needs no code edit.
    ig_app_id: str = "936619743392459"
    # Hard ceiling on a single timed doomscroll() call, so an agent can't ask
    # the browser to run for hours. Override with DOOMSCROLL_MAX_DURATION_S.
    max_duration_s: int = 1800  # 30 minutes

    @classmethod
    def from_env(cls) -> Settings:
        base = Path(
            os.environ.get(
                "DOOMSCROLL_HOME",
                str(Path.home() / ".doomscroll-mcp"),
            )
        )
        mode = os.environ.get("DOOMSCROLL_MODE", "normal_passive")
        if mode not in MODES:
            mode = "normal_passive"
        capture = os.environ.get("DOOMSCROLL_CAPTURE_FIXTURES", "") in ("1", "true", "yes")
        app_id = os.environ.get("DOOMSCROLL_IG_APP_ID") or cls.ig_app_id
        try:
            max_dur = int(os.environ.get("DOOMSCROLL_MAX_DURATION_S", "") or cls.max_duration_s)
        except ValueError:
            max_dur = cls.max_duration_s
        return cls(
            profile_dir=base / "profile",
            fixtures_dir=base / "fixtures",
            mode=mode,
            humanize=HumanizeConfig.for_mode(mode),
            capture_fixtures=capture,
            ig_app_id=app_id,
            max_duration_s=max(1, max_dur),
        )

    def with_mode(self, mode: str) -> Settings:
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
        return replace(self, mode=mode, humanize=HumanizeConfig.for_mode(mode))
