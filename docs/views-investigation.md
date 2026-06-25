# Where `views` come from (feed: no, search: yes)

Short version: the **home feed** (`scroll_reels`) does not expose reel view
counts, so `views` is null there. The **search SERP** (`search_reels` /
`hashtag_reels`, via `top_serp`) DOES include them — `play_count` /
`ig_play_count` are present, so `views` populates for those tools.

> Correction: an earlier version of this doc concluded views were unavailable
> everywhere. That holds for the feed and the standalone reel page, but the
> `top_serp` search payload was later found to carry play counts. The parser
> already reads `play_count`/`ig_play_count`, so search results return real view
> numbers (e.g. 944,436 / 3,174,121). The notes below are the original
> feed/reel-page investigation and remain accurate for those surfaces.

## What was probed (live, logged-in session)

1. **Feed graphql payload** (the source `scroll_reels` parses)
   `view_count` is present but always `null`. No `play_count` / `ig_play_count`
   anywhere in the payload.

2. **Reel page DOM / HTML / `og:description`**
   Opening `https://www.instagram.com/reel/<code>/` directly: the page and its
   `og:description` meta carry **likes + comments only** (e.g. `"2M likes, 3,017
   comments - …"`). No "views" or "plays" text in the rendered body or the
   embedded JSON.

3. **Private media-info API** — `GET /api/v1/media/{pk}/info/`
   With the authenticated web session (`X-IG-App-ID: 936619743392459`): returns
   `200` and the media item, but the count fields are stripped (even `like_count`
   is absent). The item carries `has_views_fetching: true`, meaning view data is
   loaded by a **separate lazy request**, not included here.

4. **Reel player overlay** (video actually playing)
   The numbers rendered in the player are likes / comments / reposts / **sends** —
   for one reel: `2.3M / 3,017 / 52.6K / 875K`. The `875K` is the send/DM-share
   count. There is **no view count** among the overlay numbers.

## Conclusion

Public reel view counts are not available through any web surface we can reach
with a logged-in browser session. The feed JSON omits them, the reel page omits
them, and the media-info API defers them to a lazy request that isn't returned.

## Adjacent finding: `sends` is available (not currently captured)

The player overlay exposes a **send/DM-share count** (the `875K` above) that the
feed JSON does not. It is distinct from `reposts` (`media_repost_count`, the
share-to-feed count we already return). Capturing it would mean opening each reel
and reading the overlay numbers — abbreviated (`2.3M`, not exact) and mapped by
icon/position, so it is fragile to layout changes. Not implemented; noted here in
case exact share data is wanted later.

## If views ever matter

The only remaining path is reverse-engineering the `has_views_fetching` lazy
request (path 3 above). It likely needs mobile/app headers and may be signed or
rate-blocked, so it would be fragile and is not worth building speculatively.
