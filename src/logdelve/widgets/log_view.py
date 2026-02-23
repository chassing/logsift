"""Main scrollable log line display widget."""

from __future__ import annotations

import bisect
from typing import TYPE_CHECKING, Any, ClassVar

from rich.color import Color
from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding, BindingType
from textual.geometry import Size
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

from logdelve.colors import search_current_style, search_match_style
from logdelve.filters import apply_filters, check_line
from logdelve.models import ContentType, FilterRule, LogLevel, LogLine, SearchDirection, SearchPatternSet, SearchQuery
from logdelve.search import find_all_pattern_matches
from logdelve.widgets.log_line import get_line_height, render_json_expanded

if TYPE_CHECKING:
    from datetime import datetime

# Distinct colors for component tags (work on dark and light backgrounds)
_COMPONENT_COLORS = [
    Color.parse("#e06c75"),  # red
    Color.parse("#61afef"),  # blue
    Color.parse("#98c379"),  # green
    Color.parse("#e5c07b"),  # yellow
    Color.parse("#c678dd"),  # purple
    Color.parse("#56b6c2"),  # cyan
    Color.parse("#d19a66"),  # orange
    Color.parse("#be5046"),  # dark red
]


class LogView(ScrollView, can_focus=True):  # noqa: PLR0904
    """Scrollable log line viewer using the Line API for virtual rendering."""

    DEFAULT_CSS = """
    LogView {
        background: $surface;
        height: 1fr;
    }

    LogView > .logview--highlight {
        background: $primary-darken-2;
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

    LogView > .logview--level-error {
        background: #3d1518;
    }

    LogView > .logview--level-warn {
        background: #3d2e0a;
    }

    LogView > .logview--level-debug {
        color: $text-disabled;
    }

    LogView > .logview--level-fatal {
        background: #5c1015;
        text-style: bold;
    }

    LogView > .logview--bookmark {
        color: #e5c07b;
        text-style: bold;
    }
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "logview--highlight",
        "logview--timestamp",
        "logview--json",
        "logview--text",
        "logview--line-number",
        "logview--level-error",
        "logview--level-warn",
        "logview--level-debug",
        "logview--level-fatal",
        "logview--bookmark",
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
        Binding("j", "toggle_json_global", "Expand"),
        Binding("enter", "toggle_json_line", "Expand", show=False),
        Binding("#", "toggle_line_numbers", "Lines#"),
        Binding("c", "cycle_component_display", "Component"),
        Binding("n", "next_match", "Next", show=False),
        Binding("N", "prev_match", "Prev", show=False),
    ]

    cursor_line: reactive[int] = reactive(0)

    def __init__(self, lines: list[LogLine] | None = None, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self._all_lines: list[LogLine] = lines or []
        self._g_pending: bool = False
        self._filtered_indices: list[int] = []
        self._filter_rules: list[FilterRule] = []
        self._max_width: int = 0
        self._show_line_numbers: bool = True
        # Expansion state
        self._global_expand: bool = False
        self._sticky_expand: bool = False
        # Height tracking for variable-height lines
        self._heights: list[int] = []
        self._offsets: list[int] = []
        # Level filter
        self._min_level: LogLevel | None = None
        # Component display: "tag" (color dot + number), "full" (full name), "off" (hidden)
        self._component_display: str = "tag"
        self._component_colors: dict[str, int] = {}
        self._component_index: dict[str, int] = {}
        # Anomaly detection
        self._anomaly_scores: dict[int, float] = {}
        self._anomaly_filter: bool = False
        # Search state (multi-pattern)
        self._search_patterns: SearchPatternSet = SearchPatternSet()
        self._search_matches: list[tuple[int, int, int, int]] = []  # (line_idx, start, end, pattern_index)
        self._nav_matches: list[tuple[int, int, int, int]] = []  # target-pattern subset for n/N navigation
        self._search_current: int = -1  # indexes into _nav_matches
        # Pre-computed: matches grouped by visible line index for fast render lookup (all nav_enabled patterns)
        self._search_matches_by_line: dict[int, list[tuple[int, int, int]]] = {}  # (start, end, pattern_index)
        # Bookmarks: original line index → annotation text (empty = no annotation)
        self._bookmarks: dict[int, str] = {}

    @property
    def lines(self) -> list[LogLine]:
        """Get the currently visible lines (filtered or all)."""
        if self.has_filters:
            return [self._all_lines[i] for i in self._filtered_indices]
        return self._all_lines

    @property
    def total_count(self) -> int:
        return len(self._all_lines)

    @property
    def filtered_count(self) -> int:
        return len(self.lines)

    @property
    def has_filters(self) -> bool:
        return bool(self._filter_rules) or self._min_level is not None or self._anomaly_filter

    @property
    def level_counts(self) -> dict[LogLevel, int]:
        """Count lines by log level across all (unfiltered) lines."""
        counts: dict[LogLevel, int] = {}
        for line in self._all_lines:
            if line.log_level is not None:
                counts[line.log_level] = counts.get(line.log_level, 0) + 1
        return counts

    def get_all_components(self) -> dict[str, int]:
        """Get all detected components with line counts from all (unfiltered) lines."""
        counts: dict[str, int] = {}
        for line in self._all_lines:
            if line.component is not None:
                counts[line.component] = counts.get(line.component, 0) + 1
        return counts

    @property
    def anomaly_filter(self) -> bool:
        """Whether the anomaly filter is active."""
        return self._anomaly_filter

    @anomaly_filter.setter
    def anomaly_filter(self, value: bool) -> None:
        self._anomaly_filter = value

    @property
    def min_level(self) -> LogLevel | None:
        """Current minimum log level filter."""
        return self._min_level

    @min_level.setter
    def min_level(self, value: LogLevel | None) -> None:
        self._min_level = value

    def set_anomaly_scores(self, scores: dict[int, float]) -> None:
        """Set anomaly scores from baseline comparison."""
        self._anomaly_scores = scores
        self.refresh()

    def toggle_anomaly_filter(self) -> None:
        """Toggle showing only anomalous lines."""
        orig_idx = self.cursor_orig_index()
        self._anomaly_filter = not self._anomaly_filter
        self._apply_filters()
        self.restore_cursor(orig_idx)
        self.refresh()

    @property
    def has_search(self) -> bool:
        """Whether any search patterns are active."""
        return not self._search_patterns.is_empty

    @property
    def search_patterns(self) -> SearchPatternSet:
        """The active search pattern set."""
        return self._search_patterns

    @property
    def search_pattern_match_counts(self) -> list[tuple[int, int]]:
        """Per-pattern match counts as (count, color_index) for each pattern."""
        counts: dict[int, int] = {}
        for _, _, _, pat_idx in self._search_matches:
            counts[pat_idx] = counts.get(pat_idx, 0) + 1
        return [(counts.get(i, 0), p.color_index) for i, p in enumerate(self._search_patterns.patterns)]

    @property
    def search_match_count(self) -> int:
        return len(self._search_matches)

    @property
    def nav_match_count(self) -> int:
        """Number of matches from nav-enabled patterns."""
        return len(self._nav_matches)

    @property
    def search_current_index(self) -> int:
        return self._search_current

    @property
    def nav_current_pattern_index(self) -> int:
        """Pattern index that n/N navigates, or -1 if no patterns."""
        if self._search_patterns.is_empty:
            return -1
        return self._search_patterns.nav_target_index

    def on_mount(self) -> None:
        self._apply_filters()

    def set_lines(self, lines: list[LogLine]) -> None:
        """Replace all log lines and refresh display."""
        self._all_lines = lines
        self._global_expand = False
        self._sticky_expand = False
        self._filter_rules.clear()
        self.cursor_line = 0
        self.clear_search()
        self._apply_filters()

    def cursor_orig_index(self) -> int | None:
        """Get the original line index (in _all_lines) of the current cursor."""
        if not self._filtered_indices:
            return None
        cursor = min(self.cursor_line, len(self._filtered_indices) - 1)
        if cursor < 0:
            return None
        return self._filtered_indices[cursor]

    def restore_cursor(self, orig_idx: int | None) -> None:
        """Restore cursor to the nearest visible line matching the original index and scroll to it."""
        if orig_idx is None or not self._filtered_indices:
            visible = self.lines
            self.cursor_line = max(0, len(visible) - 1) if visible else 0
        else:
            # Find the closest visible line >= orig_idx
            for new_idx, idx in enumerate(self._filtered_indices):
                if idx >= orig_idx:
                    self.cursor_line = new_idx
                    break
            else:
                self.cursor_line = len(self._filtered_indices) - 1
        # Defer centered scroll to after layout is updated
        self.call_after_refresh(self._scroll_cursor_center)

    def set_filters(self, rules: list[FilterRule]) -> None:
        """Apply filter rules and refresh display."""
        orig_idx = self.cursor_orig_index()
        self._filter_rules = list(rules)
        self._apply_filters()
        self.restore_cursor(orig_idx)
        # Re-run search on filtered lines
        if not self._search_patterns.is_empty:
            self._compute_search_matches()
        self.refresh()

    def append_line(self, line: LogLine) -> None:
        """Append a single line (for tailing). Auto-scrolls only if cursor was on last line."""
        visible_before = len(self.lines)
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
        visible_idx = len(self.lines) - 1
        expanded = self._is_expanded(visible_idx)
        h = get_line_height(line, expanded=expanded)
        self._heights.append(h)
        offset = self._offsets[-1] + self._heights[-2] if len(self._offsets) > 0 else 0
        self._offsets.append(offset)

        self._max_width = max(self._max_width, len(line.raw))
        total_height = self._offsets[-1] + self._heights[-1] if self._offsets else 0
        self.virtual_size = Size(self._max_width + 10, total_height)

        if cursor_was_on_last:
            self.cursor_line = len(self.lines) - 1
            self._scroll_cursor_into_view()

        self.refresh()

    def append_lines(self, lines: list[LogLine]) -> None:
        """Append a batch of lines (for chunked loading). More efficient than per-line append."""
        if not lines:
            return

        visible_before = len(self.lines)
        cursor_was_on_last = self.cursor_line >= visible_before - 1

        base_idx = len(self._all_lines)
        self._all_lines.extend(lines)

        # Incremental filter check for batch
        new_visible: list[LogLine] = []
        for i, line in enumerate(lines):
            idx = base_idx + i
            if self._filter_rules:
                if check_line(line, self._filter_rules):
                    self._filtered_indices.append(idx)
                    new_visible.append(line)
            else:
                self._filtered_indices.append(idx)
                new_visible.append(line)

        if not new_visible:
            return

        # Batch-compute heights and offsets
        max_width = self._max_width
        for line in new_visible:
            h = get_line_height(line, expanded=False)
            self._heights.append(h)
            offset = self._offsets[-1] + self._heights[-2] if len(self._offsets) > 0 else 0
            self._offsets.append(offset)
            max_width = max(max_width, len(line.raw))

        self._max_width = max_width
        total_height = self._offsets[-1] + self._heights[-1] if self._offsets else 0
        self.virtual_size = Size(self._max_width + 10, total_height)

        if cursor_was_on_last:
            self.cursor_line = len(self.lines) - 1
            self._scroll_cursor_into_view()

        self.refresh()

    def _is_at_bottom(self) -> bool:
        """Check if the view is scrolled to the bottom."""
        if not self._offsets:
            return True
        total_height = self._offsets[-1] + self._heights[-1]
        region_height = self.scrollable_content_region.height
        return self.scroll_offset.y + region_height >= total_height - 1

    def set_min_level(self, level: LogLevel | None) -> None:
        """Set minimum log level filter and refresh display."""
        orig_idx = self.cursor_orig_index()
        self._min_level = level
        self._apply_filters()
        self.restore_cursor(orig_idx)
        if not self._search_patterns.is_empty:
            self._compute_search_matches()
        self.refresh()

    def _apply_filters(self) -> None:
        """Recompute filtered indices and update display."""
        if self._filter_rules:
            self._filtered_indices = apply_filters(self._all_lines, self._filter_rules)
        else:
            self._filtered_indices = list(range(len(self._all_lines)))
        # Apply log level filter on top
        if self._min_level is not None:
            level_order = list(LogLevel)
            min_idx = level_order.index(self._min_level)
            self._filtered_indices = [
                i
                for i in self._filtered_indices
                if self._passes_level_filter(self._all_lines[i].log_level, level_order, min_idx)
            ]
        # Apply anomaly filter on top
        if self._anomaly_filter and self._anomaly_scores:
            self._filtered_indices = [i for i in self._filtered_indices if i in self._anomaly_scores]
        self._recompute_heights()

    def _is_expanded(self, line_index: int) -> bool:
        """Check if a visible line index should be rendered expanded."""
        if self._global_expand:
            return True
        return self._sticky_expand and line_index == self.cursor_line

    def _recompute_heights(self) -> None:
        """Recompute line heights and prefix-sum offsets."""
        visible = self.lines
        self._heights = []
        self._offsets = []
        offset = 0
        for i, line in enumerate(visible):
            expanded = self._is_expanded(i)
            h = get_line_height(line, expanded=expanded)
            # Add extra row for annotation text
            orig_idx = self._filtered_indices[i] if self._filtered_indices else i
            if self._bookmarks.get(orig_idx):
                h += 1
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
        idx = max(0, min(idx, len(self.lines) - 1))
        sub_row = display_row - self._offsets[idx]
        return idx, sub_row

    @property
    def line_count(self) -> int:
        return len(self.lines)

    # --- Search ---

    def set_search(self, query: SearchQuery) -> None:
        """Add a search pattern and find all matches."""
        result = self._search_patterns.add(query)
        if result is None:
            self.app.notify("Maximum 10 search patterns", severity="warning")
            return
        # New pattern becomes the n/N target
        self._search_patterns.nav_target_index = len(self._search_patterns.patterns) - 1
        self._compute_search_matches()
        # Jump to first match from current cursor position
        if self._search_matches:
            self._jump_to_nearest_match()
        self.refresh()

    def set_search_patterns(self, pattern_set: SearchPatternSet) -> None:
        """Replace the entire search pattern set and recompute matches."""
        self._search_patterns = pattern_set
        self._compute_search_matches()
        if self._nav_matches:
            self._jump_to_nearest_match()
        self.refresh()

    def clear_search(self) -> None:
        """Clear all search patterns."""
        self._search_patterns = SearchPatternSet()
        self._search_matches = []
        self._nav_matches = []
        self._search_current = -1
        self._search_matches_by_line = {}
        self.refresh()

    def _compute_search_matches(self) -> None:
        """Compute all search matches for visible lines across all patterns."""
        if self._search_patterns.is_empty:
            self._search_matches = []
            self._nav_matches = []
            self._search_current = -1
            self._search_matches_by_line = {}
            return
        visible = self.lines
        self._search_matches = find_all_pattern_matches(visible, self._search_patterns)
        self._search_current = -1
        # Highlight matches: all nav_enabled patterns
        nav_indices = {i for i, p in enumerate(self._search_patterns.patterns) if p.nav_enabled}
        highlight_matches = [m for m in self._search_matches if m[3] in nav_indices]
        self._search_matches_by_line = {}
        for line_idx, start, end, pat_idx in highlight_matches:
            self._search_matches_by_line.setdefault(line_idx, []).append((start, end, pat_idx))
        # Navigation matches: only the single target pattern (for n/N)
        target = self._search_patterns.nav_target_index
        self._nav_matches = [m for m in self._search_matches if m[3] == target]

    def _jump_to_nearest_match(self) -> None:
        """Jump to the nearest nav-enabled match from the current cursor position."""
        if not self._nav_matches:
            return
        direction = (
            self._search_patterns.patterns[-1].query.direction
            if self._search_patterns.patterns
            else SearchDirection.FORWARD
        )
        if direction == SearchDirection.FORWARD:
            # Find first nav match at or after cursor
            for i, (line_idx, _, _, _) in enumerate(self._nav_matches):
                if line_idx >= self.cursor_line:
                    self._search_current = i
                    self.cursor_line = line_idx
                    return
            # Wrap around
            self._search_current = 0
            self.cursor_line = self._nav_matches[0][0]
        else:
            # Find first nav match at or before cursor
            for i in range(len(self._nav_matches) - 1, -1, -1):
                line_idx = self._nav_matches[i][0]
                if line_idx <= self.cursor_line:
                    self._search_current = i
                    self.cursor_line = line_idx
                    return
            # Wrap around
            self._search_current = len(self._nav_matches) - 1
            self.cursor_line = self._nav_matches[-1][0]

    def action_next_match(self) -> None:
        """Go to the next match of the target pattern."""
        if not self._nav_matches:
            if self._search_matches:
                self.app.notify("No matches for target pattern", severity="warning")
            return
        direction = (
            self._search_patterns.patterns[-1].query.direction
            if self._search_patterns.patterns
            else SearchDirection.FORWARD
        )
        if direction == SearchDirection.FORWARD:
            self._search_current = (self._search_current + 1) % len(self._nav_matches)
        else:
            self._search_current = (self._search_current - 1) % len(self._nav_matches)
        self.cursor_line = self._nav_matches[self._search_current][0]
        # Always refresh to update current-match underline (even on same line)
        self.refresh()
        self._notify_search_status()

    def action_prev_match(self) -> None:
        """Go to the previous match of the target pattern."""
        if not self._nav_matches:
            if self._search_matches:
                self.app.notify("No matches for target pattern", severity="warning")
            return
        direction = (
            self._search_patterns.patterns[-1].query.direction
            if self._search_patterns.patterns
            else SearchDirection.FORWARD
        )
        if direction == SearchDirection.FORWARD:
            self._search_current = (self._search_current - 1) % len(self._nav_matches)
        else:
            self._search_current = (self._search_current + 1) % len(self._nav_matches)
        self.cursor_line = self._nav_matches[self._search_current][0]
        # Always refresh to update current-match underline (even on same line)
        self.refresh()
        self._notify_search_status()

    def _notify_search_status(self) -> None:
        """Notify the app to update search status display."""
        try:
            from logdelve.app import LogDelveApp  # noqa: PLC0415

            app = self.app
            if isinstance(app, LogDelveApp):
                app.update_search_status()
        except ImportError:
            pass

    # --- Rendering ---

    def render_line(self, y: int) -> Strip:  # noqa: PLR0914, C901, PLR0912, PLR0915
        scroll_x, scroll_y = self.scroll_offset
        display_row = scroll_y + y
        content_width = self.scrollable_content_region.width

        if content_width <= 0:
            return Strip.blank(self.size.width, self.rich_style)

        total_height = self._offsets[-1] + self._heights[-1] if self._offsets else 0
        if display_row >= total_height or display_row < 0:
            return Strip.blank(content_width, self.rich_style)

        line_index, sub_row = self._display_row_to_line(display_row)
        visible = self.lines
        line = visible[line_index]
        is_highlighted = line_index == self.cursor_line
        expanded = self._is_expanded(line_index)

        highlight_style = self.get_component_rich_style("logview--highlight")
        timestamp_style = self.get_component_rich_style("logview--timestamp")
        json_style = self.get_component_rich_style("logview--json")
        text_style = self.get_component_rich_style("logview--text")
        lineno_style = self.get_component_rich_style("logview--line-number")
        # Build background: cursor highlight takes priority, then level color
        if is_highlighted:
            bg_style = highlight_style
        elif line.log_level is not None:
            level_bg_map: dict[LogLevel, str | None] = {
                LogLevel.FATAL: "logview--level-fatal",
                LogLevel.ERROR: "logview--level-error",
                LogLevel.WARN: "logview--level-warn",
                LogLevel.DEBUG: "logview--level-debug",
            }
            level_class = level_bg_map.get(line.log_level)
            bg_style = self.get_component_rich_style(level_class) if level_class else Style()
        else:
            bg_style = Style()

        # Get search matches for this line (now with pattern_index)
        line_matches = self._search_matches_by_line.get(line_index)
        current_match_offsets: tuple[int, int] | None = None
        current_pattern_index: int = -1
        if self._search_current >= 0 and self._search_current < len(self._nav_matches):
            cm = self._nav_matches[self._search_current]
            if cm[0] == line_index:
                current_match_offsets = (cm[1], cm[2])
                current_pattern_index = cm[3]

        if expanded and line.content_type == ContentType.JSON and line.parsed_json is not None:
            strips = render_json_expanded(
                line, content_width, lineno_style, timestamp_style, bg_style, show_line_numbers=self._show_line_numbers
            )
            strip = strips[sub_row] if sub_row < len(strips) else Strip.blank(content_width, self.rich_style)
        elif expanded and line.content_type == ContentType.TEXT and sub_row == 1:
            # Expanded text row 1: show the full raw line (with original timestamp/date)
            segments = [Segment(f"  {line.raw}", timestamp_style + bg_style)]
            strip = Strip(segments)
        else:
            # Check anomaly status using original line index
            orig_idx = self._filtered_indices[line_index] if self._filtered_indices else line_index
            is_anomaly = orig_idx in self._anomaly_scores
            segments = self._render_compact_line(
                line,
                lineno_style,
                timestamp_style,
                json_style,
                text_style,
                bg_style,
                line_matches,
                current_match_offsets,
                current_pattern_index=current_pattern_index,
                is_anomaly=is_anomaly,
                orig_idx=orig_idx,
            )
            strip = Strip(segments)

        # Check if this sub_row is the annotation row (last row of an annotated bookmark)
        orig_idx = self._filtered_indices[line_index] if self._filtered_indices else line_index
        if self._bookmarks.get(orig_idx):
            line_height = self._heights[line_index] if line_index < len(self._heights) else 1
            if sub_row == line_height - 1:
                annotation_text = f"    >> {self._bookmarks[orig_idx]}"
                annotation_style = Style(color="#56b6c2", italic=True)
                strip = Strip([Segment(annotation_text, annotation_style + bg_style)])

        strip = strip.crop(scroll_x, scroll_x + content_width)
        if bg_style != Style():
            fill_style = Style(bgcolor=bg_style.bgcolor)
            strip = strip.extend_cell_length(content_width, fill_style)
        else:
            strip = strip.extend_cell_length(content_width)
            strip = strip.apply_style(self.rich_style)

        return strip

    def _render_compact_line(  # noqa: C901, PLR0912, PLR0915, PLR0914
        self,
        line: LogLine,
        lineno_style: Style,
        timestamp_style: Style,
        json_style: Style,
        text_style: Style,
        bg_style: Style,
        search_matches: list[tuple[int, int, int]] | None = None,
        current_match: tuple[int, int] | None = None,
        *,
        current_pattern_index: int = -1,
        is_anomaly: bool = False,
        orig_idx: int = 0,
    ) -> list[Segment]:
        """Render a single compact log line with optional multi-pattern search highlighting."""
        segments: list[Segment] = []

        # Anomaly marker
        if is_anomaly:
            segments.append(Segment("▌", Style(color="red", bold=True)))
        elif self._anomaly_scores:
            segments.append(Segment(" ", bg_style))

        # Bookmark marker
        if self._bookmarks:
            if orig_idx in self._bookmarks:
                annotation = self._bookmarks[orig_idx]
                marker = "# " if annotation else "* "
                segments.append(Segment(marker, self.get_component_rich_style("logview--bookmark") + bg_style))
            else:
                segments.append(Segment("  ", bg_style))

        if self._show_line_numbers:
            if line.source_line_number is not None:
                lineno_text = f"{line.line_number}:{line.source_line_number} "
                lineno_text = f"{lineno_text:>12}"
            else:
                lineno_text = f"{line.line_number:>6} "
            segments.append(Segment(lineno_text, lineno_style + bg_style))

        # Level badge (single char, row is already colored by level bg)
        if line.log_level is not None:
            badge_chars: dict[LogLevel, str] = {
                LogLevel.FATAL: "F",
                LogLevel.ERROR: "E",
                LogLevel.WARN: "W",
                LogLevel.INFO: "I",
                LogLevel.DEBUG: "D",
                LogLevel.TRACE: "T",
            }
            badge_char = badge_chars.get(line.log_level, "?")
            segments.append(Segment(f"{badge_char} ", Style(bold=True) + bg_style))

        # Component tag
        if line.component and self._component_display != "off":
            if self._component_display == "tag":
                tag_num, tag_style = self._get_component_tag(line.component)
                segments.append(Segment(f"·{tag_num} ", tag_style + bg_style))
            else:  # full
                _, tag_style = self._get_component_tag(line.component)
                segments.append(Segment(f"[{line.component}] ", tag_style + bg_style))

        # Compact timestamp (HH:MM:SS)
        if line.timestamp is not None:
            ts_text = self._compact_timestamp(line)
            segments.append(Segment(ts_text, timestamp_style + bg_style))

        content_style = json_style if line.content_type == ContentType.JSON else text_style

        if search_matches:
            # Render content with multi-pattern search match highlighting
            # Matches are in raw offsets; compute content offset
            content_start = line.content_offset
            content_text = line.content

            # Collect match ranges that overlap with content portion
            # (start, end, is_current, pattern_index) relative to content
            highlights: list[tuple[int, int, bool, int]] = []
            for m_start, m_end, pat_idx in search_matches:
                # Convert from raw offset to content offset
                cs = max(0, m_start - content_start)
                ce = min(len(content_text), m_end - content_start)
                if cs < ce:
                    is_current = (
                        current_match is not None
                        and m_start == current_match[0]
                        and m_end == current_match[1]
                        and pat_idx == current_pattern_index
                    )
                    highlights.append((cs, ce, is_current, pat_idx))

            if highlights:
                segments.extend(
                    self._split_with_highlights(
                        content_text,
                        highlights,
                        content_style + bg_style,
                    )
                )
            else:
                segments.append(Segment(content_text, content_style + bg_style))
        else:
            segments.append(Segment(line.content, content_style + bg_style))

        if bg_style != Style():
            segments.append(Segment(" " * 10, bg_style))

        return segments

    def _split_with_highlights(
        self,
        text: str,
        highlights: list[tuple[int, int, bool, int]],
        normal_style: Style,
    ) -> list[Segment]:
        """Split text into segments with multi-pattern highlighted search matches.

        Uses "shortest match wins" overlap resolution: when multiple patterns
        overlap, the pattern with the shorter match span gets its color displayed.
        Longer matches are painted first, then shorter ones overwrite, so the
        shortest match always wins.
        """
        if not highlights:
            return [Segment(text, normal_style)]

        # Determine the minimum highlight start for optimization
        min_pos = min(h[0] for h in highlights)

        # Paint character-level assignments: longest first, shortest overwrites
        # Each entry: (pattern_index, is_current)
        assignments: dict[int, tuple[int, bool]] = {}
        sorted_by_len = sorted(highlights, key=lambda h: h[1] - h[0], reverse=True)
        for start, end, is_current, pat_idx in sorted_by_len:
            for pos in range(start, end):
                assignments[pos] = (pat_idx, is_current)

        # Walk through text building segments, merging consecutive identical styles
        segments: list[Segment] = []
        pos = 0
        while pos < len(text):
            if pos not in assignments:
                # Find the end of this normal (non-highlighted) run
                run_end = pos + 1
                while run_end < len(text) and run_end not in assignments:
                    run_end += 1
                # Optimization: skip scanning beyond max_pos for normal text between highlights
                if pos < min_pos:
                    run_end = min(run_end, min_pos)
                segments.append(Segment(text[pos:run_end], normal_style))
                pos = run_end
            else:
                pat_idx, is_current = assignments[pos]
                color_index = self._search_patterns.patterns[pat_idx].color_index
                style = search_current_style(color_index) if is_current else search_match_style(color_index)
                # Find the end of this highlighted run with the same style
                run_end = pos + 1
                while run_end < len(text) and run_end in assignments:
                    next_pat, next_cur = assignments[run_end]
                    if next_pat != pat_idx or next_cur != is_current:
                        break
                    run_end += 1
                segments.append(Segment(text[pos:run_end], style))
                pos = run_end

        return segments

    @staticmethod
    def _passes_level_filter(level: LogLevel | None, level_order: list[LogLevel], min_idx: int) -> bool:
        """Check if a log level passes the minimum level filter."""
        if level is None:
            return False
        return level_order.index(level) >= min_idx

    def watch_cursor_line(self, _old_value: int, _new_value: int) -> None:
        self._recompute_heights()
        self._scroll_cursor_into_view()
        self.refresh()

    def _scroll_cursor_into_view(self, *, center: bool = False) -> None:
        """Ensure the cursor line is visible, optionally centering it."""
        visible = self.lines
        if not visible or not self._offsets:
            return
        region_height = self.scrollable_content_region.height
        if region_height <= 0:
            return

        cursor = min(self.cursor_line, len(visible) - 1)
        cursor_start = self._offsets[cursor]
        cursor_height = self._heights[cursor]
        scroll_y = self.scroll_offset.y

        if center:
            # Center the cursor line on screen
            target_y = max(0, cursor_start - (region_height - cursor_height) // 2)
            self.scroll_to(y=target_y, animate=False)
        elif cursor_start < scroll_y:
            self.scroll_to(y=cursor_start, animate=False)
        elif cursor_start + cursor_height > scroll_y + region_height:
            self.scroll_to(y=cursor_start + cursor_height - region_height, animate=False)

    def _scroll_cursor_center(self) -> None:
        """Center the cursor line on screen (used after filter changes)."""
        self._scroll_cursor_into_view(center=True)

    # --- Actions ---

    def action_cursor_up(self) -> None:
        if self.cursor_line > 0:
            self.cursor_line -= 1

    def action_cursor_down(self) -> None:
        if self.cursor_line < len(self.lines) - 1:
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
        self.cursor_line = min(target_line, len(self.lines) - 1)

    def action_scroll_home(self) -> None:
        self.cursor_line = 0

    def action_scroll_end(self) -> None:
        if self.lines:
            self.cursor_line = len(self.lines) - 1

    def action_toggle_json_global(self) -> None:
        """Toggle expand for all lines (JSON pretty-print / full raw text)."""
        self._global_expand = not self._global_expand
        self._sticky_expand = False
        self._recompute_heights()
        self._scroll_cursor_into_view()
        self.refresh()

    def action_toggle_json_line(self) -> None:
        """Toggle sticky expand for the current line (follows cursor on move)."""
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

    def action_cycle_component_display(self) -> None:
        """Cycle component display: tag → full → off → tag."""
        cycle = ["tag", "full", "off"]
        idx = cycle.index(self._component_display)
        self._component_display = cycle[(idx + 1) % len(cycle)]
        self.refresh()

    def _get_component_tag(self, component: str) -> tuple[int, Style]:
        """Get the numeric tag and color style for a component."""
        if component not in self._component_index:
            idx = len(self._component_index)
            self._component_index[component] = idx
            self._component_colors[component] = idx % len(_COMPONENT_COLORS)
        color_idx = self._component_colors[component]
        tag_num = self._component_index[component] + 1
        color = _COMPONENT_COLORS[color_idx]
        return tag_num, Style(color=color, bold=True)

    @staticmethod
    def _compact_timestamp(line: LogLine) -> str:
        """Format timestamp compactly: HH:MM:SS if same day, else full date."""
        if line.timestamp is None:
            return ""
        return line.timestamp.strftime("%H:%M:%S ")

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

    def jump_to_line(self, line_number: int) -> None:
        """Jump to a specific line number within visible lines."""
        visible = self.lines
        for i, line in enumerate(visible):
            if line.line_number >= line_number:
                self.cursor_line = i
                self._scroll_cursor_center()
                return
        # Line number beyond last visible line → go to last
        if visible:
            self.cursor_line = len(visible) - 1
            self._scroll_cursor_center()

    def jump_to_timestamp(self, target: datetime) -> None:
        """Jump to the first visible line with timestamp >= target."""
        visible = self.lines
        for i, line in enumerate(visible):
            if line.timestamp is not None and line.timestamp >= target:
                self.cursor_line = i
                self._scroll_cursor_center()
                return
        # No matching line found → go to last
        if visible:
            self.cursor_line = len(visible) - 1
            self._scroll_cursor_center()

    # --- Bookmarks ---

    def toggle_bookmark(self) -> bool | None:
        """Toggle bookmark on the current cursor line. Returns True if bookmarked, False if removed, None if no line."""
        orig_idx = self.cursor_orig_index()
        if orig_idx is None:
            return None
        if orig_idx in self._bookmarks:
            had_annotation = bool(self._bookmarks[orig_idx])
            del self._bookmarks[orig_idx]
            if had_annotation:
                self._recompute_heights()
            self.refresh()
            return False
        self._bookmarks[orig_idx] = ""
        self.refresh()
        return True

    def set_annotation(self, orig_idx: int, text: str) -> None:
        """Set or update annotation on a bookmarked line."""
        self._bookmarks[orig_idx] = text
        self._recompute_heights()
        self.refresh()

    def get_annotation(self, orig_idx: int) -> str | None:
        """Get annotation text for a bookmarked line, or None if not bookmarked."""
        return self._bookmarks.get(orig_idx)

    def get_bookmarks(self) -> dict[int, str]:
        """Get all bookmarks (original line index → annotation)."""
        return self._bookmarks

    def set_bookmarks(self, bookmarks: dict[int, str]) -> None:
        """Set bookmarks (for session restore)."""
        self._bookmarks = bookmarks
        self._recompute_heights()
        self.refresh()

    @property
    def bookmark_count(self) -> int:
        """Number of bookmarked lines."""
        return len(self._bookmarks)

    def next_bookmark(self) -> None:
        """Jump to the next bookmarked line from cursor position."""
        if not self._bookmarks:
            return
        visible = self.lines
        for i in range(self.cursor_line + 1, len(visible)):
            orig_idx = self._filtered_indices[i] if self._filtered_indices else i
            if orig_idx in self._bookmarks:
                self.cursor_line = i
                self._scroll_cursor_center()
                return
        # Wrap around
        for i in range(self.cursor_line + 1):
            orig_idx = self._filtered_indices[i] if self._filtered_indices else i
            if orig_idx in self._bookmarks:
                self.cursor_line = i
                self._scroll_cursor_center()
                return

    def prev_bookmark(self) -> None:
        """Jump to the previous bookmarked line from cursor position."""
        if not self._bookmarks:
            return
        visible = self.lines
        for i in range(self.cursor_line - 1, -1, -1):
            orig_idx = self._filtered_indices[i] if self._filtered_indices else i
            if orig_idx in self._bookmarks:
                self.cursor_line = i
                self._scroll_cursor_center()
                return
        # Wrap around
        for i in range(len(visible) - 1, self.cursor_line - 1, -1):
            orig_idx = self._filtered_indices[i] if self._filtered_indices else i
            if orig_idx in self._bookmarks:
                self.cursor_line = i
                self._scroll_cursor_center()
                return
