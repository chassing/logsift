"""Bottom status bar."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from logdelve.models import LogLevel


class StatusBar(Widget):
    """Bottom status bar showing line counts, search info, and source."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, source: str = "", id: str | None = None) -> None:  # noqa: A002
        super().__init__(id=id)
        self._total: int = 0
        self._filtered: int | None = None
        self._source = source
        self._tailing: bool = False
        self._new_lines: int = 0
        self._search_current: int | None = None
        self._search_total: int | None = None
        self._level_counts: dict[LogLevel, int] = {}
        self._min_level: LogLevel | None = None
        self._anomaly_count: int = 0

    def update_counts(self, total: int, filtered: int | None = None) -> None:
        """Update the line counts."""
        self._total = total
        self._filtered = filtered
        self.refresh()

    def set_tailing(self, *, tailing: bool) -> None:
        """Set tailing mode indicator."""
        self._tailing = tailing
        self.refresh()

    def set_new_lines(self, count: int) -> None:
        """Set new lines indicator (when scrolled up during tailing)."""
        self._new_lines = count
        self.refresh()

    def set_search_info(self, current: int, total: int) -> None:
        """Set search match info."""
        self._search_current = current
        self._search_total = total
        self.refresh()

    def set_level_counts(self, counts: dict[LogLevel, int], min_level: LogLevel | None = None) -> None:
        """Set log level counts and current min level filter."""
        self._level_counts = counts
        self._min_level = min_level
        self.refresh()

    def set_anomaly_count(self, count: int) -> None:
        """Set anomaly count."""
        self._anomaly_count = count
        self.refresh()

    def clear_search_info(self) -> None:
        """Clear search info from status bar."""
        self._search_current = None
        self._search_total = None
        self.refresh()

    def render(self) -> Text:  # noqa: C901, PLR0912
        text = Text()

        if self._tailing:
            text.append(" TAIL ", style="bold reverse")
            text.append(" ")

        if self._filtered is not None:
            text.append(f"{self._filtered} of {self._total} lines")
        else:
            text.append(f"{self._total} lines")

        if self._new_lines > 0:
            text.append(f"  +{self._new_lines} new", style="bold")

        if self._search_total is not None:
            if self._search_total == 0:
                text.append("  No matches", style="bold italic")
            else:
                text.append(f"  [{self._search_current}/{self._search_total}]", style="bold")

        # Level counts
        if self._level_counts:
            parts: list[str] = []
            fatal = self._level_counts.get(LogLevel.FATAL, 0)
            errors = self._level_counts.get(LogLevel.ERROR, 0)
            warns = self._level_counts.get(LogLevel.WARN, 0)
            if fatal:
                parts.append(f"F:{fatal}")
            if errors:
                parts.append(f"E:{errors}")
            if warns:
                parts.append(f"W:{warns}")
            if parts:
                text.append(f"  {' '.join(parts)}", style="bold")
            if self._min_level is not None:
                text.append(f"  ≥{self._min_level.value.upper()}", style="italic")

        if self._anomaly_count > 0:
            text.append(f"  A:{self._anomaly_count}", style="bold red")

        right_part = self._source
        if right_part:
            used = len(text.plain)
            padding = max(1, self.size.width - used - len(right_part))
            text.append(" " * padding)
            text.append(right_part)

        return text
