# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Pre-implementation. Repo currently holds only `README.md` (design spec) and `LICENSE`. No source code, tests, or build config exist yet. The README is the authoritative design — implement against it.

## What This Is

An MCP server exposing Instagram Reels browsing to AI agents. The MCP **collects and returns structured reel data only**; it performs no analysis, ranking, or recommendation. Those are the agent's job.

Pipeline: `AI Agent → DoomScroll MCP → Playwright → Instagram Web`

## Stack

- Python, managed with `uv` (dependency install + execution)
- MCP (server framework)
- Playwright (browser automation against Instagram web)

## Intended Tool Surface (from README)

- `login()`, `login_status()`, `logout()` — auth lifecycle
- `scroll_reels(limit=50, search=None, hashtag=None)` — drives default feed, keyword search, or hashtag page; returns list of reel dicts (url, creator, caption, likes, comments, date_posted, audio, etc.)

## Humanization

To reduce bot-detection risk, browsing behavior must be randomized via a `HumanizeConfig`.

**Passive (core, always on, no account side effects):**

- randomized delay between scrolls (range, not fixed)
- variable scroll distance/speed, occasional scroll-up
- random "watch" pause per reel before advancing
- jittered mouse movement, viewport randomization
- per-session reel cap + cooldown before next session

**Active (opt-in, OFF by default — mutates the user's account):**

- liking reels. This is real engagement: visible to creators, pollutes the user's algorithm, and is a *primary* IG spam-detection trigger. Gate behind an explicit flag, keep probability low, rate-limit hard, and never perform silently.

```python
class HumanizeConfig:
    scroll_delay_range: tuple = (2.0, 6.0)     # seconds
    watch_duration_range: tuple = (1.0, 5.0)
    scroll_jitter: bool = True
    session_max_reels: int = 200
    cooldown_after_session: float = 0
    # active — opt-in, risky
    enable_likes: bool = False
    like_probability: float = 0.0              # 0..1
```

## Risk / Account Safety

Automating Instagram violates its Terms of Service and can get an account rate-limited, locked, or banned. **Use at your own risk.** Strongly recommend running against a **secondary / throwaway account, never your main account.** Surface this warning in user-facing docs and ideally at login time.

## Key Design Constraints

- **Session persistence is core**: Instagram login happens once. Persist the Playwright browser profile locally and reuse it between runs so `login_status()` returns logged-in without re-auth. Do not store credentials; rely on the persisted browser profile.
- **No analysis in the server**: keep `scroll_reels` output as raw structured metadata. Trend detection, filtering, ranking, generation all live agent-side.
- Engagement fields are best-effort — Instagram does not always expose them; return what is present rather than failing. Note: there is no distinct `shares`/DM-send count in the JSON; `reposts` (media_repost_count) is the only share-type metric.

## Layout

```
src/doomscroll_mcp/
  config.py     HumanizeConfig, Settings, browsing modes (fast_test/normal_passive/conservative)
  errors.py     DoomScrollError + ErrorCode (typed, loop-recoverable for the agent)
  extract.py    network-JSON parser (primary) + DOM fallback
  browser.py    BrowserSession: persistent context, profile lock, login state machine, scroll loop
  server.py     FastMCP tools: login, login_status, logout, doctor,
                scroll_reels, doomscroll, search_reels, hashtag_reels
tests/          parser fixture tests (the test signal without ground truth)
```

## Architecture notes (post-review)

- **Extraction is network-first** (UC1): intercept IG's internal JSON via
  `page.on("response")`, parse reel nodes with a recursive walker (survives shape
  churn), DOM hrefs only as fallback. Raw responses can be dumped to
  `fixtures_dir` for replay/debug — opt-in via `DOOMSCROLL_CAPTURE_FIXTURES=1`
  (off by default; payloads carry session data).
- **Typed errors** (`AUTH_REQUIRED`, `CHECKPOINT_REQUIRED`, `COOLDOWN_ACTIVE`,
  `EXTRACTION_DEGRADED`, `SELECTOR_BROKEN`, `NO_REELS_FOUND`, …): tools return
  error dicts, never raw tracebacks, so the agent loop can branch.
- **Honest tool surface**: `scroll_reels` (default feed, /reels/ player UI),
  `search_reels` / `hashtag_reels` (topic discovery via the `top_serp` search
  API — `explore_grid` ignores its tag/query param, so it is not used).
- **Profile lock** prevents two sessions sharing one `user_data_dir`.

## Commands

```bash
uv sync --extra dev                       # install deps
uv run playwright install chromium        # one-time browser install
uv run pytest -q                          # run tests
uv run doomscroll-mcp                      # start the MCP server (stdio)
```

Env: `DOOMSCROLL_HOME` (profile+fixtures root, default `~/.doomscroll-mcp`),
`DOOMSCROLL_MODE` (fast_test|normal_passive|conservative),
`DOOMSCROLL_CAPTURE_FIXTURES` (1 to dump raw IG JSON for debug; off by default),
`DOOMSCROLL_IG_APP_ID` (override the public web app-id used for the search API,
in case Instagram rotates it; default is the long-stable public value),
`DOOMSCROLL_MAX_DURATION_S` (hard ceiling on a single `doomscroll()` call,
default 1800 = 30 min).
