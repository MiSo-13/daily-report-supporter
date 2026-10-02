from __future__ import annotations

import csv
from pathlib import Path

from PyQt6.QtCore import QPoint, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QDropEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTableView,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database_models import (
    ColumnInfo,
    DatabaseProfile,
    PageResult,
    QueryResult,
    TableInfo,
)
from app.database_table_model import DatabaseTableModel


ROLE_KIND = int(Qt.ItemDataRole.UserRole)
ROLE_PAYLOAD = ROLE_KIND + 1
KIND_PROFILE = "profile"
KIND_SCHEMA = "schema"
KIND_TABLE = "table"
KIND_RECENT_GROUP = "recent_group"
KIND_SEARCH_GROUP = "search_group"
KIND_STATUS = "status"


class ReorderableDatabaseTree(QTreeWidget):
    order_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        if (
            item is None
            or item.parent() is not None
            or item.data(0, ROLE_KIND) != KIND_PROFILE
        ):
            return
        super().startDrag(supported_actions)

    def dropEvent(self, event: QDropEvent) -> None:
        dragged = self.currentItem()
        if (
            dragged is None
            or dragged.parent() is not None
            or dragged.data(0, ROLE_KIND) != KIND_PROFILE
        ):
            event.ignore()
            return

        target = self.itemAt(event.position().toPoint())
        position = self.dropIndicatorPosition()
        if target is not None:
            if target.parent() is not None:
                event.ignore()
                return
            if position == QAbstractItemView.DropIndicatorPosition.OnItem:
                event.ignore()
                return

        before = self.profile_order()
        super().dropEvent(event)
        if event.isAccepted() and self.profile_order() != before:
            self.order_changed.emit()

    def profile_order(self) -> list[str]:
        connection_ids: list[str] = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            payload = item.data(0, ROLE_PAYLOAD)
            if not isinstance(payload, dict):
                continue
            connection_id = payload.get("profile_id")
            if connection_id:
                connection_ids.append(str(connection_id))
        return connection_ids


