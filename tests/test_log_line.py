"""Tests for log line rendering."""

from __future__ import annotations

from rich.style import Style

from logdelve.models import ContentType, LogLine
from logdelve.widgets.log_line import (
    _json_continuation_indent,
    _json_line_wrap_count,
    _text_wrap_count,
    _wrap_json_line,
    _wrap_text,
    get_line_height,
    render_expanded_content_row,
)


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


def _make_text_line(line_number: int = 1, raw: str = "2024-01-15T10:30:00Z plain text") -> LogLine:
    return LogLine(
        line_number=line_number,
        raw=raw,
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

    def test_expanded_height_includes_metadata_row(self) -> None:
        """Expanded height = metadata row + content rows."""
        line = _make_json_line(json_str='{"a": 1}')
        height = get_line_height(line, expanded=True, viewport_width=200)
        json_lines = len(line.json_lines)
        assert height == json_lines + 1  # +1 for metadata row

    def test_viewport_width_affects_height(self) -> None:
        """Narrow viewport causes wrapping, increasing height."""
        line = _make_text_line(raw="A" * 100)
        height_wide = get_line_height(line, expanded=True, viewport_width=200)
        height_narrow = get_line_height(line, expanded=True, viewport_width=30)
        assert height_narrow > height_wide

    def test_text_wrapping_height(self) -> None:
        """Text line wraps at viewport_width - 2 (content indent)."""
        line = _make_text_line(raw="A" * 50)
        # viewport_width=30, content_width=28, 50 chars -> ceil(50/28) = 2 content rows + 1 metadata
        height = get_line_height(line, expanded=True, viewport_width=30)
        assert height == 3


class TestRenderExpandedContentRow:
    def test_renders_json_content(self) -> None:
        line = _make_json_line(json_str='{"key": "val"}')
        strip = render_expanded_content_row(line, 0, 80, Style(), Style())
        text = strip.text
        # Should start with indent and contain JSON
        assert text.startswith("  ")
        assert "{" in text

    def test_renders_continuation_row(self) -> None:
        line = _make_json_line(json_str='{"a": 1, "b": 2}')
        height = get_line_height(line, expanded=True, viewport_width=80)
        # Content rows are 1..height-1, so content_row 0..height-2
        for content_row in range(height - 1):
            strip = render_expanded_content_row(line, content_row, 80, Style(), Style())
            assert strip.text.strip() != ""

    def test_renders_text_content(self) -> None:
        line = _make_text_line()
        strip = render_expanded_content_row(line, 0, 80, Style(color="cyan"), Style())
        text = strip.text
        assert text.startswith("  ")
        assert "plain text" in text

    def test_out_of_range_returns_empty(self) -> None:
        line = _make_json_line(json_str='{"key": "val"}')
        strip = render_expanded_content_row(line, 999, 80, Style(), Style())
        assert strip.text.strip() == ""


class TestWrapHelpers:
    def test_json_continuation_indent_key_value(self) -> None:
        # '": ' starts at pos 6 (the closing " of key), so indent = 6 + 3 = 9
        assert _json_continuation_indent('  "key": "value"') == 9

    def test_json_continuation_indent_no_key(self) -> None:
        assert _json_continuation_indent("    123") == 4  # base indent

    def test_json_continuation_indent_opening_brace(self) -> None:
        assert _json_continuation_indent("{") == 0  # no indent

    def test_json_line_wrap_count_short(self) -> None:
        assert _json_line_wrap_count("short", 80) == 1

    def test_json_line_wrap_count_exact(self) -> None:
        assert _json_line_wrap_count("x" * 80, 80) == 1

    def test_json_line_wrap_count_overflow(self) -> None:
        assert _json_line_wrap_count("x" * 81, 80) == 2

    def test_wrap_json_line_no_wrap(self) -> None:
        assert _wrap_json_line("short", 80) == ["short"]

    def test_wrap_json_line_wraps(self) -> None:
        result = _wrap_json_line("A" * 100, 50)
        assert len(result) == 2
        assert result[0] == "A" * 50

    def test_wrap_json_line_smart_indent(self) -> None:
        """Continuation lines align with value start."""
        line = '  "key": "' + "x" * 100 + '"'
        result = _wrap_json_line(line, 40)
        assert len(result) > 1
        # Continuation indent should be after '": '
        cont = result[1]
        stripped = cont.lstrip()
        indent_len = len(cont) - len(stripped)
        assert indent_len == 9  # position after '": ' (at the value start)

    def test_text_wrap_count_short(self) -> None:
        assert _text_wrap_count("short", 80) == 1

    def test_text_wrap_count_long(self) -> None:
        assert _text_wrap_count("x" * 160, 80) == 2

    def test_wrap_text_no_wrap(self) -> None:
        assert _wrap_text("short", 80) == ["short"]

    def test_wrap_text_wraps(self) -> None:
        result = _wrap_text("A" * 100, 50)
        assert len(result) == 2
        assert result[0] == "A" * 50
        assert result[1] == "A" * 50

    def test_wrap_text_empty(self) -> None:
        assert _wrap_text("", 80) == [""]

    def test_wrap_json_line_empty(self) -> None:
        assert _wrap_json_line("", 80) == [""]
