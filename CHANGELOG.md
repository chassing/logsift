# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - Unreleased

### Added

- **Anomaly detection**: `--baseline` option compares current logs against a known-good baseline
- **Anomaly display**: red `▌` marker on anomalous lines, auto-enabled anomaly filter, `!` to toggle
- **Log level detection**: automatic extraction from JSON fields and text patterns, color-coded line backgrounds
- **Log level filter**: `e` to cycle minimum level (ALL → ERROR → WARN → INFO)
- **Component detection**: Kubernetes pods, Docker Compose services, JSON fields — with color-coded tags (`c` to cycle)
- **Message analysis dialog**: `a` to open, groups log messages by event pattern
- **Field analysis**: `m` to switch mode, JSON field value distributions with =0/>0 buckets for integers
- **Analyze controls**: separate mode (`m`), sort (`s`), reverse (`r`) controls
- **Filter edit**: `e` in filter manager to edit a filter's pattern inline
- **Filter suspend/resume**: `x` suspends ALL filters (rules, level, anomaly), `x` again restores
- **Cursor preservation**: filter toggles (`x`, `!`, `e`) keep cursor on the same log line, centered on screen
- **Search persistence**: search dialog pre-fills with last search (pattern, case-sensitive, regex)
- **Toolbar bar**: always-visible top bar with shortcuts, active search text, level/anomaly/filter status
- **CloudWatch stream names**: `[stream-name]` prefix in cloudwatch get output
- **Flexible time parsing**: `dateparser` integration for natural language dates ("yesterday at 8am", "friday", "2 days ago", "Feb 13 2026 7:58")
- **Compact timestamp**: HH:MM:SS instead of full ISO in log view
- **Parser plugins**: pluggable log format parsers with auto-detection — ISO 8601, syslog, Apache CLF, Docker Compose, Kubernetes, journalctl, Python logging, logfmt
- **Format selection**: `--parser/-p` option to force a specific log format
- **Syslog component extraction**: hostname and program name (`program[pid]`) from syslog lines
- **Text expand**: Enter on text lines shows full raw line below the compact view
- **Level heuristics**: detect ERROR/WARN from keywords (fail, refused, timeout, deprecated) when no explicit level

### Changed

- **Tailing default**: files are read once by default, use `--tail/-t` to follow new lines; pipe input tails automatically (was: tailing on by default with `--no-tail` to disable)
- **CloudWatch output**: includes stream name as `[stream-name]` prefix for component detection
- **Default log level**: lines with timestamp but no detected level default to INFO
- **Filter bar**: always visible toolbar replaces hidden filter-only bar
- **Filter manager**: shows case-sensitive indicator `[Aa]`
- **README**: rewritten with use cases, outage investigation workflow, CloudWatch examples

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
- **Live tailing**: `--tail/-t` for files, auto-tail for pipe input
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
