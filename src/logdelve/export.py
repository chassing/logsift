"""Export filtered log lines to files."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from logdelve.models import LogLine


class ExportFormat(StrEnum):
    """Supported export formats."""

    RAW = "raw"


def _export_raw(lines: list[LogLine], output_path: Path) -> int:
    """Export lines as raw text, one per line."""
    output_path.write_text("\n".join(line.raw for line in lines) + "\n", encoding="utf-8")
    return len(lines)


_EXPORTERS: dict[ExportFormat, Callable[[list[LogLine], Path], int]] = {
    ExportFormat.RAW: _export_raw,
}


def export_lines(lines: list[LogLine], fmt: ExportFormat, output_path: Path) -> int:
    """Export lines to a file in the specified format. Returns the number of lines written."""
    exporter = _EXPORTERS.get(fmt)
    if exporter is None:
        msg = f"Export format '{fmt}' not yet implemented"
        raise NotImplementedError(msg)
    return exporter(lines, output_path)
