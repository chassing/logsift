# AGENT.md - Claude Code Instructions for logdelve

## Project Overview

logdelve is a terminal-based log viewer and analyzer. It reads log lines from files, stdin pipes, or AWS CloudWatch, auto-detects the log format, parses timestamps/JSON/levels/components, and presents everything in an interactive TUI built with Textual. Key capabilities: text/regex/JSON-key filtering, search, session management, message template analysis, anomaly detection against a baseline file, and live tailing.

## Tech Stack

- **Python**: 3.13+
- **Package manager**: uv
- **TUI framework**: Textual (>= 1.0) with Rich for text rendering
- **CLI framework**: typer (>= 0.9)
- **Data models**: pydantic (>= 2.0)
- **Async I/O**: aiofiles (>= 24.0)
- **Time parsing**: dateparser (>= 1.3.0)
- **Config storage**: TOML (stdlib `tomllib` for reading, `tomli-w` for writing)
- **Config paths**: platformdirs (>= 4.0, XDG Base Directory)
- **AWS** (optional): boto3 (>= 1.42.49) for CloudWatch integration
- **Testing**: pytest, pytest-asyncio, textual-dev (snapshot/pilot testing)
- **Linting/Formatting**: ruff
- **Type checking**: mypy (strict mode)

## Project Layout

```text
logdelve/
├── pyproject.toml              # version, dependencies, entry points
├── uv.lock
├── Makefile                    # test, lint, format, typecheck, check, gifs, clean
├── CHANGELOG.md
├── README.md
├── LICENSE                     # MIT
├── AGENT.md                    # this file
├── docs/
│   ├── guide.md                # user guide
│   ├── logo.svg
│   ├── screenshots/            # SVG screenshots
│   └── tapes/                  # VHS tape files for GIF recording
├── scripts/
│   ├── perf_test.py            # performance benchmark
│   └── gen_demo_logs.py        # demo log file generator
├── src/logdelve/
│   ├── __init__.py
│   ├── __main__.py             # python -m logdelve
│   ├── py.typed                # PEP 561 marker
│   ├── cli.py                  # typer CLI entry point
│   ├── app.py                  # LogDelveApp (Textual App subclass)
│   ├── models.py               # pydantic models
│   ├── reader.py               # file/stdin/pipe/tail reader (sync + async)
│   ├── filters.py              # filter engine (text, regex, JSON key)
│   ├── search.py               # search engine (text, regex)
│   ├── templates.py            # message template extraction & grouping
│   ├── anomaly.py              # baseline comparison & anomaly detection
│   ├── session.py              # session save/load (TOML)
│   ├── config.py               # XDG paths, app config load/save
│   ├── utils.py                # time parsing (relative, natural language, ISO)
│   ├── aws.py                  # boto3 CloudWatch Logs client
│   ├── parsers/
│   │   ├── __init__.py         # public API: LogParser, ParserName, get_parser, detect_parser
│   │   ├── base.py             # LogParser ABC, ParseResult, registry, shared utilities
│   │   ├── auto.py             # AutoParser (tries all parsers per-line)
│   │   ├── iso.py              # ISO 8601 timestamp (generic catch-all)
│   │   ├── syslog.py           # RFC 3164 syslog
│   │   ├── apache.py           # Apache access/error logs
│   │   ├── docker.py           # Docker Compose format
│   │   ├── kubernetes.py       # Kubernetes logs (bracket or prefix style)
│   │   ├── journalctl.py       # systemd journal
│   │   ├── python_logging.py   # Python logging format
│   │   └── logfmt.py           # logfmt key=value format
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── inspect.py          # main inspect command
│   │   └── cloudwatch.py       # AWS CloudWatch commands (get, tail, groups)
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── log_view.py         # main scrollable log view (ScrollView + Line API)
│   │   ├── log_line.py         # single line rendering helpers
│   │   ├── filter_bar.py       # top toolbar: active filters, search, level, anomalies
│   │   ├── filter_dialog.py    # filter input dialog (text/regex/JSON key suggestions)
│   │   ├── filter_manage_dialog.py  # toggle/edit/delete/reorder filters
│   │   ├── search_dialog.py    # search input dialog (text/regex, case-sensitive)
│   │   ├── groups_dialog.py    # message template + field analysis dialog
│   │   ├── session_dialog.py   # session load/save/rename/delete dialog
│   │   ├── theme_dialog.py     # theme selection dialog
│   │   ├── status_bar.py       # bottom status bar (counts, level, search, tailing)
│   │   ├── help_screen.py      # help overlay with all keybindings
│   │   └── demo_overlay.py     # demo mode overlay (LOGDELVE_DEMO env var)
│   └── styles/
│       └── app.tcss            # Textual CSS
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_filters.py
    ├── test_reader.py
    ├── test_session.py
    ├── test_log_line.py
    ├── test_anomaly.py
    ├── test_templates.py
    ├── test_cloudwatch.py
    └── test_parsers/
        ├── __init__.py
        ├── test_base.py
        ├── test_auto.py
        ├── test_registry.py
        ├── test_integration.py
        ├── test_iso.py
        ├── test_syslog.py
        ├── test_apache.py
        ├── test_docker.py
        ├── test_kubernetes.py
        ├── test_journalctl.py
        ├── test_python_logging.py
        └── test_logfmt.py
```

