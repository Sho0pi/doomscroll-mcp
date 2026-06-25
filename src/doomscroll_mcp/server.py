"""MCP server — tool surface for AI agents.

Tools return plain dicts. Failures come back as structured error dicts (never
raw tracebacks) so the calling agent can branch on `code`, `retry_after`,
`requires_headful`, and `suggested_tool` and keep its loop going.

The MVP ships an HONEST surface (AD2): `scroll_reels` drives the default feed
only. `search`/`hashtag` are NOT advertised as parameters yet — they will ship
as their own tools (`search_reels`, `hashtag_reels`) once implemented, rather
than as accepted-but-ignored params that mislead the agent.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .browser import BrowserSession
from .config import MODES, Settings
from .errors import DoomScrollError

mcp = FastMCP("doomscroll-mcp")

_settings = Settings.from_env()


def _session() -> BrowserSession:
    return BrowserSession(_settings)


async def _guard(coro) -> dict[str, Any]:
    try:
        return await coro
    except DoomScrollError as e:
        return e.to_dict()
    except Exception as e:  # never leak a raw traceback to the agent loop
        return {
            "error": True,
            "code": "INTERNAL",
            "message": f"{type(e).__name__}: {e}",
        }


@mcp.tool()
async def login(force: bool = False) -> dict[str, Any]:
    """Open a visible browser so you can sign in to Instagram by hand.

    Credentials are never stored — only the browser profile is persisted, so you
    log in once. Use force=True to re-auth an expired session or clear a
    checkpoint. WARNING: automating Instagram violates its ToS and risks the
    account. Use a secondary/throwaway account, never your main.
    """
    return await _guard(_session().login(force=force))


@mcp.tool()
async def login_status() -> dict[str, Any]:
    """Report whether the persisted Instagram session is currently logged in."""
    return await _guard(_session().login_status())


@mcp.tool()
async def logout() -> dict[str, Any]:
    """Clear the persisted browser profile. Next run requires login() again."""
    return await _guard(_session().logout())


@mcp.tool()
async def doctor() -> dict[str, Any]:
    """Diagnose setup: browser availability, profile path, auth state, next action."""
    return await _guard(_session().doctor())


@mcp.tool()
async def scroll_reels(limit: int = 50, mode: str | None = None) -> dict[str, Any]:
    """Scroll the default Instagram Reels feed and return structured reel metadata.

    Returns {reels: [...], count, timing, fill_rate}. Each reel: url, creator,
    caption, description (= caption), visual_description (IG auto alt-text),
    likes, comments, views, shares, reposts, date_posted (ISO 8601),
    date_posted_ts (unix), audio, _source. Engagement fields are best-effort —
    missing ones come back null rather than failing.

    Note on views: Instagram does NOT include view/play count in the home-feed
    payload, so `views` is null here (it's only exposed on a reel's own page).
    `shares` and `reposts` are the same metric (IG's media_repost_count).

    `mode` (optional): one of fast_test, normal_passive, conservative. Controls
    humanized delay/cap. Defaults to the server's configured mode.

    Note: keyword/hashtag browsing are not in this tool yet; they will ship as
    separate tools. This call drives the default feed only.
    """
    s = _session()
    if mode is not None:
        try:
            s.settings = _settings.with_mode(mode)
        except ValueError:
            return {
                "error": True,
                "code": "BAD_MODE",
                "message": f"unknown mode {mode!r}; expected one of {MODES}",
            }
    return await _guard(s.scroll_reels(limit=limit))


def main() -> None:
    """Console entry point — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
