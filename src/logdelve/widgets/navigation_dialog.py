"""Modal dialog for search, go-to-line, and jump-to-timestamp."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label, OptionList, TabbedContent, TabPane
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType
    from textual.events import Key

from logdelve.colors import _SEARCH_COLORS
from logdelve.models import (
    _MAX_SEARCH_PATTERNS,
    SearchDirection,
    SearchPattern,
    SearchPatternSet,
    SearchQuery,
)
from logdelve.widgets.timestamp_input import TimestampInput


class NavigationDialog(ModalScreen[SearchPatternSet | int | datetime | None]):
    """Modal dialog with tabs for Search, Go to Line, and Jump to Timestamp."""

    DEFAULT_CSS = """
    NavigationDialog {
        align: center middle;
    }

    NavigationDialog > Vertical {
        width: 90%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    NavigationDialog > Vertical > .title {
        text-style: bold;
    }

    NavigationDialog > Vertical > TabbedContent {
        height: 1fr;
    }

    NavigationDialog Tabs {
        height: 4;
    }

    NavigationDialog .underline--bar {
        height: 0;
    }

    NavigationDialog Tab {
        height: 3;
        padding: 1 2 0 2;
    }

    NavigationDialog Tab.-active {
        text-style: bold;
        color: $text;
        border-top: round $primary;
        border-left: round $primary;
        border-right: round $primary;
        padding: 0 2;
    }

    NavigationDialog ContentSwitcher {
        height: 1fr;
        border: round $primary;
    }

    NavigationDialog TabPane {
        padding: 1 1 0 1;
    }

    NavigationDialog Input {
        width: 100%;
    }

    NavigationDialog Horizontal {
        height: auto;
        margin-top: 1;
    }

    NavigationDialog Horizontal > Checkbox {
        margin-right: 3;
    }

    NavigationDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }

    NavigationDialog #pattern-list {
        height: auto;
        max-height: 12;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        direction: SearchDirection,
        search_patterns: SearchPatternSet | None = None,
        initial_tab: str = "tab-search",
        reference_date: datetime | None = None,
        bookmarks: dict[int, str] | None = None,
        all_lines: list[Any] | None = None,
    ) -> None:
        super().__init__()
        self._direction = direction
        self._initial_tab = initial_tab
        self._reference_date = reference_date
        self._bookmarks = bookmarks or {}
        self._all_lines = all_lines or []
        self._bookmark_indices: list[int] = sorted(self._bookmarks.keys())

        # Working copy of patterns for dialog manipulation
        self._working_patterns: list[SearchPattern] = list(search_patterns.patterns) if search_patterns else []
        self._next_color: int = (
            search_patterns._next_color if search_patterns else 0  # noqa: SLF001
        )
        self._editing_index: int | None = None

    def compose(self) -> ComposeResult:
        self._titles = {
            "tab-search": "Search forward (/)" if self._direction == SearchDirection.FORWARD else "Search backward (?)",
            "tab-line": "Go to line (:)",
            "tab-time": "Jump to timestamp (@)",
            "tab-bookmarks": f"Bookmarks ({len(self._bookmarks)})",
        }
        label = self._titles.get(self._initial_tab, self._titles["tab-search"])
        with Vertical():
            yield Label(label, classes="title", id="dialog-title")

            with TabbedContent(id="nav-tabs", initial=self._initial_tab):
                with TabPane("Search", id="tab-search"):
                    yield from self._compose_search_tab()
                with TabPane("Line", id="tab-line"):
                    yield from self._compose_line_tab()
                with TabPane("Time", id="tab-time"):
                    yield from self._compose_time_tab()
                with TabPane("Bookmarks", id="tab-bookmarks"):
                    yield from self._compose_bookmarks_tab()

            yield Label(
                "Enter: add/update  Enter(empty): apply  Tab/S-Tab: navigate  Del: remove  Space: toggle nav",
                classes="hint",
            )

    def _compose_search_tab(self) -> ComposeResult:
        # Pre-fill with last pattern's text if patterns exist
        initial_value = ""
        initial_case = False
        initial_regex = False
        if self._working_patterns:
            last = self._working_patterns[-1]
            initial_value = last.query.pattern
            initial_case = last.query.case_sensitive
            initial_regex = last.query.is_regex

        yield Input(value=initial_value, placeholder="search pattern...", id="search-input")
        with Horizontal():
            yield Checkbox("Case sensitive", initial_case, id="case-sensitive")
            yield Checkbox("Regex", initial_regex, id="regex")
        yield OptionList(id="pattern-list")

    @staticmethod
    def _compose_line_tab() -> ComposeResult:
        yield Input(placeholder="line number...", id="line-input")

    def _compose_time_tab(self) -> ComposeResult:
        yield TimestampInput(id="ts-widget", reference_date=self._reference_date)

    def _compose_bookmarks_tab(self) -> ComposeResult:
        ol = OptionList(id="bookmark-list")
        for orig_idx in self._bookmark_indices:
            if orig_idx < len(self._all_lines):
                line = self._all_lines[orig_idx]
                ts = line.timestamp.strftime("%H:%M:%S") if line.timestamp else "        "
                preview = line.content[:120]
                annotation = self._bookmarks.get(orig_idx, "")
                label = f"{line.line_number:>6} {ts} {preview}"
                if annotation:
                    label += f"\n       >> {annotation}"
                ol.add_option(Option(label))
        yield ol

    def on_mount(self) -> None:
        self._rebuild_pattern_list()
        self._focus_active_tab_content()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Update the dialog title when switching tabs."""
        import contextlib  # noqa: PLC0415

        tab_id = event.pane.id or ""
        title = self._titles.get(tab_id, "")
        with contextlib.suppress(NoMatches):
            self.query_one("#dialog-title", Label).update(title)

    def _focus_active_tab_content(self) -> None:
        try:
            tabs = self.query_one("#nav-tabs", TabbedContent)
            active_pane = tabs.active_pane
            if active_pane is None:
                return
            if active_pane.id == "tab-time":
                import contextlib  # noqa: PLC0415

                with contextlib.suppress(NoMatches):
                    self.query_one("#ts-widget", TimestampInput).focus_input()
                return
            for child in active_pane.query("Input"):
                child.focus()
                return
        except NoMatches:
            pass

    # --- Pattern list rendering ---

    @staticmethod
    def _format_pattern(pattern: SearchPattern) -> Text:
        """Format a search pattern as a Rich Text object for the OptionList."""
        text = Text()

        # Nav toggle icon
        nav_icon = "\u25cf" if pattern.nav_enabled else "\u25cb"
        nav_style = "green" if pattern.nav_enabled else "dim"
        text.append(f"{nav_icon} ", style=nav_style)

        # Color swatch with pattern text
        color_idx = pattern.color_index % len(_SEARCH_COLORS)
        bgcolor = _SEARCH_COLORS[color_idx][0]
        text.append(f" {pattern.query.pattern} ", style=f"#ffffff on {bgcolor}")

        # Flags
        if pattern.query.case_sensitive:
            text.append(" Aa", style="dim")
        if pattern.query.is_regex:
            text.append(" .*", style="dim")

        return text

    def _rebuild_pattern_list(self) -> None:
        """Rebuild the OptionList with current working patterns."""
        try:
            ol = self.query_one("#pattern-list", OptionList)
        except NoMatches:
            return

        highlighted = ol.highlighted
        ol.clear_options()
        for pattern in self._working_patterns:
            ol.add_option(Option(self._format_pattern(pattern)))
        if highlighted is not None and self._working_patterns:
            ol.highlighted = min(highlighted, len(self._working_patterns) - 1)

    # --- Key handling ---

    def _is_search_tab_active(self) -> bool:
        """Check if the Search tab is the active tab."""
        try:
            return self.query_one("#nav-tabs", TabbedContent).active == "tab-search"
        except NoMatches:
            return False

    def on_key(self, event: Key) -> None:
        """Handle special keys for Search tab interactions."""
        if not self._is_search_tab_active():
            return

        self._handle_search_tab_key(event, self.focused)

    # Tab cycle order: search-input → case-sensitive → regex → pattern-list
    _TAB_ORDER: ClassVar[list[str]] = ["search-input", "case-sensitive", "regex", "pattern-list"]

    def _cycle_focus(self, *, forward: bool) -> None:
        """Cycle focus through Search tab widgets."""
        import contextlib  # noqa: PLC0415

        focused = self.focused
        current_id = getattr(focused, "id", None)
        if current_id not in self._TAB_ORDER:
            return
        idx = self._TAB_ORDER.index(current_id)
        step = 1 if forward else -1
        next_id = self._TAB_ORDER[(idx + step) % len(self._TAB_ORDER)]
        with contextlib.suppress(NoMatches):
            self.query_one(f"#{next_id}").focus()

    def _handle_search_tab_key(self, event: Key, focused: object) -> None:
        """Handle key events specific to the Search tab."""
        is_pattern_list = isinstance(focused, OptionList) and focused.id == "pattern-list"
        is_checkbox = isinstance(focused, Checkbox) and focused.id in {"case-sensitive", "regex"}

        if event.key in {"tab", "shift+tab"}:
            event.prevent_default()
            event.stop()
            self._cycle_focus(forward=event.key == "tab")
            return

        # Delete/Backspace on OptionList: remove highlighted pattern
        if event.key in {"delete", "backspace"} and is_pattern_list:
            event.prevent_default()
            event.stop()
            self._remove_highlighted_pattern()
            return

        # Enter on checkbox: submit search
        if event.key == "enter" and is_checkbox:
            event.prevent_default()
            event.stop()
            self._submit_search()
            return

        # Space on pattern-list: toggle nav (highlight visibility)
        if event.key == "space" and is_pattern_list:
            event.prevent_default()
            event.stop()
            self._toggle_nav_highlighted()

    # --- Pattern management ---

    def _add_current_input_as_pattern(self) -> None:
        """Add the current input value as a new pattern or update the edited one."""
        try:
            inp = self.query_one("#search-input", Input)
        except NoMatches:
            return

        pattern_text = inp.value.strip()
        if not pattern_text:
            return

        case_sensitive = self.query_one("#case-sensitive", Checkbox).value
        is_regex = self.query_one("#regex", Checkbox).value

        query = SearchQuery(
            pattern=pattern_text,
            case_sensitive=case_sensitive,
            is_regex=is_regex,
            direction=self._direction,
        )

        if self._editing_index is not None:
            # Update existing pattern at editing index
            idx = self._editing_index
            if 0 <= idx < len(self._working_patterns):
                existing = self._working_patterns[idx]
                self._working_patterns[idx] = SearchPattern(
                    query=query,
                    color_index=existing.color_index,
                    nav_enabled=existing.nav_enabled,
                )
            self._editing_index = None
        else:
            # Add new pattern
            if len(self._working_patterns) >= _MAX_SEARCH_PATTERNS:
                self.notify("Maximum 10 patterns reached", severity="warning")
                return

            # Find next unused color
            used_indices = {p.color_index for p in self._working_patterns}
            color_index = self._next_color
            for _ in range(_MAX_SEARCH_PATTERNS):
                if color_index not in used_indices:
                    break
                color_index = (color_index + 1) % _MAX_SEARCH_PATTERNS
            else:
                return  # All colors taken

            self._working_patterns.append(SearchPattern(query=query, color_index=color_index))
            self._next_color = (color_index + 1) % _MAX_SEARCH_PATTERNS

        # Clear input and reset checkboxes
        inp.value = ""
        self.query_one("#case-sensitive", Checkbox).value = False
        self.query_one("#regex", Checkbox).value = False
        self._rebuild_pattern_list()

    def _remove_highlighted_pattern(self) -> None:
        """Remove the highlighted pattern from the working list."""
        try:
            ol = self.query_one("#pattern-list", OptionList)
        except NoMatches:
            return

        index = ol.highlighted
        if index is None or not (0 <= index < len(self._working_patterns)):
            return

        self._working_patterns.pop(index)

        # Adjust editing index
        if self._editing_index == index:
            self._editing_index = None
        elif self._editing_index is not None and self._editing_index > index:
            self._editing_index -= 1

        # Clear input
        try:
            inp = self.query_one("#search-input", Input)
            inp.value = ""
            self.query_one("#case-sensitive", Checkbox).value = False
            self.query_one("#regex", Checkbox).value = False
        except NoMatches:
            pass

        self._editing_index = None
        self._rebuild_pattern_list()

    def _toggle_nav_highlighted(self) -> None:
        """Toggle nav_enabled on the highlighted pattern."""
        try:
            ol = self.query_one("#pattern-list", OptionList)
        except NoMatches:
            return

        index = ol.highlighted
        if index is None or not (0 <= index < len(self._working_patterns)):
            return

        existing = self._working_patterns[index]
        self._working_patterns[index] = SearchPattern(
            query=existing.query,
            color_index=existing.color_index,
            nav_enabled=not existing.nav_enabled,
        )

        # In-place update to preserve scroll position
        ol.replace_option_prompt_at_index(
            index,
            self._format_pattern(self._working_patterns[index]),
        )

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Pre-fill input when highlighting a pattern in the list."""
        if event.option_list.id != "pattern-list":
            return

        index = event.option_index
        if not (0 <= index < len(self._working_patterns)):
            return

        pattern = self._working_patterns[index]

        # Pre-fill input and checkboxes for editing
        try:
            inp = self.query_one("#search-input", Input)
            inp.value = pattern.query.pattern
            self.query_one("#case-sensitive", Checkbox).value = pattern.query.case_sensitive
            self.query_one("#regex", Checkbox).value = pattern.query.is_regex
            self._editing_index = index
        except NoMatches:
            pass

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection: bookmark jumps, pattern-list focuses Input for editing."""
        if event.option_list.id == "bookmark-list" and event.option_index < len(self._bookmark_indices):
            orig_idx = self._bookmark_indices[event.option_index]
            if orig_idx < len(self._all_lines):
                self.dismiss(self._all_lines[orig_idx].line_number)
        elif event.option_list.id == "pattern-list":
            # Enter on pattern-list: focus Input to edit the highlighted pattern
            import contextlib  # noqa: PLC0415

            with contextlib.suppress(NoMatches):
                self.query_one("#search-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        if input_id == "search-input":
            self._submit_search()
        elif input_id == "line-input":
            self._submit_line()
        elif input_id == "ts-input":
            self._submit_timestamp()

    # --- Submission methods ---

    def _build_pattern_set(self) -> SearchPatternSet | None:
        """Build a SearchPatternSet from the working patterns."""
        if not self._working_patterns:
            return None
        pattern_set = SearchPatternSet()
        pattern_set.patterns = list(self._working_patterns)
        pattern_set._next_color = self._next_color  # noqa: SLF001
        return pattern_set

    def _add_input_if_present(self) -> None:
        """If the input has text, add it as a pattern first."""
        try:
            inp = self.query_one("#search-input", Input)
            if inp.value.strip():
                self._add_current_input_as_pattern()
        except NoMatches:
            pass

    def _submit_search(self) -> None:
        """Handle Enter on search input: add/update pattern, or apply+close if empty."""
        try:
            inp = self.query_one("#search-input", Input)
        except NoMatches:
            self.dismiss(self._build_pattern_set())
            return

        if inp.value.strip():
            # Non-empty input: add as new pattern or update edited one
            self._add_current_input_as_pattern()
        else:
            # Empty input: apply current patterns and close dialog
            self.dismiss(self._build_pattern_set())

    def _submit_line(self) -> None:
        """Submit go-to-line."""
        try:
            inp = self.query_one("#line-input", Input)
        except NoMatches:
            self.dismiss(None)
            return

        raw = inp.value.strip()
        if not raw:
            self.dismiss(None)
            return

        try:
            line_number = int(raw)
        except ValueError:
            self.notify("Invalid line number", severity="error")
            return

        if line_number < 1:
            self.notify("Line number must be positive", severity="error")
            return

        self.dismiss(line_number)

    def _submit_timestamp(self) -> None:
        """Submit jump-to-timestamp."""
        try:
            ts_widget = self.query_one("#ts-widget", TimestampInput)
        except NoMatches:
            self.dismiss(None)
            return

        result = ts_widget.parse()
        if result is not None:
            self.dismiss(result)

    def action_cancel(self) -> None:
        """Escape keeps changes - build pattern set from working patterns."""
        # Check if on search tab - if so, add input text
        try:
            tabs = self.query_one("#nav-tabs", TabbedContent)
            if tabs.active == "tab-search":
                self._add_input_if_present()
                self.dismiss(self._build_pattern_set())
                return
        except NoMatches:
            pass
        self.dismiss(None)
