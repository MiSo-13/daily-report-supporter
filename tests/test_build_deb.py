from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.build_deb import (
    DESKTOP_PATH,
    ICON_PATH,
    INSTALL_ROOT,
    LAUNCHER_PATH,
    build_deb,
    control_text,
    desktop_entry_text,
    launcher_text,
    normalize_version,
    stage_package,
)


def test_normalize_version_removes_release_tag_prefix() -> None:
    assert normalize_version("v0.2.0") == "0.2.0"
    assert normalize_version("0.2.0-beta.1") == "0.2.0-beta.1"


def test_normalize_version_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        normalize_version("release/latest")


def test_debian_control_contains_architecture_and_runtime_dependencies() -> None:
    control = control_text("v0.2.0", "amd64")

    assert "Package: working" in control
    assert "Version: 0.2.0" in control
    assert "Architecture: amd64" in control
    assert "libxcb-cursor0" in control
    assert "libxkbcommon-x11-0" in control
    assert "openssh-client" in control


def test_launcher_uses_xdg_user_data_directory() -> None:
    launcher = launcher_text()

    assert 'DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"' in launcher
    assert 'WORKING_DATA_ROOT="${DATA_HOME}/WorKing"' in launcher
    assert 'exec /opt/working/WorKing "$@"' in launcher


def test_desktop_entry_matches_qt_desktop_file_name() -> None:
    desktop = desktop_entry_text()

    assert "Name=WorKing" in desktop
    assert "Exec=/usr/bin/working" in desktop
    assert "Icon=/usr/share/icons/hicolor/scalable/apps/WorKing.svg" in desktop


def test_stage_package_creates_expected_layout(tmp_path: Path) -> None:
    source_binary = tmp_path / "source-WorKing"
    source_binary.write_bytes(b"binary")
    package_root = tmp_path / "package"

    stage_package(
        package_root,
        binary=source_binary,
        version="0.2.0",
        architecture="arm64",
    )

    assert (package_root / "DEBIAN" / "control").is_file()
    assert (package_root / INSTALL_ROOT / "WorKing").is_file()
    assert (package_root / LAUNCHER_PATH).is_file()
    assert (package_root / DESKTOP_PATH).is_file()
    assert (package_root / ICON_PATH).is_file()

    assert (package_root / LAUNCHER_PATH).stat().st_mode & 0o111
    assert (package_root / INSTALL_ROOT / "WorKing").stat().st_mode & 0o111


def test_build_deb_creates_readable_archive(tmp_path: Path) -> None:
    if shutil.which("dpkg-deb") is None:
        pytest.skip("dpkg-deb를 사용할 수 없는 환경입니다.")

    source_binary = tmp_path / "WorKing"
    source_binary.write_bytes(b"binary")
    output = tmp_path / "WorKing-linux-x64.deb"

    result = build_deb(
        binary=source_binary,
        version="v0.2.0",
        architecture="amd64",
        output=output,
    )

    assert result == output.resolve()
    assert output.is_file()

    fields = subprocess.run(
        ["dpkg-deb", "--field", str(output), "Package", "Version", "Architecture"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Package: working" in fields
    assert "Version: 0.2.0" in fields
    assert "Architecture: amd64" in fields

    contents = subprocess.run(
        ["dpkg-deb", "--contents", str(output)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "./opt/working/WorKing" in contents
    assert "./usr/bin/working" in contents
    assert "./usr/share/applications/WorKing.desktop" in contents
    assert "./usr/share/icons/hicolor/scalable/apps/WorKing.svg" in contents
