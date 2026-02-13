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

    def update_counts(self, total: int, filtered: int | None = None) -> None:
        """Update the line counts."""
        self._total = total
        self._filtered = filtered
        self.refresh()

    def render(self) -> Text:
        text = Text()
        if self._filtered is not None:
            text.append(f"{self._filtered} of {self._total} lines")
        else:
            text.append(f"{self._total} lines")

        if self._source:
            padding = max(1, self.size.width - len(text.plain) - len(self._source))
            text.append(" " * padding)
            text.append(self._source)

        return text
