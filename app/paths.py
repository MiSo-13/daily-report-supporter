from __future__ import annotations

import sys
from pathlib import Path

APP_DIR_NAME = "DailyReportSupporter"


def source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return source_root()


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def default_reports_root(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        home_dir = Path.home() if home is None else home
        return home_dir / APP_DIR_NAME / "reports"
    return source_root() / "reports"


def default_memos_root(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        home_dir = Path.home() if home is None else home
        return home_dir / APP_DIR_NAME / "memos"
    return source_root() / "memos"


def default_terminal_state_path(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        home_dir = Path.home() if home is None else home
        return home_dir / APP_DIR_NAME / "terminal-sessions.json"
    return source_root() / "terminal-sessions.json"


def default_terminal_cwd(
    *,
    frozen: bool | None = None,
    home: Path | None = None,
) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return Path.home() if home is None else home
    return source_root()
