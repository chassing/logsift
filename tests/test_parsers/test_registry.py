"""Tests for parser registry and auto-detection."""

from __future__ import annotations

from logdelve.parsers import ParserName, detect_parser, get_parser
from logdelve.parsers.apache import ApacheParser
from logdelve.parsers.auto import AutoParser
from logdelve.parsers.docker import DockerParser
from logdelve.parsers.iso import IsoParser
from logdelve.parsers.kubernetes import KubernetesParser
from logdelve.parsers.syslog import SyslogParser


class TestRegistry:
    def test_get_auto_parser(self) -> None:
        parser = get_parser(ParserName.AUTO)
        assert isinstance(parser, AutoParser)

    def test_get_iso_parser(self) -> None:
        parser = get_parser(ParserName.ISO)
        assert isinstance(parser, IsoParser)

    def test_get_syslog_parser(self) -> None:
        parser = get_parser(ParserName.SYSLOG)
        assert isinstance(parser, SyslogParser)

    def test_get_apache_parser(self) -> None:
        parser = get_parser(ParserName.APACHE)
        assert isinstance(parser, ApacheParser)

    def test_get_docker_parser(self) -> None:
        parser = get_parser(ParserName.DOCKER)
        assert isinstance(parser, DockerParser)

    def test_get_kubernetes_parser(self) -> None:
        parser = get_parser(ParserName.KUBERNETES)
        assert isinstance(parser, KubernetesParser)

    def test_all_names_resolvable(self) -> None:
        for name in ParserName:
            parser = get_parser(name)
            assert parser is not None
            assert parser.name == name.value

    def test_each_instance_is_new(self) -> None:
        p1 = get_parser(ParserName.ISO)
        p2 = get_parser(ParserName.ISO)
        assert p1 is not p2


class TestDetectParser:
    def test_detect_syslog(self) -> None:
        lines = [
            "Jan 15 10:30:03 myhost syslogd: restart",
            "Jan 15 10:30:04 myhost kernel: something",
            "Jan 15 10:30:05 myhost app[123]: hello",
        ]
        parser = detect_parser(lines)
        assert isinstance(parser, SyslogParser)

    def test_detect_iso(self) -> None:
        lines = [
            "2024-01-15T10:30:00Z message one",
            "2024-01-15T10:30:01Z message two",
            "2024-01-15T10:30:02Z message three",
        ]
        parser = detect_parser(lines)
        assert isinstance(parser, IsoParser)

    def test_detect_apache(self) -> None:
        lines = [
            '[15/Jan/2024:10:30:04 +0000] "GET / HTTP/1.1" 200 0',
            '[15/Jan/2024:10:30:05 +0000] "POST /api HTTP/1.1" 201 0',
            '[15/Jan/2024:10:30:06 +0000] "GET /health HTTP/1.1" 200 2',
        ]
        parser = detect_parser(lines)
        assert isinstance(parser, ApacheParser)

    def test_detect_mixed_falls_back_to_auto(self) -> None:
        lines = [
            "Jan 15 10:30:03 myhost syslogd: restart",
            "2024-01-15T10:30:00Z ISO line",
            '[15/Jan/2024:10:30:04 +0000] "GET / HTTP/1.1"',
            "just text",
        ]
        parser = detect_parser(lines)
        assert isinstance(parser, AutoParser)

    def test_detect_empty_lines(self) -> None:
        parser = detect_parser([])
        assert isinstance(parser, AutoParser)

    def test_detect_all_empty_strings(self) -> None:
        parser = detect_parser(["", "", ""])
        assert isinstance(parser, AutoParser)

    def test_detect_docker(self) -> None:
        lines = [
            "web  | 2024-01-15T10:30:00Z msg one",
            "web  | 2024-01-15T10:30:01Z msg two",
            "db   | 2024-01-15T10:30:02Z msg three",
        ]
        parser = detect_parser(lines)
        assert isinstance(parser, DockerParser)
