from __future__ import annotations

import json

from app.data_migration import (
    MIGRATION_MARKER_NAME,
    migrate_legacy_data,
)


def test_packaged_legacy_data_is_copied_to_portable_directory(tmp_path) -> None:
    home = tmp_path / "home"
    app_root = tmp_path / "portable"
    data_root = app_root / "data"
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

    result = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

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


def test_source_run_legacy_data_is_migrated_to_repository_data(
    tmp_path,
) -> None:
    home = tmp_path / "home"
    old_source = tmp_path / "checkout"
    data_root = old_source / "data"

    report = old_source / "reports" / "2026" / "09" / "260930.md"
    report.parent.mkdir(parents=True)
    report.write_text("# 소스 실행 보고서", encoding="utf-8")
    (old_source / "terminal-sessions.json").write_text(
        '{"sessions": [{"name": "Local"}]}',
        encoding="utf-8",
    )

    result = migrate_legacy_data(
        data_root=data_root,
        home=home,
        legacy_source_root=old_source,
        frozen=False,
    )

    assert result.migrated is True
    assert (
        data_root / "reports" / "2026" / "09" / "260930.md"
    ).exists()
    assert (
        data_root / "config" / "terminal-sessions.json"
    ).exists()


def test_transitional_home_working_data_is_migrated(tmp_path) -> None:
    home = tmp_path / "home"
    data_root = tmp_path / "portable" / "data"
    transitional = home / "WorKing"

    report = transitional / "reports" / "2026" / "10" / "261002.md"
    report.parent.mkdir(parents=True)
    report.write_text("# 전환 버전 보고서", encoding="utf-8")

    config = transitional / "config"
    config.mkdir(parents=True)
    (config / "settings.json").write_text(
        '{"theme": "Dark"}',
        encoding="utf-8",
    )
    (config / "terminal-sessions.json").write_text(
        '{"sessions": []}',
        encoding="utf-8",
    )

    result = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

    assert result.migrated is True
    assert (
        data_root / "reports" / "2026" / "10" / "261002.md"
    ).exists()
    assert (
        data_root / "config" / "settings.json"
    ).read_text(encoding="utf-8") == '{"theme": "Dark"}'
    assert (data_root / "config" / "terminal-sessions.json").exists()


def test_existing_portable_files_are_never_overwritten(tmp_path) -> None:
    home = tmp_path / "home"
    data_root = tmp_path / "portable" / "data"
    legacy = home / "DailyReportSupporter"

    old_report = legacy / "reports" / "2026" / "10" / "261001.md"
    old_report.parent.mkdir(parents=True)
    old_report.write_text("구버전", encoding="utf-8")

    new_report = data_root / "reports" / "2026" / "10" / "261001.md"
    new_report.parent.mkdir(parents=True)
    new_report.write_text("Portable", encoding="utf-8")

    old_settings = legacy / "reports" / "settings.json"
    old_settings.write_text('{"theme": "Light"}', encoding="utf-8")
    new_settings = data_root / "config" / "settings.json"
    new_settings.parent.mkdir(parents=True)
    new_settings.write_text('{"theme": "Dark"}', encoding="utf-8")

    result = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

    assert result.skipped_files == 2
    assert new_report.read_text(encoding="utf-8") == "Portable"
    assert new_settings.read_text(encoding="utf-8") == '{"theme": "Dark"}'


def test_completed_migration_does_not_run_twice(tmp_path) -> None:
    home = tmp_path / "home"
    data_root = tmp_path / "portable" / "data"
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

    first = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )
    legacy_report.write_text("나중에 바뀐 구버전", encoding="utf-8")
    second = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

    assert first.migrated is True
    assert second.already_completed is True
    assert (
        data_root / "reports" / "2026" / "10" / "261001.md"
    ).read_text(encoding="utf-8") == "첫 데이터"


def test_migration_marker_records_sources_and_counts(tmp_path) -> None:
    home = tmp_path / "home"
    data_root = tmp_path / "portable" / "data"
    legacy = home / "DailyReportSupporter"
    legacy.mkdir(parents=True)
    (legacy / "terminal-sessions.json").write_text(
        '{"sessions": []}',
        encoding="utf-8",
    )

    result = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

    marker = data_root / "config" / MIGRATION_MARKER_NAME
    payload = json.loads(marker.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["copied_files"] == result.copied_files == 1
    assert payload["source_roots"] == [str(legacy)]


def test_fresh_install_creates_marker_inside_portable_data(
    tmp_path,
) -> None:
    home = tmp_path / "home"
    data_root = tmp_path / "portable" / "data"

    result = migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

    assert result.migrated is False
    assert result.startup_message == ""
    assert (
        data_root / "config" / MIGRATION_MARKER_NAME
    ).exists()
    assert not (home / "WorKing").exists()


def test_migration_writes_nothing_to_legacy_home_directories(
    tmp_path,
) -> None:
    home = tmp_path / "home"
    data_root = tmp_path / "portable" / "data"
    legacy = home / "DailyReportSupporter"

    report = legacy / "reports" / "2026" / "10" / "261001.md"
    report.parent.mkdir(parents=True)
    report.write_text("기존", encoding="utf-8")

    before = sorted(
        str(path.relative_to(home))
        for path in home.rglob("*")
    )

    migrate_legacy_data(
        data_root=data_root,
        home=home,
        frozen=True,
    )

    after_legacy = sorted(
        str(path.relative_to(home))
        for path in legacy.rglob("*")
    )
    before_legacy = sorted(
        item
        for item in before
        if item.startswith("DailyReportSupporter")
    )

    assert after_legacy == [
        item
        for item in before_legacy
        if item != "DailyReportSupporter"
    ]
