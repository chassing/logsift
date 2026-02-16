"""Main scrollable log line display widget."""

from __future__ import annotations

import bisect
from typing import Any, ClassVar

from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding, BindingType
from textual.geometry import Size
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

from logsift.filters import apply_filters, check_line
from logsift.models import ContentType, FilterRule, LogLine
from logsift.widgets.log_line import get_line_height, render_json_expanded


class LogView(ScrollView, can_focus=True):
    """Scrollable log line viewer using the Line API for virtual rendering."""

    DEFAULT_CSS = """
    LogView {
        background: $surface;
        height: 1fr;
    }

    LogView > .logview--highlight {
        background: #264f78;
        color: #ffffff;
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
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "scroll_home", "Home", show=False),
        Binding("end", "scroll_end", "End", show=False),
        Binding("g", "goto_top_or_prefix", "Top (gg)", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
        Binding("j", "toggle_json_global", "JSON"),
        Binding("enter", "toggle_json_line", "Expand", show=False),
        Binding("n", "toggle_line_numbers", "Lines#"),
    ]

    cursor_line: reactive[int] = reactive(0)

    def __init__(self, lines: list[LogLine] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._all_lines: list[LogLine] = lines or []
        self._g_pending: bool = False
        self._filtered_indices: list[int] = []
        self._filter_rules: list[FilterRule] = []
        self._max_width: int = 0
        self._show_line_numbers: bool = True
        # JSON expansion state
        self._global_expand: bool = False
        self._line_expand: set[int] = set()
        self._sticky_expand: bool = False
        # Height tracking for variable-height lines
        self._heights: list[int] = []
        self._offsets: list[int] = []

    @property
    def _lines(self) -> list[LogLine]:
        """Get the currently visible lines (filtered or all)."""
        if self._filtered_indices is not None and self._filter_rules:
            return [self._all_lines[i] for i in self._filtered_indices]
        return self._all_lines

    @property
    def total_count(self) -> int:
        return len(self._all_lines)

    @property
    def filtered_count(self) -> int:
        return len(self._lines)

    @property
    def has_filters(self) -> bool:
        return bool(self._filter_rules)

    def on_mount(self) -> None:
        self._apply_filters()

    def set_lines(self, lines: list[LogLine]) -> None:
        """Replace all log lines and refresh display."""
        self._all_lines = lines
        self._global_expand = False
        self._line_expand.clear()
        self._sticky_expand = False
        self._filter_rules.clear()
        self.cursor_line = 0
        self._apply_filters()

    def set_filters(self, rules: list[FilterRule]) -> None:
        """Apply filter rules and refresh display."""
        self._filter_rules = list(rules)
        old_cursor = self.cursor_line
        self._apply_filters()
        # Keep cursor in bounds
        visible = self._lines
        if visible:
            self.cursor_line = min(old_cursor, len(visible) - 1)
        else:
            self.cursor_line = 0
        self.refresh()

    def append_line(self, line: LogLine) -> None:
        """Append a single line (for tailing). Auto-scrolls only if cursor was on last line."""
        visible_before = len(self._lines)
        cursor_was_on_last = self.cursor_line >= visible_before - 1

        idx = len(self._all_lines)
        self._all_lines.append(line)

        # Incremental filter check
        if self._filter_rules:
            if check_line(line, self._filter_rules):
                self._filtered_indices.append(idx)
            else:
                return  # Line filtered out, no display update needed
        else:
            self._filtered_indices.append(idx)

        # Update heights for the new visible line
        visible_idx = len(self._lines) - 1
        expanded = self._is_expanded(visible_idx)
        h = get_line_height(line, expanded)
        self._heights.append(h)
        offset = self._offsets[-1] + self._heights[-2] if len(self._offsets) > 0 else 0
        self._offsets.append(offset)

        self._max_width = max(self._max_width, len(line.raw))
        total_height = self._offsets[-1] + self._heights[-1] if self._offsets else 0
        self.virtual_size = Size(self._max_width + 10, total_height)

        if cursor_was_on_last:
            self.cursor_line = len(self._lines) - 1
            self._scroll_cursor_into_view()

        self.refresh()

    def _is_at_bottom(self) -> bool:
        """Check if the view is scrolled to the bottom."""
        if not self._offsets:
            return True
        total_height = self._offsets[-1] + self._heights[-1]
        region_height = self.scrollable_content_region.height
        return self.scroll_offset.y + region_height >= total_height - 1

    def _apply_filters(self) -> None:
        """Recompute filtered indices and update display."""
        if self._filter_rules:
            self._filtered_indices = apply_filters(self._all_lines, self._filter_rules)
        else:
            self._filtered_indices = list(range(len(self._all_lines)))
        self._recompute_heights()

    def _is_expanded(self, line_index: int) -> bool:
        """Check if a visible line index should be rendered expanded."""
        if self._global_expand:
            return True
        if line_index in self._line_expand:
            return True
        return self._sticky_expand and line_index == self.cursor_line

    def _recompute_heights(self) -> None:
        """Recompute line heights and prefix-sum offsets."""
        visible = self._lines
        self._heights = []
        self._offsets = []
        offset = 0
        for i, line in enumerate(visible):
            expanded = self._is_expanded(i)
            h = get_line_height(line, expanded)
            self._heights.append(h)
            self._offsets.append(offset)
            offset += h

        if visible:
            self._max_width = max(len(line.raw) for line in visible)
        else:
            self._max_width = 0
        self.virtual_size = Size(self._max_width + 10, offset)

    def _display_row_to_line(self, display_row: int) -> tuple[int, int]:
        """Map a display row to (line_index, sub_row) using binary search."""
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
        visible = self._lines
        line = visible[line_index]
        is_highlighted = line_index == self.cursor_line
        expanded = self._is_expanded(line_index)

        highlight_style = self.get_component_rich_style("logview--highlight")
        timestamp_style = self.get_component_rich_style("logview--timestamp")
        json_style = self.get_component_rich_style("logview--json")
        text_style = self.get_component_rich_style("logview--text")
        lineno_style = self.get_component_rich_style("logview--line-number")
        bg_style = highlight_style if is_highlighted else Style()

        if expanded and line.content_type == ContentType.JSON and line.parsed_json is not None:
            strips = render_json_expanded(
                line, content_width, lineno_style, timestamp_style, bg_style, self._show_line_numbers
            )
            strip = strips[sub_row] if sub_row < len(strips) else Strip.blank(content_width, self.rich_style)
        else:
            segments = self._render_compact_line(line, lineno_style, timestamp_style, json_style, text_style, bg_style)
            strip = Strip(segments)

        strip = strip.crop(scroll_x, scroll_x + content_width)
        if is_highlighted:
            fill_style = Style(bgcolor=highlight_style.bgcolor)
            strip = strip.extend_cell_length(content_width, fill_style)
        else:
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

        if self._show_line_numbers:
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
        visible = self._lines
        if not visible or not self._offsets:
            return
        region_height = self.scrollable_content_region.height
        if region_height <= 0:
            return

        cursor = min(self.cursor_line, len(visible) - 1)
        cursor_start = self._offsets[cursor]
        cursor_height = self._heights[cursor]
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
        visible = self._lines
        if not visible:
            return
        line = visible[self.cursor_line]
        if line.content_type != ContentType.JSON or line.parsed_json is None:
            return

        if self._global_expand:
            return

        self._sticky_expand = not self._sticky_expand

        self._recompute_heights()
        self._scroll_cursor_into_view()
        self.refresh()

    def action_toggle_line_numbers(self) -> None:
        """Toggle line number display."""
        self._show_line_numbers = not self._show_line_numbers
        self.refresh()

    def action_goto_top_or_prefix(self) -> None:
        """Handle 'g' key: second 'g' goes to top (gg)."""
        if self._g_pending:
            self._g_pending = False
            self.cursor_line = 0
        else:
            self._g_pending = True
            self.set_timer(0.5, self._clear_g_pending)

    def _clear_g_pending(self) -> None:
        self._g_pending = False
