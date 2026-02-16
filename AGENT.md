# AGENT.md - Claude Code Instructions for logsift

## Project Overview

logsift is a CLI/TUI tool for viewing and filtering log lines. It reads log lines from files or stdin, parses timestamps and JSON content, and presents them in an interactive terminal UI built with Textual.

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
logsift/
├── pyproject.toml
├── src/
│   └── logsift/
│       ├── __init__.py
│       ├── __main__.py        # python -m logsift
│       ├── cli.py             # typer CLI
│       ├── app.py             # Textual App subclass
│       ├── models.py          # pydantic models
│       ├── parser.py          # timestamp + JSON parsing
│       ├── reader.py          # file/stdin/tail reader (async)
│       ├── filters.py         # filter engine
│       ├── session.py         # session save/load
│       ├── config.py          # XDG paths, app config
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── log_view.py    # main scrollable log view
│       │   ├── log_line.py    # single log line rendering
│       │   ├── filter_bar.py  # active filter display
│       │   ├── status_bar.py  # bottom status bar
│       │   └── filter_dialog.py
│       └── styles/
│           └── app.tcss       # Textual CSS
└── tests/
    ├── conftest.py
    ├── test_parser.py
    ├── test_models.py
    ├── test_filters.py
    ├── test_reader.py
    ├── test_session.py
    └── test_app.py
```

## Coding Conventions

### General

- NO arbitrary dictionaries. Always use pydantic models for structured data.
- Use type hints everywhere. mypy strict mode must pass.
- Keep functions focused - one clear purpose per function.
- Use meaningful variable names. Avoid over-commenting.
- Prefer `pathlib.Path` over string paths.

### Textual

- All CSS goes in `.tcss` files under `src/logsift/styles/`, not inline.
- Use `compose()` for building widget trees.
- Use `@work` decorator for background/async tasks.
- Use reactive attributes for state that should trigger UI updates.
- Use Textual's message system for widget-to-app communication.
- The main log display uses `ScrollView` with the Line API (virtual rendering), not `ListView`.

### CLI

- Use typer for all CLI argument/option handling.
- Entry point: `logsift.cli:main`

### Data Models

- All models inherit from `pydantic.BaseModel`.
- Use `enum.Enum` (or `StrEnum`) for fixed choice fields.
- Validate at model boundaries, not deep inside logic.

### Config & Sessions

- Config directory: `~/.config/logsift/` (via platformdirs)
- Session files: `~/.config/logsift/sessions/<name>.toml`
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

## Do's

- Use pydantic models for all structured data (LogLine, FilterRule, Session).
- Use Textual's built-in widgets and patterns where they fit.
- Use async generators for reading log lines.
- Use Rich renderables (via Textual) for JSON syntax highlighting.
- Handle edge cases: empty files, binary content, malformed JSON, huge lines.
- Write tests for parser, filter engine, and session management.

## Don'ts

- Don't use arbitrary dicts where a pydantic model should be used.
- Don't use `ListView` for the main log display (use `ScrollView` + Line API).
- Don't use `argparse` or `click` for CLI (use typer).
- Don't inline CSS in Python code (use `.tcss` files).
- Don't block the event loop with synchronous I/O.
- Don't add emoji or colors to non-TUI CLI output.
- Don't over-engineer: build what the current phase requires, nothing more.
