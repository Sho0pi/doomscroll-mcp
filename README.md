# DoomScroll MCP

[![CI](https://github.com/Sho0pi/doomscroll-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Sho0pi/doomscroll-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/doomscroll-mcp.svg)](https://pypi.org/project/doomscroll-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/doomscroll-mcp.svg)](https://pypi.org/project/doomscroll-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An MCP server that allows AI agents to browse Instagram Reels and perform
content research.

Instead of manually scrolling through Instagram, agents can discover, inspect,
filter, and analyze reels directly from the feed.

> ⚠️ **Use at your own risk.** Automating Instagram violates its Terms of
> Service and may get an account rate-limited, locked, or banned. Use a
> **secondary / throwaway account — never your main account.**

## Features

- Login to Instagram once
- Persist browser session between runs
- Browse the default Reels feed based on your algorithm
- Search by keyword
- Search by hashtag
- Scroll through reels
- Extract reel metadata
- Filter and rank content before sending it to an AI model
- Humanized browsing (randomized delays, scroll jitter, watch pauses)
- Optional, opt-in account interactions (e.g. likes)

## Extracted Data

For each reel, DoomScroll MCP attempts to collect:

- Reel URL
- Creator username
- Caption / description
- Audio information
- Likes
- Comments
- Shares / reposts (when available)
- Date posted

> Note: `views` is always null — Instagram does not expose reel view counts on
> the web ([why](docs/views-investigation.md)).

The MCP returns structured data so the AI agent can decide what is interesting
and what should be ignored.

## Architecture

```text
AI Agent
    ↓
DoomScroll MCP
    ↓
Playwright
    ↓
Instagram Web
```

## Technology

- Python
- MCP
- Playwright
- uv

`uv` is used for fast dependency management and execution.

## Session Persistence

Instagram login is only required once.

The Playwright browser profile is persisted locally and reused between runs.

```text
First Run
---------
login()
→ User signs in
→ Session saved

Second Run
----------
login_status()
→ Logged In

No additional login required.
```

## MVP Scope

### 1. Login

```python
login()
login_status()
logout()
```

### 2. Scroll

```python
scroll_reels(limit=50)
```

Supports:

- Default Reels feed
- Search results
- Hashtag pages

Examples:

```python
scroll_reels()

scroll_reels(
    search="yoga"
)

scroll_reels(
    hashtag="yoga"
)
```

### 3. Return Results

```python
[
    {
        "url": "...",
        "creator": "...",
        "caption": "...",
        "likes": 12345,
        "comments": 123,
        "date_posted": "...",
        "audio": "...",
    }
]
```

The MCP does not perform analysis.

Its job is to collect and return reel data.

The AI agent is responsible for:

- Trend detection
- Content analysis
- Ranking
- Content recommendations
- Content generation

## Example Workflow

```text
User:
Find content ideas for beginner yoga.

Agent:
→ login_status()

Agent:
→ scroll_reels(
     search="beginner yoga",
     limit=100
   )

MCP:
→ Returns reel metadata

Agent:
→ Filters high-engagement reels
→ Analyzes hooks and formats
→ Returns top content ideas
```

## Install

Requires [`uv`](https://docs.astral.sh/uv/). Two one-time setup steps before any
agent can use it:

```bash
# 1. Install the headless browser (shared cache, done once per machine)
uvx --from doomscroll-mcp playwright install chromium

# 2. Log in to Instagram by hand (opens a visible browser; no credentials stored)
uvx --from doomscroll-mcp doomscroll-login
```

> From a git clone instead of PyPI, swap `uvx --from doomscroll-mcp` for
> `uv run --directory /path/to/doomscroll-mcp`.

Then add it to your agent. The server speaks MCP over stdio.

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) /
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "doomscroll": {
      "command": "uvx",
      "args": ["doomscroll-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add doomscroll -- uvx doomscroll-mcp
```

### Cursor

`~/.cursor/mcp.json` (or any MCP client using the standard schema):

```json
{
  "mcpServers": {
    "doomscroll": {
      "command": "uvx",
      "args": ["doomscroll-mcp"]
    }
  }
}
```

### From a local clone (no PyPI)

```json
{
  "mcpServers": {
    "doomscroll": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/doomscroll-mcp", "doomscroll-mcp"]
    }
  }
}
```

After it's wired up, have the agent call `doctor()` to confirm it sees your
logged-in profile. If `login_status()` ever reports logged out (expired session
or a checkpoint), run `doomscroll-login` again.

### Tools

- `login(force=False)` — headful sign-in, persist profile
- `login_status()` — is the session logged in?
- `logout()` — clear the profile
- `doctor()` — browser/profile/auth diagnostics + next action
- `scroll_reels(limit=50, sort_by=None, top=None, mode=None)` — feed, stop at a reel count
- `doomscroll(duration_seconds, sort_by=None, top=None, mode=None)` — feed, stop after a wall-clock time
- `search_reels(query, limit=50, sort_by=None, top=None, mode=None)` — keyword search → matching reels
- `hashtag_reels(tag, limit=50, sort_by=None, top=None, mode=None)` — hashtag → matching reels

`search_reels` / `hashtag_reels` hit Instagram's `top_serp` search API directly
(relevance-filtered, paginated), not the explore UI.

`doomscroll` scrolls for a fixed time instead of a fixed count — e.g.
`doomscroll(600)` doomscrolls for 10 minutes. Add `sort_by="views"` + `top=10`
to get "the best reels from N minutes of scrolling". Duration is clamped to
`DOOMSCROLL_MAX_DURATION_S` (default 30 min). `sort_by` ∈
`views | likes | reposts | recent` (descending; `None` = discovery order).
Responses include `stopped_reason` (`limit | duration | dry | capped`).

### Filters

All four collection tools accept filters, applied **after collection, before
sort/top**:

- `posted_within_hours` — recency window (e.g. `24` = last day)
- `min_views` / `min_likes` / `min_reposts` — engagement floors ("viral")
- `contains` — caption keyword, case-insensitive

Example — "best fresh reels from 10 minutes of doomscrolling":
`doomscroll(600, posted_within_hours=24, sort_by="likes", top=10)`.

Responses include `filtered_out` (how many were dropped) and echo the active
`filters`. An empty result purely because filters excluded everything is a valid
response (`reels: []`), not an error.

Notes:
- The feed's `views` are null — use `min_likes` on the feed, `min_views` on
  search/hashtag.
- The home feed mixes fresh and evergreen reels, so a tight `posted_within_hours`
  returns only the fresh minority (a longer `doomscroll` catches more).
- `contains` is keyword matching, not topic understanding. For real topic
  relevance use `search_reels` (Instagram's own ranking); semantic topic is the
  agent's job, not the server's.

Errors come back as structured dicts (`code`, `retry_after`, `requires_headful`,
`suggested_tool`) so an agent can recover instead of stalling.

See [`docs/sample-output.md`](docs/sample-output.md) for a real `scroll_reels`
run against the live feed.

## Vision

Turn Instagram into a structured data source for AI-powered content research.

Login once. Scroll automatically. Return structured reel data. Let the AI decide
what matters.
