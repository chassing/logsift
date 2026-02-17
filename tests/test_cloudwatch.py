"""Tests for AWS CloudWatch operations and time parsing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from logdelve.aws import (
    _extract_message,
    _format_event,
    _ms_to_iso,
    _ts_to_ms,
    get_log_events,
    list_log_groups,
    list_log_streams,
)
from logdelve.utils import parse_time


class TestParseTime:
    def test_relative_seconds(self) -> None:
        result = parse_time("30s")
        assert (datetime.now(tz=UTC) - result).total_seconds() < 35

    def test_relative_minutes(self) -> None:
        result = parse_time("5m")
        diff = datetime.now(tz=UTC) - result
        assert 295 < diff.total_seconds() < 305

    def test_relative_hours(self) -> None:
        result = parse_time("1h")
        diff = datetime.now(tz=UTC) - result
        assert 3595 < diff.total_seconds() < 3605

    def test_relative_days(self) -> None:
        result = parse_time("2d")
        diff = datetime.now(tz=UTC) - result
        assert diff.days == 2 or diff.days == 1  # boundary

    def test_relative_weeks(self) -> None:
        result = parse_time("1week")
        diff = datetime.now(tz=UTC) - result
        assert 6 <= diff.days <= 7

    def test_relative_long_unit(self) -> None:
        result = parse_time("2days")
        diff = datetime.now(tz=UTC) - result
        assert diff.days >= 1

    def test_relative_minutes_long(self) -> None:
        result = parse_time("10minutes")
        diff = datetime.now(tz=UTC) - result
        assert 595 < diff.total_seconds() < 605

    def test_time_only_hhmm(self) -> None:
        result = parse_time("14:30")
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0
        assert result.tzinfo is not None

    def test_time_only_hhmmss(self) -> None:
        result = parse_time("7:55:30")
        assert result.hour == 7
        assert result.minute == 55
        assert result.second == 30

    def test_iso8601(self) -> None:
        result = parse_time("2024-01-15T10:30:00+00:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_unknown_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse time"):
            parse_time("not a date at all xyz123")


class TestTimestampConversion:
    def test_ts_to_ms(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        ms = _ts_to_ms(dt)
        assert ms == 1705314600000

    def test_ms_to_iso(self) -> None:
        iso = _ms_to_iso(1705314600000)
        assert "2024-01-15" in iso
        assert "10:30:00" in iso


class TestExtractMessage:
    def test_no_key(self) -> None:
        assert _extract_message("raw text", None) == "raw text"

    def test_non_json(self) -> None:
        assert _extract_message("plain text", "message") == "plain text"

    def test_json_with_key(self) -> None:
        raw = json.dumps({"message": "inner content", "level": "info"})
        assert _extract_message(raw, "message") == "inner content"

    def test_json_without_key(self) -> None:
        raw = json.dumps({"level": "info", "data": "test"})
        assert _extract_message(raw, "message") == raw

    def test_nested_json_message(self) -> None:
        inner = json.dumps({"event": "request", "status": 200})
        raw = json.dumps({"message": inner, "kubernetes": {}})
        result = _extract_message(raw, "message")
        assert result == inner


class TestFormatEvent:
    def test_basic_event(self) -> None:
        event = {"timestamp": 1705312200000, "message": "test message"}
        ts, msg, stream = _format_event(event)  # type: ignore[arg-type]
        assert "2024-01-15" in ts
        assert msg == "test message"
        assert stream == ""

    def test_event_with_message_key(self) -> None:
        inner = json.dumps({"message": "inner", "level": "info"})
        event = {"timestamp": 1705312200000, "message": inner}
        _ts, msg, _stream = _format_event(event, message_key="message")  # type: ignore[arg-type]
        assert msg == "inner"

    def test_event_without_message_key(self) -> None:
        event = {"timestamp": 1705312200000, "message": "plain text"}
        _ts, msg, _stream = _format_event(event, message_key="message")  # type: ignore[arg-type]
        assert msg == "plain text"

    def test_event_with_stream_name(self) -> None:
        event = {"timestamp": 1705312200000, "message": "test", "logStreamName": "my-pod-abc123"}
        _ts, _msg, stream = _format_event(event)  # type: ignore[arg-type]
        assert stream == "my-pod-abc123"


class TestGetLogEvents:
    def test_paginates_events(self) -> None:
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "events": [
                    {"timestamp": 1705312200000, "message": "line 1", "eventId": "1"},
                    {"timestamp": 1705312201000, "message": "line 2", "eventId": "2"},
                ]
            },
            {
                "events": [
                    {"timestamp": 1705312202000, "message": "line 3", "eventId": "3"},
                ]
            },
        ]

        start = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 11, 0, tzinfo=UTC)
        events = list(get_log_events(mock_client, "/test/group", "prefix", start, end))

        assert len(events) == 3
        assert events[0][1] == "line 1"
        assert events[2][1] == "line 3"
        mock_client.get_paginator.assert_called_once_with("filter_log_events")

    def test_extracts_message_key(self) -> None:
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        inner = json.dumps({"message": "extracted", "level": "info"})
        mock_paginator.paginate.return_value = [
            {"events": [{"timestamp": 1705312200000, "message": inner, "eventId": "1"}]},
        ]

        start = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 11, 0, tzinfo=UTC)
        events = list(get_log_events(mock_client, "/test/group", "", start, end, message_key="message"))

        assert len(events) == 1
        assert events[0][1] == "extracted"


class TestListLogGroups:
    def test_paginates_groups(self) -> None:
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"logGroups": [{"logGroupName": "/aws/lambda/a"}, {"logGroupName": "/aws/lambda/b"}]},
            {"logGroups": [{"logGroupName": "/aws/lambda/c"}]},
        ]

        groups = list(list_log_groups(mock_client, prefix="/aws/lambda/"))
        assert groups == ["/aws/lambda/a", "/aws/lambda/b", "/aws/lambda/c"]

    def test_no_prefix(self) -> None:
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"logGroups": [{"logGroupName": "/group1"}]},
        ]

        groups = list(list_log_groups(mock_client))
        assert groups == ["/group1"]


class TestListLogStreams:
    def test_paginates_streams(self) -> None:
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"logStreams": [{"logStreamName": "stream-a"}, {"logStreamName": "stream-b"}]},
        ]

        streams = list(list_log_streams(mock_client, "/test/group", prefix="stream"))
        assert streams == ["stream-a", "stream-b"]
