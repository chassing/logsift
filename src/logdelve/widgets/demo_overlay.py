"""Demo mode for VHS recordings.

Activated by setting LOGDELVE_DEMO environment variable.
Call setup_demo(app) in on_mount to initialize.

Set LOGDELVE_DEMO to a tape name to get tape-specific labels:
  LOGDELVE_DEMO=hero       → JSON viewer labels
  LOGDELVE_DEMO=anomaly    → Anomaly detection labels
  LOGDELVE_DEMO=1          → Generic labels
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App

_LABEL_SETS: dict[str, list[str]] = {
    "hero": [
        """🔎 Welcome to Logdelve!

I'm going to show you how to explore and analyze JSON logs with Logdelve. Let's dive in!
""",
        "↕ Use the arrow keys to navigate through log lines.",
        "📋 Use Enter to expand/collapse a single JSON log line.",
        "📋 Use j to expand/collapse all JSON log lines",
        "🎛️ Use f/F to filter by JSON key",
        "🎛️ Only show matching logs",
        "🎛️ Let's toggle all active filters",
        "🎛️ Clear all filters",
        "🔎 Searching logs",
        "Go grab it at https://github.com/chassing/logdelve",
    ],
    "anomaly": [
        "🔍 Anomaly Detection",
        "📊 Analyzing patterns",
        "Go grab it at https://github.com/chassing/logdelve",
    ],
}

_DEFAULT_LABELS = [
    "📋 JSON Log Viewer",
    "🔍 Anomaly Detection",
    "📊 Analyzing patterns",
    "🔎 Searching logs",
    "🎛️ Filtering",
    "github.com/chassing/logdelve",
]


def setup_demo(app: App[None]) -> None:
    """Initialize demo mode on the app. Call from on_mount."""
    mode = os.environ.get("LOGDELVE_DEMO", "1")
    labels = _LABEL_SETS.get(mode, _DEFAULT_LABELS)
    index = [-1]

    def next_label() -> None:
        index[0] = (index[0] + 1) % len(labels)
        app.notify(labels[index[0]], timeout=4)

    app._demo_next_label = next_label  # type: ignore[attr-defined]  # noqa: SLF001
    app.screen.add_class("demo-mode")
