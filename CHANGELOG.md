# Changelog

All notable changes to this project will be documented in this file.

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
- **AWS CloudWatch**: `logsift cloudwatch get/groups/streams` commands
- **CloudWatch features**: `--message-key` extraction, `--tail` polling, pagination
- **Time parsing**: relative (`5m`, `1h`, `2days`, `1week`), time-only (`14:30`), ISO 8601
- **Optional boto3**: `pip install logsift[aws]` with clear error if missing
- **CI/CD**: GitHub Actions for test/lint/typecheck and PyPI publishing
