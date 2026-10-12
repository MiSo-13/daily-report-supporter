from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QKeyEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import DeleteConfirmDialog
from app.models import Task, TaskStatus
from app.reorderable_list import ReorderableListWidget
from app.task_detail_dialog import TaskDetailDialog


class PlainTextPasteEdit(QTextEdit):
    def keyPressEvent(self, event: QKeyEvent) -> None:
        modifiers = event.modifiers()
        paste_without_format = (
            event.key() == Qt.Key.Key_V
            and bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            and bool(
                modifiers
                & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.MetaModifier
                )
            )
        )

        if paste_without_format:
            self.insertPlainText(QApplication.clipboard().text())
            event.accept()
            return

        super().keyPressEvent(event)


class TaskEditor(QWidget):
    def __init__(
        self,
        title: str,
        on_persist: Callable[[], None],
        *,
        default_status: TaskStatus,
    ) -> None:
        super().__init__()
        self.on_persist = on_persist
        self.default_status = default_status
        self.tasks: list[Task] = []
        self._loading_form = False

        self.list_widget = ReorderableListWidget()
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.currentRowChanged.connect(self._load_selected)
        self.list_widget.itemDoubleClicked.connect(self._open_item_detail)
        self.list_widget.order_changed.connect(self._persist_reordered_tasks)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("업무 제목")

        self.link_text_input = QLineEdit()
        self.link_text_input.setPlaceholderText("예: 1694")

        self.link_url_input = QLineEdit()
        self.link_url_input.setPlaceholderText("https://...")

        self.open_url_button = QPushButton("열기")
        self.open_url_button.setObjectName("openUrlButton")
        self.open_url_button.setEnabled(False)
        self.open_url_button.clicked.connect(self._open_link_url)

        url_row = QWidget()
        url_layout = QHBoxLayout(url_row)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(6)
        url_layout.addWidget(self.link_url_input, 1)
        url_layout.addWidget(self.open_url_button)

        self.details_input = PlainTextPasteEdit()
        self.details_input.setPlaceholderText("Markdown으로 입력하세요.")
        self.details_input.setToolTip(
            "Ctrl+Shift+V: 서식 없이 붙여넣기"
        )

        self.status_input = QComboBox()
        for status in TaskStatus:
            self.status_input.addItem(status.value, status.value)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)

        self.title_input.textChanged.connect(self._form_changed)
        self.link_text_input.textChanged.connect(self._form_changed)
        self.link_url_input.textChanged.connect(self._form_changed)
        self.link_url_input.textChanged.connect(self._update_open_url_button)
        self.details_input.textChanged.connect(self._form_changed)
        self.status_input.currentIndexChanged.connect(self._form_changed)

        form = QFormLayout()
        form.addRow("제목", self.title_input)
        form.addRow("링크 이름", self.link_text_input)
        form.addRow("URL", url_row)
        form.addRow("주요 내용", self.details_input)
        form.addRow("상태", self.status_input)
        form.addRow("", self.validation_label)

        self.add_button = QPushButton("+ 업무 추가")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_task)

        self.new_mode_button = QPushButton("+ 새 업무 작성")
        self.new_mode_button.clicked.connect(self.enter_add_mode)

        self.detail_button = QPushButton("상세 보기")
        self.detail_button.clicked.connect(self.open_detail)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.delete_task)

        self.update_button = QPushButton("변경사항 저장")
        self.update_button.setObjectName("primaryButton")
        self.update_button.clicked.connect(self.save_changes)

        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.new_mode_button)
        buttons.addWidget(self.detail_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(self.update_button)

        self.heading_label = QLabel(f"<b>{title}</b>")
        self.list_hint = QLabel(
            "드래그해서 업무 순서 변경 · 더블클릭 또는 상세 보기로 크게 보기"
        )
        self.list_hint.setObjectName("taskListHint")

        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(0, 12, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addLayout(form)
        editor_layout.addLayout(buttons)

        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setHandleWidth(8)
        self.content_splitter.addWidget(self.list_widget)
        self.content_splitter.addWidget(editor_panel)
        self.content_splitter.setSizes([360, 300])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.heading_label)
        layout.addWidget(self.list_hint)
        layout.addWidget(self.content_splitter, 1)

        self._set_add_mode()

    def set_title(self, title: str) -> None:
        self.heading_label.setText(f"<b>{title}</b>")

    def set_tasks(self, tasks: list[Task]) -> None:
        self.tasks = [
            Task(
                title=t.title,
                link_text=t.link_text,
                link_url=t.link_url,
                details=list(t.details),
                status=t.status,
            )
            for t in tasks
        ]
        self.refresh()
        self.enter_add_mode()

    def select_task(self, index: int) -> None:
        if 0 <= index < len(self.tasks):
            self.list_widget.setCurrentRow(index)

    def get_tasks(self) -> list[Task]:
        return [
            Task(
                title=t.title,
                link_text=t.link_text,
                link_url=t.link_url,
                details=list(t.details),
                status=t.status,
            )
            for t in self.tasks
        ]

    def refresh(self, select_row: int | None = None) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        symbols = {
            TaskStatus.PLANNED: "○",
            TaskStatus.IN_PROGRESS: "▶",
            TaskStatus.COMPLETED: "✓",
        }
        for index, task in enumerate(self.tasks):
            item = QListWidgetItem(
                f"{symbols[task.status]} [{task.status.value}] "
                f"{task.title or '(제목 없음)'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, index)
            if task.link_url:
                label = task.link_text or task.link_url
                item.setToolTip(f"{label}\n{task.link_url}")
            self.list_widget.addItem(item)

        if select_row is not None and 0 <= select_row < len(self.tasks):
            self.list_widget.setCurrentRow(select_row)
        else:
            self.list_widget.setCurrentRow(-1)
        self.list_widget.blockSignals(False)

        if select_row is not None and 0 <= select_row < len(self.tasks):
            self._load_selected(select_row)
        else:
            self._clear_form()
            self._set_add_mode()
            self.list_widget.set_reordering_enabled(True)

    def enter_add_mode(self) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.setCurrentRow(-1)
        self.list_widget.clearSelection()
        self.list_widget.blockSignals(False)
        self._clear_form()
        self._set_add_mode()
        self.list_widget.set_reordering_enabled(True)
        self.title_input.setFocus()

    def save_current(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.tasks):
            self.save_changes()
            return

        if self.title_input.text().strip():
            self.add_task()
            return

        self.on_persist()

    def add_task(self) -> None:
        task = self._task_from_form()
        if task is None:
            self._show_validation("업무 제목을 입력하세요.")
            self.title_input.setFocus()
            return

        if task.link_text and not task.link_url:
            self._show_validation("URL을 입력하세요.")
            self.link_url_input.setFocus()
            return

        self.tasks.append(task)
        self.on_persist()
        self.refresh()
        self.title_input.setFocus()

    def delete_task(self) -> None:
        row = self.list_widget.currentRow()
        task_index = self._task_index_for_row(row)
        if task_index is None:
            return

        dialog = DeleteConfirmDialog(self, self.tasks[task_index].title)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        QTimer.singleShot(
            0,
            lambda task_index=task_index: self._delete_row(task_index),
        )

    def _delete_row(self, task_index: int) -> None:
        if task_index < 0 or task_index >= len(self.tasks):
            return
        del self.tasks[task_index]
        self.on_persist()
        self.refresh()

    def save_changes(self) -> None:
        row = self.list_widget.currentRow()
        task_index = self._task_index_for_row(row)
        if task_index is None:
            return

        task = self._task_from_form()
        if task is None:
            self._show_validation("업무 제목을 입력하세요.")
            self.title_input.setFocus()
            return

        if task.link_text and not task.link_url:
            self._show_validation("관련 문서 문구를 입력했다면 실제 주소도 입력하세요.")
            self.link_url_input.setFocus()
            return

        self.tasks[task_index] = task
        self.on_persist()
        self.refresh(select_row=row)
        self.update_button.setVisible(False)

    def _load_selected(self, row: int) -> None:
        task_index = self._task_index_for_row(row)
        if task_index is None:
            self._clear_form()
            self._set_add_mode()
            self.list_widget.set_reordering_enabled(True)
            return

        task = self.tasks[task_index]
        self._loading_form = True
        self.title_input.setText(task.title)
        self.link_text_input.setText(task.link_text)
        self.link_url_input.setText(task.link_url)
        self.details_input.setPlainText("\n".join(task.details))
        index = self.status_input.findData(task.status.value)
        self.status_input.setCurrentIndex(max(index, 0))
        self.validation_label.clear()
        self._loading_form = False
        self._set_edit_mode()
        self.update_button.setVisible(False)
        self.list_widget.set_reordering_enabled(True)

    def _form_changed(self, *_args: object) -> None:
        if self._loading_form:
            return

        self.validation_label.clear()
        row = self.list_widget.currentRow()
        task_index = self._task_index_for_row(row)
        if task_index is None:
            self._set_add_mode()
            self.list_widget.set_reordering_enabled(
                not self._form_has_draft()
            )
            return

        draft = self._task_from_form(allow_empty_title=True)
        changed = draft is not None and draft != self.tasks[task_index]
        self._set_edit_mode()
        self.update_button.setVisible(changed)
        self.list_widget.set_reordering_enabled(not changed)

    def open_detail(self) -> None:
        row = self.list_widget.currentRow()
        task_index = self._task_index_for_row(row)
        if task_index is None:
            return

        draft = self._task_from_form(allow_empty_title=True)
        task = draft if draft is not None else self.tasks[task_index]
        TaskDetailDialog(self, task).exec()

    def _open_item_detail(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        if row < 0:
            return
        self.list_widget.setCurrentRow(row)
        self.open_detail()

    def _persist_reordered_tasks(self) -> None:
        if self.update_button.isVisible():
            self.refresh(select_row=self.list_widget.currentRow())
            return

        old_tasks = list(self.tasks)
        order: list[int] = []
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            value = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(value, int):
                self.refresh()
                return
            order.append(value)

        if sorted(order) != list(range(len(old_tasks))):
            self.refresh()
            return

        selected_row = self.list_widget.currentRow()
        self.tasks = [old_tasks[index] for index in order]

        for row in range(self.list_widget.count()):
            self.list_widget.item(row).setData(
                Qt.ItemDataRole.UserRole,
                row,
            )

        self.on_persist()
        if 0 <= selected_row < len(self.tasks):
            self._load_selected(selected_row)

    def _task_index_for_row(self, row: int) -> int | None:
        if row < 0 or row >= self.list_widget.count():
            return None
        item = self.list_widget.item(row)
        value = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, int) and 0 <= value < len(self.tasks):
            return value
        if 0 <= row < len(self.tasks):
            return row
        return None

    def _form_has_draft(self) -> bool:
        default_status = self.default_status.value
        return bool(
            self.title_input.text().strip()
            or self.link_text_input.text().strip()
            or self.link_url_input.text().strip()
            or self.details_input.toPlainText()
            or str(self.status_input.currentData() or default_status)
            != default_status
        )

    def _task_from_form(self, *, allow_empty_title: bool = False) -> Task | None:
        title = self.title_input.text().strip()
        if not title and not allow_empty_title:
            return None

        details_text = self.details_input.toPlainText()

        return Task(
            title=title,
            link_text=self.link_text_input.text().strip(),
            link_url=self.link_url_input.text().strip(),
            details=details_text.split("\n") if details_text else [],
            status=TaskStatus.from_text(
                str(self.status_input.currentData() or self.default_status.value),
                default=self.default_status,
            ),
        )

    @staticmethod
    def _valid_url(text: str) -> bool:
        url = QUrl(text.strip())
        return (
            url.isValid()
            and url.scheme().lower() in {"http", "https"}
            and bool(url.host())
        )

    def _update_open_url_button(self, text: str) -> None:
        self.open_url_button.setEnabled(self._valid_url(text))

    def _open_link_url(self) -> None:
        url = self.link_url_input.text().strip()
        if self._valid_url(url):
            QDesktopServices.openUrl(QUrl(url))

    def _show_validation(self, message: str) -> None:
        self.validation_label.setText(message)

    def _clear_form(self) -> None:
        self._loading_form = True
        self.title_input.clear()
        self.link_text_input.clear()
        self.link_url_input.clear()
        self.details_input.clear()
        self.validation_label.clear()
        index = self.status_input.findData(self.default_status.value)
        self.status_input.setCurrentIndex(max(index, 0))
        self._loading_form = False

    def _set_add_mode(self) -> None:
        self.add_button.setVisible(True)
        self.new_mode_button.setVisible(False)
        self.detail_button.setVisible(False)
        self.delete_button.setVisible(False)
        self.update_button.setVisible(False)

    def _set_edit_mode(self) -> None:
        self.add_button.setVisible(False)
        self.new_mode_button.setVisible(True)
        self.detail_button.setVisible(True)
        self.delete_button.setVisible(True)
