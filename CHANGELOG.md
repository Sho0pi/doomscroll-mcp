# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-06-25

First release. An MCP server that lets AI agents browse Instagram Reels and
return structured reel metadata for content research.

### Added
- MCP tools: `login`, `login_status`, `logout`, `doctor`.
- `scroll_reels` — default feed, stop at a reel count.
- `doomscroll` — default feed, stop after a wall-clock duration.
- `search_reels` / `hashtag_reels` — topic discovery via Instagram's `top_serp`
  search API (relevance-filtered, paginated).
- `sort_by` (views/likes/reposts/recent) + `top` on all collection tools.
- Filters: `posted_within_hours`, `min_views` / `min_likes` / `min_reposts`,
  `contains` (caption keyword).
- Network-first extraction (intercepts Instagram JSON; DOM fallback), persistent
  login profile, anti-detection launch, typed loop-recoverable errors, passive
  humanization with `fast_test` / `normal_passive` / `conservative` modes.
- Reel fields: url, creator, caption/description, visual_description, likes,
  comments, views, reposts, date_posted (ISO + unix), audio.

### Notes
- Instagram does not expose reel view counts in the home feed; `views` populates
  only from search results. See `docs/views-investigation.md`.
- Automating Instagram violates its Terms of Service — use a throwaway account.

[Unreleased]: https://github.com/Sho0pi/doomscroll-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Sho0pi/doomscroll-mcp/releases/tag/v0.1.0
