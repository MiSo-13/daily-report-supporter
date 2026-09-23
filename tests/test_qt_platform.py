import pytest

from app.qt_platform import (
    CrostiniDependencyError,
    configure_qt_platform,
    install_crostini_dependencies,
    is_crostini,
)


def test_windows_keeps_qt_default() -> None:
    env = {}

    result = configure_qt_platform(
        env,
        platform="win32",
        crostini=False,
        missing_libraries=(),
    )

    assert result is None
    assert "QT_QPA_PLATFORM" not in env


def test_macos_keeps_qt_default() -> None:
    env = {}

    result = configure_qt_platform(
        env,
        platform="darwin",
        crostini=False,
        missing_libraries=(),
    )

    assert result is None
    assert "QT_QPA_PLATFORM" not in env


def test_regular_linux_keeps_existing_platform() -> None:
    env = {"QT_QPA_PLATFORM": "wayland"}

    result = configure_qt_platform(
        env,
        platform="linux",
        crostini=False,
        missing_libraries=(),
    )

    assert result == "wayland"
    assert env["QT_QPA_PLATFORM"] == "wayland"


def test_crostini_with_x11_dependencies_forces_xcb() -> None:
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
    }

    result = configure_qt_platform(
        env,
        platform="linux",
        crostini=True,
        missing_libraries=(),
    )

    assert result == "xcb"
    assert env["QT_QPA_PLATFORM"] == "xcb"


def test_crostini_stops_before_pyqt_when_xcb_dependency_is_missing() -> None:
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
    }

    with pytest.raises(CrostiniDependencyError) as captured:
        configure_qt_platform(
            env,
            platform="linux",
            crostini=True,
            missing_libraries=("libxcb-cursor.so.0",),
        )

    error = captured.value
    assert error.install_packages == ("libxcb-cursor0",)
    assert "sudo apt update" in error.user_message()
    assert "libxcb-cursor0" in error.user_message()
    assert "QT_QPA_PLATFORM" not in env


def test_crostini_requires_display() -> None:
    with pytest.raises(CrostiniDependencyError) as captured:
        configure_qt_platform(
            {},
            platform="linux",
            crostini=True,
            missing_libraries=(),
        )

    assert "DISPLAY" in captured.value.user_message()


def test_crostini_detection_uses_sommelier_environment() -> None:
    assert is_crostini(
        {"SOMMELIER_VERSION": "1"},
        marker_results=(False, False),
    )


def test_crostini_detection_uses_chromeos_mount_marker() -> None:
    assert is_crostini(
        {},
        marker_results=(True, False),
    )


def test_plain_linux_is_not_crostini() -> None:
    assert not is_crostini(
        {},
        marker_results=(False, False),
    )


def test_crostini_setup_script_success(tmp_path) -> None:
    script = tmp_path / "setup.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    assert install_crostini_dependencies(script)


def test_crostini_setup_script_failure(tmp_path) -> None:
    script = tmp_path / "setup.sh"
    script.write_text("#!/usr/bin/env bash\nexit 3\n", encoding="utf-8")
    assert not install_crostini_dependencies(script)


def test_crostini_setup_script_missing(tmp_path) -> None:
    assert not install_crostini_dependencies(tmp_path / "missing.sh")
