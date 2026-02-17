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

        # Base shortcuts
        text.append(" f", style="bold")
        text.append(" filter-in", style="dim")
        text.append("  F", style="bold")
        text.append(" filter-out", style="dim")
        # x toggle all filters
        text.append("  x", style="bold")
        text.append(" filters off", style="dim")

        text.append("  │", style="dim")
        text.append("  a", style="bold")
        text.append(" analyze", style="dim")

        # Search: show active search or shortcut
        text.append("  │", style="dim")
        text.append("  /", style="bold")
        if self._search_text:
            display = (
                self._search_text[:_MAX_SEARCH_DISPLAY_LEN] + "…"
                if len(self._search_text) > _MAX_SEARCH_DISPLAY_LEN
                else self._search_text
            )
            text.append(f" {display}", style="bold cyan")
            text.append("  n", style="bold")
            text.append("/", style="dim")
            text.append("N", style="bold")
            text.append(" next/prev", style="dim")
        else:
            text.append(" search", style="dim")

        # Level filter (show when levels detected)
        if self._has_levels:
            text.append("  │  ", style="dim")
            text.append("e", style="bold")
            if self._min_level is not None:
                text.append(f" ≥{self._min_level.value.upper()}", style="bold yellow")
            else:
                text.append(" level-filter", style="dim")

        # Anomaly info
        if self._anomaly_count > 0:
            text.append("  │  ", style="dim")
            text.append("!", style="bold")
            if self._anomaly_filter_active:
                text.append(f" {self._anomaly_count} anomalies", style="bold red")
            else:
                text.append(f" {self._anomaly_count} anomalies", style="dim")

        # Active filters
        if self.filters:
            text.append("  │  ", style="dim")
            total = len(self.filters)
            active = sum(1 for r in self.filters if r.enabled)
            text.append(f"{total} filters", style="bold")
            if active < total:
                text.append(f" ({active})", style="dim")
            text.append("  m", style="bold")
            text.append(" manage", style="dim")
            text.append("  1-9", style="bold")
            text.append(" toggle", style="dim")

        return text
