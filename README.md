# logsift

A terminal UI tool for viewing and filtering log lines. Think of it as a lightweight, interactive log viewer with JSON awareness.

## Features

- **File and pipe input**: Read logs from files or pipe them via stdin
- **Timestamp parsing**: Automatic detection of ISO 8601, syslog, Apache, and other common timestamp formats
- **JSON awareness**: Detects JSON content in log lines and offers pretty-printing with syntax highlighting
- **Pretty-print toggle**: Switch between compact and expanded JSON view, globally or per-line
- **Interactive filtering**: Filter log lines by text pattern or JSON key-value pairs (include or exclude)
- **Filter management**: Reorder, toggle, delete, clear filters with a dedicated dialog
- **Session management**: Save, load, rename, delete filter sessions with auto-save
- **Live tailing**: Follow growing log files in real-time with pause/resume
- **AWS CloudWatch**: Download and list CloudWatch log groups, streams, and events

## Installation

Requires Python 3.13+.

```bash
# Install with uv
uv tool install logsift

# Or install with pip
pip install logsift

# With AWS CloudWatch support
pip install logsift[aws]
```

## Commands

### `logsift inspect` - View log files

```bash
# View a log file (auto-tails by default)
logsift inspect app.log

# Pipe logs from another command
kubectl logs pod-name | logsift inspect

# Disable automatic tailing
logsift inspect --no-tail app.log

# Load a saved filter session
logsift inspect --session my-filters app.log
```

### `logsift cloudwatch` - AWS CloudWatch logs

Requires `logsift[aws]` (boto3).

```bash
# List log groups
logsift cloudwatch groups
logsift cloudwatch groups /aws/lambda/

# List streams for a log group
logsift cloudwatch streams /aws/lambda/my-function

# Download recent logs (last 5 minutes by default)
logsift cloudwatch get /aws/lambda/my-function stream-prefix

# Download with time range
logsift cloudwatch get /aws/lambda/my-function prefix -s 1h -e 30m

# Download and view in TUI
logsift cloudwatch get /aws/lambda/my-function prefix | logsift inspect

# Tail CloudWatch logs live
logsift cloudwatch get /aws/lambda/my-function prefix --tail | logsift inspect
```

Time formats for `--start`/`--end`: `5m`, `1h`, `2d`, `1week`, `14:30`, or ISO 8601. All times in UTC.

AWS credentials via `--profile`, `--aws-region`, `--aws-access-key-id`, etc. or standard environment variables.

## Keybindings

### Navigation

| Key         | Action                    |
| ----------- | ------------------------- |
| Up / Down   | Move between log lines    |
| PgUp / PgDn | Page up / down            |
| Home / End  | Jump to first / last line |
| gg          | Jump to first line        |
| G           | Jump to last line         |

### JSON Display

| Key   | Action                                            |
| ----- | ------------------------------------------------- |
| j     | Toggle pretty-print for ALL JSON lines            |
| Enter | Toggle pretty-print for the current line (sticky) |
| n     | Toggle line numbers                               |

### Filtering

| Key | Action                                          |
| --- | ----------------------------------------------- |
| /   | Filter in (text or key=value)                   |
| \   | Filter out (text or key=value)                  |
| m   | Manage filters (toggle, delete, clear, reorder) |
| 1-9 | Toggle individual filters on/off                |

On JSON lines, `/` and `\` show key-value suggestions.

### Tailing

| Key | Action                            |
| --- | --------------------------------- |
| p   | Pause/resume tailing              |
| G   | Jump to bottom (follow new lines) |

### Sessions

| Key | Action                                              |
| --- | --------------------------------------------------- |
| s   | Session manager (load, save, delete, rename)        |

### General

| Key  | Action           |
| ---- | ---------------- |
| h, ? | Show help screen |
| q    | Quit             |

## Log Format

logsift expects each line to begin with a timestamp, followed by either a JSON object or plain text:

```text
2024-01-15T10:30:00Z {"log_level": "info", "message": "Request processed", "duration_ms": 42}
2024-01-15T10:30:01Z Connection established from 192.168.1.1
Jan 15 10:30:02 myhost syslogd: restart
```

Lines without a recognized timestamp are displayed as-is.

## Sessions

Filter sessions are stored in `~/.config/logsift/sessions/` as TOML files. Filters are auto-saved on every change. Use `--session` to load a session on startup.

## Development

```bash
# Clone the repo
git clone https://github.com/chassing/logsift.git
cd logsift

# Install dependencies
uv sync

# Run from source
uv run logsift inspect sample.log

# Run all checks (lint, format, typecheck, tests)
make test

# Individual targets
make lint        # ruff check
make format      # ruff format
make typecheck   # mypy
make clean       # remove caches
```

## Releasing

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit and push: `git commit -am "Release vX.Y.Z" && git push`
4. Create a GitHub release: `gh release create vX.Y.Z --title "vX.Y.Z" --notes "See CHANGELOG.md"`
5. The `publish.yml` workflow builds and publishes to PyPI automatically

Requires `PYPI_TOKEN` secret in the GitHub repo settings.

## License

MIT
