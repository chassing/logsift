"""Bottom status bar."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget


class StatusBar(Widget):
    """Bottom status bar showing line counts and source info."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: #264f78;
        color: #ffffff;
        padding: 0 1;
    }
    """

    def __init__(self, source: str = "", id: str | None = None) -> None:
        super().__init__(id=id)
        self._total: int = 0
        self._filtered: int | None = None
        self._source = source
        self._tailing: bool = False
        self._new_lines: int = 0

    def update_counts(self, total: int, filtered: int | None = None) -> None:
        """Update the line counts."""
        self._total = total
        self._filtered = filtered
        self.refresh()

    def set_tailing(self, tailing: bool) -> None:
        """Set tailing mode indicator."""
        self._tailing = tailing
        self.refresh()

    def set_new_lines(self, count: int) -> None:
        """Set new lines indicator (when scrolled up during tailing)."""
        self._new_lines = count
        self.refresh()

    def render(self) -> Text:
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

        right_part = self._source
        if right_part:
            used = len(text.plain)
            padding = max(1, self.size.width - used - len(right_part))
            text.append(" " * padding)
            text.append(right_part)

        return text
