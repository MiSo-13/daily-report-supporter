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


def default_reports_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path.home() / APP_DIR_NAME / "reports"
    return source_root() / "reports"
