"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_LINES = [
    '2024-01-15T10:30:00Z {"log_level": "info", "message": "Server started", "port": 8080}',
    "2024-01-15T10:30:01Z Connection established from 192.168.1.1",
    '2024-01-15 10:30:02.123 {"log_level": "error", "message": "Failed to connect", "code": 500}',
    "Jan 15 10:30:03 myhost syslogd: restart",
    '[15/Jan/2024:10:30:04 +0000] "GET /api/health HTTP/1.1" 200 15',
    "2024/01/15 10:30:05 Simple slash-date log entry",
    "No timestamp here, just plain text",
    '{"orphan_json": true, "no_timestamp": "indeed"}',
    "",
    '2024-01-15T10:30:06+02:00 {"nested": {"key": "value"}, "list": [1, 2, 3]}',
]


@pytest.fixture
def sample_log_file(tmp_path: Path) -> Path:
    """Create a temporary log file with sample content."""
    log_file = tmp_path / "test.log"
    log_file.write_text("\n".join(SAMPLE_LINES) + "\n")
    return log_file
