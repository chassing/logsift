"""Single log line rendering (compact and expanded)."""

from __future__ import annotations

from rich.highlighter import JSONHighlighter
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from logdelve.models import ContentType, LogLine

_json_highlighter = JSONHighlighter()

_CONTENT_INDENT = 2  # Left indent for expanded content rows


def _json_continuation_indent(json_line: str) -> int:
    """Find the continuation indent for a JSON line (aligns with value start)."""
    colon_pos = json_line.find('": ')
    if colon_pos >= 0:
        return colon_pos + 3
    # No key-value pair, use existing indent level
    return len(json_line) - len(json_line.lstrip())


def _json_line_wrap_count(json_line: str, width: int) -> int:
    """Count how many display rows a single JSON line needs when wrapped."""
    if not json_line or width <= 0 or len(json_line) <= width:
        return 1
    remaining = len(json_line) - width
    cont_indent = _json_continuation_indent(json_line)
    cont_width = max(1, width - cont_indent)
    return 1 + -(-remaining // cont_width)


def _wrap_json_line(json_line: str, width: int) -> list[str]:
    """Wrap a single JSON line with smart continuation indent."""
    if not json_line or width <= 0 or len(json_line) <= width:
        return [json_line or ""]

    cont_indent = _json_continuation_indent(json_line)
    result = [json_line[:width]]
    pos = width

    cont_width = max(1, width - cont_indent)
    indent_str = " " * cont_indent

    while pos < len(json_line):
        end = min(pos + cont_width, len(json_line))
        result.append(indent_str + json_line[pos:end])
        pos = end

    return result


def _text_wrap_count(text: str, width: int) -> int:
    """Count how many display rows a text line needs when wrapped."""
    if not text or width <= 0:
        return 1
    return max(1, -(-len(text) // width))


def _wrap_text(text: str, width: int) -> list[str]:
    """Wrap text at width boundary."""
    if not text or width <= 0 or len(text) <= width:
        return [text or ""]

    result: list[str] = []
    pos = 0
    while pos < len(text):
        end = min(pos + width, len(text))
        result.append(text[pos:end])
        pos = end

    return result


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


def get_line_height(line: LogLine, *, expanded: bool, viewport_width: int = 0) -> int:
    """Get the display height of a line.

    Returns 1 for compact lines. For expanded lines, returns metadata row +
    wrapped content rows.
    """
    if not expanded:
        return 1

    if viewport_width <= 0:
        viewport_width = 200

    content_width = max(1, viewport_width - _CONTENT_INDENT)

    if line.content_type == ContentType.JSON and line.parsed_json is not None:
        json_lines = line.json_lines
        if not json_lines:
            return 2  # metadata + 1 empty content row
        total = sum(_json_line_wrap_count(jl, content_width) for jl in json_lines)
        return total + 1  # +1 for metadata row

    # Expanded text
    return _text_wrap_count(line.raw, content_width) + 1


def render_expanded_content_row(
    line: LogLine,
    content_row: int,
    viewport_width: int,
    content_style: Style,
    bg_style: Style,
) -> Strip:
    """Render a single content row of an expanded line.

    Args:
        line: The log line to render.
        content_row: 0-indexed content row (sub_row - 1 from display perspective).
        viewport_width: Available viewport width.
        content_style: Style for text content (ignored for JSON, which uses syntax highlighting).
        bg_style: Background style to merge.
    """
    content_width = max(1, viewport_width - _CONTENT_INDENT)
    indent = " " * _CONTENT_INDENT

    if line.content_type == ContentType.JSON and line.parsed_json is not None:
        # Find the wrapped JSON line for this content_row
        row = 0
        for jl in line.json_lines:
            wrapped = _wrap_json_line(jl, content_width)
            if row + len(wrapped) > content_row:
                text = wrapped[content_row - row]
                highlighted = _json_highlighter(Text(text))
                segments: list[Segment] = [Segment(indent, bg_style)]
                segments.extend(_text_to_segments(highlighted, bg_style))
                return Strip(segments)
            row += len(wrapped)
        return Strip([Segment(indent, bg_style)])

    # TEXT: wrap raw text
    wrapped = _wrap_text(line.raw, content_width)
    if content_row < len(wrapped):
        return Strip([Segment(indent + wrapped[content_row], content_style + bg_style)])
    return Strip([Segment(indent, bg_style)])
