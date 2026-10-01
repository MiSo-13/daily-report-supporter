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


def build() -> None:
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
                "--onedir",
                "--windowed",
                "--osx-bundle-identifier",
                BUNDLE_IDENTIFIER,
            ]
        )
    elif sys.platform == "win32":
        args.extend(
            [
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
