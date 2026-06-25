"""Filters: recency window, engagement floors, caption keyword."""

from doomscroll_mcp.extract import Filters

NOW = 1_000_000_000  # fixed reference time


def _reel(url, ts=None, views=None, likes=None, reposts=None, caption=None):
    return {
        "url": url, "date_posted_ts": ts, "views": views, "likes": likes,
        "reposts": reposts, "caption": caption,
    }


def test_empty_filter_is_noop():
    reels = [_reel("a"), _reel("b")]
    assert Filters().is_empty
    assert Filters().apply(reels) == reels


def test_posted_within_hours_drops_old_and_missing_ts():
    recent = _reel("recent", ts=NOW - 3600)        # 1h ago
    old = _reel("old", ts=NOW - 48 * 3600)         # 2 days ago
    no_ts = _reel("no_ts", ts=None)
    out = Filters(posted_within_hours=24).apply([recent, old, no_ts], now=NOW)
    assert [r["url"] for r in out] == ["recent"]


def test_min_likes_floor_drops_below_and_missing():
    out = Filters(min_likes=1000).apply(
        [_reel("a", likes=5000), _reel("b", likes=10), _reel("c", likes=None)]
    )
    assert [r["url"] for r in out] == ["a"]


def test_min_views_floor():
    out = Filters(min_views=1_000_000).apply(
        [_reel("a", views=2_000_000), _reel("b", views=500)]
    )
    assert [r["url"] for r in out] == ["a"]


def test_contains_is_case_insensitive():
    out = Filters(contains="YOGA").apply(
        [_reel("a", caption="Morning yoga flow"),
         _reel("b", caption="cooking pasta"),
         _reel("c", caption=None)]
    )
    assert [r["url"] for r in out] == ["a"]


def test_combined_filters_are_anded():
    reels = [
        _reel("hit", ts=NOW - 3600, likes=900_000, caption="viral dance"),
        _reel("too_old", ts=NOW - 100 * 3600, likes=900_000, caption="viral dance"),
        _reel("low", ts=NOW - 3600, likes=10, caption="viral dance"),
        _reel("offtopic", ts=NOW - 3600, likes=900_000, caption="quiet walk"),
    ]
    out = Filters(posted_within_hours=24, min_likes=500_000, contains="dance").apply(
        reels, now=NOW
    )
    assert [r["url"] for r in out] == ["hit"]


def test_active_echoes_only_set_filters():
    assert Filters(posted_within_hours=24, min_likes=1000).active() == {
        "posted_within_hours": 24, "min_likes": 1000,
    }
