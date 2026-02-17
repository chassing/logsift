"""Tests for Kubernetes parser."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.kubernetes import KubernetesParser


class TestKubernetesParserTryParse:
    def setup_method(self) -> None:
        self.parser = KubernetesParser()

    def test_bracket_prefix(self) -> None:
        result = self.parser.try_parse("[my-pod-abc123] 2024-01-15T10:30:00Z some message")
        assert result is not None
        assert result.component == "my-pod-abc123"
        assert result.timestamp is not None
        assert result.content == "some message"

    def test_pod_container_prefix(self) -> None:
        result = self.parser.try_parse("my-pod container-abc 2024-01-15T10:30:00Z log line")
        assert result is not None
        assert result.component == "my-pod"
        assert result.timestamp is not None

    def test_bracket_without_timestamp(self) -> None:
        result = self.parser.try_parse("[my-pod] just text no timestamp")
        assert result is not None
        assert result.component == "my-pod"
        assert result.timestamp is None

    def test_bracket_with_json(self) -> None:
        result = self.parser.try_parse('[my-pod] 2024-01-15T10:30:00Z {"level": "error", "msg": "fail"}')
        assert result is not None
        assert result.component == "my-pod"
        assert result.content_type == ContentType.JSON
        assert result.log_level == LogLevel.ERROR

    def test_non_k8s_returns_none(self) -> None:
        result = self.parser.try_parse("2024-01-15T10:30:00Z no k8s prefix")
        assert result is None

    def test_plain_text_returns_none(self) -> None:
        result = self.parser.try_parse("just some text")
        assert result is None


class TestKubernetesParserParseLine:
    def setup_method(self) -> None:
        self.parser = KubernetesParser()

    def test_parse_line_k8s(self) -> None:
        line = self.parser.parse_line(1, "[my-pod] 2024-01-15T10:30:00Z msg")
        assert line.line_number == 1
        assert line.component == "my-pod"
        assert line.timestamp is not None
        assert line.log_level == LogLevel.INFO

    def test_parse_line_non_k8s_fallback(self) -> None:
        line = self.parser.parse_line(2, "not kubernetes")
        assert line.timestamp is None
