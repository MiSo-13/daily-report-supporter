from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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


class DatabaseSidebar(QWidget):
    new_requested = pyqtSignal()
    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    connect_requested = pyqtSignal(str)
    table_selected = pyqtSignal(str, str, str)

    def __init__(self) -> None:
        super().__init__()

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setObjectName("databaseTree")
        self.tree.itemClicked.connect(self._item_clicked)
        self.tree.itemDoubleClicked.connect(self._item_double_clicked)

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
        layout.addWidget(self.tree, 1)
        layout.addLayout(profile_actions)
        layout.addWidget(self.connect_button)

    def set_profiles(
        self,
        profiles: list[DatabaseProfile],
        *,
        select_id: str | None = None,
    ) -> None:
        self.tree.clear()
        selected_item: QTreeWidgetItem | None = None
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
        item.takeChildren()
        child = QTreeWidgetItem(["연결 중..."])
        child.setDisabled(True)
        item.addChild(child)
        item.setExpanded(True)

    def set_error(self, profile_id: str, message: str) -> None:
        item = self._profile_item(profile_id)
        if item is None:
            return
        item.takeChildren()
        child = QTreeWidgetItem(["연결 실패"])
        child.setToolTip(0, message)
        child.setDisabled(True)
        item.addChild(child)
        item.setExpanded(True)

    def set_catalog(
        self,
        profile_id: str,
        catalog: dict[str, list[TableInfo]],
    ) -> None:
        item = self._profile_item(profile_id)
        if item is None:
            return

        item.takeChildren()
        for schema, tables in catalog.items():
            schema_item = QTreeWidgetItem([schema])
            schema_item.setData(0, ROLE_KIND, KIND_SCHEMA)
            schema_item.setData(
                0,
                ROLE_PAYLOAD,
                {
                    "profile_id": profile_id,
                    "schema": schema,
                },
            )
            for table in tables:
                suffix = " · VIEW" if "VIEW" in table.kind.upper() else ""
                table_item = QTreeWidgetItem([f"{table.name}{suffix}"])
                table_item.setData(0, ROLE_KIND, KIND_TABLE)
                table_item.setData(
                    0,
                    ROLE_PAYLOAD,
                    {
                        "profile_id": profile_id,
                        "schema": table.schema,
                        "table": table.name,
                    },
                )
                schema_item.addChild(table_item)
            item.addChild(schema_item)

        item.setExpanded(True)

    def _connect_selected(self) -> None:
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
        )

    def _item_double_clicked(
        self,
        item: QTreeWidgetItem,
        _column: int = 0,
    ) -> None:
        kind = item.data(0, ROLE_KIND)
        if kind == KIND_PROFILE:
            payload = item.data(0, ROLE_PAYLOAD)
            if isinstance(payload, dict):
                profile_id = str(payload.get("profile_id") or "")
                if profile_id:
                    self.connect_requested.emit(profile_id)

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


class DatabasePanel(QWidget):
    refresh_requested = pyqtSignal()
    page_requested = pyqtSignal(int)
    filter_requested = pyqtSignal(str)
    sql_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._page = 0
        self._has_next = False

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

    def set_connection_context(self, profile: DatabaseProfile) -> None:
        self.connection_label.setText(f"<b>{profile.name}</b>")
        self.connection_label.setToolTip(profile.target_label)

    def set_table_context(
        self,
        profile: DatabaseProfile,
        schema: str,
        table: str,
        sql_template: str,
    ) -> None:
        self.set_connection_context(profile)
        self.table_label.setText(f"· {schema}.{table}")
        self.refresh_button.setEnabled(True)
        self.sql_editor.setPlainText(sql_template)
        self._page = 0
        self.filter_input.clear()

    def set_loading(self, text: str = "조회 중...") -> None:
        self.data_status.setText(text)
        self.refresh_button.setEnabled(False)

    def set_data(self, result: PageResult, page: int) -> None:
        self._page = page
        self._has_next = result.has_next
        self.data_model.set_result(result.columns, result.rows)
        self.prev_button.setEnabled(page > 0)
        self.next_button.setEnabled(result.has_next)
        self.refresh_button.setEnabled(True)
        self.data_status.setText(
            f"페이지 {page + 1} · {len(result.rows)}행"
            + (" · 다음 페이지 있음" if result.has_next else "")
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
        self.sql_editor.clear()
        self.filter_input.clear()
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)

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
        self.data_table.setSortingEnabled(True)
        self.data_table.setAlternatingRowColors(True)

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

        self.data_status = QLabel("")
        pager = QHBoxLayout()
        pager.addWidget(self.prev_button)
        pager.addWidget(self.next_button)
        pager.addWidget(self.page_size_combo)
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
        self.column_table.setAlternatingRowColors(True)
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

        self.sql_button = QPushButton("SQL 실행")
        self.sql_button.setObjectName("primaryButton")
        self.sql_button.clicked.connect(
            lambda _checked=False: self.sql_requested.emit(
                self.sql_editor.toPlainText()
            )
        )
        self.sql_status = QLabel("")

        action_row = QHBoxLayout()
        action_row.addWidget(self.sql_button)
        action_row.addWidget(self.sql_status)
        action_row.addStretch(1)

        self.query_model = DatabaseTableModel()
        self.sql_table = QTableView()
        self.sql_table.setModel(self.query_model)
        self.sql_table.setSortingEnabled(True)
        self.sql_table.setAlternatingRowColors(True)

        layout = QVBoxLayout(page)
        layout.addWidget(note)
        layout.addWidget(self.sql_editor)
        layout.addLayout(action_row)
        layout.addWidget(self.sql_table, 1)
        self.tabs.addTab(page, "SQL")

    def _apply_filter(self) -> None:
        self.filter_requested.emit(self.where_clause)
