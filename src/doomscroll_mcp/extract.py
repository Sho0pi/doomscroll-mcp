"""Reel extraction — network-JSON capture is primary, DOM is fallback.

Why network-first: Instagram's web DOM uses obfuscated, rotating class names, so
CSS selectors rot almost immediately. The internal JSON responses IG's own web
client consumes are far more stable and carry complete engagement fields. We
intercept those responses, parse reel-shaped nodes out of them, and only fall
back to DOM scraping when a reel has no JSON backing.

The parser is a recursive walker rather than a fixed path: IG nests media nodes
differently across feed / search / hashtag endpoints and across A/B buckets, so
"find every node that looks like a reel" survives shape changes better than
"read response['data']['xdt_api']['edges'][i]...".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

# Substrings of IG response URLs that carry REELS payloads on the /reels/ page.
# Scoped to reels-specific endpoints so home-feed payloads IG prefetches don't
# leak in. On /reels/, reels arrive via graphql/query; clips/feed-reels are the
# api/v1 reels endpoints. The generic "/api/v1/" catch-all is deliberately NOT
# here — it would pull the home timeline.
CAPTURE_URL_HINTS = (
    "/graphql",
    "/api/graphql",
    "/api/v1/clips",
    "/api/v1/feed/reels",
)


def should_capture(url: str) -> bool:
    return any(h in url for h in CAPTURE_URL_HINTS)


def _looks_like_reel(node: dict[str, Any]) -> bool:
    if not isinstance(node, dict):
        return False
    if not (node.get("code") or node.get("pk") or node.get("id") or node.get("shortcode")):
        return False
    # is_video must be truthy to count — a node with is_video=False is an image
    # post and must NOT be mapped to a /reel/ url.
    if node.get("is_video") is False:
        return False
    if node.get("video_versions") or node.get("video_dash_manifest") or node.get("video_url"):
        return True
    if node.get("is_video") is True:
        return True
    # GraphQL shape: __typename hints
    typename = node.get("__typename", "")
    return typename in ("GraphVideo", "XDTMediaDict") and bool(node.get("is_video", True))


def _walk(obj: Any) -> Iterable[dict[str, Any]]:
    """Yield every dict node anywhere in a nested JSON structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _first(node: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = node.get(k)
        if v not in (None, ""):
            return v
    return None


def _username(node: dict[str, Any]) -> str | None:
    user = node.get("user") or node.get("owner") or {}
    if isinstance(user, dict):
        return _first(user, "username")
    return None


def _audio(node: dict[str, Any]) -> str | None:
    ci = node.get("clips_metadata")
    if not isinstance(ci, dict):
        return None
    music = ci.get("music_info")
    asset = music.get("music_asset_info") if isinstance(music, dict) else None
    if isinstance(asset, dict):
        title = _first(asset, "title")
        artist = _first(asset, "display_artist")
        if title and artist:
            return f"{title} — {artist}"
        if title:
            return title
    original = ci.get("original_sound_info")
    if isinstance(original, dict):
        return _first(original, "original_audio_title")
    return None


def _code_to_url(node: dict[str, Any]) -> str | None:
    code = _first(node, "code", "shortcode")
    if code:
        return f"https://www.instagram.com/reel/{code}/"
    return None


def _to_int(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


def _iso(ts: Any) -> str | None:
    """Unix epoch -> ISO 8601 UTC string. Instagram's taken_at is seconds."""
    n = _to_int(ts)
    if n is None:
        return None
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def reel_from_node(node: dict[str, Any]) -> dict[str, Any] | None:
    """Map one reel-shaped JSON node to the public reel dict. Best-effort."""
    if not _looks_like_reel(node):
        return None
    caption = node.get("caption")
    if isinstance(caption, dict):
        caption = caption.get("text")
    # IG's auto-generated visual description of the media (alt text), when present.
    visual = _first(node, "accessibility_caption")
    ts = _first(node, "taken_at", "taken_at_timestamp", "device_timestamp")
    # reposts/shares: IG exposes reshares as media_repost_count on the feed.
    reposts = _to_int(
        _first(node, "media_repost_count", "reshare_count", "share_count")
    )
    # views: IG omits play/view counts from the home-feed payload (view_count is
    # null there; present only on the reel's own page). Surfaced honestly.
    views = _to_int(_first(node, "play_count", "ig_play_count", "view_count"))
    return {
        "url": _code_to_url(node),
        "creator": _username(node),
        "caption": caption,
        "description": caption,         # creator's text; alias of caption
        "visual_description": visual,   # IG auto alt-text describing the media
        "likes": _to_int(_first(node, "like_count", "edge_liked_by")),
        "comments": _to_int(_first(node, "comment_count", "edge_media_to_comment")),
        "views": views,
        "shares": reposts,
        "reposts": reposts,
        "date_posted": _iso(ts),
        "date_posted_ts": _to_int(ts),
        "audio": _audio(node),
        "_source": "network",
    }


def parse_response(payload: Any) -> list[dict[str, Any]]:
    """Extract all reels from one captured network JSON payload.

    Dedupes by url within the payload. Returns [] for non-reel payloads (most of
    them) — the caller accumulates across many responses.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for node in _walk(payload):
        reel = reel_from_node(node)
        if reel is None:
            continue
        url = reel.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(reel)
    return out


# --- DOM fallback ------------------------------------------------------------
# Only used when network capture yields nothing for a visible reel. Selectors
# live HERE, in one place, so a break is a one-file fix (and a signal to widen
# network capture rather than chase CSS).

REEL_LINK_SELECTOR = 'a[href*="/reel/"]'


def reels_from_dom_hrefs(hrefs: Iterable[str]) -> list[dict[str, Any]]:
    """Minimal DOM fallback: recover at least the reel URL + creator from hrefs.

    Engagement fields are unavailable from the DOM cheaply, so they come back
    None and the caller flags EXTRACTION_DEGRADED.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for href in hrefs:
        if "/reel/" not in href:
            continue
        url = href if href.startswith("http") else f"https://www.instagram.com{href}"
        url = url.split("?")[0]
        if url in seen:
            continue
        seen.add(url)
        out.append(
            {
                "url": url,
                "creator": None,
                "caption": None,
                "description": None,
                "visual_description": None,
                "likes": None,
                "comments": None,
                "views": None,
                "shares": None,
                "reposts": None,
                "date_posted": None,
                "date_posted_ts": None,
                "audio": None,
                "_source": "dom",
            }
        )
    return out
