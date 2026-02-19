"""Bottom status bar."""

from __future__ import annotations

from rich.style import Style
from rich.text import Text
from textual.widget import Widget

from logdelve.colors import _SEARCH_COLORS
from logdelve.models import LogLevel

_MILLION = 1_000_000
_TEN_THOUSAND = 10_000
_THOUSAND = 1_000


def _format_count(n: int) -> str:
    """Format a line count compactly: 1234 -> '1,234', 1234567 -> '1.2M'."""
    if n >= _MILLION:
        return f"{n / _MILLION:.1f}M"
    if n >= _TEN_THOUSAND:
        return f"{n / _THOUSAND:.0f}K"
    return f"{n:,}"


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
        self._pattern_counts: list[tuple[int, int]] | None = None
        self._level_counts: dict[LogLevel, int] = {}
        self._min_level: LogLevel | None = None
        self._anomaly_count: int = 0
        self._bookmark_count: int = 0
        self._loading_loaded: int | None = None
        self._loading_total: int | None = None

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
        """Set search match info (single-pattern backward compat)."""
        self._search_current = current
        self._search_total = total
        self._pattern_counts = None
        self.refresh()

    def set_search_pattern_info(self, current: int, total: int, pattern_counts: list[tuple[int, int]]) -> None:
        """Set search match info with per-pattern counts."""
        self._search_current = current
        self._search_total = total
        self._pattern_counts = pattern_counts or None
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

    def set_bookmark_count(self, count: int) -> None:
        """Set bookmark count."""
        self._bookmark_count = count
        self.refresh()

    def set_loading_progress(self, loaded: int, total: int | None = None) -> None:
        """Set loading progress (for chunked file loading)."""
        self._loading_loaded = loaded
        self._loading_total = total
        self.refresh()

    def clear_loading_progress(self) -> None:
        """Clear loading progress indicator."""
        self._loading_loaded = None
        self._loading_total = None
        self.refresh()

    def clear_search_info(self) -> None:
        """Clear search info from status bar."""
        self._search_current = None
        self._search_total = None
        self._pattern_counts = None
        self.refresh()

    def _render_search_counts(self, text: Text) -> None:
        """Render search match counts with per-pattern coloring."""
        if self._search_total is None:
            return
        if self._search_total == 0:
            text.append("  No matches", style="bold italic")
        elif self._pattern_counts:
            # Per-pattern colored counts: [current/count1+count2+...]
            text.append("  [")
            if self._search_current is not None and self._search_current > 0:
                text.append(str(self._search_current), style="bold")
            text.append("/")
            for i, (count, color_index) in enumerate(self._pattern_counts):
                if i > 0:
                    text.append("+")
                fg_hex = _SEARCH_COLORS[color_index][0]
                text.append(str(count), style=Style(color=fg_hex, bold=True))
            text.append("]")
        else:
            # Fallback: single count format
            text.append(f"  [{self._search_current}/{self._search_total}]", style="bold")

    def render(self) -> Text:  # noqa: C901, PLR0912
        text = Text()

        if self._tailing:
            text.append(" TAIL ", style="bold reverse")
            text.append(" ")

        if self._filtered is not None:
            text.append(f"{self._filtered} of {self._total} lines")
        else:
            text.append(f"{self._total} lines")

        if self._loading_loaded is not None:
            loaded = _format_count(self._loading_loaded)
            if self._loading_total is not None:
                total = _format_count(self._loading_total)
                text.append(f"  Loading: {loaded}/~{total}", style="bold italic")
            else:
                text.append(f"  Loading: {loaded}...", style="bold italic")

        if self._new_lines > 0:
            text.append(f"  +{self._new_lines} new", style="bold")

        self._render_search_counts(text)

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
                text.append(f"  \u2265{self._min_level.value.upper()}", style="italic")

        if self._anomaly_count > 0:
            text.append(f"  A:{self._anomaly_count}", style="bold red")

        if self._bookmark_count > 0:
            text.append(f"  B:{self._bookmark_count}", style="bold")

        right_part = self._source
        if right_part:
            used = len(text.plain)
            padding = max(1, self.size.width - used - len(right_part))
            text.append(" " * padding)
            text.append(right_part)

        return text
