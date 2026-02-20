"""Tests for session save/load."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import tomli_w

from logdelve.models import (
    FilterRule,
    FilterType,
    SearchDirection,
    SearchHistoryEntry,
    SearchPattern,
    SearchQuery,
)
from logdelve.session import create_session, delete_session, list_sessions, load_session, save_session


class TestSession:
    def test_save_and_load_roundtrip(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            rules = [
                FilterRule(filter_type=FilterType.INCLUDE, pattern="ERROR"),
                FilterRule(filter_type=FilterType.EXCLUDE, pattern="debug"),
            ]
            session = create_session("test-session", rules)
            save_session(session)

            loaded = load_session("test-session")
            assert loaded.name == "test-session"
            assert len(loaded.filters) == 2
            assert loaded.filters[0].filter_type == FilterType.INCLUDE
            assert loaded.filters[0].pattern == "ERROR"
            assert loaded.filters[1].filter_type == FilterType.EXCLUDE
            assert loaded.filters[1].pattern == "debug"

    def test_save_and_load_json_key_filter(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            rules = [
                FilterRule(
                    filter_type=FilterType.INCLUDE,
                    pattern="log_level=error",
                    is_json_key=True,
                    json_key="log_level",
                    json_value="error",
                ),
            ]
            session = create_session("json-session", rules)
            save_session(session)

            loaded = load_session("json-session")
            assert len(loaded.filters) == 1
            f = loaded.filters[0]
            assert f.is_json_key is True
            assert f.json_key == "log_level"
            assert f.json_value == "error"

    def test_list_sessions(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            save_session(create_session("alpha", []))
            save_session(create_session("beta", []))
            save_session(create_session("gamma", []))

            names = list_sessions()
            assert names == ["alpha", "beta", "gamma"]

    def test_list_sessions_empty(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            assert list_sessions() == []

    def test_load_nonexistent_session(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path), pytest.raises(FileNotFoundError):
            load_session("nonexistent")

    def test_delete_session(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            save_session(create_session("to-delete", []))
            assert "to-delete" in list_sessions()

            delete_session("to-delete")
            assert "to-delete" not in list_sessions()

    def test_overwrite_session(self, tmp_path: object) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            rules1 = [FilterRule(filter_type=FilterType.INCLUDE, pattern="first")]
            save_session(create_session("overwrite", rules1))

            rules2 = [FilterRule(filter_type=FilterType.EXCLUDE, pattern="second")]
            save_session(create_session("overwrite", rules2))

            loaded = load_session("overwrite")
            assert len(loaded.filters) == 1
            assert loaded.filters[0].pattern == "second"

    def test_save_and_load_search_patterns_roundtrip(self, tmp_path: Path) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            patterns = [
                SearchPattern(
                    query=SearchQuery(
                        pattern="warn.*",
                        case_sensitive=True,
                        is_regex=True,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=0,
                    nav_enabled=False,
                ),
                SearchPattern(
                    query=SearchQuery(
                        pattern="error",
                        case_sensitive=False,
                        is_regex=False,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=1,
                    nav_enabled=True,
                ),
            ]
            session = create_session("search-test", [], search_patterns=patterns)
            save_session(session)

            loaded = load_session("search-test")
            assert len(loaded.search_patterns) == 2

            p0 = loaded.search_patterns[0]
            assert p0.query.pattern == "warn.*"
            assert p0.query.case_sensitive is True
            assert p0.query.is_regex is True
            assert p0.nav_enabled is False
            assert p0.color_index == 0

            p1 = loaded.search_patterns[1]
            assert p1.query.pattern == "error"
            assert p1.query.case_sensitive is False
            assert p1.query.is_regex is False
            assert p1.nav_enabled is True
            assert p1.color_index == 1

    def test_save_and_load_search_history_roundtrip(self, tmp_path: Path) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            history = [
                SearchHistoryEntry(pattern="first", case_sensitive=False, is_regex=False),
                SearchHistoryEntry(pattern="second.*", case_sensitive=True, is_regex=True),
                SearchHistoryEntry(pattern="third", case_sensitive=False, is_regex=False),
            ]
            session = create_session("history-test", [], search_history=history)
            save_session(session)

            loaded = load_session("history-test")
            assert len(loaded.search_history) == 3
            assert loaded.search_history[0].pattern == "first"
            assert loaded.search_history[1].pattern == "second.*"
            assert loaded.search_history[1].case_sensitive is True
            assert loaded.search_history[1].is_regex is True
            assert loaded.search_history[2].pattern == "third"

    def test_load_legacy_session_without_search(self, tmp_path: Path) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            # Write a legacy session TOML manually (no search_patterns, no search_history, no version)
            data = {
                "name": "legacy",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "filters": [],
                "source_files": [],
                "bookmarks": {},
            }
            path = tmp_path / "legacy.toml"
            path.write_bytes(tomli_w.dumps(data).encode())

            loaded = load_session("legacy")
            assert loaded.search_patterns == []
            assert loaded.search_history == []
            assert loaded.version == 1  # Upgraded from 0 to 1

    def test_invalid_regex_skipped_on_load(self, tmp_path: Path) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            patterns = [
                SearchPattern(
                    query=SearchQuery(
                        pattern="valid",
                        case_sensitive=False,
                        is_regex=False,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=0,
                ),
                SearchPattern(
                    query=SearchQuery(
                        pattern="[invalid",
                        case_sensitive=False,
                        is_regex=True,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=1,
                ),
                SearchPattern(
                    query=SearchQuery(
                        pattern="also-valid",
                        case_sensitive=False,
                        is_regex=False,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=2,
                ),
            ]
            session = create_session("regex-test", [], search_patterns=patterns)
            save_session(session)

            loaded = load_session("regex-test")
            # Invalid regex should be skipped
            assert len(loaded.search_patterns) == 2
            assert loaded.search_patterns[0].query.pattern == "valid"
            assert loaded.search_patterns[0].color_index == 0
            assert loaded.search_patterns[1].query.pattern == "also-valid"
            assert loaded.search_patterns[1].color_index == 1

    def test_version_field_roundtrip(self, tmp_path: Path) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            session = create_session("version-test", [])
            save_session(session)

            loaded = load_session("version-test")
            assert loaded.version == 1

    def test_color_index_reassigned_on_load(self, tmp_path: Path) -> None:
        with patch("logdelve.session.get_sessions_dir", return_value=tmp_path):
            # Create patterns with non-sequential color indices (simulating removal)
            patterns = [
                SearchPattern(
                    query=SearchQuery(
                        pattern="first",
                        case_sensitive=False,
                        is_regex=False,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=0,
                ),
                SearchPattern(
                    query=SearchQuery(
                        pattern="third",
                        case_sensitive=False,
                        is_regex=False,
                        direction=SearchDirection.FORWARD,
                    ),
                    color_index=2,
                ),
            ]
            session = create_session("color-test", [], search_patterns=patterns)
            save_session(session)

            loaded = load_session("color-test")
            assert len(loaded.search_patterns) == 2
            # Colors reassigned sequentially on load
            assert loaded.search_patterns[0].color_index == 0
            assert loaded.search_patterns[1].color_index == 1
