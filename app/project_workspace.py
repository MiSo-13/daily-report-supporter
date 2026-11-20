from __future__ import annotations

from collections.abc import Callable
from datetime import date
from html import escape

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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

from app.models import Project
from app.project_store import ProjectStore
from app.markdown_store import MarkdownStore
from app.project_tasks import ProjectTaskEntry, ProjectTaskIndex, project_task_counts


class ProjectDialog(QDialog):
    """프로젝트 이름과 설명을 입력한다."""

    def __init__(self, parent: QWidget, project: Project | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("프로젝트 수정" if project else "새 프로젝트")
        self.setMinimumWidth(380)

        self.name_input = QLineEdit(project.name if project else "")
        self.name_input.setPlaceholderText("프로젝트 이름")
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("프로젝트 설명 (선택)")
        self.description_input.setFixedHeight(110)
        if project:
            self.description_input.setPlainText(project.description)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._validate)
        self.buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("이름", self.name_input)
        form.addRow("설명", self.description_input)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.buttons)

    @property
    def project_name(self) -> str:
        return self.name_input.text().strip()

    @property
    def project_description(self) -> str:
        return self.description_input.toPlainText()

    def _validate(self) -> None:
        if not self.project_name:
            self.error_label.setText("프로젝트 이름을 입력하세요.")
            self.name_input.setFocus()
            return
        self.accept()


