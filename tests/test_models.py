"""Tests for pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

from logdelve.models import ContentType, LogLine


class TestLogLine:
    def test_text_line(self) -> None:
        line = LogLine(
            line_number=1,
            raw="some raw text",
            content_type=ContentType.TEXT,
        )
        assert line.line_number == 1
        assert line.content == "some raw text"
        assert line.timestamp is None
        assert line.parsed_json is None
        assert line.content_type == ContentType.TEXT

    def test_json_line(self) -> None:
        raw = '2024-01-15T10:30:00Z {"key": "value"}'
        content_offset = len("2024-01-15T10:30:00Z ")
        line = LogLine(
            line_number=2,
            raw=raw,
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            content_type=ContentType.JSON,
            content_offset=content_offset,
            parsed_json={"key": "value"},
        )
        assert line.content_type == ContentType.JSON
        assert line.content == '{"key": "value"}'
        assert line.parsed_json is not None
        assert line.parsed_json["key"] == "value"
        assert line.timestamp is not None
        assert line.timestamp.year == 2024

    def test_line_without_timestamp(self) -> None:
        line = LogLine(
            line_number=3,
            raw="no timestamp",
            content_type=ContentType.TEXT,
        )
        assert line.timestamp is None
        assert line.content == "no timestamp"

    def test_content_offset_default(self) -> None:
        line = LogLine(
            line_number=1,
            raw="hello world",
            content_type=ContentType.TEXT,
        )
        assert line.content_offset == 0
        assert line.content == "hello world"


class TestContentType:
    def test_values(self) -> None:
        assert ContentType.JSON == "json"  # type: ignore[comparison-overlap]
        assert ContentType.TEXT == "text"  # type: ignore[comparison-overlap]

    def test_str_enum(self) -> None:
        assert str(ContentType.JSON) == "json"
        assert str(ContentType.TEXT) == "text"