## Architecture

### Data Flow

```
Input (file/pipe/CloudWatch)
  → reader.py (sync read or async generator)
    → parsers/ (auto-detect format, extract timestamp/level/component/JSON)
      → models.LogLine (one per raw line)
        → app.py (state management, keybinding dispatch)
          → LogView (virtual rendering via ScrollView + Line API)
          → FilterBar / StatusBar / Footer (chrome)
          → Modal dialogs (search, filter, analyze, sessions, theme, help)
```

### Core Models (`models.py`)

| Model         | Purpose                                                                                                                                   |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `LogLine`     | Single parsed log line: `line_number`, `raw`, `timestamp`, `content_type` (JSON/TEXT), `content`, `parsed_json`, `log_level`, `component` |
| `FilterRule`  | A filter: `filter_type` (INCLUDE/EXCLUDE), `pattern`, `enabled`, `is_regex`, `case_sensitive`, `is_json_key`, `json_key`, `json_value`    |
| `SearchQuery` | Search: `pattern`, `case_sensitive`, `is_regex`, `direction` (FORWARD/BACKWARD)                                                           |
| `AppConfig`   | Persisted config: `theme`                                                                                                                 |
| `Session`     | Named filter set: `name`, `filters: list[FilterRule]`, `created_at`, `updated_at`                                                         |

### Parser System (`parsers/`)

- **`LogParser`** (ABC in `base.py`): `try_parse(raw) -> ParseResult | None`, `parse_line(line_number, raw) -> LogLine`
- **`ParseResult`** (dataclass): `timestamp`, `content`, `content_type`, `parsed_json`, `log_level`, `component`
- **`ParserName`** (StrEnum): `AUTO`, `ISO`, `SYSLOG`, `APACHE`, `DOCKER`, `KUBERNETES`, `JOURNALCTL`, `PYTHON`, `LOGFMT`
- **Auto-detection** (`detect_parser()`): samples first 20 lines, tries each parser, selects the one with >50% match rate. Falls back to `AutoParser` (per-line detection).
- **Shared utilities**: `classify_content()` (JSON vs text), `extract_log_level()` (JSON keys → bracket patterns → keyword heuristics), `extract_component_from_json()` (checks `service`, `component`, `app`, `source`, `container`, `pod` keys)

### Filter Engine (`filters.py`)

- `apply_filters(lines, rules) -> list[int]` — returns indices of matching lines
- **Include rules**: OR logic (match any include)
- **Exclude rules**: AND logic (excluded if matches any exclude)
- **Match modes**: text substring, regex, JSON key-value
- `check_line()` — single-line filter check (used for incremental tailing)
- `flatten_json()` / `get_nested_value()` — JSON traversal utilities

