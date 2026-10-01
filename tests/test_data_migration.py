from __future__ import annotations

import json

from app.data_migration import (
    MIGRATION_MARKER_NAME,
    migrate_legacy_data,
)


def test_packaged_legacy_data_is_copied_to_unified_directory(tmp_path) -> None:
    home = tmp_path / "home"
    legacy = home / "DailyReportSupporter"

    report = legacy / "reports" / "2026" / "10" / "261001.md"
    report.parent.mkdir(parents=True)
    report.write_text("# 기존 보고서", encoding="utf-8")

    settings = legacy / "reports" / "settings.json"
    settings.write_text('{"theme": "Nord"}', encoding="utf-8")

    memo = legacy / "memos" / "memo-1.md"
    memo.parent.mkdir(parents=True)
    memo.write_text("# 기존 메모", encoding="utf-8")
    (legacy / "memos" / ".order.json").write_text(
        '["memo-1"]',
        encoding="utf-8",
    )

    (legacy / "terminal-sessions.json").write_text(
        '{"sessions": []}',
        encoding="utf-8",
    )
    (legacy / "database-connections.json").write_text(
        '{"connections": []}',
        encoding="utf-8",
    )

    result = migrate_legacy_data(home=home, frozen=True)

    data_root = home / "WorKing"
    assert result.migrated is True
    assert result.errors == ()
    assert (
        data_root / "reports" / "2026" / "10" / "261001.md"
    ).read_text(encoding="utf-8") == "# 기존 보고서"
    assert (
        data_root / "memos" / "memo-1.md"
    ).read_text(encoding="utf-8") == "# 기존 메모"
    assert (data_root / "memos" / ".order.json").exists()
    assert (
        data_root / "config" / "settings.json"
    ).read_text(encoding="utf-8") == '{"theme": "Nord"}'
    assert (data_root / "config" / "terminal-sessions.json").exists()
    assert (data_root / "config" / "database-connections.json").exists()
    assert not (data_root / "reports" / "settings.json").exists()

    # 구버전 데이터는 롤백을 위해 그대로 보존한다.
    assert report.exists()
    assert memo.exists()


def test_source_run_legacy_data_is_also_migrated(tmp_path) -> None:
    home = tmp_path / "home"
    old_source = tmp_path / "checkout"
    report = old_source / "reports" / "2026" / "09" / "260930.md"
    report.parent.mkdir(parents=True)
    report.write_text("# 소스 실행 보고서", encoding="utf-8")
    (old_source / "terminal-sessions.json").write_text(
        '{"sessions": [{"name": "Local"}]}',
        encoding="utf-8",
    )

    result = migrate_legacy_data(
        home=home,
        legacy_source_root=old_source,
        frozen=False,
    )

    assert result.migrated is True
    assert (
        home / "WorKing" / "reports" / "2026" / "09" / "260930.md"
    ).exists()
    assert (
        home / "WorKing" / "config" / "terminal-sessions.json"
    ).exists()


def test_existing_new_files_are_never_overwritten(tmp_path) -> None:
    home = tmp_path / "home"
    legacy = home / "DailyReportSupporter"
    old_report = legacy / "reports" / "2026" / "10" / "261001.md"
    old_report.parent.mkdir(parents=True)
    old_report.write_text("구버전", encoding="utf-8")

    new_report = home / "WorKing" / "reports" / "2026" / "10" / "261001.md"
    new_report.parent.mkdir(parents=True)
    new_report.write_text("새버전", encoding="utf-8")

    old_settings = legacy / "reports" / "settings.json"
    old_settings.write_text('{"theme": "Light"}', encoding="utf-8")
    new_settings = home / "WorKing" / "config" / "settings.json"
    new_settings.parent.mkdir(parents=True)
    new_settings.write_text('{"theme": "Dark"}', encoding="utf-8")

    result = migrate_legacy_data(home=home, frozen=True)

    assert result.skipped_files == 2
    assert new_report.read_text(encoding="utf-8") == "새버전"
    assert new_settings.read_text(encoding="utf-8") == '{"theme": "Dark"}'


def test_completed_migration_does_not_run_twice(tmp_path) -> None:
    home = tmp_path / "home"
    legacy_report = (
        home
        / "DailyReportSupporter"
        / "reports"
        / "2026"
        / "10"
        / "261001.md"
    )
    legacy_report.parent.mkdir(parents=True)
    legacy_report.write_text("첫 데이터", encoding="utf-8")

    first = migrate_legacy_data(home=home, frozen=True)
    legacy_report.write_text("나중에 바뀐 구버전", encoding="utf-8")
    second = migrate_legacy_data(home=home, frozen=True)

    assert first.migrated is True
    assert second.already_completed is True
    assert (
        home / "WorKing" / "reports" / "2026" / "10" / "261001.md"
    ).read_text(encoding="utf-8") == "첫 데이터"


def test_migration_marker_records_sources_and_counts(tmp_path) -> None:
    home = tmp_path / "home"
    legacy = home / "DailyReportSupporter"
    legacy.mkdir(parents=True)
    (legacy / "terminal-sessions.json").write_text(
        '{"sessions": []}',
        encoding="utf-8",
    )

    result = migrate_legacy_data(home=home, frozen=True)

    marker = (
        home
        / "WorKing"
        / "config"
        / MIGRATION_MARKER_NAME
    )
    payload = json.loads(marker.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["copied_files"] == result.copied_files == 1
    assert payload["source_roots"] == [str(legacy)]


def test_fresh_install_creates_marker_without_migration_message(
    tmp_path,
) -> None:
    home = tmp_path / "home"

    result = migrate_legacy_data(home=home, frozen=True)

    assert result.migrated is False
    assert result.startup_message == ""
    assert (
        home / "WorKing" / "config" / MIGRATION_MARKER_NAME
    ).exists()
