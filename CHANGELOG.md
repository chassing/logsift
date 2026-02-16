# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-16

### Added

- **Search**: forward (`/`) and backward (`?`) search with match highlighting
- **Search options**: case-sensitive and regex toggles in search dialog
- **Search navigation**: `n` for next match, `N` for previous match, with wrap-around
- **Search status**: match count `[x/y]` shown in status bar
- **Regex filters**: regex checkbox in filter dialog, displayed as `/.../` in filter manager
- **Case-sensitive filters**: case-sensitive checkbox in filter dialog
- **Theme selection**: `t` opens dialog with all available Textual themes
- **Theme persistence**: selected theme saved to `~/.config/logdelve/config.toml`
- **Performance benchmark**: `scripts/perf_test.py` for measuring parse, filter, and search speed
- **Contributing guide**: added to README
- **SVG logo**: project logo in `docs/logo.svg`
- **Additional badges**: CI, Ruff, mypy, PyPI downloads

### Changed

- **Filter keybindings**: `f` for filter-in, `F` for filter-out (was `/` and `\`)
- **Line numbers**: `#` to toggle (was `n`)
- **Help**: `h` only (was `h` and `?`)
- **Enter on checkboxes**: submits the dialog instead of toggling (use Space to toggle)
- **Session dialog**: Enter on OptionList now correctly loads the selected session
- **Design tokens**: replaced hardcoded colors with Textual theme variables
- **Renamed**: `LogSiftApp` → `LogDelveApp`

### Fixed

- Filter manage dialog no longer scrolls to bottom when toggling a filter

## [0.1.0] - 2026-02-16

### Added

- **TUI log viewer** with ScrollView-based virtual rendering
- **Log parsing**: ISO 8601, syslog, Apache CLF, slash-date timestamp detection
- **JSON awareness**: automatic detection and pretty-print with syntax highlighting
- **JSON toggle**: `j` for all lines, `Enter` for per-line sticky expand
- **Line numbers**: toggleable with `n`
- **Text filtering**: `/` filter-in, `\` filter-out with case-insensitive substring matching
- **JSON key filtering**: `key=value` syntax in filter dialogs, key-value suggestions on JSON lines
- **Filter management**: `m` dialog to toggle, delete, clear, reorder filters
- **Filter toggle**: `1-9` keys for quick filter on/off
- **Session management**: `s` dialog to load, save, delete, rename filter sessions
- **Auto-save**: filters automatically saved as timestamped sessions
- **CLI session loading**: `--session/-s` flag to load filters on startup
- **Live tailing**: auto-tail for files and pipe input with `--no-tail` to disable
- **Pause/resume**: `p` to pause tailing, buffer new lines, resume to flush
- **Pipe input**: progressive loading via fd duplication, Textual keyboard support preserved
- **vim navigation**: `gg` for top, `G` for bottom
- **Status bar**: line counts, filter counts, tail indicator
- **Footer**: visible keyboard shortcuts
- **Help screen**: `?` or `h` with full keybinding reference
- **AWS CloudWatch**: `logdelve cloudwatch get/groups/streams` commands
- **CloudWatch features**: `--message-key` extraction, `--tail` polling, pagination
- **Time parsing**: relative (`5m`, `1h`, `2days`, `1week`), time-only (`14:30`), ISO 8601
- **Optional boto3**: `pip install logdelve[aws]` with clear error if missing
- **CI/CD**: GitHub Actions for test/lint/typecheck and PyPI publishing
