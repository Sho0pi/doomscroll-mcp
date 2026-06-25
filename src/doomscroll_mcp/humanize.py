"""Passive humanization — randomized timing, scroll jitter, session caps.

Reduces (does not eliminate) bot-detection risk. Returns timing state so the
caller can report to the agent why it is waiting or capped (AD5).
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

from .config import HumanizeConfig


@dataclass
class SessionState:
    reels_seen: int = 0
    capped: bool = False
    cooldown_remaining: float = 0.0
    total_wait_s: float = 0.0


class Humanizer:
    def __init__(self, cfg: HumanizeConfig) -> None:
        self.cfg = cfg
        self.state = SessionState()

    def _rand(self, lo_hi: tuple[float, float]) -> float:
        lo, hi = lo_hi
        return random.uniform(lo, hi) if hi > lo else lo

    async def scroll_pause(self) -> float:
        d = self._rand(self.cfg.scroll_delay_range)
        await asyncio.sleep(d)
        self.state.total_wait_s += d
        return d

    async def watch(self) -> float:
        d = self._rand(self.cfg.watch_duration_range)
        await asyncio.sleep(d)
        self.state.total_wait_s += d
        return d

    def scroll_delta(self, base: int = 800) -> int:
        if not self.cfg.scroll_jitter:
            return base
        # variable distance, occasional shorter "re-read" scroll-up
        if random.random() < 0.08:
            return -random.randint(150, 400)
        return base + random.randint(-200, 400)

    def note_reel(self) -> None:
        self.state.reels_seen += 1
        if self.state.reels_seen >= self.cfg.session_max_reels:
            self.state.capped = True
            self.state.cooldown_remaining = self.cfg.cooldown_after_session

    @property
    def cap_reached(self) -> bool:
        return self.state.capped

    def timing_state(self) -> dict:
        return {
            "reels_seen": self.state.reels_seen,
            "session_max": self.cfg.session_max_reels,
            "capped": self.state.capped,
            "cooldown_remaining_s": round(self.state.cooldown_remaining, 1),
            "total_wait_s": round(self.state.total_wait_s, 1),
        }
