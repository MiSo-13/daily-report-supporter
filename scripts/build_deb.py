from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_BINARY_NAME = "WorKing"
PACKAGE_NAME = "working"
INSTALL_ROOT = Path("opt/working")
LAUNCHER_PATH = Path("usr/bin/working")
DESKTOP_PATH = Path("usr/share/applications/WorKing.desktop")
ICON_PATH = Path("usr/share/icons/hicolor/scalable/apps/WorKing.svg")

SUPPORTED_ARCHITECTURES = {"amd64", "arm64"}
RUNTIME_DEPENDENCIES = (
    "libegl1",
    "libx11-6",
    "libx11-xcb1",
    "libxext6",
    "libxfixes3",
    "libxi6",
    "libxrender1",
    "libice6",
    "libsm6",
    "libfontconfig1",
    "libfreetype6",
    "libxcb1",
    "libxcb-cursor0",
    "libxcb-icccm4",
    "libxcb-image0",
    "libxcb-keysyms1",
    "libxcb-randr0",
    "libxcb-render-util0",
    "libxcb-shape0",
    "libxcb-shm0",
    "libxcb-sync1",
    "libxcb-util1",
    "libxcb-xfixes0",
    "libxcb-xkb1",
    "libxkbcommon0",
    "libxkbcommon-x11-0",
    "openssh-client",
)


def normalize_version(value: str) -> str:
    version = value.strip()
    if version.startswith("v"):
        version = version[1:]
    if not re.fullmatch(r"[0-9][0-9A-Za-z.+:~-]*", version):
        raise ValueError(f"Debian 패키지 버전 형식이 올바르지 않습니다: {value}")
    return version


def control_text(version: str, architecture: str) -> str:
    if architecture not in SUPPORTED_ARCHITECTURES:
        raise ValueError(f"지원하지 않는 Debian architecture입니다: {architecture}")

    dependencies = ", ".join(RUNTIME_DEPENDENCIES)
    return (
        f"Package: {PACKAGE_NAME}\n"
        f"Version: {normalize_version(version)}\n"
        "Section: utils\n"
        "Priority: optional\n"
        f"Architecture: {architecture}\n"
        "Maintainer: MiSo-13\n"
        f"Depends: {dependencies}\n"
        "Description: WorKing 업무 보조 데스크톱 앱\n"
        " Markdown 업무 기록, 메모, 터미널, DB Viewer를 제공하는 PyQt6 앱입니다.\n"
    )


def launcher_text() -> str:
    return """#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export WORKING_DATA_ROOT="${DATA_HOME}/WorKing"

exec /opt/working/WorKing "$@"
"""


def desktop_entry_text() -> str:
    return """[Desktop Entry]
Version=1.0
Type=Application
Name=WorKing
Comment=업무 보조
Exec=/usr/bin/working
Icon=/usr/share/icons/hicolor/scalable/apps/WorKing.svg
Terminal=false
Categories=Office;Utility;
StartupNotify=true
"""


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def stage_package(
    root: Path,
    *,
    binary: Path,
    version: str,
    architecture: str,
) -> None:
    if not binary.is_file():
        raise FileNotFoundError(f"Linux 실행 파일을 찾지 못했습니다: {binary}")

    icon = ROOT / "assets" / "app-icon.svg"
    if not icon.is_file():
        raise FileNotFoundError(f"앱 아이콘을 찾지 못했습니다: {icon}")

    control = root / "DEBIAN" / "control"
    control.parent.mkdir(parents=True, exist_ok=True)
    control.write_text(control_text(version, architecture), encoding="utf-8")

    installed_binary = root / INSTALL_ROOT / APP_BINARY_NAME
    installed_binary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, installed_binary)
    installed_binary.chmod(
        installed_binary.stat().st_mode
        | stat.S_IXUSR
        | stat.S_IXGRP
        | stat.S_IXOTH
    )

    _write_executable(root / LAUNCHER_PATH, launcher_text())

    desktop = root / DESKTOP_PATH
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(desktop_entry_text(), encoding="utf-8")

    installed_icon = root / ICON_PATH
    installed_icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon, installed_icon)


def build_deb(
    *,
    binary: Path,
    version: str,
    architecture: str,
    output: Path,
) -> Path:
    normalized_version = normalize_version(version)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="working-deb-") as temp_dir:
        root = Path(temp_dir) / f"{PACKAGE_NAME}_{normalized_version}_{architecture}"
        stage_package(
            root,
            binary=binary.resolve(),
            version=normalized_version,
            architecture=architecture,
        )
        subprocess.run(
            [
                "dpkg-deb",
                "--root-owner-group",
                "--build",
                str(root),
                str(output),
            ],
            check=True,
        )

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WorKing Linux 실행 파일을 Debian 패키지로 만듭니다."
    )
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument(
        "--architecture",
        required=True,
        choices=sorted(SUPPORTED_ARCHITECTURES),
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_deb(
        binary=args.binary,
        version=args.version,
        architecture=args.architecture,
        output=args.output,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
