from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from app.paths import (
    default_config_root,
    default_data_root,
    legacy_data_root,
    source_root,
)


MIGRATION_VERSION = 1
MIGRATION_MARKER_NAME = f"migration-v{MIGRATION_VERSION}.json"


@dataclass(frozen=True, slots=True)
class MigrationResult:
    migrated: bool
    already_completed: bool
    copied_files: int
    skipped_files: int
    source_roots: tuple[Path, ...]
    errors: tuple[str, ...]

    @property
    def startup_message(self) -> str:
        if self.errors:
            return (
                "기존 데이터 마이그레이션 일부 실패 · "
                "다음 실행에서 다시 시도합니다."
            )
        if self.migrated:
            return (
                f"기존 WorKing 데이터 마이그레이션 완료 · "
                f"{self.copied_files}개 파일"
            )
        return ""


def migrate_legacy_data(
    *,
    home: Path | None = None,
    legacy_source_root: Path | None = None,
    frozen: bool | None = None,
) -> MigrationResult:
    """구버전 데이터를 새 WorKing 데이터 디렉터리로 안전하게 복사한다."""
    data_root = default_data_root(home=home)
    config_root = default_config_root(home=home)
    marker_path = config_root / MIGRATION_MARKER_NAME

    if marker_path.exists():
        return MigrationResult(
            migrated=False,
            already_completed=True,
            copied_files=0,
            skipped_files=0,
            source_roots=(),
            errors=(),
        )

    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    candidates: list[Path] = [legacy_data_root(home=home)]

    if not is_frozen:
        source_candidate = (
            source_root()
            if legacy_source_root is None
            else Path(legacy_source_root)
        )
        if source_candidate not in candidates and source_candidate != data_root:
            candidates.append(source_candidate)

    existing_sources = tuple(
        candidate
        for candidate in candidates
        if _has_legacy_data(candidate)
    )

    copied = 0
    skipped = 0
    errors: list[str] = []

    for legacy_root in existing_sources:
        report_result = _copy_tree_missing(
            legacy_root / "reports",
            data_root / "reports",
            skip_relative={Path("settings.json")},
        )
        copied += report_result[0]
        skipped += report_result[1]
        errors.extend(report_result[2])

        memo_result = _copy_tree_missing(
            legacy_root / "memos",
            data_root / "memos",
        )
        copied += memo_result[0]
        skipped += memo_result[1]
        errors.extend(memo_result[2])

        for source, destination in (
            (
                legacy_root / "reports" / "settings.json",
                config_root / "settings.json",
            ),
            (
                legacy_root / "terminal-sessions.json",
                config_root / "terminal-sessions.json",
            ),
            (
                legacy_root / "database-connections.json",
                config_root / "database-connections.json",
            ),
        ):
            file_result = _copy_file_missing(source, destination)
            copied += file_result[0]
            skipped += file_result[1]
            errors.extend(file_result[2])

    if not errors:
        try:
            config_root.mkdir(parents=True, exist_ok=True)
            _write_marker(
                marker_path,
                existing_sources,
                copied_files=copied,
                skipped_files=skipped,
            )
        except OSError as exc:
            errors.append(f"{marker_path}: {exc}")

    return MigrationResult(
        migrated=copied > 0,
        already_completed=False,
        copied_files=copied,
        skipped_files=skipped,
        source_roots=existing_sources,
        errors=tuple(errors),
    )


def _has_legacy_data(root: Path) -> bool:
    return any(
        path.exists()
        for path in (
            root / "reports",
            root / "memos",
            root / "terminal-sessions.json",
            root / "database-connections.json",
        )
    )


def _copy_tree_missing(
    source: Path,
    destination: Path,
    *,
    skip_relative: set[Path] | None = None,
) -> tuple[int, int, list[str]]:
    if not source.is_dir():
        return 0, 0, []

    skip_relative = skip_relative or set()
    copied = 0
    skipped = 0
    errors: list[str] = []

    for source_path in source.rglob("*"):
        if not source_path.is_file():
            continue

        relative = source_path.relative_to(source)
        if relative in skip_relative:
            continue

        destination_path = destination / relative
        result = _copy_file_missing(source_path, destination_path)
        copied += result[0]
        skipped += result[1]
        errors.extend(result[2])

    return copied, skipped, errors


def _copy_file_missing(
    source: Path,
    destination: Path,
) -> tuple[int, int, list[str]]:
    if not source.is_file():
        return 0, 0, []

    if destination.exists():
        return 0, 1, []

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except OSError as exc:
        return 0, 0, [f"{source} -> {destination}: {exc}"]

    return 1, 0, []


def _write_marker(
    marker_path: Path,
    source_roots: tuple[Path, ...],
    *,
    copied_files: int,
    skipped_files: int,
) -> None:
    payload = {
        "version": MIGRATION_VERSION,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_roots": [str(path) for path in source_roots],
        "copied_files": copied_files,
        "skipped_files": skipped_files,
    }

    temp_path = marker_path.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(marker_path)
