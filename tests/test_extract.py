"""Parser tests over saved-response fixtures (AD4).

These are the backbone of testing a scraper with no ground truth: feed the
parser realistic IG-shaped JSON and assert it pulls the right reel fields. When
IG changes its payload shape, a fixture here breaks loudly instead of the live
scraper returning plausible junk.
"""

from doomscroll_mcp import extract


# Minimal node shaped like an IG api/v1 reel media item.
API_V1_REEL = {
    "code": "Cabc123",
    "pk": "987654321",
    "is_video": True,
    "video_versions": [{"url": "https://video.example/x.mp4"}],
    "like_count": 12345,
    "comment_count": 123,
    "media_repost_count": 33666,   # IG's reshare/repost count (real field name)
    "view_count": None,            # IG omits views from the home-feed payload
    "taken_at": 1700000000,        # 2023-11-14T22:13:20+00:00
    "caption": {"text": "beginner yoga flow"},
    "accessibility_caption": "Photo of a person on a yoga mat.",
    "user": {"username": "yogi.jane"},
    "clips_metadata": {
        "music_info": {"music_asset_info": {"title": "Calm", "display_artist": "Artist X"}}
    },
}

# A GraphQL-style response nesting the reel deep in edges.
GRAPHQL_RESPONSE = {
    "data": {
        "xdt_api_v1_feed": {
            "edges": [
                {"node": API_V1_REEL},
                {"node": {"code": "noVideo", "pk": "1", "__typename": "GraphImage"}},
            ]
        }
    }
}


def test_parses_api_v1_reel_fields():
    reels = extract.parse_response({"items": [API_V1_REEL]})
    assert len(reels) == 1
    r = reels[0]
    assert r["url"] == "https://www.instagram.com/reel/Cabc123/"
    assert r["creator"] == "yogi.jane"
    assert r["caption"] == "beginner yoga flow"
    assert r["description"] == "beginner yoga flow"   # alias of caption
    assert r["visual_description"] == "Photo of a person on a yoga mat."
    assert r["likes"] == 12345
    assert r["comments"] == 123
    assert r["shares"] == 33666          # from media_repost_count
    assert r["reposts"] == 33666
    assert r["views"] is None            # not in feed payload
    assert r["date_posted"] == "2023-11-14T22:13:20+00:00"  # epoch -> ISO
    assert r["date_posted_ts"] == 1700000000
    assert r["audio"] == "Calm — Artist X"
    assert r["_source"] == "network"


def test_walks_nested_graphql_and_skips_non_reels():
    reels = extract.parse_response(GRAPHQL_RESPONSE)
    assert len(reels) == 1  # image node skipped
    assert reels[0]["url"].endswith("/reel/Cabc123/")


def test_dedupes_within_payload():
    reels = extract.parse_response({"a": [API_V1_REEL], "b": [API_V1_REEL]})
    assert len(reels) == 1


def test_non_reel_payload_returns_empty():
    assert extract.parse_response({"status": "ok", "data": {}}) == []


def test_image_post_with_is_video_false_is_skipped():
    # An image post carries a code/pk but is_video=False — must NOT become a reel.
    image = {"code": "IMG123", "pk": "5", "is_video": False, "like_count": 9}
    assert extract.parse_response({"items": [image]}) == []


def test_non_dict_music_info_does_not_crash():
    node = dict(API_V1_REEL, clips_metadata={"music_info": "unexpected_string"})
    r = extract.reel_from_node(node)
    assert r is not None
    assert r["audio"] is None  # gracefully degraded, no crash


def test_should_capture_url_hints():
    assert extract.should_capture("https://www.instagram.com/api/v1/feed/reels/")
    assert extract.should_capture("https://www.instagram.com/api/v1/clips/home/")
    assert extract.should_capture("https://www.instagram.com/graphql/query")
    assert not extract.should_capture("https://www.instagram.com/static/bundle.js")
    # home timeline must NOT be captured — reels browsing only
    assert not extract.should_capture("https://www.instagram.com/api/v1/feed/timeline/")


def test_dom_fallback_recovers_urls_only():
    out = extract.reels_from_dom_hrefs(["/reel/AAA/", "/reel/AAA/?x=1", "/p/BBB/"])
    assert len(out) == 1  # deduped, /p/ skipped
    assert out[0]["url"] == "https://www.instagram.com/reel/AAA/"
    assert out[0]["likes"] is None
    assert out[0]["reposts"] is None
    assert out[0]["_source"] == "dom"


def test_iso_date_conversion_and_int_coercion():
    node = dict(API_V1_REEL, taken_at="1700000000", like_count="999")
    r = extract.reel_from_node(node)
    assert r["date_posted"] == "2023-11-14T22:13:20+00:00"
    assert r["likes"] == 999  # numeric string coerced to int


def test_missing_timestamp_yields_null_date():
    node = {k: v for k, v in API_V1_REEL.items() if k != "taken_at"}
    r = extract.reel_from_node(node)
    assert r["date_posted"] is None
    assert r["date_posted_ts"] is None
