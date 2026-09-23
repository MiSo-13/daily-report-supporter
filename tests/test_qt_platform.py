from app.qt_platform import SAFE_UI_ENV, configure_qt_platform


def test_linux_with_usable_xcb_selects_xcb() -> None:
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
        "QT_QPA_PLATFORM": "wayland",
    }

    result = configure_qt_platform(env, "linux", xcb_usable=True)

    assert result == "xcb"
    assert env["QT_QPA_PLATFORM"] == "xcb"
    assert SAFE_UI_ENV not in env


def test_linux_with_missing_xcb_dependency_uses_safe_ui() -> None:
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
        "QT_QPA_PLATFORM": "wayland",
    }

    result = configure_qt_platform(env, "linux", xcb_usable=False)

    assert result == "wayland"
    assert env["QT_QPA_PLATFORM"] == "wayland"
    assert env[SAFE_UI_ENV] == "1"


def test_explicit_wayland_uses_safe_ui() -> None:
    env = {
        "DISPLAY": ":0",
        "DAILY_REPORT_QT_PLATFORM": "wayland",
    }

    result = configure_qt_platform(env, "linux", xcb_usable=True)

    assert result == "wayland"
    assert env["QT_QPA_PLATFORM"] == "wayland"
    assert env[SAFE_UI_ENV] == "1"


def test_explicit_xcb_disables_safe_ui() -> None:
    env = {
        "DISPLAY": ":0",
        "DAILY_REPORT_QT_PLATFORM": "xcb",
        SAFE_UI_ENV: "1",
    }

    result = configure_qt_platform(env, "linux", xcb_usable=False)

    assert result == "xcb"
    assert env["QT_QPA_PLATFORM"] == "xcb"
    assert SAFE_UI_ENV not in env


def test_non_linux_is_unchanged() -> None:
    env = {"QT_QPA_PLATFORM": "cocoa"}

    result = configure_qt_platform(env, "darwin", xcb_usable=False)

    assert result == "cocoa"
    assert env["QT_QPA_PLATFORM"] == "cocoa"
    assert SAFE_UI_ENV not in env
