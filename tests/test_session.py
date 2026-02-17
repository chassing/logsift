"""Tests for session save/load."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from logdelve.models import FilterRule, FilterType
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