class DatabaseSidebar(QWidget):
    new_requested = pyqtSignal()
    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    connect_requested = pyqtSignal(str)
    schema_expand_requested = pyqtSignal(str, str)
    table_search_requested = pyqtSignal(str, str)
    table_selected = pyqtSignal(str, str, str, str)
    profile_reorder_requested = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("테이블 검색")
        self.search_input.setClearButtonEnabled(True)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self.search_input.textChanged.connect(
            lambda _text: self._search_timer.start()
        )
        self.search_input.returnPressed.connect(self._emit_search)
        self._search_timer.timeout.connect(self._emit_search)

        self.tree = ReorderableDatabaseTree()
        self.tree.setHeaderHidden(True)
        self.tree.setObjectName("databaseTree")
        self.tree.itemClicked.connect(self._item_clicked)
        self.tree.itemDoubleClicked.connect(self._item_double_clicked)
        self.tree.itemExpanded.connect(self._item_expanded)
        self.tree.currentItemChanged.connect(self._current_item_changed)
        self.tree.order_changed.connect(self._persist_profile_order)

        self.new_button = QPushButton("+ 연결")
        self.new_button.setObjectName("primaryButton")
        self.edit_button = QPushButton("편집")
        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.connect_button = QPushButton("연결 / 새로고침")

        self.new_button.clicked.connect(
            lambda _checked=False: self.new_requested.emit()
        )
        self.edit_button.clicked.connect(
            lambda _checked=False: self.edit_requested.emit()
        )
        self.delete_button.clicked.connect(
            lambda _checked=False: self.delete_requested.emit()
        )
        self.connect_button.clicked.connect(self._connect_selected)

        profile_actions = QHBoxLayout()
        profile_actions.setSpacing(8)
        profile_actions.addWidget(self.new_button)
        profile_actions.addWidget(self.edit_button)
        profile_actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(QLabel("<b>DB 연결</b>"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.tree, 1)
        layout.addLayout(profile_actions)
        layout.addWidget(self.connect_button)

    def set_profiles(
        self,
        profiles: list[DatabaseProfile],
        *,
        recent_tables: dict[str, list[TableInfo]] | None = None,
        select_id: str | None = None,
    ) -> None:
        self.tree.clear()
        selected_item: QTreeWidgetItem | None = None
        recent_tables = recent_tables or {}

        for profile in profiles:
            item = QTreeWidgetItem([profile.name])
            item.setData(0, ROLE_KIND, KIND_PROFILE)
            item.setData(
                0,
                ROLE_PAYLOAD,
                {
                    "profile_id": profile.connection_id,
                },
            )
            item.setToolTip(0, profile.target_label)
            self.tree.addTopLevelItem(item)
            self._append_recent_group(
                item,
                profile.connection_id,
                recent_tables.get(profile.connection_id, []),
            )
            if profile.connection_id == select_id:
                selected_item = item

        if selected_item is not None:
            self.tree.setCurrentItem(selected_item)

    def selected_profile_id(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        payload = item.data(0, ROLE_PAYLOAD)
        if not isinstance(payload, dict):
            return None
        value = payload.get("profile_id")
        return str(value) if value else None

    def set_loading(self, profile_id: str) -> None:
        item = self._profile_item(profile_id)
        if item is None:
            return
        self._remove_children(
            item,
            {KIND_SCHEMA, KIND_SEARCH_GROUP, KIND_STATUS},
        )
        status = QTreeWidgetItem(["연결 중..."])
        status.setData(0, ROLE_KIND, KIND_STATUS)
        status.setDisabled(True)
        item.addChild(status)
        item.setExpanded(True)

    def set_error(self, profile_id: str, message: str) -> None:
        item = self._profile_item(profile_id)
        if item is None:
            return
        self._remove_children(
            item,
            {KIND_SCHEMA, KIND_SEARCH_GROUP, KIND_STATUS},
        )
        status = QTreeWidgetItem(["연결 실패"])
        status.setData(0, ROLE_KIND, KIND_STATUS)
        status.setToolTip(0, message)
        status.setDisabled(True)
        item.addChild(status)
        item.setExpanded(True)

    def set_schemas(self, profile_id: str, schemas: list[str]) -> None:
        item = self._profile_item(profile_id)
        if item is None:
            return

        self._remove_children(item, {KIND_SCHEMA, KIND_STATUS})
        for schema in schemas:
            schema_item = QTreeWidgetItem([schema])
            schema_item.setData(0, ROLE_KIND, KIND_SCHEMA)
            schema_item.setData(
                0,
                ROLE_PAYLOAD,
                {
                    "profile_id": profile_id,
                    "schema": schema,
                    "loaded": False,
                    "loading": False,
                },
            )
            placeholder = QTreeWidgetItem(["펼치면 테이블 조회"])
            placeholder.setData(0, ROLE_KIND, KIND_STATUS)
            placeholder.setDisabled(True)
            schema_item.addChild(placeholder)
            item.addChild(schema_item)

        item.setExpanded(True)

    def set_schema_loading(self, profile_id: str, schema: str) -> None:
        item = self._schema_item(profile_id, schema)
        if item is None:
            return
        payload = item.data(0, ROLE_PAYLOAD)
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["loading"] = True
            item.setData(0, ROLE_PAYLOAD, payload)
        item.takeChildren()
        status = QTreeWidgetItem(["불러오는 중..."])
        status.setData(0, ROLE_KIND, KIND_STATUS)
        status.setDisabled(True)
        item.addChild(status)

    def set_schema_tables(
        self,
        profile_id: str,
        schema: str,
        tables: list[TableInfo],
    ) -> None:
        item = self._schema_item(profile_id, schema)
        if item is None:
            return

        item.takeChildren()
        for table in tables:
            item.addChild(
                self._table_item(
                    profile_id,
                    table,
                    include_schema=False,
                )
            )

        if not tables:
            status = QTreeWidgetItem(["테이블 없음"])
            status.setData(0, ROLE_KIND, KIND_STATUS)
            status.setDisabled(True)
            item.addChild(status)

        payload = item.data(0, ROLE_PAYLOAD)
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["loaded"] = True
            payload["loading"] = False
            item.setData(0, ROLE_PAYLOAD, payload)
        item.setExpanded(True)

    def set_schema_error(
        self,
        profile_id: str,
        schema: str,
        message: str,
    ) -> None:
        item = self._schema_item(profile_id, schema)
        if item is None:
            return
        item.takeChildren()
        status = QTreeWidgetItem(["조회 실패"])
        status.setData(0, ROLE_KIND, KIND_STATUS)
        status.setToolTip(0, message)
        status.setDisabled(True)
        item.addChild(status)

        payload = item.data(0, ROLE_PAYLOAD)
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["loaded"] = False
            payload["loading"] = False
            item.setData(0, ROLE_PAYLOAD, payload)

    def set_search_results(
        self,
        profile_id: str,
        query: str,
        tables: list[TableInfo],
    ) -> None:
        profile_item = self._profile_item(profile_id)
        if profile_item is None:
            return
        self.clear_search_results(profile_id)
        if not query.strip():
            return

        group = QTreeWidgetItem([f"검색 결과 ({len(tables)})"])
        group.setData(0, ROLE_KIND, KIND_SEARCH_GROUP)
        group.setData(
            0,
            ROLE_PAYLOAD,
            {"profile_id": profile_id},
        )
        for table in tables:
            group.addChild(
                self._table_item(
                    profile_id,
                    table,
                    include_schema=True,
                )
            )
        if not tables:
            status = QTreeWidgetItem(["일치하는 테이블 없음"])
            status.setData(0, ROLE_KIND, KIND_STATUS)
            status.setDisabled(True)
            group.addChild(status)

        profile_item.insertChild(0, group)
        group.setExpanded(True)
        profile_item.setExpanded(True)

    def clear_search_results(self, profile_id: str) -> None:
        item = self._profile_item(profile_id)
        if item is None:
            return
        self._remove_children(item, {KIND_SEARCH_GROUP})

    def set_recent_tables(
        self,
        profile_id: str,
        tables: list[TableInfo],
    ) -> None:
        profile_item = self._profile_item(profile_id)
        if profile_item is None:
            return
        self._remove_children(profile_item, {KIND_RECENT_GROUP})
        self._append_recent_group(profile_item, profile_id, tables)

    def _append_recent_group(
        self,
        profile_item: QTreeWidgetItem,
        profile_id: str,
        tables: list[TableInfo],
    ) -> None:
        if not tables:
            return
        group = QTreeWidgetItem(["최근 테이블"])
        group.setData(0, ROLE_KIND, KIND_RECENT_GROUP)
        group.setData(0, ROLE_PAYLOAD, {"profile_id": profile_id})
        for table in tables:
            group.addChild(
                self._table_item(
                    profile_id,
                    table,
                    include_schema=True,
                )
            )
        profile_item.insertChild(0, group)

    def _table_item(
        self,
        profile_id: str,
        table: TableInfo,
        *,
        include_schema: bool,
    ) -> QTreeWidgetItem:
        suffix = " · VIEW" if "VIEW" in table.kind.upper() else ""
        label = (
            f"{table.schema}.{table.name}{suffix}"
            if include_schema
            else f"{table.name}{suffix}"
        )
        item = QTreeWidgetItem([label])
        item.setData(0, ROLE_KIND, KIND_TABLE)
        item.setData(
            0,
            ROLE_PAYLOAD,
            {
                "profile_id": profile_id,
                "schema": table.schema,
                "table": table.name,
                "kind": table.kind,
            },
        )
        return item

    def _connect_selected(self, _checked: bool = False) -> None:
        profile_id = self.selected_profile_id()
        if profile_id:
            self.connect_requested.emit(profile_id)

    def _item_clicked(
        self,
        item: QTreeWidgetItem,
        _column: int = 0,
    ) -> None:
        if item.data(0, ROLE_KIND) != KIND_TABLE:
            return
        payload = item.data(0, ROLE_PAYLOAD)
        if not isinstance(payload, dict):
            return
        self.table_selected.emit(
            str(payload.get("profile_id") or ""),
            str(payload.get("schema") or ""),
            str(payload.get("table") or ""),
            str(payload.get("kind") or "TABLE"),
        )

    def _item_double_clicked(
        self,
        item: QTreeWidgetItem,
        _column: int = 0,
    ) -> None:
        if item.data(0, ROLE_KIND) != KIND_PROFILE:
            return
        payload = item.data(0, ROLE_PAYLOAD)
        if not isinstance(payload, dict):
            return
        profile_id = str(payload.get("profile_id") or "")
        if profile_id:
            self.connect_requested.emit(profile_id)

    def _item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, ROLE_KIND) != KIND_SCHEMA:
            return
        payload = item.data(0, ROLE_PAYLOAD)
        if not isinstance(payload, dict):
            return
        if payload.get("loaded") or payload.get("loading"):
            return
        profile_id = str(payload.get("profile_id") or "")
        schema = str(payload.get("schema") or "")
        if not profile_id or not schema:
            return
        payload = dict(payload)
        payload["loading"] = True
        item.setData(0, ROLE_PAYLOAD, payload)
        self.schema_expand_requested.emit(profile_id, schema)

    def _current_item_changed(
        self,
        _current: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ) -> None:
        if self.search_input.text().strip():
            self._search_timer.start()

    def _emit_search(self) -> None:
        profile_id = self.selected_profile_id()
        if not profile_id:
            return
        query = self.search_input.text().strip()
        if not query:
            self.clear_search_results(profile_id)
        self.table_search_requested.emit(profile_id, query)

    def _persist_profile_order(self) -> None:
        connection_ids = self.tree.profile_order()
        if connection_ids:
            self.profile_reorder_requested.emit(connection_ids)

    def _profile_item(self, profile_id: str) -> QTreeWidgetItem | None:
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            payload = item.data(0, ROLE_PAYLOAD)
            if (
                isinstance(payload, dict)
                and payload.get("profile_id") == profile_id
            ):
                return item
        return None

    def _schema_item(
        self,
        profile_id: str,
        schema: str,
    ) -> QTreeWidgetItem | None:
        profile = self._profile_item(profile_id)
        if profile is None:
            return None
        for index in range(profile.childCount()):
            item = profile.child(index)
            if item.data(0, ROLE_KIND) != KIND_SCHEMA:
                continue
            payload = item.data(0, ROLE_PAYLOAD)
            if (
                isinstance(payload, dict)
                and payload.get("schema") == schema
            ):
                return item
        return None

    @staticmethod
    def _remove_children(
        parent: QTreeWidgetItem,
        kinds: set[str],
    ) -> None:
        for index in range(parent.childCount() - 1, -1, -1):
            child = parent.child(index)
            if child.data(0, ROLE_KIND) in kinds:
                parent.takeChild(index)


class DatabasePanel(QWidget):
    refresh_requested = pyqtSignal()
    page_requested = pyqtSignal(int)
    filter_requested = pyqtSignal(str)
    sql_requested = pyqtSignal(str)
    sql_draft_changed = pyqtSignal(str)
    sort_requested = pyqtSignal(str, str)
    quick_filter_requested = pyqtSignal(str, object, str)

    def __init__(self) -> None:
        super().__init__()
        self._page = 0
        self._has_next = False
        self._sort_column = ""
        self._sort_direction = "ASC"
        self._sort_section = -1

        self.connection_label = QLabel("<b>DB 연결을 선택하세요.</b>")
        self.table_label = QLabel("")
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(
            lambda _checked=False: self.refresh_requested.emit()
        )
        self.refresh_button.setEnabled(False)

        header = QHBoxLayout()
        header.addWidget(self.connection_label)
        header.addWidget(self.table_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)

        self.tabs = QTabWidget()
        self._build_data_tab()
        self._build_columns_tab()
        self._build_sql_tab()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.tabs, 1)

    @property
    def page_size(self) -> int:
        value = self.page_size_combo.currentData()
        return int(value or 100)

    @property
    def where_clause(self) -> str:
        return self.filter_input.text().strip()

    @property
    def sort_column(self) -> str:
        return self._sort_column

    @property
    def sort_direction(self) -> str:
        return self._sort_direction

    def set_connection_context(self, profile: DatabaseProfile) -> None:
        self.connection_label.setText(f"<b>{profile.name}</b>")
        self.connection_label.setToolTip(profile.target_label)

    def set_table_context(
        self,
        profile: DatabaseProfile,
        schema: str,
        table: str,
        sql_text: str,
    ) -> None:
        self.set_connection_context(profile)
        self.table_label.setText(f"· {schema}.{table}")
        self.refresh_button.setEnabled(True)
        self.set_sql_text(sql_text)
        self._page = 0
        self.filter_input.clear()
        self._sort_column = ""
        self._sort_direction = "ASC"
        self._sort_section = -1
        self.data_table.horizontalHeader().setSortIndicatorShown(False)

    def set_loading(self, text: str = "조회 중...") -> None:
        self.data_status.setText(text)
        self.refresh_button.setEnabled(False)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)

    def set_data(self, result: PageResult, page: int) -> None:
        self._page = page
        self._has_next = result.has_next
        self.data_model.set_result(result.columns, result.rows)
        self.prev_button.setEnabled(page > 0)
        self.next_button.setEnabled(result.has_next)
        self.refresh_button.setEnabled(True)

        sort_label = (
            f" · {self._sort_column} {self._sort_direction}"
            if self._sort_column
            else ""
        )
        self.data_status.setText(
            f"페이지 {page + 1} · {len(result.rows)}행"
            + (" · 다음 페이지 있음" if result.has_next else "")
            + sort_label
        )
        self.data_table.resizeColumnsToContents()

    def set_columns(self, columns: list[ColumnInfo]) -> None:
        rows = [
            [
                column.name,
                column.data_type,
                "YES" if column.nullable else "NO",
                column.default if column.default is not None else "",
                column.key,
            ]
            for column in columns
        ]
        self.column_model.set_result(
            ["컬럼", "타입", "NULL", "기본값", "Key"],
            rows,
        )
        self.column_table.resizeColumnsToContents()

    def set_query_result(self, result: QueryResult) -> None:
        self.query_model.set_result(result.columns, result.rows)
        suffix = " · 500행까지만 표시" if result.truncated else ""
        self.sql_status.setText(f"{len(result.rows)}행{suffix}")
        self.sql_table.resizeColumnsToContents()

    def set_filter_clause(self, clause: str) -> None:
        self.filter_input.setText(clause)

    def set_sql_text(self, sql: str) -> None:
        self.sql_editor.blockSignals(True)
        self.sql_editor.setPlainText(sql)
        self.sql_editor.blockSignals(False)

    @property
    def sql_text(self) -> str:
        return self.sql_editor.toPlainText()

    def set_error(self, message: str) -> None:
        self.refresh_button.setEnabled(True)
        self.data_status.setText(f"오류: {message}")

    def clear(self) -> None:
        self.connection_label.setText("<b>DB 연결을 선택하세요.</b>")
        self.table_label.clear()
        self.refresh_button.setEnabled(False)
        self.data_model.clear()
        self.column_model.clear()
        self.query_model.clear()
        self.data_status.clear()
        self.sql_status.clear()
        self.set_sql_text("")
        self.filter_input.clear()
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self._sort_column = ""
        self._sort_direction = "ASC"
        self._sort_section = -1
        self.data_table.horizontalHeader().setSortIndicatorShown(False)

    def _build_data_tab(self) -> None:
        page = QWidget()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(
            "WHERE 조건만 입력 · 예: status = 'ERROR' AND id > 100"
        )
        self.filter_button = QPushButton("조건 적용")
        self.filter_button.clicked.connect(self._apply_filter)
        self.filter_input.returnPressed.connect(self._apply_filter)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter"))
        filter_row.addWidget(self.filter_input, 1)
        filter_row.addWidget(self.filter_button)

        self.data_model = DatabaseTableModel()
        self.data_table = QTableView()
        self.data_table.setModel(self.data_model)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.data_table.customContextMenuRequested.connect(
            self._open_data_context_menu
        )
        self.data_table.horizontalHeader().setSectionsClickable(True)
        self.data_table.horizontalHeader().setSortIndicatorShown(False)
        self.data_table.horizontalHeader().sectionClicked.connect(
            self._request_server_sort
        )
        self._install_copy_shortcut(self.data_table)

        self.prev_button = QPushButton("← 이전")
        self.next_button = QPushButton("다음 →")
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.prev_button.clicked.connect(
            lambda _checked=False: self.page_requested.emit(
                max(self._page - 1, 0)
            )
        )
        self.next_button.clicked.connect(
            lambda _checked=False: self.page_requested.emit(self._page + 1)
        )

        self.page_size_combo = QComboBox()
        for size in (50, 100, 200):
            self.page_size_combo.addItem(f"{size}행", size)
        self.page_size_combo.setCurrentIndex(1)
        self.page_size_combo.currentIndexChanged.connect(
            lambda _index: self.page_requested.emit(0)
        )

        copy_button = QPushButton("선택 복사")
        copy_button.clicked.connect(
            lambda _checked=False: self._copy_selection(self.data_table)
        )
        copy_header_button = QPushButton("헤더 포함 복사")
        copy_header_button.clicked.connect(
            lambda _checked=False: self._copy_selection(
                self.data_table,
                include_headers=True,
            )
        )
        export_button = QPushButton("현재 페이지 CSV")
        export_button.clicked.connect(
            lambda _checked=False: self._export_model_csv(
                self.data_model,
                "db-table.csv",
            )
        )

        self.data_status = QLabel("")
        pager = QHBoxLayout()
        pager.addWidget(self.prev_button)
        pager.addWidget(self.next_button)
        pager.addWidget(self.page_size_combo)
        pager.addWidget(copy_button)
        pager.addWidget(copy_header_button)
        pager.addWidget(export_button)
        pager.addWidget(self.data_status)
        pager.addStretch(1)

        layout = QVBoxLayout(page)
        layout.addLayout(filter_row)
        layout.addWidget(self.data_table, 1)
        layout.addLayout(pager)
        self.tabs.addTab(page, "데이터")

    def _build_columns_tab(self) -> None:
        page = QWidget()
        self.column_model = DatabaseTableModel()
        self.column_table = QTableView()
        self.column_table.setModel(self.column_model)
        self.column_table.setSortingEnabled(True)
        self.column_table.setAlternatingRowColors(True)
        self._install_copy_shortcut(self.column_table)
        layout = QVBoxLayout(page)
        layout.addWidget(self.column_table)
        self.tabs.addTab(page, "컬럼")

    def _build_sql_tab(self) -> None:
        page = QWidget()
        note = QLabel(
            "Read Only · SELECT/SHOW/DESCRIBE/EXPLAIN 계열만 실행 · 최대 500행"
        )
        note.setObjectName("databaseHint")

        self.sql_editor = QPlainTextEdit()
        self.sql_editor.setPlaceholderText("SELECT ...")
        self.sql_editor.setMaximumHeight(150)
        self.sql_editor.textChanged.connect(
            lambda: self.sql_draft_changed.emit(
                self.sql_editor.toPlainText()
            )
        )

        self.sql_button = QPushButton("SQL 실행")
        self.sql_button.setObjectName("primaryButton")
        self.sql_button.clicked.connect(
            lambda _checked=False: self.sql_requested.emit(
                self.sql_editor.toPlainText()
            )
        )
        copy_button = QPushButton("선택 복사")
        copy_button.clicked.connect(
            lambda _checked=False: self._copy_selection(self.sql_table)
        )
        export_button = QPushButton("결과 CSV")
        export_button.clicked.connect(
            lambda _checked=False: self._export_model_csv(
                self.query_model,
                "db-query-result.csv",
            )
        )
        self.sql_status = QLabel("")

        action_row = QHBoxLayout()
        action_row.addWidget(self.sql_button)
        action_row.addWidget(copy_button)
        action_row.addWidget(export_button)
        action_row.addWidget(self.sql_status)
        action_row.addStretch(1)

        self.query_model = DatabaseTableModel()
        self.sql_table = QTableView()
        self.sql_table.setModel(self.query_model)
        self.sql_table.setSortingEnabled(True)
        self.sql_table.setAlternatingRowColors(True)
        self._install_copy_shortcut(self.sql_table)

        layout = QVBoxLayout(page)
        layout.addWidget(note)
        layout.addWidget(self.sql_editor)
        layout.addLayout(action_row)
        layout.addWidget(self.sql_table, 1)
        self.tabs.addTab(page, "SQL")

    def _apply_filter(self, _checked: bool = False) -> None:
        self.filter_requested.emit(self.where_clause)

    def _request_server_sort(self, section: int) -> None:
        column = self.data_model.header_name(section)
        if not column:
            return

        if self._sort_column == column:
            direction = (
                "DESC"
                if self._sort_direction == "ASC"
                else "ASC"
            )
        else:
            direction = "ASC"

        self._sort_column = column
        self._sort_direction = direction
        self._sort_section = section
        header = self.data_table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(
            section,
            (
                Qt.SortOrder.AscendingOrder
                if direction == "ASC"
                else Qt.SortOrder.DescendingOrder
            ),
        )
        self.sort_requested.emit(column, direction)

    def _open_data_context_menu(self, position: QPoint) -> None:
        index = self.data_table.indexAt(position)
        if not index.isValid():
            return

        column = self.data_model.header_name(index.column())
        if column is None:
            return
        value = self.data_model.raw_value(index.row(), index.column())

        menu = QMenu(self.data_table)
        copy_action = menu.addAction("값 복사")
        copy_action.triggered.connect(
            lambda _checked=False: QApplication.clipboard().setText(
                DatabaseTableModel.display_value(value)
            )
        )
        menu.addSeparator()

        if value is None:
            null_action = menu.addAction("NULL만 보기")
            null_action.triggered.connect(
                lambda _checked=False: self.quick_filter_requested.emit(
                    column,
                    value,
                    "is_null",
                )
            )
            not_null_action = menu.addAction("NULL 제외")
            not_null_action.triggered.connect(
                lambda _checked=False: self.quick_filter_requested.emit(
                    column,
                    value,
                    "not_null",
                )
            )
        else:
            equal_action = menu.addAction("이 값으로 필터")
            equal_action.triggered.connect(
                lambda _checked=False: self.quick_filter_requested.emit(
                    column,
                    value,
                    "equals",
                )
            )
            not_equal_action = menu.addAction("이 값 제외")
            not_equal_action.triggered.connect(
                lambda _checked=False: self.quick_filter_requested.emit(
                    column,
                    value,
                    "not_equals",
                )
            )

        if self.where_clause:
            menu.addSeparator()
            clear_action = menu.addAction("필터 지우기")
            clear_action.triggered.connect(
                lambda _checked=False: self._clear_filter()
            )

        menu.exec(self.data_table.viewport().mapToGlobal(position))

    def _clear_filter(self) -> None:
        self.filter_input.clear()
        self.filter_requested.emit("")

    def _install_copy_shortcut(self, table: QTableView) -> None:
        shortcut = QShortcut(
            QKeySequence.StandardKey.Copy,
            table,
        )
        shortcut.activated.connect(
            lambda target=table: self._copy_selection(target)
        )

    def _copy_selection(
        self,
        table: QTableView,
        *,
        include_headers: bool = False,
    ) -> None:
        selection_model = table.selectionModel()
        if selection_model is None:
            return
        indexes = selection_model.selectedIndexes()
        if not indexes:
            return

        model = table.model()
        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        selected = {
            (index.row(), index.column())
            for index in indexes
        }

        lines: list[str] = []
        if include_headers:
            headers = [
                str(
                    model.headerData(
                        column,
                        Qt.Orientation.Horizontal,
                        Qt.ItemDataRole.DisplayRole,
                    )
                    or ""
                )
                for column in columns
            ]
            lines.append("\t".join(headers))

        for row in rows:
            values: list[str] = []
            for column in columns:
                if (row, column) not in selected:
                    values.append("")
                    continue
                index = model.index(row, column)
                value = model.data(index, Qt.ItemDataRole.DisplayRole)
                values.append("" if value is None else str(value))
            lines.append("\t".join(values))

        QApplication.clipboard().setText("\n".join(lines))

    def _export_model_csv(
        self,
        model: DatabaseTableModel,
        suggested_name: str,
    ) -> None:
        if model.columnCount() <= 0:
            return
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "CSV 저장",
            suggested_name,
            "CSV 파일 (*.csv)",
        )
        if not filename:
            return

        path = Path(filename)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")

        with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            writer = csv.writer(stream)
            writer.writerow(model.headers())
            for row in model.rows():
                writer.writerow(
                    [
                        DatabaseTableModel.display_value(value)
                        for value in row
                    ]
                )
