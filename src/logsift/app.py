"""Textual application for logsift."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer
from textual.worker import get_current_worker

from logsift.models import ContentType, FilterRule, FilterType, LogLine
from logsift.reader import read_file_async, read_stdin_async
from logsift.session import create_session, load_session, save_session
from logsift.widgets.filter_bar import FilterBar
from logsift.widgets.filter_dialog import FilterDialog
from logsift.widgets.filter_manage_dialog import FilterManageDialog
from logsift.widgets.help_screen import HelpScreen
from logsift.widgets.log_view import LogView
from logsift.widgets.session_dialog import SessionLoadDialog, SessionSaveDialog
from logsift.widgets.status_bar import StatusBar


class LogSiftApp(App[None]):
    """Log viewer TUI application."""

    CSS_PATH = "styles/app.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help"),
        Binding("h", "show_help", "Help", show=False),
        Binding("slash", "filter_in", "Filter in"),
        Binding("backslash", "filter_out", "Filter out"),
        Binding("m", "manage_filters", "Manage filters"),
        Binding("c", "clear_filters", "Clear"),
        Binding("p", "toggle_tail_pause", "Pause"),
        Binding("s", "save_session", "Save"),
        Binding("l", "load_session", "Load"),
        Binding("1", "toggle_filter(1)", "Toggle 1", show=False),
        Binding("2", "toggle_filter(2)", "Toggle 2", show=False),
        Binding("3", "toggle_filter(3)", "Toggle 3", show=False),
        Binding("4", "toggle_filter(4)", "Toggle 4", show=False),
        Binding("5", "toggle_filter(5)", "Toggle 5", show=False),
        Binding("6", "toggle_filter(6)", "Toggle 6", show=False),
        Binding("7", "toggle_filter(7)", "Toggle 7", show=False),
        Binding("8", "toggle_filter(8)", "Toggle 8", show=False),
        Binding("9", "toggle_filter(9)", "Toggle 9", show=False),
    ]

    def __init__(
        self,
        lines: list[LogLine] | None = None,
        source: str = "",
        session_name: str | None = None,
        file_path: Path | None = None,
        tail: bool = False,
        pipe_input: bool = False,
    ) -> None:
        super().__init__()
        self._lines = lines or []
        self._source = source
        self._filter_rules: list[FilterRule] = []
        self._session_name = session_name or datetime.now(tz=UTC).strftime("%Y-%m-%d-%H%M%S")
        self._file_path = file_path
        self._tail = tail
        self._pipe_input = pipe_input
        self._tail_paused: bool = False
        self._tail_buffer: list[LogLine] = []

    def compose(self) -> ComposeResult:
        yield FilterBar(id="filter-bar")
        yield LogView(id="log-view")
        yield StatusBar(source=self._source, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)

        if self._lines:
            log_view.set_lines(self._lines)

        if self._session_name:
            try:
                session = load_session(self._session_name)
                self._filter_rules = list(session.filters)
                self._apply_filters()
                self.notify(f"Session '{self._session_name}' loaded")
            except FileNotFoundError:
                pass

        # Start tailing if requested
        if self._tail and self._file_path:
            status_bar.set_tailing(True)
            self._start_tail_file(self._file_path)
        elif self._pipe_input:
            status_bar.set_tailing(True)
            self._start_tail_stdin()

        self._update_status_bar()

    def _start_tail_file(self, path: Path) -> None:
        """Start async file tailing worker."""
        self.run_worker(self._tail_worker(read_file_async(path, tail=True)), exclusive=True)

    def _start_tail_stdin(self) -> None:
        """Start async stdin tailing worker."""
        self.run_worker(self._tail_worker(read_stdin_async()), exclusive=True)

    async def _tail_worker(self, reader: AsyncIterator[LogLine]) -> None:
        """Consume async line reader and append lines to the view."""

        log_view = self.query_one("#log-view", LogView)
        worker = get_current_worker()
        async for line in reader:
            if worker.is_cancelled:
                break
            if self._tail_paused:
                self._tail_buffer.append(line)
                status_bar = self.query_one("#status-bar", StatusBar)
                status_bar.set_new_lines(len(self._tail_buffer))
            else:
                log_view.append_line(line)
                self._update_status_bar()

    def action_toggle_tail_pause(self) -> None:
        """Toggle tail pause/resume."""
        if not self._tail and not self._pipe_input:
            return
        self._tail_paused = not self._tail_paused
        status_bar = self.query_one("#status-bar", StatusBar)

        if self._tail_paused:
            status_bar.set_tailing(False)
            self.notify("Tailing paused")
        else:
            # Flush buffered lines
            log_view = self.query_one("#log-view", LogView)
            for line in self._tail_buffer:
                log_view.append_line(line)
            self._tail_buffer.clear()
            status_bar.set_tailing(True)
            status_bar.set_new_lines(0)
            self._update_status_bar()
            self.notify("Tailing resumed")

    def _update_status_bar(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)
        if log_view.has_filters:
            status_bar.update_counts(log_view.total_count, log_view.filtered_count)
        else:
            status_bar.update_counts(log_view.total_count)

    def _apply_filters(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        filter_bar = self.query_one("#filter-bar", FilterBar)
        log_view.set_filters(self._filter_rules)
        filter_bar.update_filters(self._filter_rules)
        self._update_status_bar()
        self._autosave_filters()

    def _autosave_filters(self) -> None:
        """Auto-save current filters under session name."""
        if not self._filter_rules:
            return
        session = create_session(self._session_name, self._filter_rules)
        save_session(session)

    def _add_filter(self, rule: FilterRule) -> None:
        self._filter_rules.append(rule)
        self._apply_filters()

    def _get_current_json_data(self) -> dict[str, Any] | None:
        """Get JSON data from the current cursor line, if it's a JSON line."""
        log_view = self.query_one("#log-view", LogView)
        visible = log_view._lines
        if not visible:
            return None
        line = visible[log_view.cursor_line]
        if line.content_type == ContentType.JSON and line.parsed_json is not None:
            return line.parsed_json
        return None

    # --- Filter actions ---

    def action_filter_in(self) -> None:
        json_data = self._get_current_json_data()
        self.push_screen(FilterDialog(FilterType.INCLUDE, json_data=json_data), callback=self._on_filter_result)

    def action_filter_out(self) -> None:
        json_data = self._get_current_json_data()
        self.push_screen(FilterDialog(FilterType.EXCLUDE, json_data=json_data), callback=self._on_filter_result)

    def _on_filter_result(self, result: FilterRule | None) -> None:
        if result is not None:
            self._add_filter(result)

    def action_manage_filters(self) -> None:
        if not self._filter_rules:
            self.notify("No filters to manage", severity="warning")
            return
        self.push_screen(FilterManageDialog(self._filter_rules), callback=self._on_manage_result)

    def _on_manage_result(self, result: list[FilterRule] | None) -> None:
        if result is not None:
            self._filter_rules = result
            self._apply_filters()

    def action_clear_filters(self) -> None:
        if self._filter_rules:
            self._filter_rules.clear()
            self._apply_filters()

    def action_toggle_filter(self, index: int) -> None:
        idx = index - 1
        if 0 <= idx < len(self._filter_rules):
            self._filter_rules[idx].enabled = not self._filter_rules[idx].enabled
            self._apply_filters()

    # --- Session actions ---

    def action_save_session(self) -> None:
        if not self._filter_rules:
            self.notify("No filters to save", severity="warning")
            return
        self.push_screen(SessionSaveDialog(), callback=self._on_save_session)

    def _on_save_session(self, name: str | None) -> None:
        if name is None:
            return
        self._session_name = name
        session = create_session(name, self._filter_rules)
        save_session(session)
        self.notify(f"Session '{name}' saved")

    def action_load_session(self) -> None:
        self.push_screen(SessionLoadDialog(), callback=self._on_load_session)

    def _on_load_session(self, name: str | None) -> None:
        if name is None:
            return
        try:
            session = load_session(name)
        except FileNotFoundError:
            self.notify(f"Session '{name}' not found", severity="error")
            return
        self._session_name = name
        self._filter_rules = list(session.filters)
        self._apply_filters()
        self.notify(f"Session '{name}' loaded")

    # --- Help ---

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide pause binding when not tailing."""
        if action == "toggle_tail_pause":
            return True if (self._tail or self._pipe_input) else None
        return True
