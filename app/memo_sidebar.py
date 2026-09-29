from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.memo_store import MemoStore


class MemoSidebar(QWidget):
    def __init__(
        self,
        store: MemoStore,
        on_select: Callable[[str], None],
        on_new: Callable[[], None],
        on_delete: Callable[[], None],
    ) -> None:
        super().__init__()
        self.store = store
        self.on_select = on_select

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("메모 검색")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.refresh)

        self.new_button = QPushButton("+ 새 메모")
        self.new_button.setObjectName("primaryButton")
        self.new_button.clicked.connect(on_new)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(on_delete)

        actions = QHBoxLayout()
        actions.addWidget(self.new_button)
        actions.addWidget(self.delete_button)

        self.count_label = QLabel("")
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._selected)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_input)
        layout.addWidget(self.count_label)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(actions)

        self.refresh()

    def refresh(self, *_args: object, select_id: str | None = None) -> None:
        query = self.search_input.text().strip()

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        if query:
            results = self.store.search(query)
            self.count_label.setText(f"{len(results)}건")
            for result in results:
                item = QListWidgetItem(f"{result.title}\n{result.snippet}")
                item.setData(Qt.ItemDataRole.UserRole, result.memo_id)
                self.list_widget.addItem(item)
                if select_id == result.memo_id:
                    self.list_widget.setCurrentItem(item)
        else:
            memos = self.store.list_memos()
            self.count_label.setText(f"{len(memos)}개")
            for memo in memos:
                item = QListWidgetItem(memo.title)
                item.setData(Qt.ItemDataRole.UserRole, memo.memo_id)
                self.list_widget.addItem(item)
                if select_id == memo.memo_id:
                    self.list_widget.setCurrentItem(item)

        self.list_widget.blockSignals(False)

    def selected_id(self) -> str | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value) if value else None

    def select_id(self, memo_id: str) -> None:
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == memo_id:
                self.list_widget.setCurrentItem(item)
                return

    def first_id(self) -> str | None:
        if self.list_widget.count() == 0:
            return None
        value = self.list_widget.item(0).data(Qt.ItemDataRole.UserRole)
        return str(value) if value else None

    def _selected(self, item: QListWidgetItem) -> None:
        value = item.data(Qt.ItemDataRole.UserRole)
        if value:
            self.on_select(str(value))
