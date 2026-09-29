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
