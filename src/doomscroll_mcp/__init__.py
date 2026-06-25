"""DoomScroll MCP — Instagram Reels browsing for AI agents.

Collects and returns structured reel metadata only. No analysis, ranking, or
recommendation happens here; that is the calling agent's job.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("doomscroll-mcp")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0+dev"
