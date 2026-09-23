import os
import sys


def _configure_qt_platform() -> None:
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("QT_QPA_PLATFORM"):
        return

    # 일부 Linux/Crostini/Wayland 환경에서 QMenu/QDialog popup surface를
    # 닫을 때 Qt Wayland connection이 끊기는 문제가 있다.
    # X11 display도 제공되는 환경에서는 Qt가 시작되기 전에 xcb를 사용한다.
    if os.environ.get("WAYLAND_DISPLAY") and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


_configure_qt_platform()

from app.main_window import run


if __name__ == "__main__":
    raise SystemExit(run())
