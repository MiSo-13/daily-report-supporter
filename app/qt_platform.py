from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import MutableMapping
from pathlib import Path

SAFE_UI_ENV = "DAILY_REPORT_SAFE_UI"


def _xcb_dependencies_available() -> bool:
    spec = importlib.util.find_spec("PyQt6")
    if spec is None or spec.origin is None:
        return False

    plugin = (
        Path(spec.origin).resolve().parent
        / "Qt6"
        / "plugins"
        / "platforms"
        / "libqxcb.so"
    )
    if not plugin.exists():
        return False

    try:
        result = subprocess.run(
            ["ldd", str(plugin)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    output = f"{result.stdout}\n{result.stderr}"
    return result.returncode == 0 and "not found" not in output.lower()


def configure_qt_platform(
    env: MutableMapping[str, str] | None = None,
    platform: str | None = None,
    xcb_usable: bool | None = None,
) -> str | None:
    target_env = env if env is not None else os.environ
    current_platform = platform if platform is not None else sys.platform

    if not current_platform.startswith("linux"):
        target_env.pop(SAFE_UI_ENV, None)
        return target_env.get("QT_QPA_PLATFORM")

    explicit = target_env.get("DAILY_REPORT_QT_PLATFORM")
    if explicit:
        target_env["QT_QPA_PLATFORM"] = explicit
        if explicit.startswith("wayland"):
            target_env[SAFE_UI_ENV] = "1"
        else:
            target_env.pop(SAFE_UI_ENV, None)
        return explicit

    can_use_xcb = (
        _xcb_dependencies_available() if xcb_usable is None else xcb_usable
    )

    if target_env.get("DISPLAY") and can_use_xcb:
        target_env["QT_QPA_PLATFORM"] = "xcb"
        target_env.pop(SAFE_UI_ENV, None)
        return "xcb"

    # xcb plugin 또는 그 native dependency가 부족하면 Qt의 기본/Wayland
    # backend를 유지한다. 이 경우 popup QMenu/QDialog를 만들지 않는 안전 UI를 쓴다.
    if target_env.get("WAYLAND_DISPLAY"):
        target_env["QT_QPA_PLATFORM"] = "wayland"
        selected = "wayland"
    else:
        target_env.pop("QT_QPA_PLATFORM", None)
        selected = None

    target_env[SAFE_UI_ENV] = "1"
    return selected


def safe_ui_enabled(env: MutableMapping[str, str] | None = None) -> bool:
    target_env = env if env is not None else os.environ
    return target_env.get(SAFE_UI_ENV) == "1"
