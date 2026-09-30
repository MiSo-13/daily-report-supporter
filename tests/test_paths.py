from __future__ import annotations

import sys

from app import paths


def test_source_build_uses_repository_reports() -> None:
    assert (
        paths.default_reports_root(frozen=False)
        == paths.source_root() / "reports"
    )


def test_frozen_build_uses_home_directory(tmp_path) -> None:
    assert (
        paths.default_reports_root(frozen=True, home=tmp_path)
        == tmp_path / "DailyReportSupporter" / "reports"
    )


def test_resource_path_uses_meipass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert (
        paths.resource_path("scripts", "setup_crostini.sh")
        == tmp_path / "scripts" / "setup_crostini.sh"
    )



def test_source_build_uses_repository_memos() -> None:
    assert (
        paths.default_memos_root(frozen=False)
        == paths.source_root() / "memos"
    )


def test_frozen_build_uses_home_memos_directory(tmp_path) -> None:
    assert (
        paths.default_memos_root(frozen=True, home=tmp_path)
        == tmp_path / "DailyReportSupporter" / "memos"
    )



def test_source_build_uses_repository_terminal_state() -> None:
    assert (
        paths.default_terminal_state_path(frozen=False)
        == paths.source_root() / "terminal-sessions.json"
    )


def test_frozen_build_uses_home_terminal_state(tmp_path) -> None:
    assert (
        paths.default_terminal_state_path(frozen=True, home=tmp_path)
        == tmp_path / "DailyReportSupporter" / "terminal-sessions.json"
    )


def test_source_terminal_starts_in_repository() -> None:
    assert paths.default_terminal_cwd(frozen=False) == paths.source_root()


def test_frozen_terminal_starts_in_home(tmp_path) -> None:
    assert paths.default_terminal_cwd(frozen=True, home=tmp_path) == tmp_path
