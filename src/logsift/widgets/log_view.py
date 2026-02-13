"""Main scrollable log line display widget."""

from __future__ import annotations

import bisect
from typing import Any, ClassVar

from rich.segment import Segment
from rich.style import Style
from textual.binding import BindingType
from textual.geometry import Size
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

from logsift.models import ContentType, LogLine
from logsift.widgets.log_line import get_line_height, render_json_expanded


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
        ("j", "toggle_json_global", "Toggle JSON"),
        ("enter", "toggle_json_line", "Toggle line"),
    ]

    cursor_line: reactive[int] = reactive(0)

    def __init__(self, lines: list[LogLine] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._lines: list[LogLine] = lines or []
        self._max_width: int = 0
        # JSON expansion state
        self._global_expand: bool = False
        self._line_expand: set[int] = set()
        self._sticky_expand: bool = False
        # Height tracking for variable-height lines
        self._heights: list[int] = []
        self._offsets: list[int] = []

    def on_mount(self) -> None:
        self._recompute_heights()

    def set_lines(self, lines: list[LogLine]) -> None:
        """Replace all log lines and refresh display."""
        self._lines = lines
        self._global_expand = False
        self._line_expand.clear()
        self._sticky_expand = False
        self.cursor_line = 0
        self._recompute_heights()
        self.refresh()

    def _is_expanded(self, line_index: int) -> bool:
        """Check if a line should be rendered expanded."""
        if self._global_expand:
            return True
        if line_index in self._line_expand:
            return True
        return self._sticky_expand and line_index == self.cursor_line

    def _recompute_heights(self) -> None:
        """Recompute line heights and prefix-sum offsets."""
        self._heights = []
        self._offsets = []
        offset = 0
        for i, line in enumerate(self._lines):
            expanded = self._is_expanded(i)
            h = get_line_height(line, expanded)
            self._heights.append(h)
            self._offsets.append(offset)
            offset += h

        if self._lines:
            self._max_width = max(len(line.raw) for line in self._lines)
        else:
            self._max_width = 0
        total_height = offset
        self.virtual_size = Size(self._max_width + 10, total_height)

    def _display_row_to_line(self, display_row: int) -> tuple[int, int]:
        """Map a display row to (line_index, sub_row) using binary search on offsets."""
        if not self._offsets:
            return 0, 0
        idx = bisect.bisect_right(self._offsets, display_row) - 1
        idx = max(0, min(idx, len(self._lines) - 1))
        sub_row = display_row - self._offsets[idx]
        return idx, sub_row

    @property
    def line_count(self) -> int:
        return len(self._lines)

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        display_row = scroll_y + y
        content_width = self.scrollable_content_region.width

        if content_width <= 0:
            return Strip.blank(self.size.width, self.rich_style)

        total_height = self._offsets[-1] + self._heights[-1] if self._offsets else 0
        if display_row >= total_height or display_row < 0:
            return Strip.blank(content_width, self.rich_style)

        line_index, sub_row = self._display_row_to_line(display_row)
        line = self._lines[line_index]
        is_highlighted = line_index == self.cursor_line
        expanded = self._is_expanded(line_index)

        highlight_style = self.get_component_rich_style("logview--highlight")
        timestamp_style = self.get_component_rich_style("logview--timestamp")
        json_style = self.get_component_rich_style("logview--json")
        text_style = self.get_component_rich_style("logview--text")
        lineno_style = self.get_component_rich_style("logview--line-number")
        bg_style = highlight_style if is_highlighted else Style()

        if expanded and line.content_type == ContentType.JSON and line.parsed_json is not None:
            strips = render_json_expanded(line, content_width, lineno_style, timestamp_style, bg_style)
            strip = strips[sub_row] if sub_row < len(strips) else Strip.blank(content_width, self.rich_style)
        else:
            segments = self._render_compact_line(line, lineno_style, timestamp_style, json_style, text_style, bg_style)
            strip = Strip(segments)

        strip = strip.crop(scroll_x, scroll_x + content_width)
        strip = strip.extend_cell_length(content_width)
        strip = strip.apply_style(self.rich_style)

        return strip

    def _render_compact_line(
        self,
        line: LogLine,
        lineno_style: Style,
        timestamp_style: Style,
        json_style: Style,
        text_style: Style,
        bg_style: Style,
    ) -> list[Segment]:
        """Render a single compact log line."""
        segments: list[Segment] = []

        lineno_text = f"{line.line_number:>6} "
        segments.append(Segment(lineno_text, lineno_style + bg_style))

        if line.timestamp is not None:
            ts_end = len(line.raw) - len(line.content)
            ts_text = line.raw[:ts_end]
            segments.append(Segment(ts_text, timestamp_style + bg_style))

        if line.content_type == ContentType.JSON:
            segments.append(Segment(line.content, json_style + bg_style))
        else:
            segments.append(Segment(line.content, text_style + bg_style))

        if bg_style != Style():
            segments.append(Segment(" " * 10, bg_style))

        return segments

    def watch_cursor_line(self, _old_value: int, _new_value: int) -> None:
        self._recompute_heights()
        self._scroll_cursor_into_view()
        self.refresh()

    def _scroll_cursor_into_view(self) -> None:
        """Ensure the cursor line is visible."""
        if not self._lines or not self._offsets:
            return
        region_height = self.scrollable_content_region.height
        if region_height <= 0:
            return

        cursor_start = self._offsets[self.cursor_line]
        cursor_height = self._heights[self.cursor_line]
        scroll_y = self.scroll_offset.y

        if cursor_start < scroll_y:
            self.scroll_to(y=cursor_start, animate=False)
        elif cursor_start + cursor_height > scroll_y + region_height:
            self.scroll_to(y=cursor_start + cursor_height - region_height, animate=False)

    # --- Actions ---

    def action_cursor_up(self) -> None:
        if self.cursor_line > 0:
            self.cursor_line -= 1

    def action_cursor_down(self) -> None:
        if self.cursor_line < len(self._lines) - 1:
            self.cursor_line += 1

    def action_page_up(self) -> None:
        page_size = max(1, self.scrollable_content_region.height - 1)
        # Find the line that is page_size display rows above
        if not self._offsets:
            return
        target_row = max(0, self._offsets[self.cursor_line] - page_size)
        target_line, _ = self._display_row_to_line(target_row)
        self.cursor_line = target_line

    def action_page_down(self) -> None:
        page_size = max(1, self.scrollable_content_region.height - 1)
        if not self._offsets:
            return
        target_row = self._offsets[self.cursor_line] + page_size
        target_line, _ = self._display_row_to_line(target_row)
        self.cursor_line = min(target_line, len(self._lines) - 1)

    def action_scroll_home(self) -> None:
        self.cursor_line = 0

    def action_scroll_end(self) -> None:
        if self._lines:
            self.cursor_line = len(self._lines) - 1

    def action_toggle_json_global(self) -> None:
        """Toggle global JSON pretty-print for all lines."""
        self._global_expand = not self._global_expand
        self._line_expand.clear()
        self._sticky_expand = False
        self._recompute_heights()
        self._scroll_cursor_into_view()
        self.refresh()

    def action_toggle_json_line(self) -> None:
        """Toggle JSON pretty-print for the current line."""
        if not self._lines:
            return
        line = self._lines[self.cursor_line]
        if line.content_type != ContentType.JSON or line.parsed_json is None:
            return

        if self._global_expand:
            return

        self._sticky_expand = not self._sticky_expand

        self._recompute_heights()
        self._scroll_cursor_into_view()
        self.refresh()
