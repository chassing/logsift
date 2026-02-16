"""Baseline comparison and anomaly detection for log analysis."""

from __future__ import annotations

from logdelve.models import ContentType, LogLine
from logdelve.templates import MessageTemplate, build_template_groups, extract_template


class BaselineData:
    """Pre-computed template statistics from a baseline log file."""

    def __init__(self, template_hashes: set[str], template_counts: dict[str, int], total_lines: int) -> None:
        self.template_hashes = template_hashes
        self.template_counts = template_counts
        self.total_lines = total_lines


class AnomalyResult:
    """Results of comparing current logs against a baseline."""

    def __init__(self) -> None:
        self.novel_templates: list[MessageTemplate] = []
        self.disappeared_hashes: list[str] = []
        self.frequency_spikes: list[tuple[MessageTemplate, int, int]] = []  # (template, baseline_count, current_count)
        self.scores: dict[int, float] = {}  # line_index → anomaly score (0.0-1.0)
        self.anomaly_count = 0


def build_baseline(lines: list[LogLine]) -> BaselineData:
    """Build baseline statistics from a set of known-good log lines."""
    groups = build_template_groups(lines)
    hashes: set[str] = set()
    counts: dict[str, int] = {}

    for group in groups:
        hashes.add(group.template_hash)
        counts[group.template_hash] = group.count

    return BaselineData(
        template_hashes=hashes,
        template_counts=counts,
        total_lines=len(lines),
    )


def detect_anomalies(lines: list[LogLine], baseline: BaselineData) -> AnomalyResult:
    """Compare current log lines against a baseline to find anomalies.

    Scoring:
    - 1.0: template completely new (not in baseline)
    - 0.5: template frequency increased significantly (>5x)
    - 0.0: known/normal pattern
    """
    result = AnomalyResult()
    current_groups = build_template_groups(lines)
    current_hashes: set[str] = set()

    # Build a mapping from template_hash to line indices
    hash_to_lines: dict[str, list[int]] = {}
    for group in current_groups:
        current_hashes.add(group.template_hash)
        hash_to_lines[group.template_hash] = group.line_indices

        if group.template_hash not in baseline.template_hashes:
            # Completely new template
            result.novel_templates.append(group)
            for idx in group.line_indices:
                result.scores[idx] = 1.0
        elif baseline.total_lines > 0:
            # Check for frequency spikes
            baseline_count = baseline.template_counts.get(group.template_hash, 0)
            if baseline_count > 0:
                # Normalize by total lines to compare rates
                baseline_rate = baseline_count / baseline.total_lines
                current_rate = group.count / len(lines) if len(lines) > 0 else 0
                if current_rate > baseline_rate * 5 and group.count > 10:
                    result.frequency_spikes.append((group, baseline_count, group.count))
                    for idx in group.line_indices:
                        result.scores[idx] = max(result.scores.get(idx, 0), 0.5)

    # Find disappeared templates
    result.disappeared_hashes = [h for h in baseline.template_hashes if h not in current_hashes]

    result.anomaly_count = sum(1 for s in result.scores.values() if s > 0)
    return result


def compute_line_templates(lines: list[LogLine]) -> list[str]:
    """Compute the template hash for each line (for per-line anomaly lookup)."""
    from logdelve.templates import _compute_hash

    result: list[str] = []
    for line in lines:
        is_json = line.content_type == ContentType.JSON
        template_str = extract_template(line.content, is_json=is_json, parsed_json=line.parsed_json)
        result.append(_compute_hash(template_str))
    return result
