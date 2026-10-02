from __future__ import annotations

import sys

import pytest

from app import paths
from app.app_meta import (
    LEGACY_DATA_DIR_NAME,
    PORTABLE_DATA_DIR_NAME,
    TRANSITIONAL_DATA_DIR_NAME,
)
from app.runtime_paths import resolve_runtime_paths


def test_source_build_uses_repository_as_app_root() -> None:
    assert paths.app_root(frozen=False) == paths.source_root()
    assert (
        paths.default_data_root(frozen=False)
        == paths.source_root() / "data"
    )


def test_windows_executable_uses_executable_directory(tmp_path) -> None:
    executable = tmp_path / "WorKing.exe"

    assert paths.app_root(
        frozen=True,
        executable=executable,
        platform="win32",
    ) == tmp_path
    assert paths.default_data_root(
        frozen=True,
        executable=executable,
        platform="win32",
    ) == tmp_path / "data"


def test_linux_executable_uses_executable_directory(tmp_path) -> None:
    executable = tmp_path / "WorKing"

    assert paths.app_root(
        frozen=True,
        executable=executable,
        platform="linux",
    ) == tmp_path
    assert paths.default_data_root(
        frozen=True,
        executable=executable,
        platform="linux",
    ) == tmp_path / "data"


def test_macos_bundle_uses_directory_outside_app_bundle(tmp_path) -> None:
    executable = (
        tmp_path
        / "WorKing.app"
        / "Contents"
        / "MacOS"
        / "WorKing"
    )

    assert paths.app_root(
        frozen=True,
        executable=executable,
        platform="darwin",
    ) == tmp_path
    assert paths.default_data_root(
        frozen=True,
        executable=executable,
        platform="darwin",
    ) == tmp_path / "data"


def test_config_files_are_grouped_under_portable_data(tmp_path) -> None:
    executable = tmp_path / "WorKing.exe"
    kwargs = {
        "frozen": True,
        "executable": executable,
        "platform": "win32",
    }

    assert paths.default_config_root(**kwargs) == tmp_path / "data" / "config"
    assert paths.default_reports_root(**kwargs) == tmp_path / "data" / "reports"
    assert paths.default_memos_root(**kwargs) == tmp_path / "data" / "memos"
    assert paths.default_terminal_state_path(**kwargs) == (
        tmp_path / "data" / "config" / "terminal-sessions.json"
    )
    assert paths.default_database_state_path(**kwargs) == (
        tmp_path / "data" / "config" / "database-connections.json"
    )


def test_legacy_home_directories_are_only_migration_sources(tmp_path) -> None:
    assert paths.legacy_data_root(home=tmp_path) == (
        tmp_path / "DailyReportSupporter"
    )
    assert paths.transitional_data_root(home=tmp_path) == (
        tmp_path / "WorKing"
    )


def test_resource_path_uses_meipass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert (
        paths.resource_path("scripts", "setup_crostini.sh")
        == tmp_path / "scripts" / "setup_crostini.sh"
    )


def test_source_terminal_starts_in_repository() -> None:
    assert paths.default_terminal_cwd(frozen=False) == paths.source_root()


def test_packaged_terminal_starts_next_to_executable(tmp_path) -> None:
    executable = tmp_path / "WorKing.exe"

    assert paths.default_terminal_cwd(
        frozen=True,
        executable=executable,
        platform="win32",
    ) == tmp_path


def test_runtime_paths_derive_data_from_explicit_reports_root(
    tmp_path,
) -> None:
    reports_root = tmp_path / "data" / "reports"

    resolved = resolve_runtime_paths(reports_root=reports_root)

    assert resolved.data_root == tmp_path / "data"
    assert resolved.config_root == tmp_path / "data" / "config"
    assert resolved.reports_root == reports_root
    assert resolved.memos_root == tmp_path / "data" / "memos"
    assert (
        resolved.terminal_state_path
        == tmp_path / "data" / "config" / "terminal-sessions.json"
    )
    assert (
        resolved.database_state_path
        == tmp_path / "data" / "config" / "database-connections.json"
    )
    assert resolved.terminal_cwd == tmp_path / "data"


def test_runtime_paths_support_explicit_data_root(tmp_path) -> None:
    data_root = tmp_path / "portable-data"

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


def test_writable_check_creates_only_requested_data_root(tmp_path) -> None:
    data_root = tmp_path / "portable" / "data"

    result = paths.ensure_data_root_writable(data_root)

    assert result == data_root
    assert data_root.is_dir()
    assert list(data_root.iterdir()) == []


def test_writable_check_fails_when_data_root_is_a_file(tmp_path) -> None:
    data_root = tmp_path / "data"
    data_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(OSError):
        paths.ensure_data_root_writable(data_root)


def test_data_directory_names_are_centralized() -> None:
    assert paths.APP_DIR_NAME == PORTABLE_DATA_DIR_NAME == "data"
    assert (
        paths.LEGACY_APP_DIR_NAME
        == LEGACY_DATA_DIR_NAME
        == "DailyReportSupporter"
    )
    assert (
        paths.TRANSITIONAL_APP_DIR_NAME
        == TRANSITIONAL_DATA_DIR_NAME
        == "WorKing"
    )
