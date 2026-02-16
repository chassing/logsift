# AGENT.md - Claude Code Instructions for logdelve

## Project Overview

logdelve is a CLI/TUI tool for viewing and filtering log lines. It reads log lines from files or stdin, parses timestamps and JSON content, and presents them in an interactive terminal UI built with Textual.

## Tech Stack

- **Python**: 3.13+
- **Package manager**: uv
- **TUI framework**: Textual (>= 1.0)
- **CLI framework**: typer
- **Data models**: pydantic (>= 2.0)
- **Async I/O**: aiofiles
- **Config storage**: TOML (stdlib `tomllib` for reading, `tomli-w` for writing)
- **Config paths**: platformdirs (XDG Base Directory)
- **Testing**: pytest, pytest-asyncio, textual-dev (snapshot/pilot testing)
- **Linting/Formatting**: ruff
- **Type checking**: mypy (strict mode)

## Project Layout

```text
logdelve/
├── pyproject.toml
├── CHANGELOG.md
├── Makefile
├── docs/
│   └── logo.svg
├── scripts/
│   └── perf_test.py            # performance benchmark
├── src/
│   └── logdelve/
│       ├── __init__.py
│       ├── __main__.py          # python -m logdelve
│       ├── cli.py               # typer CLI entry point
│       ├── app.py               # LogDelveApp (Textual App subclass)
│       ├── models.py            # pydantic models (LogLine, FilterRule, SearchQuery, AppConfig, Session)
│       ├── parser.py            # timestamp + JSON parsing
│       ├── reader.py            # file/stdin/tail reader (async)
│       ├── filters.py           # filter engine (text, regex, JSON key)
│       ├── search.py            # search engine (text, regex)
│       ├── session.py           # session save/load (TOML)
│       ├── config.py            # XDG paths, app config load/save
│       ├── utils.py             # time parsing utilities
│       ├── commands/
│       │   ├── inspect.py       # inspect command
│       │   └── cloudwatch.py    # AWS CloudWatch commands
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── log_view.py      # main scrollable log view (ScrollView + Line API)
│       │   ├── log_line.py      # single log line rendering
│       │   ├── filter_bar.py    # active filter summary bar
│       │   ├── filter_dialog.py # filter input dialog (text/regex/JSON key)
│       │   ├── filter_manage_dialog.py  # filter management dialog
│       │   ├── search_dialog.py # search input dialog (text/regex, case-sensitive)
│       │   ├── session_dialog.py # session management dialog
│       │   ├── theme_dialog.py  # theme selection dialog
│       │   ├── status_bar.py    # bottom status bar
│       │   └── help_screen.py   # help overlay
│       └── styles/
│           └── app.tcss         # Textual CSS
└── tests/
    ├── conftest.py
    ├── test_parser.py
    ├── test_models.py
    ├── test_filters.py
    ├── test_reader.py
    ├── test_session.py
    ├── test_log_line.py
    └── test_cloudwatch.py
```

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
- Keep functions focused - one clear purpose per function.
- Use meaningful variable names. Avoid over-commenting.
- Prefer `pathlib.Path` over string paths.

### Textual

- Use Textual design tokens (`$primary`, `$text`, `$surface`, etc.) instead of hardcoded colors.
- Use `compose()` for building widget trees.
- Use `@work` decorator for background/async tasks.
- Use reactive attributes for state that should trigger UI updates.
- Use Textual's message system for widget-to-app communication.
- The main log display uses `ScrollView` with the Line API (virtual rendering), not `ListView`.
- In dialogs: Enter on checkboxes should submit the form, Space toggles — use `on_key` handler.
- For OptionList selection: use `on_option_list_option_selected` handler, not screen-level Enter binding.

### CLI

- Use typer for all CLI argument/option handling.
- Entry point: `logdelve.cli:main`

### Data Models

- All models inherit from `pydantic.BaseModel`.
- Use `enum.Enum` (or `StrEnum`) for fixed choice fields.
- Validate at model boundaries, not deep inside logic.

### Config & Sessions

- Config directory: `~/.config/logdelve/` (via platformdirs)
- App config: `~/.config/logdelve/config.toml`
- Session files: `~/.config/logdelve/sessions/<name>.toml`
- Use stdlib `tomllib` for reading TOML, `tomli-w` for writing.

### Testing

- Use pytest with `pytest-asyncio` for async tests.
- Use Textual's `app.run_test()` pilot for TUI tests.
- Test files mirror source structure: `test_parser.py` tests `parser.py`.
- Keep tests focused and fast. Mock I/O where needed.

### Tooling

- Format: `uv run ruff format src/ tests/`
- Lint: `uv run ruff check src/ tests/`
- Type check: `uv run mypy src/`
- Test: `uv run pytest`
- All at once: `make test`

## Do's

- Use pydantic models for all structured data (LogLine, FilterRule, Session, SearchQuery, AppConfig).
- Use Textual's built-in widgets and patterns where they fit.
- Use async generators for reading log lines.
- Use Rich renderables (via Textual) for JSON syntax highlighting.
- Handle edge cases: empty files, binary content, malformed JSON, huge lines.
- Write tests for parser, filter engine, search engine, and session management.
- Use `replace_option_prompt_at_index` for in-place OptionList updates to preserve scroll position.

## Don'ts

- Don't use arbitrary dicts where a pydantic model should be used.
- Don't use `ListView` for the main log display (use `ScrollView` + Line API).
- Don't use `argparse` or `click` for CLI (use typer).
- Don't hardcode colors in CSS — use Textual design tokens.
- Don't block the event loop with synchronous I/O.
- Don't add emoji or colors to non-TUI CLI output.
- Don't over-engineer: build what the current phase requires, nothing more.
- Don't use `clear_options()` + rebuild for single-item updates in OptionList (causes scroll reset).
