"""Kubernetes log format parser."""

from __future__ import annotations

import re

from logdelve.parsers.base import (
    LogParser,
    ParseResult,
    classify_content,
    extract_log_level,
)

# Kubernetes/CloudWatch bracket: "[pod-name-abc123]"
_K8S_BRACKET_RE = re.compile(r"^\[(?P<comp>[a-z0-9][\w.-]+)\]\s*")

# Kubernetes prefix: "pod-name container 2024-..."
_K8S_PREFIX_RE = re.compile(r"^(?P<comp>[a-z0-9][\w.-]+)\s+(?P<cont>[a-z0-9][\w.-]+)\s+(?=\d{4}-)")


class KubernetesParser(LogParser):
    """Parses Kubernetes kubectl log formats (bracket and prefix styles)."""

    @property
    def name(self) -> str:
        return "kubernetes"

    @property
    def description(self) -> str:
        return "Kubernetes kubectl logs ([pod-name] or pod container timestamp)"

    def __init__(self) -> None:
        from logdelve.parsers.iso import IsoParser

        self._iso_parser = IsoParser()

    def try_parse(self, raw: str) -> ParseResult | None:
        component: str | None = None
        remainder = raw

        # [pod-name] style
        m = _K8S_BRACKET_RE.match(raw)
        if m:
            component = m.group("comp")
            remainder = raw[m.end() :]
        else:
            # pod-name container 2024-... style
            m = _K8S_PREFIX_RE.match(raw)
            if m:
                component = m.group("comp")
                remainder = raw[m.end() :]
            else:
                return None

        # Parse the remainder for timestamp
        result = self._iso_parser.try_parse(remainder)
        if result is not None:
            result.component = component
            return result

        # K8s prefix found but no timestamp in remainder
        content_type, parsed_json = classify_content(remainder)
        log_level = extract_log_level(remainder, parsed_json)
        return ParseResult(
            timestamp=None,
            content=remainder,
            content_type=content_type,
            parsed_json=parsed_json,
            log_level=log_level,
            component=component,
        )
