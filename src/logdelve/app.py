"""Textual application for logdelve."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer
from textual.worker import get_current_worker

from logdelve.anomaly import AnomalyResult, build_baseline, detect_anomalies
from logdelve.config import load_config, save_config
from logdelve.models import ContentType, FilterRule, FilterType, LogLevel, LogLine, SearchDirection, SearchQuery
from logdelve.reader import read_file, read_file_async, read_pipe_async
from logdelve.session import create_session, load_session, save_session
from logdelve.widgets.filter_bar import FilterBar
from logdelve.widgets.filter_dialog import FilterDialog
from logdelve.widgets.filter_manage_dialog import FilterManageDialog
from logdelve.widgets.groups_dialog import GroupsDialog
from logdelve.widgets.help_screen import HelpScreen
from logdelve.widgets.log_view import LogView
from logdelve.widgets.search_dialog import SearchDialog
from logdelve.widgets.session_dialog import SessionAction, SessionActionType, SessionManageDialog
from logdelve.widgets.status_bar import StatusBar
from logdelve.widgets.theme_dialog import ThemeDialog

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from logdelve.parsers import LogParser
_ANALYZE_LINE_THRESHOLD = 10_000


class LogDelveApp(App[None]):  # noqa: PLR0904
    """Log viewer TUI application."""

    CSS_PATH = "styles/app.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("s", "manage_sessions", "Sessions"),
        Binding("x", "toggle_all_filters", "Filters off", show=False),
        Binding("slash", "search_forward", "Search", show=False),
        Binding("question_mark", "search_backward", "Search back", show=False),
        Binding("f", "filter_in", "Filter in", show=False),
        Binding("F", "filter_out", "Filter out", show=False),
        Binding("a", "analyze", "Analyze", show=False),
        Binding("m", "manage_filters", "Filters", show=False),
        Binding("t", "toggle_theme", "Theme", show=False),
        Binding("e", "cycle_level_filter", "Level", show=False),
        Binding("exclamation_mark", "toggle_anomalies", "Anomalies", show=False),
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_tail_pause", "Tail pause", show=False),
        Binding("h", "show_help", "Help"),
        Binding("ctrl+s", "save_screenshot_svg", "Screenshot", show=False),
        Binding("ctrl+b", "next_demo_label", "Demo", show=False),
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
        *,
        tail: bool = False,
        pipe_fd: int | None = None,
        baseline_path: Path | None = None,
        parser: LogParser | None = None,
    ) -> None:
        super().__init__()
        self._lines = lines or []
        self._source = source
        self._filter_rules: list[FilterRule] = []
        self._session_name = session_name or datetime.now(tz=UTC).strftime("%Y-%m-%d-%H%M%S")
        self._file_path = file_path
        self._tail = tail
        self._pipe_fd = pipe_fd
        self._parser = parser
        self._tail_paused: bool = False
        self._tail_buffer: list[LogLine] = []
        self._last_search: SearchQuery | None = None
        self._filters_suspended: bool = False
        self._suspended_rules: list[FilterRule] = []
        self._suspended_level: LogLevel | None = None
        self._suspended_anomaly: bool = False
        self._min_level: LogLevel | None = None
        self._baseline_path = baseline_path
        self._anomaly_result: AnomalyResult | None = None
        self._config = load_config()
        self.theme = self._config.theme

    @property
    def _is_streaming(self) -> bool:
        return self._tail or self._pipe_fd is not None

    def compose(self) -> ComposeResult:
        yield FilterBar(id="filter-bar")
        yield LogView(id="log-view")
        yield StatusBar(source=self._source, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)

        if os.environ.get("LOGDELVE_DEMO"):
            from logdelve.widgets.demo_overlay import setup_demo  # noqa: PLC0415

            setup_demo(self)

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

        # Baseline anomaly detection
        if self._baseline_path and self._lines:
            baseline_lines = read_file(self._baseline_path, parser=self._parser)
            baseline = build_baseline(baseline_lines)
            self._anomaly_result = detect_anomalies(self._lines, baseline)
            log_view.set_anomaly_scores(self._anomaly_result.scores)
            n = self._anomaly_result.anomaly_count
            if n > 0:
                log_view.toggle_anomaly_filter()
                self.notify(f"{n} anomalies detected — showing anomalies only (! to toggle)")
            else:
                self.notify("No anomalies found")

        if self._tail and self._file_path:
            status_bar.set_tailing(tailing=True)
            self.run_worker(
                self._tail_worker(read_file_async(self._file_path, tail=True, parser=self._parser)), exclusive=True
            )
        elif self._pipe_fd is not None:
            status_bar.set_tailing(tailing=True)
            self.run_worker(self._tail_worker(read_pipe_async(self._pipe_fd, parser=self._parser)), exclusive=True)

        self._update_status_bar()

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
        if not self._is_streaming:
            return
        self._tail_paused = not self._tail_paused
        status_bar = self.query_one("#status-bar", StatusBar)

        if self._tail_paused:
            status_bar.set_tailing(tailing=False)
            self.notify("Tailing paused")
        else:
            log_view = self.query_one("#log-view", LogView)
            for line in self._tail_buffer:
                log_view.append_line(line)
            self._tail_buffer.clear()
            status_bar.set_tailing(tailing=True)
            status_bar.set_new_lines(0)
            self._update_status_bar()
            self.notify("Tailing resumed")

    def _update_status_bar(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)
        filter_bar = self.query_one("#filter-bar", FilterBar)
        if log_view.has_filters:
            status_bar.update_counts(log_view.total_count, log_view.filtered_count)
        else:
            status_bar.update_counts(log_view.total_count)
        level_counts = log_view.level_counts
        status_bar.set_level_counts(level_counts, self._min_level)
        filter_bar.set_level_info(self._min_level, has_levels=bool(level_counts))
        if self._anomaly_result:
            status_bar.set_anomaly_count(self._anomaly_result.anomaly_count)
            filter_bar.set_anomaly_info(self._anomaly_result.anomaly_count, filter_active=log_view.anomaly_filter)

    def update_search_status(self) -> None:
        """Update status bar with current search match info."""
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)
        if log_view.search_match_count > 0:
            status_bar.set_search_info(log_view.search_current_index + 1, log_view.search_match_count)
        elif log_view.has_search:
            status_bar.set_search_info(0, 0)
        else:
            status_bar.clear_search_info()

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
        visible = log_view.lines
        if not visible:
            return None
        line = visible[log_view.cursor_line]
        if line.content_type == ContentType.JSON and line.parsed_json is not None:
            return line.parsed_json
        return None

    # --- Search actions ---

    def action_search_forward(self) -> None:
        self.push_screen(
            SearchDialog(SearchDirection.FORWARD, last_query=self._last_search), callback=self._on_search_result
        )

    def action_search_backward(self) -> None:
        self.push_screen(
            SearchDialog(SearchDirection.BACKWARD, last_query=self._last_search), callback=self._on_search_result
        )

    def _on_search_result(self, result: SearchQuery | None) -> None:
        if result is None:
            return
        self._last_search = result
        filter_bar = self.query_one("#filter-bar", FilterBar)
        filter_bar.set_search_text(result.pattern)
        log_view = self.query_one("#log-view", LogView)
        log_view.set_search(result)
        self.update_search_status()

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

    def action_toggle_filter(self, index: int) -> None:
        idx = index - 1
        if 0 <= idx < len(self._filter_rules):
            self._filter_rules[idx].enabled = not self._filter_rules[idx].enabled
            self._apply_filters()

    def action_toggle_all_filters(self) -> None:
        """Suspend/resume ALL filters (rules, level, anomaly) preserving cursor line."""
        log_view = self.query_one("#log-view", LogView)
        orig_idx = log_view.cursor_orig_index()

        if self._filters_suspended:
            # Restore everything
            self._filter_rules = self._suspended_rules
            self._suspended_rules = []
            self._min_level = self._suspended_level
            self._suspended_level = None
            log_view.anomaly_filter = self._suspended_anomaly
            self._suspended_anomaly = False
            self._filters_suspended = False
            log_view.min_level = self._min_level
            self._apply_filters()
            log_view.restore_cursor(orig_idx)
            self.notify("Filters restored")
        else:
            # Suspend everything
            has_anything = bool(self._filter_rules) or self._min_level is not None or log_view.anomaly_filter
            if not has_anything:
                return
            self._suspended_rules = list(self._filter_rules)
            self._suspended_level = self._min_level
            self._suspended_anomaly = log_view.anomaly_filter
            self._filter_rules = []
            self._min_level = None
            log_view.anomaly_filter = False
            self._filters_suspended = True
            log_view.min_level = None
            self._apply_filters()
            log_view.restore_cursor(orig_idx)
            self.notify("All filters suspended")

        self._update_status_bar()

    # --- Session actions ---

    def action_manage_sessions(self) -> None:
        self.push_screen(SessionManageDialog(current_session=self._session_name), callback=self._on_session_result)

    def _on_session_result(self, result: SessionAction | None) -> None:
        if result is None:
            return
        if result.action == SessionActionType.LOAD:
            try:
                session = load_session(result.name)
            except FileNotFoundError:
                self.notify(f"Session '{result.name}' not found", severity="error")
                return
            self._session_name = result.name
            self._filter_rules = list(session.filters)
            self._apply_filters()
            self.notify(f"Session '{result.name}' loaded")
        elif result.action == SessionActionType.SAVE:
            if not self._filter_rules:
                self.notify("No filters to save", severity="warning")
                return
            self._session_name = result.name
            session = create_session(result.name, self._filter_rules)
            save_session(session)
            self.notify(f"Session '{result.name}' saved")

    # --- Anomaly filter ---

    def action_toggle_anomalies(self) -> None:
        """Toggle showing only anomalous lines."""
        if not self._anomaly_result or self._anomaly_result.anomaly_count == 0:
            self.notify("No anomalies detected (use --baseline)", severity="warning")
            return
        log_view = self.query_one("#log-view", LogView)
        log_view.toggle_anomaly_filter()
        self._update_status_bar()
        if log_view.anomaly_filter:
            self.notify("Showing anomalies only")
        else:
            self.notify("Showing all lines")

    # --- Analyze ---

    def action_analyze(self) -> None:
        """Open message group analysis dialog."""
        log_view = self.query_one("#log-view", LogView)
        lines = log_view.lines
        if not lines:
            self.notify("No lines to analyze", severity="warning")
            return
        n = len(lines)
        if n > _ANALYZE_LINE_THRESHOLD:
            self.notify(f"Analyzing {n:,} lines...", timeout=3)
            self.set_timer(0.1, lambda: self._open_analyze(lines))
        else:
            self._open_analyze(lines)

    def _open_analyze(self, lines: list[LogLine] | None = None) -> None:
        """Open the analyze dialog (deferred to show notification first)."""
        if lines is None:
            lines = self.query_one("#log-view", LogView).lines
        self.push_screen(GroupsDialog(lines), callback=self._on_groups_result)

    def _on_groups_result(self, result: FilterRule | None) -> None:
        if result is not None:
            self._add_filter(result)

    # --- Level filter ---

    def action_cycle_level_filter(self) -> None:
        """Cycle through minimum log level: ALL → ERROR → WARN → INFO → ALL."""
        cycle: list[LogLevel | None] = [None, LogLevel.ERROR, LogLevel.WARN, LogLevel.INFO]
        try:
            idx = cycle.index(self._min_level)
        except ValueError:
            idx = 0
        self._min_level = cycle[(idx + 1) % len(cycle)]
        log_view = self.query_one("#log-view", LogView)
        log_view.set_min_level(self._min_level)
        self._update_status_bar()
        if self._min_level:
            self.notify(f"Level filter: {self._min_level.value.upper()}+")
        else:
            self.notify("Level filter: ALL")

    # --- Theme ---

    def action_toggle_theme(self) -> None:
        """Open theme selection dialog."""
        self.push_screen(ThemeDialog(self.theme), callback=self._on_theme_result)

    def _on_theme_result(self, result: str | None) -> None:
        if result is None:
            return
        self.theme = result
        self._config.theme = result
        save_config(self._config)

    # --- Screenshot ---

    def action_save_screenshot_svg(self) -> None:
        """Save a screenshot as SVG to docs/screenshots/."""
        from pathlib import Path  # noqa: PLC0415

        out_dir = Path("docs/screenshots")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
        path = out_dir / f"logdelve-{ts}.svg"
        self.save_screenshot(str(path))
        self.notify(f"Screenshot saved: {path}")

    # --- Demo labels ---

    def action_next_demo_label(self) -> None:
        """Show the next demo label (Ctrl+B). No-op without LOGDELVE_DEMO."""
        if handler := getattr(self, "_demo_next_label", None):
            handler()

    # --- Help ---

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def check_action(self, action: str, _parameters: tuple[object, ...]) -> bool | None:
        """Hide pause binding when not streaming."""
        if action == "toggle_tail_pause":
            return True if self._is_streaming else None
        return True
