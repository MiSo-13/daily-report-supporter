from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from collections.abc import Iterable, MutableMapping
from pathlib import Path

CROSTINI_MARKER_PATHS = (
    Path("/mnt/chromeos"),
    Path("/opt/google/cros-containers"),
)

LIBRARY_TO_DEBIAN_PACKAGE = {
    "libX11-xcb.so.1": "libx11-xcb1",
    "libX11.so.6": "libx11-6",
    "libXext.so.6": "libxext6",
    "libXfixes.so.3": "libxfixes3",
    "libXi.so.6": "libxi6",
    "libXrender.so.1": "libxrender1",
    "libICE.so.6": "libice6",
    "libSM.so.6": "libsm6",
    "libfontconfig.so.1": "libfontconfig1",
    "libfreetype.so.6": "libfreetype6",
    "libxcb.so.1": "libxcb1",
    "libxcb-cursor.so.0": "libxcb-cursor0",
    "libxcb-icccm.so.4": "libxcb-icccm4",
    "libxcb-image.so.0": "libxcb-image0",
    "libxcb-keysyms.so.1": "libxcb-keysyms1",
    "libxcb-randr.so.0": "libxcb-randr0",
    "libxcb-render-util.so.0": "libxcb-render-util0",
    "libxcb-shape.so.0": "libxcb-shape0",
    "libxcb-shm.so.0": "libxcb-shm0",
    "libxcb-sync.so.1": "libxcb-sync1",
    "libxcb-util.so.1": "libxcb-util1",
    "libxcb-xfixes.so.0": "libxcb-xfixes0",
    "libxcb-xkb.so.1": "libxcb-xkb1",
    "libxkbcommon.so.0": "libxkbcommon0",
    "libxkbcommon-x11.so.0": "libxkbcommon-x11-0",
}

NOT_FOUND_RE = re.compile(r"^\s*(?P<library>\S+)\s+=>\s+not found\s*$")


class CrostiniDependencyError(RuntimeError):
    def __init__(
        self,
        reason: str,
        missing_libraries: tuple[str, ...] = (),
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.missing_libraries = missing_libraries

    @property
    def install_packages(self) -> tuple[str, ...]:
        packages = {
            package
            for library in self.missing_libraries
            if (package := LIBRARY_TO_DEBIAN_PACKAGE.get(library))
        }
        return tuple(sorted(packages))

    def user_message(self) -> str:
        lines = [
            "Daily Report Supporter를 ChromeOS/Crostini에서 실행하기 위한 X11 의존성이 부족합니다.",
            "",
            self.reason,
        ]

        if self.missing_libraries:
            lines.extend(
                [
                    "",
                    "누락된 라이브러리:",
                    *[f"  - {library}" for library in self.missing_libraries],
                ]
            )

        if self.install_packages:
            packages = " ".join(self.install_packages)
            lines.extend(
                [
                    "",
                    "다음 명령으로 필요한 패키지를 설치한 뒤 다시 실행하세요:",
                    f"  sudo apt update && sudo apt install -y {packages}",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "저장소의 Crostini 설치 스크립트를 실행하세요:",
                    "  bash scripts/setup_crostini.sh",
                ]
            )

        lines.extend(
            [
                "",
                "설치 후:",
                "  python main.py",
            ]
        )
        return "\n".join(lines)


def is_crostini(
    env: MutableMapping[str, str] | None = None,
    marker_results: Iterable[bool] | None = None,
) -> bool:
    target_env = env if env is not None else os.environ

    if target_env.get("SOMMELIER_VERSION"):
        return True
    if target_env.get("CROS_USER_ID_HASH"):
        return True

    if marker_results is not None:
        return any(marker_results)

    return any(path.exists() for path in CROSTINI_MARKER_PATHS)


def _find_xcb_plugin() -> Path | None:
    spec = importlib.util.find_spec("PyQt6")
    if spec is None or spec.origin is None:
        return None

    plugin = (
        Path(spec.origin).resolve().parent
        / "Qt6"
        / "plugins"
        / "platforms"
        / "libqxcb.so"
    )
    return plugin if plugin.exists() else None


def missing_xcb_libraries(plugin: Path | None = None) -> tuple[str, ...]:
    target = plugin or _find_xcb_plugin()
    if target is None:
        return ("libqxcb.so",)

    try:
        result = subprocess.run(
            ["ldd", str(target)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ("ldd-unavailable",)

    missing: list[str] = []
    for line in f"{result.stdout}\n{result.stderr}".splitlines():
        match = NOT_FOUND_RE.match(line)
        if match:
            missing.append(match.group("library"))

    return tuple(sorted(set(missing)))


def install_crostini_dependencies(
    script_path: Path | None = None,
) -> bool:
    script = (
        script_path
        if script_path is not None
        else Path(__file__).resolve().parent.parent / "scripts" / "setup_crostini.sh"
    )
    if not script.exists():
        return False

    try:
        result = subprocess.run(
            ["bash", str(script)],
            check=False,
        )
    except OSError:
        return False

    return result.returncode == 0


def configure_qt_platform(
    env: MutableMapping[str, str] | None = None,
    platform: str | None = None,
    crostini: bool | None = None,
    missing_libraries: tuple[str, ...] | None = None,
) -> str | None:
    target_env = env if env is not None else os.environ
    current_platform = platform if platform is not None else sys.platform

    # Windows와 macOS는 Qt가 제공하는 기본 QPA plugin을 그대로 사용한다.
    if not current_platform.startswith("linux"):
        return target_env.get("QT_QPA_PLATFORM")

    # 일반 Linux도 사용자가 지정한 값 또는 Qt의 기본 선택을 존중한다.
    running_crostini = is_crostini(target_env) if crostini is None else crostini
    if not running_crostini:
        return target_env.get("QT_QPA_PLATFORM")

    if not target_env.get("DISPLAY"):
        raise CrostiniDependencyError(
            "Crostini X11 DISPLAY를 찾지 못했습니다. Sommelier/XWayland 세션을 확인하세요."
        )

    missing = (
        missing_xcb_libraries()
        if missing_libraries is None
        else tuple(sorted(set(missing_libraries)))
    )
    if missing:
        raise CrostiniDependencyError(
            "이 환경에서는 Qt Wayland 연결이 불안정하므로 X11(xcb) 모드가 필요합니다.",
            missing,
        )

    target_env["QT_QPA_PLATFORM"] = "xcb"
    return "xcb"
