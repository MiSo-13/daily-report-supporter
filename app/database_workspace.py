from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit, QWidget

from app.database_dialogs import DatabaseProfileDialog
from app.database_models import DatabaseProfile
from app.database_service import DatabaseService
from app.database_store import DatabaseStore
from app.database_ui import DatabasePanel, DatabaseSidebar
from app.dialogs import DeleteConfirmDialog


class _WorkerSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class _DatabaseWorker(QRunnable):
    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self.task = task
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            result = self.task()
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)


class DatabaseWorkspace:
    def __init__(
        self,
        state_path: Path | str,
        parent: QWidget,
        status_message: Callable[[str, int], None] | None = None,
    ) -> None:
        self.store = DatabaseStore(state_path)
        self.service = DatabaseService()
        self.parent = parent
        self.status_message = status_message
        self.sidebar = DatabaseSidebar()
        self.panel = DatabasePanel()
        self.thread_pool = QThreadPool.globalInstance()

        self._passwords: dict[str, str] = {}
        self._current_profile_id: str | None = None
        self._current_schema: str | None = None
        self._current_table: str | None = None
        self._generation = 0

        self.sidebar.new_requested.connect(self.create)
        self.sidebar.edit_requested.connect(self.edit)
        self.sidebar.delete_requested.connect(self.delete)
        self.sidebar.connect_requested.connect(self.connect_profile)
        self.sidebar.table_selected.connect(self.select_table)

        self.panel.refresh_requested.connect(self.refresh_table)
        self.panel.page_requested.connect(self.load_page)
        self.panel.filter_requested.connect(self.apply_filter)
        self.panel.sql_requested.connect(self.execute_sql)

        self._reload_profiles()

    def activate(self) -> None:
        if not self.store.list_profiles():
            self.panel.clear()

    def shutdown(self) -> None:
        self._passwords.clear()

    def create(self) -> None:
        dialog = DatabaseProfileDialog(
            self.parent,
            test_connection=self.service.test_connection,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        preview = dialog.build_profile()
        profile = self.store.create(
            name=preview.name,
            db_type=preview.db_type,
            host=preview.host,
            port=preview.port,
            database=preview.database,
            user=preview.user,
        )
        self._passwords[profile.connection_id] = dialog.password
        self._reload_profiles(select_id=profile.connection_id)
        self.connect_profile(profile.connection_id)

    def edit(self) -> None:
        profile_id = self.sidebar.selected_profile_id()
        if not profile_id:
            return
        try:
            profile = self.store.get(profile_id)
        except KeyError:
            return

        dialog = DatabaseProfileDialog(
            self.parent,
            profile=profile,
            test_connection=self.service.test_connection,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        preview = dialog.build_profile()
        updated = self.store.update(
            profile_id,
            name=preview.name,
            db_type=preview.db_type,
            host=preview.host,
            port=preview.port,
            database=preview.database,
            user=preview.user,
        )
        if dialog.password:
            self._passwords[profile_id] = dialog.password

        self._reload_profiles(select_id=profile_id)
        if self._current_profile_id == profile_id:
            self.panel.set_connection_context(updated)

    def delete(self) -> None:
        profile_id = self.sidebar.selected_profile_id()
        if not profile_id:
            return
        try:
            profile = self.store.get(profile_id)
        except KeyError:
            return

        dialog = DeleteConfirmDialog(
            self.parent,
            profile.name,
            item_name="DB 연결",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.store.delete(profile_id)
        self._passwords.pop(profile_id, None)
        if self._current_profile_id == profile_id:
            self._clear_current()
        self._reload_profiles()

    def connect_profile(self, profile_id: str) -> None:
        try:
            profile = self.store.get(profile_id)
        except KeyError:
            return

        password = self._password_for(profile)
        if password is None:
            return

        if self._current_profile_id != profile_id:
            self._current_schema = None
            self._current_table = None
            self._generation += 1
            self.panel.clear()

        self._current_profile_id = profile_id
        self.panel.set_connection_context(profile)
        self.sidebar.set_loading(profile_id)
        self._show_status(f"{profile.name} 연결 중...", 1800)

        self._run(
            lambda: self.service.load_catalog(profile, password),
            lambda result: self._catalog_loaded(profile, result),
            lambda message: self._catalog_failed(profile, message),
        )

    def select_table(
        self,
        profile_id: str,
        schema: str,
        table: str,
    ) -> None:
        if not profile_id or not schema or not table:
            return
        try:
            profile = self.store.get(profile_id)
        except KeyError:
            return

        password = self._password_for(profile)
        if password is None:
            return

        self._current_profile_id = profile_id
        self._current_schema = schema
        self._current_table = table
        self._generation += 1
        generation = self._generation

        self.panel.set_table_context(
            profile,
            schema,
            table,
            self.service.select_template(profile, schema, table),
        )
        self.panel.set_loading()

        self._run(
            lambda: self.service.load_table(
                profile,
                password,
                schema,
                table,
                page=0,
                page_size=self.panel.page_size,
                where_clause="",
            ),
            lambda result: self._table_loaded(
                generation,
                result,
                page=0,
            ),
            lambda message: self._table_failed(generation, message),
        )

    def refresh_table(self) -> None:
        if not self._has_table():
            return
        self._load_table_snapshot(page=0)

    def load_page(self, page: int) -> None:
        if not self._has_table():
            return

        profile = self.store.get(str(self._current_profile_id))
        password = self._password_for(profile)
        if password is None:
            return

        schema = str(self._current_schema)
        table = str(self._current_table)
        self._generation += 1
        generation = self._generation
        self.panel.set_loading()

        self._run(
            lambda: self.service.load_page(
                profile,
                password,
                schema,
                table,
                page=max(page, 0),
                page_size=self.panel.page_size,
                where_clause=self.panel.where_clause,
            ),
            lambda result: self._page_loaded(
                generation,
                result,
                max(page, 0),
            ),
            lambda message: self._table_failed(generation, message),
        )

    def apply_filter(self, _where_clause: str) -> None:
        if self._has_table():
            self.load_page(0)

    def execute_sql(self, sql: str) -> None:
        profile_id = self._current_profile_id
        if not profile_id:
            self.panel.sql_status.setText("DB 연결을 먼저 선택하세요.")
            return

        try:
            profile = self.store.get(profile_id)
        except KeyError:
            return

        password = self._password_for(profile)
        if password is None:
            return

        self.panel.sql_button.setEnabled(False)
        self.panel.sql_status.setText("실행 중...")
        self._run(
            lambda: self.service.run_query(profile, password, sql),
            self._query_loaded,
            self._query_failed,
        )

    def _load_table_snapshot(self, *, page: int) -> None:
        if not self._has_table():
            return

        profile = self.store.get(str(self._current_profile_id))
        password = self._password_for(profile)
        if password is None:
            return

        schema = str(self._current_schema)
        table = str(self._current_table)
        self._generation += 1
        generation = self._generation
        self.panel.set_loading()

        self._run(
            lambda: self.service.load_table(
                profile,
                password,
                schema,
                table,
                page=page,
                page_size=self.panel.page_size,
                where_clause=self.panel.where_clause,
            ),
            lambda result: self._table_loaded(
                generation,
                result,
                page=page,
            ),
            lambda message: self._table_failed(generation, message),
        )

    def _catalog_loaded(
        self,
        profile: DatabaseProfile,
        result: object,
    ) -> None:
        if not isinstance(result, dict):
            return
        self.sidebar.set_catalog(profile.connection_id, result)
        if self._current_profile_id == profile.connection_id:
            self.panel.set_connection_context(profile)
        table_count = sum(len(tables) for tables in result.values())
        self._show_status(
            f"{profile.name} 연결 완료 · {table_count}개 테이블/뷰",
            3000,
        )

    def _catalog_failed(
        self,
        profile: DatabaseProfile,
        message: str,
    ) -> None:
        self.sidebar.set_error(profile.connection_id, message)
        self._show_status(f"{profile.name} 연결 실패", 3000)

    def _table_loaded(
        self,
        generation: int,
        result: object,
        *,
        page: int,
    ) -> None:
        if generation != self._generation:
            return
        if not isinstance(result, tuple) or len(result) != 2:
            return
        columns, data = result
        self.panel.set_columns(columns)
        self.panel.set_data(data, page)

    def _page_loaded(
        self,
        generation: int,
        result: object,
        page: int,
    ) -> None:
        if generation != self._generation:
            return
        self.panel.set_data(result, page)

    def _table_failed(self, generation: int, message: str) -> None:
        if generation != self._generation:
            return
        self.panel.set_error(message)

    def _query_loaded(self, result: object) -> None:
        self.panel.sql_button.setEnabled(True)
        self.panel.set_query_result(result)

    def _query_failed(self, message: str) -> None:
        self.panel.sql_button.setEnabled(True)
        self.panel.sql_status.setText(f"오류: {message}")

    def _password_for(self, profile: DatabaseProfile) -> str | None:
        if profile.connection_id in self._passwords:
            return self._passwords[profile.connection_id]

        password, accepted = QInputDialog.getText(
            self.parent,
            "DB 비밀번호",
            f"{profile.name} 비밀번호\n파일에는 저장되지 않습니다.",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return None
        self._passwords[profile.connection_id] = password
        return password

    def _reload_profiles(self, *, select_id: str | None = None) -> None:
        self.sidebar.set_profiles(
            self.store.list_profiles(),
            select_id=select_id or self._current_profile_id,
        )

    def _clear_current(self) -> None:
        self._current_profile_id = None
        self._current_schema = None
        self._current_table = None
        self._generation += 1
        self.panel.clear()

    def _has_table(self) -> bool:
        return bool(
            self._current_profile_id
            and self._current_schema
            and self._current_table
        )

    def _run(
        self,
        task: Callable[[], object],
        success: Callable[[object], None],
        failure: Callable[[str], None],
    ) -> None:
        worker = _DatabaseWorker(task)
        worker.signals.finished.connect(success)
        worker.signals.failed.connect(failure)
        self.thread_pool.start(worker)

    def _show_status(self, message: str, timeout: int) -> None:
        if self.status_message is not None:
            self.status_message(message, timeout)