### Search Engine (`search.py`)

- `find_matches(lines, query) -> list[tuple[int, int, int]]` — returns `(line_index, start_pos, end_pos)`
- Supports text (substring) and regex modes
- Matches are grouped by line in `LogView._search_matches_by_line` for efficient rendering

### Template & Anomaly System

- **`templates.py`**: Extracts message templates by tokenizing variable parts (UUIDs, timestamps, IPs, paths, numbers) into placeholders. Groups lines by template. Also provides field-value analysis for JSON logs.
- **`anomaly.py`**: Compares current log templates against a baseline file. Scores: 1.0 = novel template (not in baseline), 0.5 = frequency spike (>5x). `AnomalyResult` tracks novel templates, disappeared patterns, frequency spikes, and per-line scores.

### TUI Architecture (`app.py`)

**Widget composition**: `FilterBar` → `LogView` → `StatusBar` → `Footer`

**`LogDelveApp` state**:

- `_lines: list[LogLine]` — all loaded lines
- `_filter_rules: list[FilterRule]` — active filters
- `_min_level: LogLevel | None` — minimum level filter
- `_last_search: SearchQuery | None` — last search query
- `_filters_suspended: bool` — toggle all filters state (with `_suspended_rules`, `_suspended_level`, `_suspended_anomaly`)
- `_anomaly_result: AnomalyResult | None` — baseline comparison result
- `_tail_paused: bool` / `_tail_buffer: list[LogLine]` — tailing state
- `_config: AppConfig` — persisted configuration
- `_session_name: str` — current session name (auto-generated timestamp or user-provided)

**`LogView` state** (`widgets/log_view.py`):

- `_all_lines: list[LogLine]` — all lines (reference shared with app)
- `_filtered_indices: list[int]` — indices into `_all_lines` for visible lines
- `_heights: list[int]` / `_offsets: list[int]` — variable-height line layout (prefix-sum for binary search)
- `_component_display: str` — `"tag"` / `"full"` / `"off"`
- `_component_colors: dict[str, int]` / `_component_index: dict[str, int]` — color assignment
- `_search_query` / `_search_matches` / `_search_current` / `_search_matches_by_line` — search state
- `_global_expand: bool` / `_sticky_expand: bool` — JSON expansion state
- `cursor_line: reactive[int]` — current cursor position (Textual reactive)

### Keybindings

**App-level** (`app.py`):

| Key      | Action                | Description                            |
| -------- | --------------------- | -------------------------------------- |
| `/`      | `search_forward`      | Search forward                         |
| `?`      | `search_backward`     | Search backward                        |
| `f`      | `filter_in`           | Add include filter                     |
| `F`      | `filter_out`          | Add exclude filter                     |
| `m`      | `manage_filters`      | Manage filters dialog                  |
| `1-9`    | `toggle_filter(N)`    | Toggle filter N on/off                 |
| `x`      | `toggle_all_filters`  | Suspend/restore all filters            |
| `e`      | `cycle_level_filter`  | Cycle level: ALL → ERROR → WARN → INFO |
| `!`      | `toggle_anomalies`    | Toggle anomaly-only view               |
| `a`      | `analyze`             | Message template / field analysis      |
| `s`      | `manage_sessions`     | Session management                     |
| `t`      | `toggle_theme`        | Theme selection                        |
| `p`      | `toggle_tail_pause`   | Pause/resume tailing                   |
| `h`      | `show_help`           | Help screen                            |
| `q`      | `quit`                | Quit                                   |
| `Ctrl+S` | `save_screenshot_svg` | Save SVG screenshot                    |
| `Ctrl+B` | `next_demo_label`     | Demo mode (LOGDELVE_DEMO)              |

**LogView-level** (`widgets/log_view.py`):

