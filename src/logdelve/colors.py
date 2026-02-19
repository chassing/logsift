"""Search pattern color palette for multi-pattern highlighting."""

from __future__ import annotations

from rich.style import Style

# 10 distinct background color pairs (normal, bright) for multi-pattern search highlights.
# White foreground text on tinted backgrounds. First entry matches the original single-search highlight.
_SEARCH_COLORS: list[tuple[str, str]] = [
    ("#6e5600", "#9e7c00"),  # amber
    ("#5c1a1a", "#8c2a2a"),  # red
    ("#1a4a5c", "#2a7a8c"),  # teal
    ("#3d1a5c", "#5d2a8c"),  # purple
    ("#1a5c2e", "#2a8c4e"),  # green
    ("#5c3a1a", "#8c5a2a"),  # orange
    ("#1a2a5c", "#2a4a8c"),  # blue
    ("#5c1a4a", "#8c2a7a"),  # magenta
    ("#3a5c1a", "#5a8c2a"),  # olive
    ("#1a5c5c", "#2a8c8c"),  # cyan
]


def search_match_style(color_index: int) -> Style:
    """Return the normal (non-current) highlight style for a search pattern."""
    return Style(bgcolor=_SEARCH_COLORS[color_index][0], color="#ffffff")


def search_current_style(color_index: int) -> Style:
    """Return the current-match highlight style for a search pattern (brighter + bold)."""
    return Style(bgcolor=_SEARCH_COLORS[color_index][1], color="#ffffff", bold=True)
