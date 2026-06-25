# DoomScroll MCP

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
- Shares (when available)
- Date posted
- Visible engagement metrics

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

## Install & Run

```bash
uv sync                              # install
uv run playwright install chromium   # one-time browser
uv run doomscroll-mcp                # start MCP server (stdio)
```

First run: call `login()` — a visible browser opens, you sign in by hand (handles
2FA / checkpoints), and the session is persisted. No credentials are stored.

### MCP client config

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

### Tools

- `login(force=False)` — headful sign-in, persist profile
- `login_status()` — is the session logged in?
- `logout()` — clear the profile
- `doctor()` — browser/profile/auth diagnostics + next action
- `scroll_reels(limit=50, mode=None)` — default feed → structured reel metadata

Errors come back as structured dicts (`code`, `retry_after`, `requires_headful`,
`suggested_tool`) so an agent can recover instead of stalling.

See [`docs/sample-output.md`](docs/sample-output.md) for a real `scroll_reels`
run against the live feed.

## Vision

Turn Instagram into a structured data source for AI-powered content research.

Login once. Scroll automatically. Return structured reel data. Let the AI decide
what matters.
