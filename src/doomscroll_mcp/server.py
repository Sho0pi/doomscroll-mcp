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
from .extract import Filters

mcp = FastMCP("doomscroll-mcp")

_settings = Settings.from_env()


def _session() -> BrowserSession:
    return BrowserSession(_settings)


def _filters(
    posted_within_hours: int | None,
    min_views: int | None,
    min_likes: int | None,
    min_reposts: int | None,
    contains: str | None,
) -> Filters:
    return Filters(
        posted_within_hours=posted_within_hours,
        min_views=min_views,
        min_likes=min_likes,
        min_reposts=min_reposts,
        contains=contains,
    )


def _session_with_mode(mode: str | None):
    """Fresh session, optionally with a per-call humanize mode override.

    Returns (session, error_dict). error_dict is None on success, or a structured
    BAD_MODE error if the mode is unknown.
    """
    s = _session()
    if mode is not None:
        try:
            s.settings = _settings.with_mode(mode)
        except ValueError:
            return s, {
                "error": True,
                "code": "BAD_MODE",
                "message": f"unknown mode {mode!r}; expected one of {MODES}",
            }
    return s, None


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
async def scroll_reels(
    limit: int = 50,
    sort_by: str | None = None,
    top: int | None = None,
    posted_within_hours: int | None = None,
    min_views: int | None = None,
    min_likes: int | None = None,
    min_reposts: int | None = None,
    contains: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Scroll the default Instagram Reels feed until `limit` reels are collected.

    Returns {reels: [...], count, filtered_out, stopped_reason,
    duration_elapsed_s, timing, fill_rate}. Each reel: url, creator, caption,
    description, visual_description, likes, comments, views, shares, reposts,
    date_posted (ISO 8601), date_posted_ts (unix), audio, _source. Engagement
    fields are best-effort — missing ones come back null.

    To scroll for a fixed TIME instead of a count, use `doomscroll`.

    sort_by: views | likes | reposts | recent (descending; None = discovery
    order). top: keep only the top K after sorting.

    Filters (applied before sort): posted_within_hours (recency window),
    min_views / min_likes / min_reposts (engagement floors), contains (caption
    keyword, case-insensitive). A reel missing a filtered metric is dropped.
    Note: feed `views` are null, so use min_likes on the feed, min_views on
    search. `contains` is keyword matching, not topic understanding — for real
    topic relevance use search_reels.

    mode: fast_test | normal_passive | conservative.
    """
    s, err = _session_with_mode(mode)
    if err:
        return err
    f = _filters(posted_within_hours, min_views, min_likes, min_reposts, contains)
    return await _guard(s.scroll_reels(limit=limit, sort_by=sort_by, top=top, filters=f))


@mcp.tool()
async def doomscroll(
    duration_seconds: int,
    sort_by: str | None = None,
    top: int | None = None,
    posted_within_hours: int | None = None,
    min_views: int | None = None,
    min_likes: int | None = None,
    min_reposts: int | None = None,
    contains: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Doomscroll the default feed for a wall-clock duration, return what you saw.

    Like scroll_reels but the stop condition is TIME, not a reel count: scroll
    the feed for `duration_seconds` (clamped to the server's max, default 30 min)
    and return every reel collected. Stops early if Instagram's per-session reel
    cap is hit (account safety) — see stopped_reason.

    Filters (posted_within_hours, min_views/likes/reposts, contains) apply to the
    collected reels — e.g. doomscroll(600, posted_within_hours=24) returns only
    reels posted in the last 24h from 10 minutes of scrolling. Pair with
    sort_by="likes" + top=K for "the best fresh reels". Note: feed reels skew
    evergreen, so a tight recency window may return few — for fresh-viral by
    topic, search_reels(topic, posted_within_hours=24, sort_by="views") is
    stronger. Feed `views` are null (use min_likes here).
    """
    if not isinstance(duration_seconds, int) or duration_seconds <= 0:
        return {
            "error": True, "code": "BAD_DURATION",
            "message": "duration_seconds must be a positive integer.",
        }
    s, err = _session_with_mode(mode)
    if err:
        return err
    f = _filters(posted_within_hours, min_views, min_likes, min_reposts, contains)
    return await _guard(
        s.doomscroll(
            duration_seconds=duration_seconds, sort_by=sort_by, top=top, filters=f
        )
    )


@mcp.tool()
async def search_reels(
    query: str,
    limit: int = 50,
    sort_by: str | None = None,
    top: int | None = None,
    posted_within_hours: int | None = None,
    min_views: int | None = None,
    min_likes: int | None = None,
    min_reposts: int | None = None,
    contains: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Search Instagram by keyword and return matching reels.

    Same reel shape/errors as scroll_reels, sourced from IG's search SERP for
    `query` (e.g. "beginner yoga"). Unlike the feed, search results DO include
    `views`; `comments` is not in this payload (null).

    sort_by (views|likes|reposts|recent) + top=K rank the results. Filters
    (posted_within_hours, min_views/likes/reposts, contains) narrow them — e.g.
    search_reels("cooking", posted_within_hours=24, min_views=500000,
    sort_by="views", top=10) = top viral cooking reels from the last 24h.
    """
    s, err = _session_with_mode(mode)
    if err:
        return err
    f = _filters(posted_within_hours, min_views, min_likes, min_reposts, contains)
    return await _guard(
        s.search_reels(query=query, limit=limit, sort_by=sort_by, top=top, filters=f)
    )


@mcp.tool()
async def hashtag_reels(
    tag: str,
    limit: int = 50,
    sort_by: str | None = None,
    top: int | None = None,
    posted_within_hours: int | None = None,
    min_views: int | None = None,
    min_likes: int | None = None,
    min_reposts: int | None = None,
    contains: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Return reels for a hashtag (with or without a leading '#').

    Same reel shape, views, sort_by/top, and filters as search_reels.
    """
    s, err = _session_with_mode(mode)
    if err:
        return err
    f = _filters(posted_within_hours, min_views, min_likes, min_reposts, contains)
    return await _guard(
        s.hashtag_reels(tag=tag, limit=limit, sort_by=sort_by, top=top, filters=f)
    )


def main() -> None:
    """Console entry point — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
