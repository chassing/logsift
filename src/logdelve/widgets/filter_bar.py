"""Compact filter/toolbar bar at the top."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

if TYPE_CHECKING:
    from logdelve.models import FilterRule, LogLevel

_MAX_SEARCH_DISPLAY_LEN = 10


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
        self._search_text: str | None = None
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

    def set_search_text(self, pattern: str | None) -> None:
        """Update active search display."""
        self._search_text = pattern
        self.refresh()

    def render(self) -> Text:
        text = Text()
        s = "  "

        # Search
        if self._search_text:
            display = self._search_text[:_MAX_SEARCH_DISPLAY_LEN] + ("…" if len(self._search_text) > _MAX_SEARCH_DISPLAY_LEN else "")
            text.append(f" /? 🔍 {display}", style="bold cyan")
            text.append(f"{s}n/N ↕", style="dim")
        else:
            text.append(" /? 🔍", style="dim")

        # Filters
        if self.filters:
            total = len(self.filters)
            active = sum(1 for r in self.filters if r.enabled)
            label = f"{active}/{total}" if active < total else str(total)
            text.append(f"{s}f/F ⊞ {label}", style="bold")
            text.append(f"{s}m 📋", style="dim")
        else:
            text.append(f"{s}f/F ⊞", style="dim")

        # Level
        if self._has_levels:
            if self._min_level is not None:
                text.append(f"{s}e ≥{self._min_level.value.upper()}", style="bold yellow")
            else:
                text.append(f"{s}e ≥", style="dim")

        # Anomalies
        if self._anomaly_count > 0:
            style = "bold red" if self._anomaly_filter_active else "dim"
            text.append(f"{s}! ⚠ {self._anomaly_count}", style=style)

        # Bookmarks
        if self._bookmark_count > 0:
            text.append(f"{s}b/B 📌 {self._bookmark_count}", style="bold")
            text.append(f"{s}A ✏", style="dim")
        else:
            text.append(f"{s}b/B 📌", style="dim")

        # Right-aligned shortcuts
        shortcuts = " @ ⏱  : 📍  r 🔗  a 📊  h ❓"
        used = len(text.plain)
        padding = max(1, self.size.width - used - len(shortcuts))
        text.append(" " * padding)
        text.append(shortcuts, style="dim")

        return text
