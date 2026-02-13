# logsift

A terminal UI tool for viewing and filtering log lines. Think of it as a lightweight, interactive log viewer with JSON awareness.

## Features

- **File and pipe input**: Read logs from files or pipe them via stdin
- **Timestamp parsing**: Automatic detection of ISO 8601, syslog, Apache, and other common timestamp formats
- **JSON awareness**: Detects JSON content in log lines and offers pretty-printing with syntax highlighting
- **Pretty-print toggle**: Switch between compact and expanded JSON view, globally or per-line
- **Interactive filtering**: Filter log lines by text pattern (include or exclude)
- **JSON key filtering**: Filter by specific JSON key-value pairs (e.g., show only `"log_level": "error"`)
- **Mouse selection filtering**: Select text with the mouse to create filters
- **Named sessions**: Save and load filter configurations by name
- **Live tailing**: Follow growing log files in real-time (like `tail -f`)

## Installation

Requires Python 3.13+.

```bash
# Install with uv
uv tool install logsift

# Or install with pip
pip install logsift
```

## Usage

```bash
# View a log file
logsift app.log

# Pipe logs from another command
kubectl logs pod-name | logsift

# Follow a growing file (tail mode)
logsift -f /var/log/syslog

# Load a saved filter session
logsift --session my-filters app.log
```

## Keybindings

### Navigation

| Key | Action |
| --- | ------ |
| Up / Down | Move between log lines |
| PgUp / PgDn | Page up / down |
| Home / End | Jump to first / last line |
| G | Jump to bottom |
| q | Quit |

### JSON Display

| Key | Action |
| --- | ------ |
| j | Toggle pretty-print for ALL JSON lines |
| Enter | Toggle pretty-print for the current line |

### Filtering

| Key | Action |
| --- | ------ |
| / | Filter in: show only lines matching a pattern |
| \ | Filter out: hide lines matching a pattern |
| f | Filter by JSON key-value pair (on JSON lines) |
| c | Clear all filters |
| 1-9 | Toggle individual filters on/off |

### Sessions

| Key | Action |
| --- | ------ |
| s | Save current filters as a named session |
| l | Load a saved session |

### Search

| Key | Action |
| --- | ------ |
| ? | Search within log lines |
| n / N | Next / previous search match |
| h | Show help screen |

## Log Format

logsift expects each line to begin with a timestamp, followed by either a JSON object or plain text:

```
2024-01-15T10:30:00Z {"log_level": "info", "message": "Request processed", "duration_ms": 42}
2024-01-15T10:30:01Z Connection established from 192.168.1.1
Jan 15 10:30:02 myhost syslogd: restart
```

Lines without a recognized timestamp are displayed as-is.

## Sessions

Filter sessions are stored in `~/.config/logsift/sessions/` as TOML files. You can load a session on startup with the `--session` flag or manage sessions interactively with `s` (save) and `l` (load).

## Development

```bash
# Clone the repo
git clone https://github.com/chassing/logsift.git
cd logsift

# Install dependencies
uv sync

# Run from source
uv run logsift sample.log

# Run tests
uv run pytest

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## License

MIT
