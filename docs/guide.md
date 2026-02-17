# logdelve User Guide

Complete documentation for all logdelve features. For a quick overview, see the [README](../README.md).

## Table of Contents

- [Getting Started](#getting-started)
- [UI Layout](#ui-layout)
- [Log Level Detection](#log-level-detection)
- [Component Detection](#component-detection)
- [Navigation & Display](#navigation--display)
- [Search](#search)
- [Filtering](#filtering)
- [Filter Management](#filter-management)
- [Message Analysis](#message-analysis)
- [Anomaly Detection](#anomaly-detection)
- [Sessions](#sessions)
- [Live Tailing](#live-tailing)
- [AWS CloudWatch](#aws-cloudwatch)
- [Time Parsing](#time-parsing)
- [Themes](#themes)
- [Keyboard Reference](#keyboard-reference)

---

## Getting Started

```bash
# Install with uv (recommended)
uv tool install logdelve

# No uv? Install both in one step:
curl -LsSf uvx.sh/logdelve/install.sh | sh

# Alternative: pip
pip install logdelve

# With AWS CloudWatch support
uv tool install logdelve[aws]
```

```bash
# View a log file
logdelve inspect app.log

# Pipe from kubectl
kubectl logs deploy/my-app --since=1h | logdelve inspect

# Download and view CloudWatch logs
logdelve cloudwatch get /aws/ecs/my-service prefix -s 1h | logdelve inspect
```

---

## UI Layout

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ f filter-in  F filter-out  x filters off  │  a analyze  │  / search         │
├──┬──┬────┬──────────┬───────────────────────────────────────────────────────┤
│▌ │E │·1  │ 10:30:01 │ {"event": "Connection refused", "host": "10.0.1.5"}.  │
│  │I │·2  │ 10:30:02 │ {"event": "Request processed", "status": 200}      .  │
│  │I │·1  │ 10:30:03 │ {"event": "Health check passed"}                   .  │
│▌ │E │·1  │ 10:30:04 │ {"event": "Timeout after 5000ms", "path": "/api"}  .  │
│  │D │·3  │ 10:30:05 │ {"event": "Cache hit", "key": "user:42"}           .  │
├──┴──┴────┴──────────┴───────────────────────────────────────────────────────┤
│ 500 lines  E:12 W:3  A:2                                      app.log       │
├─────────────────────────────────────────────────────────────────────────────┤
│ s Sessions  q Quit  h Help                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

From left to right, each log line shows:

| Column                | Description                                                                     |
| --------------------- | ------------------------------------------------------------------------------- |
| `▌`                   | Anomaly marker — red indicator for lines with patterns not seen in the baseline |
| `E` / `I` / `W` / `D` | Log level badge — single character, line background colored by severity         |
| `·1` / `·2`           | Component tag — color-coded number identifying the source pod/service           |
| `10:30:01`            | Compact timestamp — HH:MM:SS instead of full ISO                                |
| Content               | The actual log message (JSON or plain text)                                     |

The three bars:

- **Toolbar** (top): Always-visible shortcuts and active filter/search/anomaly status
- **Status bar**: Line counts, level counts (E:n W:n), anomaly count (A:n), file name
- **Footer**: Session management, quit, help

---

## Log Level Detection

logdelve automatically detects log levels from two sources:

**JSON fields** (checked in order): `log_level`, `level`, `severity`, `loglevel`, `lvl`

```json
{"level": "error", "event": "Connection failed"}
{"severity": "warning", "msg": "Slow query"}
```

**Text patterns**: `[ERROR]`, `ERROR`, `level=error`

```text
[ERROR] Connection refused
2024-01-15 ERROR Database timeout
level=warn msg="retrying"
```

Levels are normalized: `err`/`error`/`ERROR` → ERROR, `warning`/`warn` → WARN, `critical`/`fatal`/`panic` → FATAL.

### Level display

Each line gets a background color based on severity:

- **FATAL/ERROR**: dark red background
- **WARN**: dark yellow/brown background
- **INFO**: no special background
- **DEBUG**: dim text

### Level filter

Press `e` to cycle through minimum log level:

```
ALL → ERROR (only errors) → WARN+ → INFO+ → ALL
```

The status bar shows `≥ERROR` when a level filter is active. The toolbar shows `e ≥ERROR` in yellow.

### Level counts

The status bar always shows: `E:12 W:3` — count of error and warning lines across all (unfiltered) lines.

---

## Component Detection

logdelve identifies the source component/service from log line prefixes or JSON fields.

### Supported formats

**CloudWatch / Kubernetes bracket prefix**:

```text
[my-pod-abc123] 2024-01-15T10:30:00Z {"event": "start"}
```

**Docker Compose prefix**:

```text
web-service  | 2024-01-15T10:30:00Z Request processed
```

**JSON fields** (checked in order): `service`, `component`, `app`, `source`, `container`, `pod`

```json
{"service": "api-gateway", "event": "request"}
```

### Component display

Press `c` to cycle through display modes:

- **tag** (default): Color-coded `·1`, `·2`, `·3` — compact, 3 characters per component
- **full**: `[full-pod-name]` with the same color
- **off**: No component display

Each unique component gets a deterministic color from a palette of 8 distinct colors.

### Component prefix stripping

When a component prefix like `[pod-name]` is detected, it's stripped before timestamp parsing. This means CloudWatch output with `[stream-name]` prefixes works correctly:

```bash
logdelve cloudwatch get /log/group prefix | logdelve inspect
# Each line: [stream-name] 2024-01-15T10:30:00Z {"event": "..."}
# → component = stream-name, timestamp parsed correctly
```

---

## Navigation & Display

### Navigation keys

| Key         | Action                               |
| ----------- | ------------------------------------ |
| Up / Down   | Move between log lines               |
| PgUp / PgDn | Page up / down                       |
| Home / End  | Jump to first / last line            |
| `gg`        | Jump to first line (press `g` twice) |
| `G`         | Jump to last line                    |

### JSON display

| Key   | Action                                                 |
| ----- | ------------------------------------------------------ |
| `j`   | Toggle pretty-print for ALL JSON lines (global)        |
| Enter | Toggle pretty-print for the current line only (sticky) |
| `#`   | Toggle line number display                             |

When a JSON line is expanded, it shows syntax-highlighted, indented JSON:

```json
{
  "event": "Request processed",
  "status": 200,
  "duration_ms": 42,
  "user": "admin"
}
```

---

## Search

![Search demo](screenshots/search.gif)

Press `/` for forward search, `?` for backward search.

### Search dialog

The search dialog offers:

- **Pattern input**: text or regex pattern
- **Case sensitive**: toggle with Space
- **Regex**: toggle with Space

Press Enter to search, Escape to cancel.

### Search navigation

| Key | Action                              |
| --- | ----------------------------------- |
| `n` | Next match (in search direction)    |
| `N` | Previous match (opposite direction) |

Matches are highlighted in the log view. The current match has a brighter highlight. The status bar shows `[3/42]` — current match position and total count.

### Search persistence

When you press `/` or `?` again, the dialog is pre-filled with your last search (pattern, case-sensitive, and regex settings).

The toolbar shows the active search text: `/ connection…` in cyan, with `n/N next/prev` shortcut hints.

---

## Filtering

![Filter demo](screenshots/filter.gif)

### Filter in / Filter out

| Key | Action                               |
| --- | ------------------------------------ |
| `f` | Filter in — show only matching lines |
| `F` | Filter out — hide matching lines     |

The filter dialog supports:

- **Text pattern**: simple substring match
- **key=value**: JSON key-value filter (auto-detected when pattern contains `=`)
- **Regex**: toggle the regex checkbox
- **Case sensitive**: toggle the case-sensitive checkbox

### JSON key suggestions

On JSON lines, pressing `f` or `F` shows clickable key-value suggestions from the current line's JSON data. Select one to create a JSON key filter.

### Filter logic

- Multiple **include** filters use OR logic (match any)
- Multiple **exclude** filters use AND logic (excluded if matches any)
- No include filters = all lines are candidates

### Level filter

Press `e` to cycle: ALL → ERROR → WARN → INFO → ALL. This filters by the detected log level.

### Anomaly filter

Press `!` to toggle showing only anomalous lines (requires `--baseline`). See [Anomaly Detection](#anomaly-detection).

### Suspend / Resume

Press `x` to suspend ALL active filters (rules, level, anomaly) at once. Press `x` again to restore them exactly as they were.

The cursor stays on the same log line when toggling filters — the view centers on the current line.

---

## Filter Management

Press `m` to open the filter manager dialog.

### Available actions

| Key           | Action                     |
| ------------- | -------------------------- |
| Space / Enter | Toggle filter on/off       |
| `e`           | Edit filter pattern inline |
| `d`           | Delete filter              |
| `c`           | Clear all filters          |
| `k` / `i`     | Move filter up / down      |
| Escape        | Close (apply changes)      |

Filters show their type (`+` include, `-` exclude), status (ON/OFF), pattern, and indicators for regex (`/.../`) and case-sensitive (`[Aa]`).

### Quick toggle

Press `1`-`9` to toggle individual filters on/off without opening the manager.

---

## Message Analysis

![Analyze demo](screenshots/analyze.gif)

Press `a` to open the analysis dialog. It groups log lines by message pattern and shows field value distributions.

### Messages mode (default)

Groups log lines by their event/message template. Variable parts (IPs, UUIDs, timestamps, numbers) are replaced with tokens:

```text
 I   1628x  Start GET <PATH>
 I    860x  Done GET <PATH>
 E    145x  Connection refused to <IP>:<NUM>
 W     89x  Retry attempt <NUM> for <STR>
```

Press Enter on a group to create a filter that matches those lines.

### Fields mode

Press `m` to switch to field analysis. Shows JSON field value distributions:

```text
    49x  applied_count: 0
   471x  applied_count: >0
    45x  http_status: 500
  3000x  http_status: 200
```

- **String/bool fields**: grouped by exact value
- **Integer fields**: grouped as `=0` vs `>0`
- **Float fields**: skipped (continuous values)
- **High-cardinality fields** (>20 values): skipped

### Controls

| Key    | Action                                                          |
| ------ | --------------------------------------------------------------- |
| `m`    | Toggle mode (messages ↔ fields)                                 |
| `s`    | Cycle sort (count ↔ level for messages, count ↔ key for fields) |
| `r`    | Reverse sort order                                              |
| Enter  | Create filter from selected group                               |
| Escape | Close                                                           |

---

## Anomaly Detection

![Anomaly demo](screenshots/hero-anomaly.gif)

Compare current logs against a known-good baseline to find what changed.

### Usage

```bash
# Create baseline from a good day
logdelve cloudwatch get /log/group prefix -s "yesterday 6:00" -e "yesterday 18:00" > baseline.log

# Compare current logs against baseline
logdelve inspect --baseline baseline.log current.log

# Or pipe current logs
logdelve cloudwatch get /log/group prefix -s 1h | logdelve inspect --baseline baseline.log
```

### How it works

1. logdelve extracts message templates from both baseline and current logs
2. Templates that appear in current but NOT in baseline are marked as **anomalies** (score 1.0)
3. Templates with significantly increased frequency (>5x) are marked with score 0.5
4. The anomaly filter is **automatically enabled** when anomalies are found

### Visual indicators

- **Red `▌` marker**: left edge of anomalous lines
- **Status bar**: `A:23` shows anomaly count
- **Toolbar**: `! 23 anomalies` with toggle hint

### Keyboard

| Key | Action                                         |
| --- | ---------------------------------------------- |
| `!` | Toggle anomaly-only filter                     |
| `x` | Suspend/resume all filters (including anomaly) |

When you press `!` to toggle off the anomaly filter, the cursor stays on the same line so you can see the surrounding context.

---

## Sessions

Press `s` to open the session manager.

Filter sessions are saved automatically on every filter change. They persist as TOML files in `~/.config/logdelve/sessions/`.

### Session manager

| Key           | Action                              |
| ------------- | ----------------------------------- |
| Enter         | Load selected session               |
| `d`           | Delete session                      |
| `r`           | Rename session                      |
| Input + Enter | Save current filters as new session |
| Escape        | Close                               |

### CLI

```bash
# Load a session on startup
logdelve inspect --session my-filters app.log
```

---

## Live Tailing

When reading from a file, logdelve loads the entire file. Use `--tail` to follow new lines (like `tail -f`).
Pipe input is always tailed automatically.

```bash
# Read file once (default)
logdelve inspect app.log

# Tail a growing log file
logdelve inspect --tail app.log

# Pipe: auto-tail
kubectl logs -f deploy/my-app | logdelve inspect
```

### Controls

| Key | Action                            |
| --- | --------------------------------- |
| `p` | Pause/resume tailing              |
| `G` | Jump to bottom (follow new lines) |

When paused, the status bar shows the count of buffered new lines. Pressing `p` again flushes the buffer and resumes.

---

## AWS CloudWatch

Requires `uv tool install logdelve[aws]`.

### Commands

```bash
# List log groups
logdelve cloudwatch groups
logdelve cloudwatch groups /aws/ecs/

# List streams
logdelve cloudwatch streams /aws/ecs/my-service

# Download logs
logdelve cloudwatch get /aws/ecs/my-service stream-prefix

# Download with time range
logdelve cloudwatch get /aws/ecs/my-service prefix -s "yesterday 8am" -e "yesterday 18:00"

# Live tail
logdelve cloudwatch get /aws/ecs/my-service prefix --tail | logdelve inspect
```

### Stream names

Each downloaded line includes the CloudWatch stream name as a `[stream-name]` prefix. logdelve uses this as the component name for color-coded tags.

### AWS credentials

Use any standard AWS authentication:

```bash
# AWS profile
logdelve cloudwatch get /log/group prefix --profile my-profile

# Region
logdelve cloudwatch get /log/group prefix --aws-region eu-west-1

# Or standard environment variables
export AWS_PROFILE=my-profile
export AWS_DEFAULT_REGION=eu-west-1
```

---

## Time Parsing

The `--start` and `--end` options for CloudWatch accept flexible time formats via [dateparser](https://dateparser.readthedocs.io/):

| Format             | Example                                  |
| ------------------ | ---------------------------------------- |
| Shorthand relative | `5m`, `1h`, `2d`, `1week`                |
| Natural language   | `yesterday`, `2 days ago`, `friday`      |
| Time with context  | `yesterday at 8am`, `friday 14:30`       |
| Date               | `Feb 13 2026`, `2026-02-13`              |
| ISO 8601           | `2026-02-13T07:58:00Z`                   |
| Flexible           | `2026-02-13 7:58` (single-digit hour OK) |

All times are interpreted as UTC.

---

## Themes

Press `t` to open the theme selection dialog. All built-in Textual themes are available.

The selected theme is persisted in `~/.config/logdelve/config.toml` and restored on next launch.

---

## Keyboard Reference

### Global

| Key    | Action              |
| ------ | ------------------- |
| `h`    | Show help screen    |
| `t`    | Select theme        |
| `s`    | Session manager     |
| `q`    | Quit                |
| Ctrl+S | Save SVG screenshot |

### Navigation

| Key         | Action             |
| ----------- | ------------------ |
| Up / Down   | Move between lines |
| PgUp / PgDn | Page up / down     |
| Home / End  | First / last line  |
| `gg`        | First line         |
| `G`         | Last line          |

### Display

| Key   | Action                                     |
| ----- | ------------------------------------------ |
| `j`   | Toggle JSON pretty-print (all lines)       |
| Enter | Toggle JSON pretty-print (current line)    |
| `#`   | Toggle line numbers                        |
| `c`   | Cycle component display (tag / full / off) |

### Search

| Key | Action          |
| --- | --------------- |
| `/` | Search forward  |
| `?` | Search backward |
| `n` | Next match      |
| `N` | Previous match  |

### Filtering

| Key     | Action                       |
| ------- | ---------------------------- |
| `f`     | Filter in                    |
| `F`     | Filter out                   |
| `e`     | Cycle log level filter       |
| `!`     | Toggle anomaly filter        |
| `x`     | Suspend / resume all filters |
| `m`     | Manage filters               |
| `1`-`9` | Toggle individual filter     |

### Analysis

| Key | Action                       |
| --- | ---------------------------- |
| `a` | Open message analysis dialog |

### Tailing

| Key | Action         |
| --- | -------------- |
| `p` | Pause / resume |
| `G` | Jump to bottom |
