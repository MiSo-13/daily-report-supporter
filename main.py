from app.qt_platform import configure_qt_platform

configure_qt_platform()

from app.main_window import run


if __name__ == "__main__":
    raise SystemExit(run())
