# Sample Output — `scroll_reels`

Real run against the live Instagram default Reels feed (logged-in session,
`normal_passive` mode, `limit=10`). Data extracted from intercepted Instagram
network JSON (`_source: "network"`), not DOM scraping.

## Call

```python
scroll_reels(limit=10)
```

## Response

```json
{
  "reels": [
    {
      "url": "https://www.instagram.com/reel/DZ9xluGynNI/",
      "creator": "balabinggg",
      "caption": "🧠: oh ya let’s do this",
      "likes": 50,
      "comments": 6,
      "date_posted": "1782362891",
      "audio": "Original audio",
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DZf6PYtGyay/",
      "creator": "instagram",
      "caption": "A new album and font go really nice together 🩷 … Try it now in Stories.",
      "likes": 819876,
      "comments": 72765,
      "date_posted": "1781294695",
      "audio": null,
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DYgHnSQjKWJ/",
      "creator": "chatgpt",
      "caption": "Get a free personalized palm reading with ChatGPT …",
      "likes": 684,
      "comments": 20,
      "date_posted": "1779154223",
      "audio": null,
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DZU4ZAvGNqf/",
      "creator": "nataliesung.yoga",
      "caption": "Scroll ⬅️ to see more … #yoga",
      "likes": 436,
      "comments": 13,
      "date_posted": "1780924627",
      "audio": null,
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DYrlgmySMTC/",
      "creator": "balabinggg",
      "caption": "Sorry I am busy",
      "likes": 122,
      "comments": 15,
      "date_posted": "1779592267",
      "audio": "Original audio",
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DYwzxhwoTyC/",
      "creator": "vitukhinan_n",
      "caption": "🔥 @shakedancegroup_students",
      "likes": 787108,
      "comments": 845,
      "date_posted": "1779714573",
      "audio": "Kavkaz — Starly",
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DZQ3kKzgxUW/",
      "creator": "kelly_okiee",
      "caption": "I’m more scared of your spelling!!! #funny #fyp #grammar #foryourpage",
      "likes": 1015108,
      "comments": 3536,
      "date_posted": "1780790055",
      "audio": "Original audio",
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DWkIyh2yLar/",
      "creator": "sailahnicol",
      "caption": "When life gives you fruit… not lemons 🍌🍓",
      "likes": 1800258,
      "comments": 5312,
      "date_posted": "1774994125",
      "audio": "Made You Look — Meghan Trainor",
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DXRxTctj2Ff/",
      "creator": "fitness_girl_10031",
      "caption": "Gymnastics 🤸🏻 #fitnessgirl #gymnastics",
      "likes": 138991,
      "comments": 5836,
      "date_posted": "1776525359",
      "audio": "Original audio",
      "_source": "network"
    },
    {
      "url": "https://www.instagram.com/reel/DZ4PL1dNUlF/",
      "creator": "cio0061",
      "caption": "Geldi sabah dozunuz ashaasdhaja😂 #cio0061",
      "likes": 4443908,
      "comments": 16723,
      "date_posted": "1782111074",
      "audio": "Original audio",
      "_source": "network"
    }
  ],
  "count": 10,
  "timing": {
    "reels_seen": 15,
    "session_max": 200,
    "capped": false,
    "cooldown_remaining_s": 0.0,
    "total_wait_s": 7.6
  },
  "fill_rate": {
    "creator": 1.0,
    "caption": 1.0,
    "likes": 1.0,
    "comments": 1.0,
    "date_posted": 1.0,
    "audio": 0.7
  }
}
```

## Fields added after first run (views / upload date / reposts)

A later run resolved the originally-null engagement fields against real captured
payloads:

| creator | likes | reposts | views | date_posted |
|---|---|---|---|---|
| instagram | 819,880 | 33,666 | null | 2026-06-12T20:04:55+00:00 |
| balabinggg | 50 | 3 | null | 2026-06-25T04:48:11+00:00 |
| pauulinaperez | 1,741,803 | 13,906 | null | 2026-06-06T16:22:31+00:00 |
| rickylimon99 | 3,971,446 | 89,787 | null | 2026-05-10T00:59:09+00:00 |
| dom.crocitto23 | 2,026,431 | 75,738 | null | 2026-05-23T18:00:59+00:00 |

- **`reposts`** = Instagram's `media_repost_count` (reshares to feed) — real
  data. This is the only share-type count in the JSON; there is no separate
  DM-send/`shares` count (player-overlay DOM only), so the field was removed.
- **`date_posted`** now ISO 8601 UTC; raw epoch kept as `date_posted_ts`.
- **`views`** = `null`, always. Instagram does not expose reel view/play counts
  on the web — not in the feed, the reel page, or the media-info API. See
  [`views-investigation.md`](views-investigation.md) for the full probe log.

## Full reel shape (current)

Every reel returned by `scroll_reels` has this shape. Example (creator `chatgpt`):

```json
{
  "url": "https://www.instagram.com/reel/DYgHnSQjKWJ/",
  "creator": "chatgpt",
  "caption": "Get a free personalized palm reading with ChatGPT...",
  "description": "Get a free personalized palm reading with ChatGPT...",
  "visual_description": "Photo by ChatGPT on May 18, 2026.",
  "likes": 684,
  "comments": 20,
  "views": null,
  "reposts": 0,
  "date_posted": "2026-05-19T01:30:23+00:00",
  "date_posted_ts": 1779154223,
  "audio": null,
  "_source": "network"
}
```

Field reference:

| field | meaning | availability |
|---|---|---|
| `caption` / `description` | creator's post text (identical; two names) | ~always |
| `visual_description` | IG auto-generated alt-text of the media | sparse (~1 in 6) |
| `likes`, `comments` | engagement counts | ~always |
| `reposts` | IG `media_repost_count` (reshares to feed) | ~always |
| `views` | play/view count | **always null** — IG hides web view counts ([why](views-investigation.md)) |
| `date_posted` | upload time, ISO 8601 UTC | ~always |
| `date_posted_ts` | upload time, unix epoch | ~always |
| `audio` | track title — artist, or "Original audio" | ~80% |
| `_source` | `"network"` (JSON) or `"dom"` (fallback) | always |

## Notes

- **`fill_rate`** is field-fill telemetry — fraction of reels with each field
  populated. Catches silent extraction regressions (a parser returning plausible
  junk shows up as a fill_rate drop, not a crash). This run: every reel has
  creator / caption / likes / comments / date_posted; audio on 7/10 (some reels
  carry no music node).
- **`reposts`** is `null` across this older feed sample — the default-feed
  payload often omits the count. Best-effort by design: missing fields come back
  null rather than failing the call. (Search results populate it reliably.)
- **`date_posted`** is a raw Unix epoch string straight from Instagram.
- **`timing`** lets the agent see humanization cost: 15 reels scrolled to collect
  10 unique, 7.6s of randomized wait, session cap not reached.
- **`_source: "network"`** confirms data came from intercepted JSON, not DOM.
