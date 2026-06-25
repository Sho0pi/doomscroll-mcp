"""Browser session — persistent Playwright context with a login state machine.

The persistent context (`launch_persistent_context(user_data_dir=...)`) is what
makes "login once" work: the cookie/session lives in the profile dir and is
reused across runs. That convenience is also the main source of hidden bugs
(expired sessions, checkpoint pages, corrupted/locked profiles, concurrent
access, headless/headful drift), so this module adds:

  - a per-profile lock (AD3) so two MCP calls never share one profile dir
  - an explicit login state machine + checkpoint detection (AD3)
  - a headful repair path via login(force=True)
  - network-response capture wired in for extraction (UC1)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any

from .config import Settings
from .errors import DoomScrollError, ErrorCode
from . import extract
from .humanize import Humanizer

INSTAGRAM_URL = "https://www.instagram.com/"
REELS_URL = "https://www.instagram.com/reels/"

# Anti-detection. Instagram blocks logins from automation-flagged browsers, so we
# present as a normal desktop Chrome: real UA, a locale/timezone, no
# automation banner, and navigator.webdriver scrubbed.
_REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-default-browser-check",
]
# Playwright adds these flags; they are the giveaway IG keys on. Strip them.
_IGNORE_DEFAULT_ARGS = ["--enable-automation"]
# Runs before any page script: erase the webdriver tell + give plugins/languages.
_STEALTH_INIT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {runtime: {}};
"""


class LoginState(str, Enum):
    NO_BROWSER = "NO_BROWSER"
    LOGGED_OUT = "LOGGED_OUT"
    CHECKPOINT = "CHECKPOINT"
    LOGGED_IN = "LOGGED_IN"


class ProfileLock:
    """Cooperative cross-process lock on the profile dir (AD3)."""

    def __init__(self, profile_dir: Path) -> None:
        self.path = profile_dir / ".doomscroll.lock"

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            stale = self._stale()
            if stale:
                self.release()
                return self.acquire()
            raise DoomScrollError(
                ErrorCode.PROFILE_LOCKED,
                "Another DoomScroll session is using this browser profile.",
                retry_after=10.0,
                details={"lock": str(self.path)},
            )
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)

    def _stale(self) -> bool:
        try:
            pid = int(self.path.read_text().strip())
        except (ValueError, OSError):
            return True
        try:
            os.kill(pid, 0)  # signal 0 = liveness probe
            return False
        except OSError:
            return True

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


async def _detect_state(page: Any) -> LoginState:
    """Classify the current page into a login state.

    Signals (cheap, resilient to class-name churn):
      - login form / accounts/login URL  -> LOGGED_OUT
      - challenge/checkpoint/2FA URL      -> CHECKPOINT
      - main nav present                  -> LOGGED_IN
    """
    url = page.url or ""
    if any(s in url for s in ("/accounts/login", "/accounts/emailsignup")):
        return LoginState.LOGGED_OUT
    if any(s in url for s in ("/challenge", "/checkpoint", "/auth_platform", "two_factor")):
        return LoginState.CHECKPOINT
    # logged-in signal: the home/profile nav links exist
    try:
        nav = await page.query_selector('svg[aria-label="Home"], a[href="/"][role="link"]')
        if nav:
            return LoginState.LOGGED_IN
        login_form = await page.query_selector('input[name="username"], input[name="password"]')
        if login_form:
            return LoginState.LOGGED_OUT
    except Exception:
        pass
    # ambiguous: a logged-out home often redirects to the login form
    return LoginState.LOGGED_OUT


