<p align="center">
  <img src="docs/logo.svg" alt="logdelve" width="480">
</p>

<p align="center">
  <a href="https://pypi.org/project/logdelve/"><img src="https://img.shields.io/pypi/v/logdelve" alt="PyPI"></a>
  <a href="https://pypi.org/project/logdelve/"><img src="https://img.shields.io/pypi/pyversions/logdelve" alt="Python versions"></a>
  <img src="https://img.shields.io/pypi/l/logdelve" alt="License">
  <a href="https://pypi.org/project/logdelve/"><img src="https://img.shields.io/pypi/dm/logdelve" alt="Downloads"></a>
  <br>
  <a href="https://github.com/chassing/logdelve/actions/workflows/ci.yml"><img src="https://github.com/chassing/logdelve/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/chassing/logdelve/actions/workflows/publish.yml"><img src="https://github.com/chassing/logdelve/actions/workflows/publish.yml/badge.svg" alt="Publish"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://mypy-lang.org/"><img src="https://img.shields.io/badge/type--checked-mypy-blue.svg" alt="mypy"></a>
</p>

# logdelve

A terminal UI tool for viewing and filtering log lines. Think of it as a lightweight, interactive log viewer with JSON awareness.

## Features

- **File and pipe input**: Read logs from files or pipe them via stdin
- **Timestamp parsing**: Automatic detection of ISO 8601, syslog, Apache, and other common timestamp formats
- **JSON awareness**: Detects JSON content in log lines and offers pretty-printing with syntax highlighting
- **Pretty-print toggle**: Switch between compact and expanded JSON view, globally or per-line
- **Search**: Forward and backward search with regex and case-sensitive options, match highlighting
- **Interactive filtering**: Filter log lines by text pattern, regex, or JSON key-value pairs (include or exclude)
- **Filter management**: Reorder, toggle, delete, clear filters with a dedicated dialog
- **Session management**: Save, load, rename, delete filter sessions with auto-save
- **Live tailing**: Follow growing log files in real-time with pause/resume
- **Theme support**: Toggle between dark and light themes with persistent preference
- **AWS CloudWatch**: Download and list CloudWatch log groups, streams, and events

## Installation

Requires Python 3.13+.

```bash
# Install with uv
uv tool install logdelve

# Or install with pip
pip install logdelve

# With AWS CloudWatch support
pip install logdelve[aws]
```

## Commands

### `logdelve inspect` - View log files

```bash
# View a log file (auto-tails by default)
logdelve inspect app.log

# Pipe logs from another command
kubectl logs pod-name | logdelve inspect

# Disable automatic tailing
logdelve inspect --no-tail app.log

# Load a saved filter session
logdelve inspect --session my-filters app.log
```

### `logdelve cloudwatch` - AWS CloudWatch logs

Requires `logdelve[aws]` (boto3).

```bash
# List log groups
logdelve cloudwatch groups
logdelve cloudwatch groups /aws/lambda/

# List streams for a log group
logdelve cloudwatch streams /aws/lambda/my-function

# Download recent logs (last 5 minutes by default)
logdelve cloudwatch get /aws/lambda/my-function stream-prefix

# Download with time range
logdelve cloudwatch get /aws/lambda/my-function prefix -s 1h -e 30m

# Download and view in TUI
logdelve cloudwatch get /aws/lambda/my-function prefix | logdelve inspect

# Tail CloudWatch logs live
logdelve cloudwatch get /aws/lambda/my-function prefix --tail | logdelve inspect
```

Time formats for `--start`/`--end`: `5m`, `1h`, `2d`, `1week`, `14:30`, or ISO 8601. All times in UTC.

AWS credentials via `--profile`, `--aws-region`, `--aws-access-key-id`, etc. or standard environment variables.

## Keybindings

### Search

| Key | Action                                                |
| --- | ----------------------------------------------------- |
| /   | Search forward (opens dialog with regex/case options) |
| ?   | Search backward                                       |
| n   | Next match                                            |
| N   | Previous match                                        |

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
| #     | Toggle line numbers                               |

### Filtering

| Key | Action                                          |
| --- | ----------------------------------------------- |
| f   | Filter in (text, key=value, or regex)           |
| F   | Filter out (text, key=value, or regex)          |
| m   | Manage filters (toggle, delete, clear, reorder) |
| 1-9 | Toggle individual filters on/off                |

On JSON lines, `f` and `F` show key-value suggestions.

### Tailing

| Key | Action                            |
| --- | --------------------------------- |
| p   | Pause/resume tailing              |
| G   | Jump to bottom (follow new lines) |

### Sessions

| Key | Action                                       |
| --- | -------------------------------------------- |
| s   | Session manager (load, save, delete, rename) |

### General

| Key | Action                  |
| --- | ----------------------- |
| t   | Toggle dark/light theme |
| h   | Show help screen        |
| q   | Quit                    |

## Log Format

logdelve expects each line to begin with a timestamp, followed by either a JSON object or plain text:

```text
2024-01-15T10:30:00Z {"log_level": "info", "message": "Request processed", "duration_ms": 42}
2024-01-15T10:30:01Z Connection established from 192.168.1.1
Jan 15 10:30:02 myhost syslogd: restart
```

Lines without a recognized timestamp are displayed as-is.

## Sessions

Filter sessions are stored in `~/.config/logdelve/sessions/` as TOML files. Filters are auto-saved on every change. Use `--session` to load a session on startup.

## Configuration

Theme preference is stored in `~/.config/logdelve/config.toml`. Toggle with `t` during use.

## Development

```bash
# Clone the repo
git clone https://github.com/chassing/logdelve.git
cd logdelve

# Install dependencies
uv sync

# Run from source
uv run logdelve inspect sample.log

# Run all checks (lint, format, typecheck, tests)
make test

# Individual targets
make lint        # ruff check
make format      # ruff format
make typecheck   # mypy
make clean       # remove caches

# Performance benchmark
uv run python scripts/perf_test.py
```

## Contributing

1. Fork the repo and create a feature branch
2. Install dependencies: `uv sync`
3. Make your changes
4. Run checks: `make test` (runs lint, format check, type check, and tests)
5. Submit a pull request

### Code style

- Python 3.13+ with type hints (strict mypy)
- Formatting and linting via [Ruff](https://github.com/astral-sh/ruff)
- Pydantic models for data structures
- Textual framework for the TUI

## Releasing

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit and push: `git commit -am "Release vX.Y.Z" && git push`
4. Create a GitHub release: `gh release create vX.Y.Z --title "vX.Y.Z" --notes "See CHANGELOG.md"`
5. The `publish.yml` workflow builds and publishes to PyPI automatically

Requires `PYPI_TOKEN` secret in the GitHub repo settings.

## License

MIT