| Key               | Action                    | Description                                 |
| ----------------- | ------------------------- | ------------------------------------------- |
| `up/down`         | `cursor_up/down`          | Move cursor                                 |
| `PageUp/PageDown` | `page_up/down`            | Page navigation                             |
| `Home/End`        | `scroll_home/end`         | Jump to start/end                           |
| `g` (gg)          | `goto_top_or_prefix`      | Go to top (double-tap)                      |
| `G`               | `scroll_end`              | Go to bottom                                |
| `j`               | `toggle_json_global`      | Toggle JSON expand (all lines)              |
| `Enter`           | `toggle_json_line`        | Toggle JSON expand (sticky, follows cursor) |
| `#`               | `toggle_line_numbers`     | Toggle line numbers                         |
| `c`               | `cycle_component_display` | Component: tag → full → off                 |
| `n`               | `next_match`              | Next search match                           |
| `N`               | `prev_match`              | Previous search match                       |

### CLI Entry Points

- **Entry point**: `logdelve = "logdelve.cli:main"` (in pyproject.toml)
- **Inspect command**: `logdelve inspect <file> [--tail/-t] [--session/-s NAME] [--baseline/-b FILE] [--parser/-p FORMAT]`
- **CloudWatch**: `logdelve cloudwatch get/tail/groups` (requires optional `boto3` dependency)

### Config & Sessions

- Config directory: `~/.config/logdelve/` (via `platformdirs.user_config_dir`)
- App config: `~/.config/logdelve/config.toml` (currently only `theme` field)
- Session files: `~/.config/logdelve/sessions/<name>.toml` (filter rules persisted as TOML)
- Sessions are auto-saved on filter changes

## Release Checklist

When creating a new release, **all** of the following steps must be completed:

1. **Version bump**: Update `version` in `pyproject.toml`
2. **Lock file**: Run `uv lock` to update `uv.lock` with the new version
3. **CHANGELOG.md**: Add new section with all changes (Added, Changed, Fixed)
4. **README.md**: Ensure all of the following are up to date:
   - Feature list matches current capabilities
   - Keybinding tables match actual bindings in `app.py`, `log_view.py`, and `help_screen.py`
   - General table (t, h, q) matches actual behavior
   - Configuration section reflects current config options
   - Installation instructions are correct
5. **Help screen**: Verify `help_screen.py` HELP_TEXT matches actual keybindings
6. **Run all checks**: `make test` (lint, format, typecheck, tests)
7. **Commit**: `git commit -m "Release vX.Y.Z"`
8. **Push**: `git push`
9. **Create release**: `gh release create vX.Y.Z --title "vX.Y.Z" --notes "See CHANGELOG.md"`

The `publish.yml` GitHub Action automatically builds and publishes to PyPI on release.

### Cross-check consistency

These files must stay in sync when keybindings or features change:

- `src/logdelve/app.py` — BINDINGS
- `src/logdelve/widgets/log_view.py` — BINDINGS
- `src/logdelve/widgets/help_screen.py` — HELP_TEXT
- `README.md` — Keybindings tables + Feature list

## Coding Conventions

### General

- NO arbitrary dictionaries. Always use pydantic models for structured data.
- Use type hints everywhere. mypy strict mode must pass.
- Keep functions focused — one clear purpose per function.
- Use meaningful variable names. Avoid over-commenting.
- Prefer `pathlib.Path` over string paths.
- Use `StrEnum` for fixed choice fields.
- Use `dataclass(slots=True)` for internal data transfer objects (like `ParseResult`).

### Textual

- Use Textual design tokens (`$primary`, `$text`, `$surface`, etc.) instead of hardcoded colors.
- Use `compose()` for building widget trees.
- Use `run_worker()` for background/async tasks. Check `worker.is_cancelled` in loops.
- Use reactive attributes for state that should trigger UI updates.
- Use Textual's message system for widget-to-app communication.
- The main log display uses `ScrollView` with the Line API (virtual rendering), not `ListView`.
- In dialogs: Enter on checkboxes should submit the form, Space toggles — use `on_key` handler.
- For OptionList selection: use `on_option_list_option_selected` handler, not screen-level Enter binding.
- Use `ModalScreen[ReturnType]` for dialogs that return data. Dismiss with `self.dismiss(value)`.
- Follow existing dialog patterns: `compose()` → `Vertical` container → Label (title) → Input/OptionList → Horizontal (checkboxes) → Label (hint).