class BrowserSession:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.lock = ProfileLock(settings.profile_dir)

    # --- context lifecycle ---------------------------------------------------
    async def _launch(self, headless: bool):
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise DoomScrollError(
                ErrorCode.BROWSER_UNAVAILABLE,
                "Playwright is not installed. Run: uv run playwright install chromium",
                requires_headful=False,
                details={"import_error": str(e)},
            ) from e

        self.settings.profile_dir.mkdir(parents=True, exist_ok=True)
        pw = await async_playwright().start()
        try:
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.profile_dir),
                headless=headless,
                user_agent=_REAL_UA,
                locale="en-US",
                timezone_id="America/New_York",
                viewport={"width": 1280 + (hash(time.time()) % 80), "height": 800},
                args=_STEALTH_ARGS,
                ignore_default_args=_IGNORE_DEFAULT_ARGS,
            )
            await ctx.add_init_script(_STEALTH_INIT)
        except Exception as e:
            await pw.stop()
            raise DoomScrollError(
                ErrorCode.BROWSER_UNAVAILABLE,
                f"Failed to launch Chromium: {e}. Try: uv run playwright install chromium",
                details={"launch_error": str(e)},
            ) from e
        return pw, ctx

    # --- auth ----------------------------------------------------------------
    async def login(self, force: bool = False, timeout_s: float = 300.0) -> dict[str, Any]:
        """Open a HEADFUL browser; the human signs in by hand, then we persist.

        No credentials are stored — only the browser profile. `force=True` is the
        repair path for an expired session or a checkpoint page.
        """
        self.lock.acquire()
        pw = ctx = None
        try:
            pw, ctx = await self._launch(headless=False)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")
            state = await _detect_state(page)
            if state == LoginState.LOGGED_IN and not force:
                return {"state": state.value, "message": "Already logged in."}

            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                state = await _detect_state(page)
                if state == LoginState.LOGGED_IN:
                    return {"state": state.value, "message": "Login persisted."}
                await asyncio.sleep(1.5)
            raise DoomScrollError(
                ErrorCode.CHECKPOINT_REQUIRED,
                "Login did not complete within the timeout.",
                requires_headful=True,
                suggested_tool="login",
                details={"last_state": state.value},
            )
        finally:
            if ctx:
                await ctx.close()
            if pw:
                await pw.stop()
            self.lock.release()

    async def login_status(self) -> dict[str, Any]:
        self.lock.acquire()
        pw = ctx = None
        try:
            pw, ctx = await self._launch(headless=True)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")
            state = await _detect_state(page)
            return {"state": state.value, "logged_in": state == LoginState.LOGGED_IN}
        finally:
            if ctx:
                await ctx.close()
            if pw:
                await pw.stop()
            self.lock.release()

    async def logout(self) -> dict[str, Any]:
        """Clear the persisted profile (no IG-side logout needed)."""
        import shutil

        self.lock.acquire()
        try:
            if self.settings.profile_dir.exists():
                shutil.rmtree(self.settings.profile_dir, ignore_errors=True)
            return {"message": "Profile cleared. Next run requires login()."}
        finally:
            self.lock.release()

    async def doctor(self) -> dict[str, Any]:
        """Report browser availability, profile path, and auth state + next action."""
        report: dict[str, Any] = {
            "profile_dir": str(self.settings.profile_dir),
            "fixtures_dir": str(self.settings.fixtures_dir),
            "mode": self.settings.mode,
            "profile_exists": self.settings.profile_dir.exists(),
        }
        try:
            import playwright  # noqa: F401

            report["playwright_installed"] = True
        except ImportError:
            report["playwright_installed"] = False
            report["next_action"] = "uv run playwright install chromium"
            return report
        try:
            status = await self.login_status()
            report.update(status)
            report["next_action"] = (
                "ready" if status["logged_in"] else "call login() (headful)"
            )
        except DoomScrollError as e:
            report["error"] = e.to_dict()
            report["next_action"] = "resolve error above"
        return report

    # --- scrolling -----------------------------------------------------------
    async def scroll_reels(self, limit: int = 50) -> dict[str, Any]:
        """Drive the default Reels feed, capture network JSON, return reel dicts.

        Network capture is primary; DOM hrefs are a fallback only for reels with
        no JSON backing (flagged EXTRACTION_DEGRADED).
        """
        self.lock.acquire()
        pw = ctx = None
        hz = Humanizer(self.settings.humanize)
        reels: dict[str, dict[str, Any]] = {}
        degraded = False
        try:
            pw, ctx = await self._launch(headless=True)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            captured: list[Any] = []

            async def on_response(resp: Any) -> None:
                try:
                    if not extract.should_capture(resp.url):
                        return
                    ct = (resp.headers or {}).get("content-type", "")
                    if "json" not in ct:
                        return
                    payload = await resp.json()
                except Exception:
                    return
                captured.append(payload)
                if self.settings.capture_fixtures:
                    self._dump_fixture(resp.url, payload)
                for reel in extract.parse_response(payload):
                    if reel["url"] and reel["url"] not in reels:
                        reels[reel["url"]] = reel
                        hz.note_reel()

            page.on("response", lambda r: asyncio.create_task(on_response(r)))

            await page.goto(REELS_URL, wait_until="domcontentloaded")
            state = await _detect_state(page)
            if state == LoginState.LOGGED_OUT:
                raise DoomScrollError(
                    ErrorCode.AUTH_REQUIRED,
                    "Not logged in.",
                    requires_headful=True,
                    suggested_tool="login",
                )
            if state == LoginState.CHECKPOINT:
                raise DoomScrollError(
                    ErrorCode.CHECKPOINT_REQUIRED,
                    "Instagram is showing a checkpoint/challenge.",
                    requires_headful=True,
                    suggested_tool="login",
                    details={"hint": "call login(force=True)"},
                )

            stagnant = 0
            while len(reels) < limit and not hz.cap_reached and stagnant < 5:
                before = len(reels)
                await page.mouse.wheel(0, hz.scroll_delta())
                await hz.scroll_pause()
                await hz.watch()
                await asyncio.sleep(0)  # let response handlers drain
                if len(reels) == before:
                    stagnant += 1
                else:
                    stagnant = 0

            # DOM fallback if network capture produced nothing
            if not reels:
                try:
                    hrefs = await page.eval_on_selector_all(
                        extract.REEL_LINK_SELECTOR,
                        "els => els.map(e => e.getAttribute('href'))",
                    )
                except Exception:
                    hrefs = []
                fallback = extract.reels_from_dom_hrefs(hrefs or [])
                if fallback:
                    degraded = True
                    for r in fallback:
                        reels[r["url"]] = r

            result = list(reels.values())[:limit]
            if not result:
                raise DoomScrollError(
                    ErrorCode.NO_REELS_FOUND,
                    "No reels extracted from the feed.",
                    retry_after=30.0,
                    suggested_tool="scroll_reels",
                )

            payload = {
                "reels": result,
                "count": len(result),
                "timing": hz.timing_state(),
                "fill_rate": _fill_rate(result),  # field-fill telemetry (AD4)
            }
            if degraded:
                payload["warning"] = ErrorCode.EXTRACTION_DEGRADED.value
            if hz.cap_reached:
                payload["warning"] = ErrorCode.COOLDOWN_ACTIVE.value
                payload["retry_after"] = hz.state.cooldown_remaining
            return payload
        finally:
            if ctx:
                await ctx.close()
            if pw:
                await pw.stop()
            self.lock.release()

    def _dump_fixture(self, url: str, payload: Any) -> None:
        try:
            self.settings.fixtures_dir.mkdir(parents=True, exist_ok=True)
            name = f"{int(time.time()*1000)}-{abs(hash(url)) % 10**8}.json"
            (self.settings.fixtures_dir / name).write_text(
                json.dumps(payload)[:2_000_000]
            )
        except Exception:
            pass  # fixtures are best-effort; never fail a scroll over them


def _fill_rate(reels: list[dict[str, Any]]) -> dict[str, float]:
    """Fraction of reels with each field populated — catches silent junk (AD4)."""
    if not reels:
        return {}
    fields = (
        "creator", "caption", "likes", "comments",
        "views", "reposts", "date_posted", "audio",
    )
    n = len(reels)
    return {f: round(sum(1 for r in reels if r.get(f) not in (None, "")) / n, 2) for f in fields}
