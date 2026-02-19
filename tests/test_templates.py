"""Tests for message template extraction and grouping."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel, LogLine
from logdelve.templates import build_template_groups, extract_template


def _make_line(
    content: str,
    line_number: int = 1,
    content_type: ContentType = ContentType.TEXT,
    parsed_json: dict | None = None,  # type: ignore[type-arg]
    log_level: LogLevel | None = None,
) -> LogLine:
    return LogLine(
        line_number=line_number,
        raw=content,
        content_type=content_type,
        parsed_json=parsed_json,
        log_level=log_level,
    )


class TestExtractTemplate:
    def test_uuid(self) -> None:
        result = extract_template("Request 550e8400-e29b-41d4-a716-446655440000 processed")
        assert result == "Request <UUID> processed"

    def test_ipv4(self) -> None:
        result = extract_template("Connection from 192.168.1.5 established")
        assert result == "Connection from <IP> established"

    def test_numbers(self) -> None:
        result = extract_template("Processed in 42ms with 3 retries")
        assert result == "Processed in <NUM>ms with <NUM> retries"

    def test_iso_timestamp(self) -> None:
        result = extract_template("Event at 2024-01-15T10:30:00Z completed")
        assert result == "Event at <TS> completed"

    def test_path(self) -> None:
        result = extract_template("GET /api/v1/users/123 HTTP/1.1")
        assert "<PATH>" in result

    def test_hex_string(self) -> None:
        result = extract_template("Hash: abcdef0123456789 computed")
        assert result == "Hash: <HEX> computed"

    def test_mixed(self) -> None:
        result = extract_template("Connection to 192.168.1.5:8080 failed after 3 retries")
        assert "<IP>" in result
        assert "<NUM>" in result

    def test_no_variables(self) -> None:
        result = extract_template("Health check passed")
        assert result == "Health check passed"

    def test_json_template_no_event(self) -> None:
        """JSON without event key falls back to full key structure."""
        data = {"status": 500, "path": "/api/users", "duration": 42}
        result = extract_template("", is_json=True, parsed_json=data)
        assert "status=<NUM>" in result

    def test_json_template_with_event(self) -> None:
        """JSON with event key groups by event value."""
        data = {"event": "Request processed", "user": "admin"}
        result = extract_template("", is_json=True, parsed_json=data)
        assert result == "event:Request processed"

    def test_json_template_event_with_variables(self) -> None:
        """JSON event with variable parts gets tokenized."""
        data = {"event": "GET /api/users/123", "status": 200}
        result = extract_template("", is_json=True, parsed_json=data)
        assert result == "event:GET <PATH>"

    def test_json_template_same_event_different_keys(self) -> None:
        """Same event value should produce same template regardless of other keys."""
        data1 = {"event": "Start", "a": 1}
        data2 = {"event": "Start", "a": 1, "b": 2, "c": 3}
        assert extract_template("", is_json=True, parsed_json=data1) == extract_template(
            "", is_json=True, parsed_json=data2
        )

    def test_json_template_list(self) -> None:
        data = {"items": [1, 2, 3]}
        result = extract_template("", is_json=True, parsed_json=data)
        assert "items=[...]" in result


class TestBuildTemplateGroups:
    def test_groups_identical_messages(self) -> None:
        lines = [
            _make_line("Connection from 192.168.1.1 established", line_number=1),
            _make_line("Connection from 192.168.1.2 established", line_number=2),
            _make_line("Connection from 10.0.0.5 established", line_number=3),
        ]
        groups = build_template_groups(lines)
        assert len(groups) == 1
        assert groups[0].count == 3

    def test_groups_different_messages(self) -> None:
        lines = [
            _make_line("Connection established", line_number=1),
            _make_line("Health check passed", line_number=2),
            _make_line("Connection established", line_number=3),
        ]
        groups = build_template_groups(lines)
        assert len(groups) == 2
        assert groups[0].count == 2  # Connection established
        assert groups[1].count == 1  # Health check

    def test_sorted_by_count(self) -> None:
        lines = [
            _make_line("Rare event", line_number=1),
            _make_line("Common event", line_number=2),
            _make_line("Common event", line_number=3),
            _make_line("Common event", line_number=4),
        ]
        groups = build_template_groups(lines)
        assert groups[0].count > groups[1].count

    def test_tracks_line_indices(self) -> None:
        lines = [
            _make_line("Event A", line_number=1),
            _make_line("Event B", line_number=2),
            _make_line("Event A", line_number=3),
        ]
        groups = build_template_groups(lines)
        a_group = next(g for g in groups if "Event A" in g.example)
        assert a_group.line_indices == [0, 2]

    def test_tracks_first_last_seen(self) -> None:
        lines = [
            _make_line("Event", line_number=1),
            _make_line("Other", line_number=2),
            _make_line("Event", line_number=3),
        ]
        groups = build_template_groups(lines)
        event_group = next(g for g in groups if "Event" in g.example)
        assert event_group.first_seen == 0
        assert event_group.last_seen == 2

    def test_tracks_log_level(self) -> None:
        lines = [
            _make_line("Error occurred", line_number=1, log_level=LogLevel.ERROR),
            _make_line("Error occurred", line_number=2, log_level=LogLevel.ERROR),
            _make_line("Error occurred", line_number=3, log_level=LogLevel.WARN),
        ]
        groups = build_template_groups(lines)
        assert groups[0].log_level == LogLevel.ERROR  # most frequent

    def test_json_grouping_by_event(self) -> None:
        lines = [
            _make_line(
                '{"event": "Request done", "status": 200}',
                line_number=1,
                content_type=ContentType.JSON,
                parsed_json={"event": "Request done", "status": 200},
            ),
            _make_line(
                '{"event": "Request done", "status": 500, "extra": "key"}',
                line_number=2,
                content_type=ContentType.JSON,
                parsed_json={"event": "Request done", "status": 500, "extra": "key"},
            ),
        ]
        groups = build_template_groups(lines)
        # Same event value → one group, regardless of different extra keys
        assert len(groups) == 1
        assert groups[0].count == 2

    def test_empty_lines(self) -> None:
        groups = build_template_groups([])
        assert len(groups) == 0

    def test_template_hash_consistency(self) -> None:
        lines = [
            _make_line("Error on host 10.0.0.1", line_number=1),
            _make_line("Error on host 10.0.0.2", line_number=2),
        ]
        groups = build_template_groups(lines)
        assert len(groups) == 1
        assert len(groups[0].template_hash) == 16
