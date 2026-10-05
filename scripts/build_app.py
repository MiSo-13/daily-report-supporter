from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.app_meta import APP_NAME, BUNDLE_IDENTIFIER

ENTRYPOINT = ROOT / "main.py"
CROSTINI_SETUP = ROOT / "scripts" / "setup_crostini.sh"
APP_ICON_SOURCE = ROOT / "assets" / "app-icon.svg"
APP_ICON_BUNDLE_DIR = "assets"
BUILD_ROOT = ROOT / "build"


def _prepare_build_icon() -> Path:
    from PIL import Image
    from app.app_icon import render_app_icon_png

    png_path = render_app_icon_png(
        BUILD_ROOT / "app-icon.png",
        size=1024,
    )

    with Image.open(png_path) as image:
        rgba = image.convert("RGBA")
        if sys.platform == "win32":
            icon_path = BUILD_ROOT / "app-icon.ico"
            rgba.save(
                icon_path,
                format="ICO",
                sizes=[
                    (16, 16),
                    (24, 24),
                    (32, 32),
                    (48, 48),
                    (64, 64),
                    (128, 128),
                    (256, 256),
                ],
            )
            return icon_path

        if sys.platform == "darwin":
            icon_path = BUILD_ROOT / "app-icon.icns"
            rgba.save(icon_path, format="ICNS")
            return icon_path

    return png_path


def build() -> None:
    icon_path = (
        _prepare_build_icon()
        if sys.platform in ("darwin", "win32")
        else None
    )
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--add-data",
        f"{CROSTINI_SETUP}:scripts",
        "--add-data",
        f"{APP_ICON_SOURCE}:{APP_ICON_BUNDLE_DIR}",
        "--collect-all",
        "pymysql",
        "--collect-all",
        "psycopg",
        "--collect-all",
        "psycopg_binary",
    ]

    if sys.platform == "darwin":
        args.extend(
            [
                "--icon",
                str(icon_path),
                "--onedir",
                "--windowed",
                "--osx-bundle-identifier",
                BUNDLE_IDENTIFIER,
            ]
        )
    elif sys.platform == "win32":
        args.extend(
            [
                "--icon",
                str(icon_path),
                "--onefile",
                "--windowed",
                "--collect-all",
                "winpty",
            ]
        )
    else:
        args.append("--onefile")

    args.append(str(ENTRYPOINT))
    subprocess.run(args, cwd=ROOT, check=True)


if __name__ == "__main__":
    build()
