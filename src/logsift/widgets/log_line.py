"""Single log line rendering (compact and expanded JSON)."""

from __future__ import annotations

import json

from rich.console import Console
from rich.highlighter import JSONHighlighter
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from logsift.models import ContentType, LogLine

_json_highlighter = JSONHighlighter()


def render_json_expanded(
    line: LogLine,
    width: int,
    lineno_style: Style,
    timestamp_style: Style,
    bg_style: Style,
) -> list[Strip]:
    """Render a JSON log line as pretty-printed, syntax-highlighted strips."""
    if line.parsed_json is None:
        return [_render_compact_strip(line, lineno_style, timestamp_style, Style(), bg_style)]

    try:
        formatted = json.dumps(line.parsed_json, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return [_render_compact_strip(line, lineno_style, timestamp_style, Style(), bg_style)]

    json_lines = formatted.split("\n")
    strips: list[Strip] = []

    for i, json_line in enumerate(json_lines):
        segments: list[Segment] = []

        if i == 0:
            lineno_text = f"{line.line_number:>6} "
            segments.append(Segment(lineno_text, lineno_style + bg_style))
            if line.timestamp is not None:
                ts_end = len(line.raw) - len(line.content)
                ts_text = line.raw[:ts_end]
                segments.append(Segment(ts_text, timestamp_style + bg_style))
        else:
            prefix_width = 7
            if line.timestamp is not None:
                ts_end = len(line.raw) - len(line.content)
                prefix_width += ts_end
            segments.append(Segment(" " * prefix_width, bg_style))

        highlighted = _json_highlighter(Text(json_line))
        for seg in _text_to_segments(highlighted, bg_style):
            segments.append(seg)

        strips.append(Strip(segments))

    return strips


def _text_to_segments(text: Text, bg_style: Style) -> list[Segment]:
    """Convert a Rich Text object to a list of Segments with background applied."""
    if not text.highlight_regex(r"."):
        return [Segment(text.plain, bg_style)]

    console = Console(width=200, no_color=False)
    segments: list[Segment] = []
    for seg in text.render(console):
        if seg.text:
            combined = (seg.style or Style()) + bg_style if seg.style else bg_style
            segments.append(Segment(seg.text, combined))
    return segments


def _render_compact_strip(
    line: LogLine,
    lineno_style: Style,
    timestamp_style: Style,
    content_style: Style,
    bg_style: Style,
) -> Strip:
    """Render a single compact line as a Strip."""
    segments: list[Segment] = []
    lineno_text = f"{line.line_number:>6} "
    segments.append(Segment(lineno_text, lineno_style + bg_style))
    if line.timestamp is not None:
        ts_end = len(line.raw) - len(line.content)
        ts_text = line.raw[:ts_end]
        segments.append(Segment(ts_text, timestamp_style + bg_style))
    segments.append(Segment(line.content, content_style + bg_style))
    return Strip(segments)


def get_line_height(line: LogLine, expanded: bool) -> int:
    """Get the display height of a line (1 for compact, N for expanded JSON)."""
    if not expanded or line.content_type != ContentType.JSON or line.parsed_json is None:
        return 1
    try:
        formatted = json.dumps(line.parsed_json, indent=2, ensure_ascii=False)
        return formatted.count("\n") + 1
    except (TypeError, ValueError):
        return 1
