from __future__ import annotations

import sys

from app.qt_platform import CrostiniDependencyError, configure_qt_platform


def main() -> int:
    try:
        configure_qt_platform()
    except CrostiniDependencyError as exc:
        print(exc.user_message(), file=sys.stderr)
        return 2

    from app.main_window import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