### Adding New Dialogs

Follow this pattern (see `search_dialog.py`, `filter_dialog.py` for reference):

1. Create `src/logdelve/widgets/my_dialog.py`
2. Class inherits `ModalScreen[ReturnType | None]`
3. Define `DEFAULT_CSS` with `align: center middle` and styled `Vertical` container
4. Add `BINDINGS` with `escape` → `cancel`
5. Implement `compose()`, `on_input_submitted()`, `_submit()`, `action_cancel()`
6. In `app.py`: add `Binding`, `action_*()` method, `push_screen(dialog, callback=self._on_result)`

### Adding New Parsers

Follow this pattern (see `syslog.py`, `docker.py` for reference):

1. Create `src/logdelve/parsers/my_parser.py`
2. Class inherits `LogParser` (from `base.py`)
3. Implement `name` (property), `description` (property), `try_parse(raw) -> ParseResult | None`
4. Register in `base.py`: add to `ParserName` enum, `_build_registry()`, `_DETECTION_ORDER`
5. Create `tests/test_parsers/test_my_parser.py`

### CLI

- Use typer for all CLI argument/option handling.
- Entry point: `logdelve.cli:main`
- Main app is `typer.Typer(add_completion=False)`
- Sub-commands via `app.add_typer()` (see `cloudwatch.py`)

### Config & Sessions

- Config directory: `~/.config/logdelve/` (via platformdirs)
- App config: `~/.config/logdelve/config.toml`
- Session files: `~/.config/logdelve/sessions/<name>.toml`
- Use stdlib `tomllib` for reading TOML, `tomli-w` for writing.

### Testing

- Use pytest with `pytest-asyncio` for async tests.
- Use Textual's `app.run_test()` pilot for TUI tests.
- Test files mirror source structure: `test_filters.py` tests `filters.py`.
- Parser tests live in `tests/test_parsers/` subdirectory.
- Keep tests focused and fast. Mock I/O where needed.

### Tooling

```bash
uv run ruff format src/ tests/    # format
uv run ruff check src/ tests/     # lint
uv run mypy src/                  # type check
uv run pytest                     # test
make test                         # all of the above
make check                        # lint + format-check + typecheck (no tests)
make gifs                         # generate GIF recordings from docs/tapes/
```

## Do's

- Use pydantic models for all structured data.
- Use Textual's built-in widgets and patterns where they fit.
- Use async generators for reading log lines.
- Use Rich `Segment`/`Strip` for low-level line rendering in `LogView`.
- Handle edge cases: empty files, binary content, malformed JSON, huge lines.
- Write tests for all new modules.
- Use `replace_option_prompt_at_index` for in-place OptionList updates to preserve scroll position.
- Preserve cursor position across filter changes via `cursor_orig_index()` / `restore_cursor()`.
- Call `_update_status_bar()` after any state change that affects counts or indicators.

## Don'ts

- Don't use arbitrary dicts where a pydantic model should be used.
- Don't use `ListView` for the main log display (use `ScrollView` + Line API).
- Don't use `argparse` or `click` for CLI (use typer).
- Don't hardcode colors in CSS — use Textual design tokens.
- Don't block the event loop with synchronous I/O in the TUI.
- Don't add emoji or colors to non-TUI CLI output.
- Don't over-engineer: build what the current task requires, nothing more.
- Don't use `clear_options()` + rebuild for single-item updates in OptionList (causes scroll reset).
- Don't access `_all_lines` by filtered index — always go through `_filtered_indices` to map visible index → original index.
