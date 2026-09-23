from __future__ import annotations

import sys
from app.qt_platform import (
    CrostiniDependencyError,
    configure_input_method,
    configure_qt_platform,
    install_crostini_dependencies,
)
from app.paths import default_reports_root
from app.settings import AppSettings

REPORTS_ROOT = default_reports_root()


def _configure_input_method_from_settings() -> None:
    settings = AppSettings(REPORTS_ROOT)
    configure_input_method(settings.input_method_mode)


def _configure_platform_with_auto_setup() -> bool:
    try:
        configure_qt_platform()
        return True
    except CrostiniDependencyError as exc:
        if not exc.missing_libraries:
            print(exc.user_message(), file=sys.stderr)
            return False

        print(
            "Crostini용 Qt/X11 의존성이 없어 자동 설치를 시도합니다.",
            file=sys.stderr,
        )
        print(
            "sudo 권한이 필요한 경우 터미널에서 비밀번호를 입력하세요.",
            file=sys.stderr,
        )

        if not install_crostini_dependencies():
            print(exc.user_message(), file=sys.stderr)
            return False

        try:
            configure_qt_platform()
            return True
        except CrostiniDependencyError as retry_exc:
            print(retry_exc.user_message(), file=sys.stderr)
            return False


def main() -> int:
    _configure_input_method_from_settings()

    if not _configure_platform_with_auto_setup():
        return 2

    from app.main_window import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
