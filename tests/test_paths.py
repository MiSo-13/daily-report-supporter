from __future__ import annotations

import sys

from app import paths
from app.app_meta import DATA_DIR_NAME, LEGACY_DATA_DIR_NAME
from app.runtime_paths import resolve_runtime_paths


def test_default_data_root_uses_working_directory(tmp_path) -> None:
    assert paths.default_data_root(home=tmp_path) == tmp_path / "WorKing"


def test_reports_are_stored_under_working_data_root(tmp_path) -> None:
    assert (
        paths.default_reports_root(frozen=False, home=tmp_path)
        == tmp_path / "WorKing" / "reports"
    )
    assert (
        paths.default_reports_root(frozen=True, home=tmp_path)
        == tmp_path / "WorKing" / "reports"
    )


def test_memos_are_stored_under_working_data_root(tmp_path) -> None:
    assert (
        paths.default_memos_root(frozen=False, home=tmp_path)
        == tmp_path / "WorKing" / "memos"
    )
    assert (
        paths.default_memos_root(frozen=True, home=tmp_path)
        == tmp_path / "WorKing" / "memos"
    )


def test_config_files_are_grouped_under_config_directory(tmp_path) -> None:
    assert paths.default_config_root(home=tmp_path) == (
        tmp_path / "WorKing" / "config"
    )
    assert paths.default_terminal_state_path(home=tmp_path) == (
        tmp_path / "WorKing" / "config" / "terminal-sessions.json"
    )
    assert paths.default_database_state_path(home=tmp_path) == (
        tmp_path / "WorKing" / "config" / "database-connections.json"
    )


def test_legacy_data_root_is_kept_for_migration(tmp_path) -> None:
    assert paths.legacy_data_root(home=tmp_path) == (
        tmp_path / "DailyReportSupporter"
    )


def test_resource_path_uses_meipass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert (
        paths.resource_path("scripts", "setup_crostini.sh")
        == tmp_path / "scripts" / "setup_crostini.sh"
    )


def test_source_terminal_starts_in_repository() -> None:
    assert paths.default_terminal_cwd(frozen=False) == paths.source_root()


def test_frozen_terminal_starts_in_home(tmp_path) -> None:
    assert paths.default_terminal_cwd(frozen=True, home=tmp_path) == tmp_path


def test_runtime_paths_derive_unified_data_from_explicit_reports_root(
    tmp_path,
) -> None:
    reports_root = tmp_path / "reports"

    resolved = resolve_runtime_paths(reports_root=reports_root)

    assert resolved.data_root == tmp_path
    assert resolved.config_root == tmp_path / "config"
    assert resolved.reports_root == reports_root
    assert resolved.memos_root == tmp_path / "memos"
    assert (
        resolved.terminal_state_path
        == tmp_path / "config" / "terminal-sessions.json"
    )
    assert (
        resolved.database_state_path
        == tmp_path / "config" / "database-connections.json"
    )
    assert resolved.terminal_cwd == tmp_path


def test_runtime_paths_support_explicit_data_root(tmp_path) -> None:
    data_root = tmp_path / "custom-working"

    resolved = resolve_runtime_paths(data_root=data_root)

    assert resolved.data_root == data_root
    assert resolved.config_root == data_root / "config"
    assert resolved.reports_root == data_root / "reports"
    assert resolved.memos_root == data_root / "memos"
    assert resolved.terminal_state_path == (
        data_root / "config" / "terminal-sessions.json"
    )
    assert resolved.database_state_path == (
        data_root / "config" / "database-connections.json"
    )
    assert resolved.terminal_cwd == data_root


def test_runtime_paths_respect_explicit_overrides(tmp_path) -> None:
    resolved = resolve_runtime_paths(
        data_root=tmp_path / "data",
        config_root=tmp_path / "custom-config",
        reports_root=tmp_path / "custom-reports",
        memos_root=tmp_path / "custom-memos",
        terminal_state_path=tmp_path / "custom-terminal.json",
        database_state_path=tmp_path / "custom-database.json",
        terminal_cwd=tmp_path / "workspace",
    )

    assert resolved.data_root == tmp_path / "data"
    assert resolved.config_root == tmp_path / "custom-config"
    assert resolved.reports_root == tmp_path / "custom-reports"
    assert resolved.memos_root == tmp_path / "custom-memos"
    assert resolved.terminal_state_path == tmp_path / "custom-terminal.json"
    assert resolved.database_state_path == tmp_path / "custom-database.json"
    assert resolved.terminal_cwd == tmp_path / "workspace"


def test_data_directory_names_are_centralized() -> None:
    assert paths.APP_DIR_NAME == DATA_DIR_NAME == "WorKing"
    assert (
        paths.LEGACY_APP_DIR_NAME
        == LEGACY_DATA_DIR_NAME
        == "DailyReportSupporter"
    )
