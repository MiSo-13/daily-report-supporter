from __future__ import annotations

import sys
from pathlib import Path

from app.app_meta import DATA_DIR_NAME, LEGACY_DATA_DIR_NAME

APP_DIR_NAME = DATA_DIR_NAME
LEGACY_APP_DIR_NAME = LEGACY_DATA_DIR_NAME


def source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return source_root()


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def default_data_root(
    *,
    home: Path | None = None,
) -> Path:
    home_dir = Path.home() if home is None else Path(home)
    return home_dir / APP_DIR_NAME


def legacy_data_root(
    *,
    home: Path | None = None,
) -> Path:
    home_dir = Path.home() if home is None else Path(home)
    return home_dir / LEGACY_APP_DIR_NAME


def default_config_root(
    *,
    home: Path | None = None,
) -> Path:
    return default_data_root(home=home) / "config"


def default_reports_root(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    # frozen 인자는 기존 호출부 호환을 위해 유지한다.
    _ = frozen
    return default_data_root(home=home) / "reports"


def default_memos_root(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    # frozen 인자는 기존 호출부 호환을 위해 유지한다.
    _ = frozen
    return default_data_root(home=home) / "memos"


def default_terminal_state_path(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    # frozen 인자는 기존 호출부 호환을 위해 유지한다.
    _ = frozen
    return default_config_root(home=home) / "terminal-sessions.json"


def default_database_state_path(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    # frozen 인자는 기존 호출부 호환을 위해 유지한다.
    _ = frozen
    return default_config_root(home=home) / "database-connections.json"


def default_terminal_cwd(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return Path.home() if home is None else Path(home)
    return source_root()
