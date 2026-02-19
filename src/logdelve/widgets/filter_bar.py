"""Compact filter/toolbar bar at the top."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.style import Style
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from logdelve.colors import _SEARCH_COLORS

if TYPE_CHECKING:
    from logdelve.models import FilterRule, LogLevel, SearchPatternSet


class FilterBar(Widget):
    """Always-visible toolbar showing shortcuts and active filter state."""

    DEFAULT_CSS = """
    FilterBar {
        height: 1;
        dock: top;
        background: $surface-darken-1;
        padding: 0 1;
    }
    """

    filters: reactive[list[FilterRule]] = reactive(list, always_update=True)

    def __init__(self, *, id: str | None = None) -> None:  # noqa: A002
        super().__init__(id=id)
        self._min_level: LogLevel | None = None
        self._has_levels: bool = False
        self._anomaly_count: int = 0
        self._anomaly_filter_active: bool = False
        self._search_patterns: SearchPatternSet | None = None
        self._bookmark_count: int = 0

    def set_bookmark_count(self, count: int) -> None:
        """Update bookmark count display."""
        self._bookmark_count = count
        self.refresh()

    def update_filters(self, rules: list[FilterRule]) -> None:
        """Update the displayed filters."""
        self.filters = list(rules)

    def set_level_info(self, min_level: LogLevel | None, *, has_levels: bool = False) -> None:
        """Update level filter display."""
        self._min_level = min_level
        self._has_levels = has_levels
        self.refresh()

    def set_anomaly_info(self, count: int, *, filter_active: bool) -> None:
        """Update anomaly detection display."""
        self._anomaly_count = count
        self._anomaly_filter_active = filter_active
        self.refresh()

    def set_search_patterns(self, patterns: SearchPatternSet) -> None:
        """Update active search patterns display."""
        self._search_patterns = patterns if patterns.active_count > 0 else None
        self.refresh()

    def render(self) -> Text:
        text = Text()
        s = "  "

        # Search chips
        if self._search_patterns and self._search_patterns.active_count > 0:
            self._render_search_chips(text, s)
        else:
            text.append(" /? \U0001f50d", style="dim")

        # Filters
        if self.filters:
            total = len(self.filters)
            active = sum(1 for r in self.filters if r.enabled)
            label = f"{active}/{total}" if active < total else str(total)
            text.append(f"{s}f/F \u229e {label}", style="bold")
            text.append(f"{s}m \U0001f4cb", style="dim")
        else:
            text.append(f"{s}f/F \u229e", style="dim")

        # Level
        if self._has_levels:
            if self._min_level is not None:
                text.append(f"{s}e \u2265{self._min_level.value.upper()}", style="bold yellow")
            else:
                text.append(f"{s}e \u2265", style="dim")

        # Anomalies
        if self._anomaly_count > 0:
            style = "bold red" if self._anomaly_filter_active else "dim"
            text.append(f"{s}! \u26a0 {self._anomaly_count}", style=style)

        # Bookmarks
        if self._bookmark_count > 0:
            text.append(f"{s}b/B \U0001f4cc {self._bookmark_count}", style="bold")
            text.append(f"{s}A \u270f", style="dim")
        else:
            text.append(f"{s}b/B \U0001f4cc", style="dim")

        # Right-aligned shortcuts
        shortcuts = " @ \u23f1  : \U0001f4cd  r \U0001f517  a \U0001f4ca"
        used = len(text.plain)
        padding = max(1, self.size.width - used - len(shortcuts))
        text.append(" " * padding)
        text.append(shortcuts, style="dim")

        return text

    def _render_search_chips(self, text: Text, s: str) -> None:
        """Render color-coded search pattern chips with overflow handling."""
        assert self._search_patterns is not None
        available_width = max(10, self.size.width - 40)
        used_width = 0
        total_patterns = self._search_patterns.active_count
        for shown, pattern in enumerate(self._search_patterns.patterns):
            chip_text = f" {pattern.query.pattern} "
            chip_width = len(chip_text)
            # Check if this chip fits, accounting for potential +N badge
            remaining = total_patterns - shown - 1
            badge_width = len(f" +{remaining} ") + 1 if remaining > 0 else 0
            if used_width + chip_width + badge_width > available_width and shown > 0:
                hidden = total_patterns - shown
                text.append(f" +{hidden} ", style="bold dim")
                break
            bg_hex = _SEARCH_COLORS[pattern.color_index][0]
            text.append(chip_text, style=Style(bgcolor=bg_hex, color="#ffffff"))
            text.append(" ")
            used_width += chip_width + 1
        text.append(f"{s}n/N \u2195", style="dim")
