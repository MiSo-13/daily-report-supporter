from __future__ import annotations

import sys

from app.data_migration import migrate_legacy_data
from app.paths import (
    default_config_root,
    default_data_root,
    ensure_data_root_writable,
)
from app.qt_platform import (
    CrostiniDependencyError,
    configure_input_method,
    configure_qt_platform,
    install_crostini_dependencies,
)
from app.settings import AppSettings


DATA_ROOT = default_data_root()
CONFIG_ROOT = default_config_root()


def _configure_input_method_from_settings() -> None:
    settings = AppSettings(CONFIG_ROOT)
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


def _show_data_root_error(message: str) -> int:
    print(message, file=sys.stderr)

    if not _configure_platform_with_auto_setup():
        return 3

    from PyQt6.QtWidgets import QApplication, QMessageBox

    app = QApplication([])
    QMessageBox.critical(
        None,
        "WorKing 데이터 폴더 오류",
        message,
    )
    app.quit()
    return 3


def main() -> int:
    try:
        ensure_data_root_writable(DATA_ROOT)
    except OSError as exc:
        return _show_data_root_error(
            "WorKing은 실행 위치의 data 폴더에만 사용자 데이터를 저장합니다.\n\n"
            f"저장 경로: {DATA_ROOT}\n"
            f"오류: {exc}\n\n"
            "WorKing을 쓰기 가능한 폴더로 옮긴 뒤 다시 실행하세요."
        )

    migration = migrate_legacy_data(data_root=DATA_ROOT)
    if migration.errors:
        for error in migration.errors:
            print(f"데이터 마이그레이션 실패: {error}", file=sys.stderr)

    _configure_input_method_from_settings()

    if not _configure_platform_with_auto_setup():
        return 2

    from app.main_window import run

    return run(startup_message=migration.startup_message)


if __name__ == "__main__":
    raise SystemExit(main())
