"""Main scrollable log line display widget."""

from __future__ import annotations

from typing import Any, ClassVar

from rich.segment import Segment
from rich.style import Style
from textual.binding import BindingType
from textual.geometry import Size
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

from logsift.models import ContentType, LogLine


class LogView(ScrollView, can_focus=True):
    """Scrollable log line viewer using the Line API for virtual rendering."""

    DEFAULT_CSS = """
    LogView {
        background: $surface;
    }

    LogView > .logview--highlight {
        background: $accent;
        color: $text;
    }

    LogView > .logview--timestamp {
        color: $text-muted;
    }

    LogView > .logview--json {
        color: $success;
    }

    LogView > .logview--text {
        color: $text;
    }

    LogView > .logview--line-number {
        color: $text-disabled;
    }
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "logview--highlight",
        "logview--timestamp",
        "logview--json",
        "logview--text",
        "logview--line-number",
    }

    BINDINGS: ClassVar[list[BindingType]] = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
        ("home", "scroll_home", "Home"),
        ("end", "scroll_end", "End"),
    ]

    cursor_line: reactive[int] = reactive(0)

    def __init__(self, lines: list[LogLine] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._lines: list[LogLine] = lines or []
        self._max_width: int = 0

    def on_mount(self) -> None:
        self._update_virtual_size()

    def set_lines(self, lines: list[LogLine]) -> None:
        """Replace all log lines and refresh display."""
        self._lines = lines
        self.cursor_line = 0
        self._update_virtual_size()
        self.refresh()

    def _update_virtual_size(self) -> None:
        if self._lines:
            self._max_width = max(len(line.raw) for line in self._lines)
        else:
            self._max_width = 0
        self.virtual_size = Size(self._max_width + 10, len(self._lines))

    @property
    def line_count(self) -> int:
        return len(self._lines)

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        line_index = scroll_y + y
        content_width = self.scrollable_content_region.width

        if content_width <= 0:
            return Strip.blank(self.size.width, self.rich_style)

        if line_index >= len(self._lines) or line_index < 0:
            return Strip.blank(content_width, self.rich_style)

        line = self._lines[line_index]
        is_highlighted = line_index == self.cursor_line

        segments = self._render_log_line(line, is_highlighted)
        strip = Strip(segments)
        strip = strip.crop(scroll_x, scroll_x + content_width)
        strip = strip.extend_cell_length(content_width)
        strip = strip.apply_style(self.rich_style)

        return strip

    def _render_log_line(self, line: LogLine, highlighted: bool) -> list[Segment]:
        """Render a single log line to a list of segments."""
        highlight_style = self.get_component_rich_style("logview--highlight")
        timestamp_style = self.get_component_rich_style("logview--timestamp")
        json_style = self.get_component_rich_style("logview--json")
        text_style = self.get_component_rich_style("logview--text")
        lineno_style = self.get_component_rich_style("logview--line-number")

        bg_style = highlight_style if highlighted else Style()

        segments: list[Segment] = []

        # Line number
        lineno_text = f"{line.line_number:>6} "
        segments.append(Segment(lineno_text, lineno_style + bg_style))

        # Timestamp portion (if present)
        if line.timestamp is not None:
            ts_end = len(line.raw) - len(line.content)
            ts_text = line.raw[:ts_end]
            segments.append(Segment(ts_text, timestamp_style + bg_style))

        # Content
        if line.content_type == ContentType.JSON:
            segments.append(Segment(line.content, json_style + bg_style))
        else:
            segments.append(Segment(line.content, text_style + bg_style))

        # Pad for highlighted lines
        if highlighted:
            segments.append(Segment(" " * 10, bg_style))

        return segments

    def watch_cursor_line(self, _old_value: int, _new_value: int) -> None:
        self._scroll_cursor_into_view()
        self.refresh()

    def _scroll_cursor_into_view(self) -> None:
        """Ensure the cursor line is visible."""
        if not self._lines:
            return
        region_height = self.scrollable_content_region.height
        if region_height <= 0:
            return

        scroll_y = self.scroll_offset.y
        if self.cursor_line < scroll_y:
            self.scroll_to(y=self.cursor_line, animate=False)
        elif self.cursor_line >= scroll_y + region_height:
            self.scroll_to(y=self.cursor_line - region_height + 1, animate=False)

    def action_cursor_up(self) -> None:
        if self.cursor_line > 0:
            self.cursor_line -= 1

    def action_cursor_down(self) -> None:
        if self.cursor_line < len(self._lines) - 1:
            self.cursor_line += 1

    def action_page_up(self) -> None:
        page_size = max(1, self.scrollable_content_region.height - 1)
        self.cursor_line = max(0, self.cursor_line - page_size)

    def action_page_down(self) -> None:
        page_size = max(1, self.scrollable_content_region.height - 1)
        self.cursor_line = min(len(self._lines) - 1, self.cursor_line + page_size)

    def action_scroll_home(self) -> None:
        self.cursor_line = 0

    def action_scroll_end(self) -> None:
        if self._lines:
            self.cursor_line = len(self._lines) - 1
