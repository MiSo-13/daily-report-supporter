from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from app.app_meta import (
    LEGACY_DATA_DIR_NAME,
    PORTABLE_DATA_DIR_NAME,
    TRANSITIONAL_DATA_DIR_NAME,
)

APP_DIR_NAME = PORTABLE_DATA_DIR_NAME
LEGACY_APP_DIR_NAME = LEGACY_DATA_DIR_NAME
TRANSITIONAL_APP_DIR_NAME = TRANSITIONAL_DATA_DIR_NAME


def source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return source_root()


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def app_root(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    """사용자 데이터의 기준이 되는 프로젝트/실행파일 디렉터리를 반환한다."""
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not is_frozen:
        return source_root()

    executable_path = Path(
        sys.executable if executable is None else executable
    ).resolve()
    current_platform = sys.platform if platform is None else platform

    if current_platform == "darwin":
        for parent in executable_path.parents:
            if parent.name.endswith(".app"):
                return parent.parent

    return executable_path.parent


def default_data_root(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return app_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    ) / PORTABLE_DATA_DIR_NAME


def legacy_data_root(
    *,
    home: Path | None = None,
) -> Path:
    home_dir = Path.home() if home is None else Path(home)
    return home_dir / LEGACY_APP_DIR_NAME


def transitional_data_root(
    *,
    home: Path | None = None,
) -> Path:
    home_dir = Path.home() if home is None else Path(home)
    return home_dir / TRANSITIONAL_APP_DIR_NAME


def default_config_root(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return default_data_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    ) / "config"


def default_reports_root(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return default_data_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    ) / "reports"


def default_memos_root(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return default_data_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    ) / "memos"


def default_terminal_state_path(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return default_config_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    ) / "terminal-sessions.json"


def default_database_state_path(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return default_config_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    ) / "database-connections.json"


def default_terminal_cwd(
    *,
    frozen: bool | None = None,
    executable: Path | str | None = None,
    platform: str | None = None,
) -> Path:
    return app_root(
        frozen=frozen,
        executable=executable,
        platform=platform,
    )


def ensure_data_root_writable(
    data_root: Path | str | None = None,
) -> Path:
    """Portable data 디렉터리에 실제 쓰기가 가능한지 확인한다."""
    root = default_data_root() if data_root is None else Path(data_root)
    root.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        prefix=".working-write-",
        dir=root,
        delete=True,
    ):
        pass

    return root
