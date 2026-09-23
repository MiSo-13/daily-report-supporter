from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import Task, TaskStatus


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

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentRowChanged.connect(self._load_selected)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("업무 제목")
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("https://...")
        self.details_input = QTextEdit()
        self.details_input.setPlaceholderText("주요 내용을 한 줄에 하나씩 입력하세요.")
        self.status_input = QComboBox()
        for status in TaskStatus:
            self.status_input.addItem(status.value, status.value)

        self.title_input.textChanged.connect(self._form_changed)
        self.link_input.textChanged.connect(self._form_changed)
        self.details_input.textChanged.connect(self._form_changed)
        self.status_input.currentIndexChanged.connect(self._form_changed)

        form = QFormLayout()
        form.addRow("제목", self.title_input)
        form.addRow("관련 문서 링크", self.link_input)
        form.addRow("주요 내용", self.details_input)
        form.addRow("상태", self.status_input)

        self.add_button = QPushButton("+ 업무 추가")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_task)

        self.new_mode_button = QPushButton("+ 새 업무 작성")
        self.new_mode_button.clicked.connect(self.enter_add_mode)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.delete_task)

        self.update_button = QPushButton("변경사항 저장")
        self.update_button.setObjectName("primaryButton")
        self.update_button.clicked.connect(self.save_changes)

        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.new_mode_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(self.update_button)

        help_label = QLabel(
            "새 업무는 입력 후 '+ 업무 추가'를 누르면 즉시 저장됩니다. "
            "기존 업무는 목록에서 선택해 수정하세요."
        )
        help_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{title}</b>"))
        layout.addWidget(help_label)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(form)
        layout.addLayout(buttons)

        self._set_add_mode()

    def set_tasks(self, tasks: list[Task]) -> None:
        self.tasks = [Task(t.title, t.link, list(t.details), t.status) for t in tasks]
        self.refresh()
        self.enter_add_mode()

    def get_tasks(self) -> list[Task]:
        return [Task(t.title, t.link, list(t.details), t.status) for t in self.tasks]

    def refresh(self, select_row: int | None = None) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        symbols = {
            TaskStatus.PLANNED: "○",
            TaskStatus.IN_PROGRESS: "▶",
            TaskStatus.COMPLETED: "✓",
        }
        for task in self.tasks:
            item = QListWidgetItem(
                f"{symbols[task.status]} [{task.status.value}] "
                f"{task.title or '(제목 없음)'}"
            )
            if task.link:
                item.setToolTip(task.link)
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

    def enter_add_mode(self) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.setCurrentRow(-1)
        self.list_widget.clearSelection()
        self.list_widget.blockSignals(False)
        self._clear_form()
        self._set_add_mode()
        self.title_input.setFocus()

    def add_task(self) -> None:
        task = self._task_from_form()
        if task is None:
            QMessageBox.warning(self, "입력 확인", "업무 제목을 입력하세요.")
            self.title_input.setFocus()
            return

        self.tasks.append(task)
        self.on_persist()
        self.refresh()
        self.title_input.setFocus()

    def delete_task(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.tasks):
            return
        if (
            QMessageBox.question(
                self,
                "업무 삭제",
                f"'{self.tasks[row].title}' 업무를 삭제할까요?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        del self.tasks[row]
        self.on_persist()
        self.refresh()

    def save_changes(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.tasks):
            return

        task = self._task_from_form()
        if task is None:
            QMessageBox.warning(self, "입력 확인", "업무 제목을 입력하세요.")
            self.title_input.setFocus()
            return

        self.tasks[row] = task
        self.on_persist()
        self.refresh(select_row=row)
        self.update_button.setVisible(False)

    def _load_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.tasks):
            self._clear_form()
            self._set_add_mode()
            return

        task = self.tasks[row]
        self._loading_form = True
        self.title_input.setText(task.title)
        self.link_input.setText(task.link)
        self.details_input.setPlainText("\n".join(task.details))
        index = self.status_input.findData(task.status.value)
        self.status_input.setCurrentIndex(max(index, 0))
        self._loading_form = False
        self._set_edit_mode()
        self.update_button.setVisible(False)

    def _form_changed(self, *_args: object) -> None:
        if self._loading_form:
            return

        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.tasks):
            self._set_add_mode()
            return

        draft = self._task_from_form(allow_empty_title=True)
        self._set_edit_mode()
        self.update_button.setVisible(draft is not None and draft != self.tasks[row])

    def _task_from_form(self, *, allow_empty_title: bool = False) -> Task | None:
        title = self.title_input.text().strip()
        if not title and not allow_empty_title:
            return None

        return Task(
            title=title,
            link=self.link_input.text().strip(),
            details=[
                line.strip()
                for line in self.details_input.toPlainText().splitlines()
                if line.strip()
            ],
            status=TaskStatus.from_text(
                str(self.status_input.currentData() or self.default_status.value),
                default=self.default_status,
            ),
        )

    def _clear_form(self) -> None:
        self._loading_form = True
        self.title_input.clear()
        self.link_input.clear()
        self.details_input.clear()
        index = self.status_input.findData(self.default_status.value)
        self.status_input.setCurrentIndex(max(index, 0))
        self._loading_form = False

    def _set_add_mode(self) -> None:
        self.add_button.setVisible(True)
        self.new_mode_button.setVisible(False)
        self.delete_button.setVisible(False)
        self.update_button.setVisible(False)

    def _set_edit_mode(self) -> None:
        self.add_button.setVisible(False)
        self.new_mode_button.setVisible(True)
        self.delete_button.setVisible(True)
