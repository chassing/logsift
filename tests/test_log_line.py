"""Tests for log line rendering."""

from __future__ import annotations

from rich.style import Style

from logdelve.models import ContentType, LogLine
from logdelve.widgets.log_line import get_line_height, render_json_expanded_row


def _make_json_line(line_number: int = 1, json_str: str = '{"key": "value"}') -> LogLine:
    import json

    raw = f"2024-01-15T10:30:00Z {json_str}"
    return LogLine(
        line_number=line_number,
        raw=raw,
        timestamp=None,
        content_type=ContentType.JSON,
        content_offset=len("2024-01-15T10:30:00Z "),
        parsed_json=json.loads(json_str),
    )


def _make_text_line(line_number: int = 1) -> LogLine:
    return LogLine(
        line_number=line_number,
        raw="2024-01-15T10:30:00Z plain text",
        timestamp=None,
        content_type=ContentType.TEXT,
        content_offset=len("2024-01-15T10:30:00Z "),
    )


class TestGetLineHeight:
    def test_text_line_compact(self) -> None:
        line = _make_text_line()
        assert get_line_height(line, expanded=False) == 1

    def test_text_line_expanded(self) -> None:
        line = _make_text_line()
        assert get_line_height(line, expanded=True) == 2

    def test_json_line_collapsed(self) -> None:
        line = _make_json_line()
        assert get_line_height(line, expanded=False) == 1

    def test_json_line_expanded(self) -> None:
        line = _make_json_line(json_str='{"a": 1, "b": 2}')
        height = get_line_height(line, expanded=True)
        assert height > 1

    def test_json_line_no_parsed_json(self) -> None:
        line = LogLine(
            line_number=1,
            raw="{}",
            content_type=ContentType.JSON,
            parsed_json=None,
        )
        # JSON without parsed data falls through to text expand (height 2)
        assert get_line_height(line, expanded=True) == 2

    def test_nested_json_height(self) -> None:
        line = _make_json_line(json_str='{"a": {"b": {"c": 1}}, "d": [1, 2]}')
        height = get_line_height(line, expanded=True)
        assert height >= 5


class TestRenderJsonExpandedRow:
    def test_renders_first_row_with_line_number(self) -> None:
        line = _make_json_line(json_str='{"key": "val"}')
        strip = render_json_expanded_row(line, 0, Style(dim=True), Style(color="cyan"), Style())
        assert strip.text.lstrip().startswith("1")

    def test_renders_continuation_row(self) -> None:
        line = _make_json_line(json_str='{"a": 1, "b": 2}')
        height = get_line_height(line, expanded=True)
        assert height > 1
        strip = render_json_expanded_row(line, 1, Style(dim=True), Style(color="cyan"), Style())
        assert strip.text.strip() != ""

    def test_no_parsed_json_returns_compact(self) -> None:
        line = LogLine(
            line_number=1,
            raw="{}",
            content_type=ContentType.JSON,
            parsed_json=None,
        )
        strip = render_json_expanded_row(line, 0, Style(dim=True), Style(color="cyan"), Style())
        assert strip.text is not None
