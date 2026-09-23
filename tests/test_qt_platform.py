from app.qt_platform import configure_qt_platform


def test_linux_with_display_forces_xcb() -> None:
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
        "QT_QPA_PLATFORM": "wayland",
    }

    result = configure_qt_platform(env, "linux")
    assert result == "xcb"
    assert env["QT_QPA_PLATFORM"] == "xcb"


def test_explicit_daily_report_platform_wins() -> None:
    env = {
        "DISPLAY": ":0",
        "DAILY_REPORT_QT_PLATFORM": "wayland",
    }

    result = configure_qt_platform(env, "linux")
    assert result == "wayland"
    assert env["QT_QPA_PLATFORM"] == "wayland"


def test_non_linux_is_unchanged() -> None:
    env = {"QT_QPA_PLATFORM": "cocoa"}

    result = configure_qt_platform(env, "darwin")
    assert result == "cocoa"
    assert env["QT_QPA_PLATFORM"] == "cocoa"
