"""Single log line rendering (compact and expanded JSON)."""

from __future__ import annotations

from rich.highlighter import JSONHighlighter
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from logdelve.models import ContentType, LogLine

_json_highlighter = JSONHighlighter()


def render_json_expanded_row(
    line: LogLine,
    sub_row: int,
    lineno_style: Style,
    timestamp_style: Style,
    bg_style: Style,
    *,
    show_line_numbers: bool = True,
) -> Strip:
    """Render a single sub-row of an expanded JSON log line."""
    json_lines = line.json_lines
    if not json_lines or sub_row >= len(json_lines):
        return _render_compact_strip(
            line, lineno_style, timestamp_style, Style(), bg_style, show_line_numbers=show_line_numbers
        )

    segments: list[Segment] = []

    if sub_row == 0:
        if show_line_numbers:
            if line.source_line_number is not None:
                lineno_text = f"{line.line_number}:{line.source_line_number} "
                lineno_text = f"{lineno_text:>12}"
            else:
                lineno_text = f"{line.line_number:>6} "
            segments.append(Segment(lineno_text, lineno_style + bg_style))
        if line.timestamp is not None:
            ts_end = len(line.raw) - len(line.content)
            ts_text = line.raw[:ts_end]
            segments.append(Segment(ts_text, timestamp_style + bg_style))
    else:
        # Compute prefix width for continuation line alignment
        prefix_width = 0
        if show_line_numbers:
            prefix_width += 12 if line.source_line_number is not None else 7
        if line.timestamp is not None:
            ts_end = len(line.raw) - len(line.content)
            prefix_width += ts_end
        segments.append(Segment(" " * prefix_width, bg_style))

    # Apply JSON syntax highlighting, merging bg_style into every segment
    highlighted = _json_highlighter(Text(json_lines[sub_row]))
    segments.extend(_text_to_segments(highlighted, bg_style))

    return Strip(segments)


def _text_to_segments(text: Text, bg_style: Style) -> list[Segment]:
    """Convert a Rich Text object to Segments with background applied to all.

    Only the background color from bg_style is merged into syntax-highlighted
    segments, preserving their foreground colors.
    """
    from rich.console import Console  # noqa: PLC0415

    plain = text.plain
    if not plain:
        return [Segment("", bg_style)]

    # Extract only background from bg_style to avoid overriding syntax colors
    bg_only = Style(bgcolor=bg_style.bgcolor) if bg_style.bgcolor else Style()

    console = Console(width=500, no_color=False)
    result: list[Segment] = []
    for seg in text.render(console):
        if seg.text:
            combined = (seg.style + bg_only) if seg.style else bg_style
            result.append(Segment(seg.text, combined))

    return result or [Segment(plain, bg_style)]


def _render_compact_strip(
    line: LogLine,
    lineno_style: Style,
    timestamp_style: Style,
    content_style: Style,
    bg_style: Style,
    *,
    show_line_numbers: bool = True,
) -> Strip:
    """Render a single compact line as a Strip."""
    segments: list[Segment] = []
    if show_line_numbers:
        if line.source_line_number is not None:
            lineno_text = f"{line.line_number}:{line.source_line_number} "
            lineno_text = f"{lineno_text:>12}"
        else:
            lineno_text = f"{line.line_number:>6} "
        segments.append(Segment(lineno_text, lineno_style + bg_style))
    if line.timestamp is not None:
        ts_end = len(line.raw) - len(line.content)
        ts_text = line.raw[:ts_end]
        segments.append(Segment(ts_text, timestamp_style + bg_style))
    segments.append(Segment(line.content, content_style + bg_style))
    return Strip(segments)


def get_line_height(line: LogLine, *, expanded: bool) -> int:
    """Get the display height of a line (1 for compact, N for expanded JSON, 2 for expanded text)."""
    if not expanded:
        return 1
    if line.content_type == ContentType.JSON and line.parsed_json is not None:
        lines = line.json_lines
        return len(lines) if lines else 1
    # Expanded text: compact line + full raw line below
    return 2
