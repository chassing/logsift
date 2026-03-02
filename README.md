<p align="center">
  <img src="https://raw.githubusercontent.com/chassing/logdelve/refs/heads/main/docs/logo.svg" alt="logdelve" width="480">
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

A terminal UI tool for viewing, filtering, and analyzing log lines. Built for outage investigation — find the needle in the haystack across thousands of log lines from multi-component applications.

<img src="docs/screenshots/hero.gif" alt="logdelve" width="1024">

## Features

- **[Log level detection](docs/guide.md#log-level-detection)**: Automatic extraction from JSON fields and text patterns, color-coded line backgrounds
- **[Multiple file input](docs/guide.md#multiple-files)**: Merge multiple log files chronologically with per-file component tagging
- **[Component detection](docs/guide.md#component-detection)**: Kubernetes pods, Docker Compose services, JSON fields — with color-coded tags
- **[Anomaly detection](docs/guide.md#anomaly-detection)**: Baseline comparison to find log patterns that are new or changed (`--baseline`)
- **[Message analysis](docs/guide.md#message-analysis)**: Group log messages by event pattern, analyze JSON field value distributions
- **[Search](docs/guide.md#search)**: Multi-pattern search with up to 10 simultaneous patterns, each highlighted in a distinct color — with per-pattern n/N navigation control
- **[Interactive filtering](docs/guide.md#filtering)**: Filter by text, regex, JSON key-value, component, or log level — tabbed dialog with multi-select
- **[Filter management](docs/guide.md#filter-management)**: Reorder, toggle, edit, delete, suspend/resume all filters with cursor preservation
- **[Bookmarks & Annotations](docs/guide.md#bookmarks--annotations)**: Mark lines, attach notes, navigate between bookmarks, persisted in sessions
- **[Sessions](docs/guide.md#sessions)**: Save, load, rename, delete named sessions — persists filters, bookmarks, and search patterns with auto-save
- **[Streaming large files](docs/guide.md#large-files)**: Chunked background loading for files up to 2-3GB with instant startup and progress display
- **[Live tailing](docs/guide.md#live-tailing)**: Follow growing log files in real-time with pause/resume
- **[Flexible time parsing](docs/guide.md#time-parsing)**: Natural language dates ("yesterday at 8am", "friday", "2 days ago")
- **[Themes](docs/guide.md#themes)**: Choose from all built-in Textual themes with persistent preference
- **[Configurable Keybindings](docs/guide.md#configurable-keybindings)**: Remap any keybinding via `config.toml` with validation, symbol aliases, and dynamic help screen
- **[AWS CloudWatch](docs/guide.md#aws-cloudwatch)**: Download and list CloudWatch log groups, streams, and events with stream names

📖 **[Full User Guide](docs/guide.md)** — detailed documentation for all features with examples

🎬 **[Demo Videos](docs/demos/index.md)** — step-by-step workflow walkthroughs: [You Just Got Paged](docs/demos/you-just-got-paged.md) · [What Changed?](docs/demos/what-changed.md) · [Post-Mortem](docs/demos/post-mortem.md)

## Installation

Requires Python 3.13+.

```bash
# Recommended: install with uv
uv tool install logdelve

# With AWS CloudWatch support
uv tool install logdelve[aws]

# No uv? Install it first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Alternative: pip
pip install logdelve
```

## Quick Start

```bash
# View a log file
logdelve inspect app.log

# Merge multiple log files chronologically
logdelve inspect api.log worker.log scheduler.log

# Pipe logs from kubectl
kubectl logs deploy/my-app --since=1h | logdelve inspect

# Download and view CloudWatch logs
logdelve cloudwatch get /aws/ecs/my-service prefix -s 1h | logdelve inspect

# Filter by time range
logdelve inspect --start "14:30" --end "14:35" app.log

# Export filtered lines to file
logdelve inspect --session my-session --output export.log app.log

# Compare against a known-good baseline
logdelve inspect --baseline yesterday.log today.log
```

## UI Layout

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ f filter-in  F filter-out  x filters off  │  a analyze  │  / search         │ ← Toolbar
├──┬──┬────┬──────────┬───────────────────────────────────────────────────────┤
│▌ │E │·1  │ 10:30:01 │ {"event": "Connection refused", "host": "10.0.1.5"}   │ ← Anomaly + Level + Component + Time + Content
│  │I │·2  │ 10:30:02 │ {"event": "Request processed", "status": 200}         │
│  │I │·1  │ 10:30:03 │ {"event": "Health check passed"}                      │
│▌ │E │·1  │ 10:30:04 │ {"event": "Timeout after 5000ms", "path": "/api"}     │ ← Error background
│  │D │·3  │ 10:30:05 │ {"event": "Cache hit", "key": "user:42"}              │ ← Debug (dim)
│  │I │·2  │ 10:30:06 │ {"event": "Request processed", "status": 200}         │
├──┴──┴────┴──────────┴───────────────────────────────────────────────────────┤
│ 500 lines  E:12 W:3  A:2                                      app.log       │ ← Status bar
├─────────────────────────────────────────────────────────────────────────────┤
│ s Sessions  q Quit  h Help                                                  │ ← Footer
└─────────────────────────────────────────────────────────────────────────────┘
 ▲  ▲   ▲       ▲                            ▲
 │  │   │       │                            │
 │  │   │       │                            └─ Content (JSON or text)
 │  │   │       └─ Compact timestamp (HH:MM:SS)
 │  │   └─ Component tag (color-coded, c to cycle: tag/full/off)
 │  └─ Log level badge (E=error, W=warn, I=info, D=debug)
 └─ Anomaly marker (▌ = new pattern not in baseline)
```

## Use Cases

### Outage Investigation with CloudWatch

```bash
# 1. Download baseline (yesterday, everything was fine)
logdelve cloudwatch get /aws/ecs/my-service "" \
  -s "yesterday 6:00" -e "yesterday 8:00" > baseline.log

# 2. Download current logs (outage happening now)
logdelve cloudwatch get /aws/ecs/my-service "" -s 1h > current.log

# 3. Compare — automatically shows only anomalous lines
logdelve inspect --baseline baseline.log current.log

# 4. In the TUI:
#    - Anomaly filter is auto-enabled (! to toggle off)
#    - Press 'a' to analyze message groups
#    - Press 'e' to filter by ERROR level
#    - Press 'x' to suspend all filters and see context around a line
```

### CloudWatch Log Download

```bash
# Flexible time formats
logdelve cloudwatch get /aws/ecs/my-service prefix -s "2 days ago"
logdelve cloudwatch get /aws/ecs/my-service prefix -s "friday" -e "saturday"
logdelve cloudwatch get /aws/ecs/my-service prefix -s "yesterday at 8am"
logdelve cloudwatch get /aws/ecs/my-service prefix -s 1h          # shorthand
logdelve cloudwatch get /aws/ecs/my-service prefix -s "Feb 13 2026 7:58"

# List available log groups and streams
logdelve cloudwatch groups /aws/ecs/
logdelve cloudwatch streams /aws/ecs/my-service

# Live tail CloudWatch logs
logdelve cloudwatch get /aws/ecs/my-service prefix --tail | logdelve inspect

# Each line includes [stream-name] prefix for component detection
```

### Analyzing Multi-Component Logs

```bash
# Pipe mixed logs from multiple pods
kubectl logs -l app=my-service --prefix --since=30m | logdelve inspect

# In the TUI:
#    - Component tags (·1, ·2) identify pods — press 'c' to see full names
#    - Press 'f'/'F' and switch to Component tab to filter by pod
#    - Press 'e' to filter by log level (ERROR → WARN → INFO)
#    - Press 'a' then 'm' to switch to field analysis mode
#    - Select a field value to filter (e.g., http_status: 500)
```

## Keybindings

| Key       | Action                   |     | Key       | Action                    |
| --------- | ------------------------ | --- | --------- | ------------------------- |
| `f` / `F` | Filter in / out          |     | `/` / `?` | Search forward / backward |
| `e`       | Cycle level filter       |     | `n` / `N` | Next / previous match     |
| `Ctrl+D`  | Clear all search patterns |     |           |                           |
| `!`       | Toggle anomaly filter    |     | `j`       | Toggle JSON pretty-print  |
| `x`       | Suspend / resume filters |     | `c`       | Cycle component display   |
| `m`       | Manage filters           |     | `a`       | Analyze messages          |
| `1`-`9`   | Toggle individual filter |     | `s`       | Session manager           |
| `p`       | Pause / resume tailing   |     | `h`       | Help screen               |
| `r`       | Show related (trace ID)  |     | `:`       | Go to line number         |
| `b` / `B` | Bookmark / list          |     | `A`       | Annotate bookmark         |
| `[` / `]` | Prev / next bookmark     |     | `@`       | Jump to timestamp         |
| `Ctrl+E`  | Export filtered lines    |     | `t`       | Select theme              |

📖 [Full keyboard reference](docs/guide.md#keyboard-reference) in the User Guide

## Configurable Keybindings

Remap any keybinding by adding a `[keybindings]` section to your config file (Linux: `~/.config/logdelve/config.toml`, macOS: `~/Library/Application Support/logdelve/config.toml`):

```toml
[keybindings]
search_forward = "ctrl+f"
quit = "Q"
filter_in = "i"
```

Overridden bindings replace defaults; unspecified bindings keep their default keys. Both app-level and log-view-level bindings can be overridden from this single flat section.

Common symbol aliases are accepted: `/` for `slash`, `?` for `question_mark`, `!` for `exclamation_mark`, `#` for `hash`, `@` for `at`, `:` for `colon`, `[` / `]` for bracket keys.

**Validation:** Invalid configs (duplicate keys, unknown actions, bad key format) are caught at startup with a clear error message before the TUI launches.

**Print defaults:** Run `logdelve keybindings` to print a valid TOML template with all configurable actions and their default keys.

📖 [Full configuration guide](docs/guide.md#configurable-keybindings) in the User Guide

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

See `AGENT.md` for the full release checklist.

```bash
# After updating version + changelog + README:
git push
gh release create vX.Y.Z --title "vX.Y.Z" --notes "See CHANGELOG.md"
```

The `publish.yml` workflow builds and publishes to PyPI automatically. Requires `PYPI_TOKEN` secret in the GitHub repo settings.

## Alternatives

- **[lnav](https://lnav.org/)** — Feature-rich log file navigator with SQL queries, automatic format detection, and timeline view. C++-based.
- **[tailspin](https://github.com/bensadeh/tailspin)** — Log file highlighter with automatic pattern detection. Focused on making logs readable, no filtering or analysis.
- **[GoAccess](https://goaccess.io/)** — Real-time web log analyzer with terminal and HTML dashboards. Specialized for access logs (Apache, Nginx), not general-purpose.
- **[Textualog](https://github.com/rhuygen/textualog)** — Textual-based log viewer. Minimal feature set, no filtering or anomaly detection.
- **[jq](https://jqlang.github.io/jq/)** — JSON processor. Powerful for one-off queries but no TUI, no live tailing, no session management.

## License

MIT
