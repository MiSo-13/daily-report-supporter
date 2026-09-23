from __future__ import annotations

import os
import sys
from collections.abc import MutableMapping


def configure_qt_platform(
    env: MutableMapping[str, str] | None = None,
    platform: str | None = None,
) -> str | None:
    target_env = env if env is not None else os.environ
    current_platform = platform if platform is not None else sys.platform

    if not current_platform.startswith("linux"):
        return target_env.get("QT_QPA_PLATFORM")

    explicit = target_env.get("DAILY_REPORT_QT_PLATFORM")
    if explicit:
        target_env["QT_QPA_PLATFORM"] = explicit
        return explicit

    # Crostini/Wayland처럼 Wayland와 X11이 함께 제공되는 환경에서는
    # QMenu/QDialog popup surface 종료 시 연결이 끊기는 Qt/Wayland 문제를
    # 피하기 위해 xcb(X11)를 기본값으로 사용한다.
    if target_env.get("DISPLAY"):
        target_env["QT_QPA_PLATFORM"] = "xcb"
        return "xcb"

    return target_env.get("QT_QPA_PLATFORM")
