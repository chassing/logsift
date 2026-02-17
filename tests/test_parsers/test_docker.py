"""Tests for Docker Compose parser."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.docker import DockerParser


class TestDockerParserTryParse:
    def setup_method(self) -> None:
        self.parser = DockerParser()

    def test_docker_compose_with_iso_timestamp(self) -> None:
        result = self.parser.try_parse("web-service  | 2024-01-15T10:30:00Z some message")
        assert result is not None
        assert result.component == "web-service"
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.content == "some message"

    def test_docker_compose_without_timestamp(self) -> None:
        result = self.parser.try_parse("app  | just plain text here")
        assert result is not None
        assert result.component == "app"
        assert result.timestamp is None
        assert result.content == "just plain text here"

    def test_docker_compose_json_content(self) -> None:
        result = self.parser.try_parse('redis  | 2024-01-15T10:30:00Z {"level": "error", "msg": "fail"}')
        assert result is not None
        assert result.component == "redis"
        assert result.content_type == ContentType.JSON
        assert result.log_level == LogLevel.ERROR

    def test_non_docker_returns_none(self) -> None:
        result = self.parser.try_parse("2024-01-15T10:30:00Z no docker prefix")
        assert result is None

    def test_dotted_service_name(self) -> None:
        result = self.parser.try_parse("my.service  | hello")
        assert result is not None
        assert result.component == "my.service"


class TestDockerParserParseLine:
    def setup_method(self) -> None:
        self.parser = DockerParser()

    def test_parse_line_docker(self) -> None:
        line = self.parser.parse_line(1, "web  | 2024-01-15T10:30:00Z ok")
        assert line.line_number == 1
        assert line.component == "web"
        assert line.timestamp is not None

    def test_parse_line_non_docker_fallback(self) -> None:
        line = self.parser.parse_line(2, "not docker")
        assert line.timestamp is None
        assert line.component is None