class ProjectWorkspace:
    """프로젝트 목록과 상태별 업무를 관리하는 화면."""

    def __init__(
        self,
        store: ProjectStore,
        parent: QWidget,
        notify: Callable[[str], None],
        report_store: MarkdownStore | None = None,
        open_task: Callable[[ProjectTaskEntry], None] | None = None,
        new_task: Callable[[str], None] | None = None,
    ) -> None:
        self.store = store
        self.parent = parent
        self.notify = notify
        self.report_store = report_store
        self.task_index = ProjectTaskIndex(report_store) if report_store is not None else None
        self.open_task = open_task
        self.new_task = new_task
        self._task_entries: list[ProjectTaskEntry] = []
        self._has_selected_project = False
        self.selected_id: str | None = None

        self.sidebar = QWidget(parent)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>프로젝트</b>"))
        self.add_button = QPushButton("+ 새 프로젝트")
        self.add_button.setObjectName("primaryButton")
        header.addWidget(self.add_button)
        side_layout.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("프로젝트 검색")
        self.search_input.setClearButtonEnabled(True)
        self.show_archived = QCheckBox("보관된 프로젝트 표시")
        self.project_sort = QComboBox()
        self.project_sort.addItems(("이름순", "이름 역순"))
        self.project_sort.setObjectName("projectSort")
        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        side_layout.addWidget(self.search_input)
        side_layout.addWidget(self.show_archived)
        side_layout.addWidget(self.project_sort)
        side_layout.addWidget(self.project_list, 1)

        self.panel = QWidget(parent)
        content_layout = QVBoxLayout(self.panel)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        self.title_label = QLabel("<b>프로젝트를 선택하세요</b>")
        self.title_label.setObjectName("projectTitle")
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.state_label = QLabel("")

        self.edit_button = QPushButton("수정")
        self.archive_button = QPushButton("보관")
        self.restore_button = QPushButton("복원")
        buttons = QHBoxLayout()
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.archive_button)
        buttons.addWidget(self.restore_button)
        buttons.addStretch(1)
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.description_label)
        content_layout.addWidget(self.state_label)
        content_layout.addLayout(buttons)
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("projectTaskSummary")
        self.summary_label.setWordWrap(True)
        content_layout.addWidget(self.summary_label)

        task_header = QHBoxLayout()
        self.task_count_label = QLabel("소속 업무")
        self.new_task_button = QPushButton("+ 업무 추가")
        self.new_task_button.setObjectName("primaryButton")
        task_header.addWidget(self.task_count_label)
        task_header.addStretch(1)
        self.task_search = QLineEdit()
        self.task_search.setPlaceholderText("업무 검색")
        self.task_search.setClearButtonEnabled(True)
        self.task_status_filter = QComboBox()
        for status in ("전체", "예정", "진행중", "완료", "보류", "취소"):
            self.task_status_filter.addItem(status)
        self.task_status_filter.setObjectName("projectTaskStatusFilter")
        self.task_sort = QComboBox()
        self.task_sort.addItems(("최신순", "오래된순", "제목순", "상태순"))
        self.task_sort.setObjectName("projectTaskSort")
        task_header.addWidget(self.new_task_button)
        content_layout.addLayout(task_header)
        filters = QHBoxLayout()
        filters.addWidget(self.task_search, 1)
        filters.addWidget(self.task_status_filter)
        filters.addWidget(self.task_sort)
        self.clear_filters_button = QPushButton("초기화")
        filters.addWidget(self.clear_filters_button)
        content_layout.addLayout(filters)
        self.task_list = QListWidget()
        self.task_list.setObjectName("projectTaskList")
        content_layout.addWidget(self.task_list, 1)
        self.task_placeholder = QLabel(
            "프로젝트에 연결된 업무가 없습니다. 업무를 추가하거나 기존 업무에서 프로젝트를 선택하세요."
        )
        self.task_placeholder.setWordWrap(True)
        content_layout.addWidget(self.task_placeholder)
        self.no_results_label = QLabel("검색 조건에 맞는 업무가 없습니다.")
        self.no_results_label.setWordWrap(True)
        content_layout.addWidget(self.no_results_label)

        self.add_button.clicked.connect(self.create_project)
        self.edit_button.clicked.connect(self.edit_project)
        self.archive_button.clicked.connect(self.archive_project)
        self.restore_button.clicked.connect(self.restore_project)
        self.new_task_button.clicked.connect(self._create_project_task)
        self.task_list.itemDoubleClicked.connect(self._open_project_task)
        self.task_search.textChanged.connect(self._render_tasks)
        self.task_status_filter.currentIndexChanged.connect(self._render_tasks)
        self.task_sort.currentIndexChanged.connect(self._render_tasks)
        self.clear_filters_button.clicked.connect(self._clear_task_filters)
        self.project_sort.currentIndexChanged.connect(self.refresh)
        self.search_input.textChanged.connect(self.refresh)
        self.show_archived.toggled.connect(self.refresh)
        self.project_list.currentItemChanged.connect(self._selected)
        self.refresh()

    def refresh(self, *_args: object) -> None:
        keyword = self.search_input.text().strip().casefold()
        selected_id = self.selected_id
        self.project_list.blockSignals(True)
        self.project_list.clear()
        selected_item: QListWidgetItem | None = None
        projects = self.store.list_projects(
            include_archived=self.show_archived.isChecked()
        )
        projects.sort(
            key=lambda project: (project.name.casefold(), project.id),
            reverse=self.project_sort.currentIndex() == 1,
        )
        for project in projects:
            if keyword and keyword not in (
                project.name + " " + project.description
            ).casefold():
                continue
            label = project.name + ("  ·  보관됨" if project.archived else "")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, project.id)
            self.project_list.addItem(item)
            if project.id == selected_id:
                selected_item = item
        self.project_list.blockSignals(False)
        if selected_item is not None:
            self.project_list.setCurrentItem(selected_item)
        elif self.project_list.count():
            self.project_list.setCurrentRow(0)
        else:
            self.selected_id = None
            self._show_project(None)

    def _selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        self.selected_id = (
            str(current.data(Qt.ItemDataRole.UserRole))
            if current is not None else None
        )
        self._show_project(
            self.store.get(self.selected_id) if self.selected_id else None
        )

    def _show_project(self, project: Project | None) -> None:
        self.title_label.setText(
            f"<b>{escape(project.name)}</b>" if project else "<b>프로젝트를 선택하세요</b>"
        )
        self.description_label.setText(project.description if project else "")
        self.state_label.setText(
            "보관된 프로젝트" if project and project.archived else ""
        )
        self.edit_button.setEnabled(project is not None)
        self.archive_button.setVisible(bool(project and not project.archived))
        self.restore_button.setVisible(bool(project and project.archived))
        self._reload_tasks(project)

    def _reload_tasks(self, project: Project | None) -> None:
        self._has_selected_project = project is not None
        self._task_entries = (
            self.task_index.for_project(project.id)
            if project is not None and self.task_index is not None else []
        )
        counts = project_task_counts(self._task_entries)
        self.summary_label.setText(
            f"전체 {counts['전체']}   ·   진행중 {counts['진행중']}"
            f"   ·   완료 {counts['완료']}   ·   예정 {counts['예정']}"
            f"   ·   보류 {counts['보류']}   ·   취소 {counts['취소']}"
            if project is not None else ""
        )
        self.summary_label.setVisible(project is not None)
        self.new_task_button.setEnabled(bool(project and not project.archived))
        self.task_list.setEnabled(project is not None)
        self.task_search.setEnabled(project is not None)
        self.task_status_filter.setEnabled(project is not None)
        self.task_sort.setEnabled(project is not None)
        self.clear_filters_button.setEnabled(project is not None)
        self._render_tasks()

    def _clear_task_filters(self) -> None:
        self.task_search.clear()
        self.task_status_filter.setCurrentIndex(0)
        self.task_sort.setCurrentIndex(0)

    def _render_tasks(self, *_args: object) -> None:
        keyword = self.task_search.text().strip().casefold()
        status = self.task_status_filter.currentText()
        selected = self.task_list.currentItem()
        selected_index = (
            selected.data(Qt.ItemDataRole.UserRole) if selected is not None else None
        )
        matching = [
            (index, entry)
            for index, entry in enumerate(self._task_entries)
            if (status == "전체" or entry.task.status.value == status)
            and (
                not keyword
                or keyword in (
                    entry.task.title + " " + " ".join(entry.task.details)
                ).casefold()
            )
        ]
        sort_mode = self.task_sort.currentIndex()
        if sort_mode == 1:
            matching.sort(key=lambda pair: (
                pair[1].target, pair[1].task_index, pair[0]
            ))
        elif sort_mode == 2:
            matching.sort(key=lambda pair: (
                pair[1].task.title.casefold(), -pair[1].target.toordinal(),
                pair[1].task_index, pair[0],
            ))
        elif sort_mode == 3:
            status_order = {"진행중": 0, "예정": 1, "보류": 2, "완료": 3, "취소": 4}
            matching.sort(key=lambda pair: (
                status_order.get(pair[1].task.status.value, 5),
                -pair[1].target.toordinal(), pair[1].task_index, pair[0],
            ))
        else:
            matching.sort(key=lambda pair: (
                pair[1].target, pair[1].task_index, pair[0]
            ), reverse=True)

        self.task_list.clear()
        selected_item = None
        for index, entry in matching:
            task = entry.task
            item = QListWidgetItem(
                f"[{task.status.value}] {task.title}  ·  {entry.target:%Y-%m-%d}"
            )
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.task_list.addItem(item)
            if index == selected_index:
                selected_item = item
        if selected_item is not None:
            self.task_list.setCurrentItem(selected_item)
        self.task_count_label.setText(
            f"소속 업무 ({len(matching)}/{len(self._task_entries)})"
        )
        self.task_placeholder.setVisible(
            self._has_selected_project and not self._task_entries
        )
        self.no_results_label.setVisible(
            self._has_selected_project
            and bool(self._task_entries)
            and not matching
        )

    def _create_project_task(self) -> None:
        project = self.store.get(self.selected_id) if self.selected_id else None
        if project is not None and not project.archived and self.new_task:
            self.new_task(project.id)

    def _open_project_task(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if (
            self.open_task is not None
            and isinstance(index, int)
            and 0 <= index < len(self._task_entries)
        ):
            self.open_task(self._task_entries[index])

    def create_project(self) -> None:
        dialog = ProjectDialog(self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            project = self.store.create(
                dialog.project_name, dialog.project_description
            )
        except (OSError, ValueError) as exc:
            self._show_error(str(exc))
            return
        self.selected_id = project.id
        self.search_input.clear()
        self.show_archived.setChecked(False)
        self.refresh()
        self.notify("프로젝트 생성 완료")

    def edit_project(self) -> None:
        project = self.store.get(self.selected_id) if self.selected_id else None
        if project is None:
            return
        dialog = ProjectDialog(self.parent, project)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.store.update(
                project.id, name=dialog.project_name,
                description=dialog.project_description,
            )
        except (OSError, ValueError) as exc:
            self._show_error(str(exc))
            return
        self.refresh()
        self.notify("프로젝트 수정 완료")

    def archive_project(self) -> None:
        if not self.selected_id:
            return
        try:
            self.store.archive(self.selected_id)
        except (OSError, ValueError, KeyError) as exc:
            self._show_error(str(exc))
            return
        self.refresh()
        self.notify("프로젝트를 보관했습니다.")

    def restore_project(self) -> None:
        if not self.selected_id:
            return
        try:
            self.store.update(self.selected_id, archived=False)
        except (OSError, ValueError, KeyError) as exc:
            self._show_error(str(exc))
            return
        self.refresh()
        self.notify("프로젝트를 복원했습니다.")

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self.parent, "프로젝트 저장 오류", message)
