from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.project_store import ProjectStore
from app.project_workspace import ProjectWorkspace

_APP = QApplication.instance() or QApplication([])


def test_project_name_sort_preserves_selection(tmp_path):
    store = ProjectStore(tmp_path / "config")
    zulu = store.create("Zulu")
    store.create("alpha")
    store.create("Beta")
    workspace = ProjectWorkspace(store, QWidget(), lambda _message: None)
    assert [workspace.project_list.item(i).text() for i in range(3)] == [
        "alpha", "Beta", "Zulu"
    ]
    workspace.selected_id = zulu.id
    workspace.refresh()
    assert workspace.project_list.currentItem().text() == "Zulu"

    workspace.project_sort.setCurrentIndex(1)
    assert [workspace.project_list.item(i).text() for i in range(3)] == [
        "Zulu", "Beta", "alpha"
    ]
    assert workspace.selected_id == zulu.id
    assert workspace.project_list.currentItem().text() == "Zulu"


def test_task_sort_and_filter_keep_original_link(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("개발")
    reports = MarkdownStore(tmp_path / "reports")
    older = date(2026, 11, 17)
    newer = date(2026, 11, 19)
    reports.save(older, DailyDocument(today_tasks=[
        Task("Z-작업", task_id="z", project_id=project.id,
             status=TaskStatus.COMPLETED),
    ]))
    reports.save(newer, DailyDocument(today_tasks=[
        Task("A-작업", task_id="a", project_id=project.id,
             status=TaskStatus.PLANNED),
        Task("M-작업", task_id="m", project_id=project.id,
             status=TaskStatus.IN_PROGRESS),
    ]))
    opened = []
    workspace = ProjectWorkspace(
        projects, QWidget(), lambda _message: None,
        report_store=reports, open_task=opened.append,
    )
    titles = lambda: [
        workspace.task_list.item(i).text() for i in range(workspace.task_list.count())
    ]
    assert "M-작업" in titles()[0]
    assert "A-작업" in titles()[1]
    assert "Z-작업" in titles()[2]

    workspace.task_sort.setCurrentText("오래된순")
    assert "Z-작업" in titles()[0]
    workspace.task_sort.setCurrentText("제목순")
    assert "A-작업" in titles()[0]
    assert "M-작업" in titles()[1]
    assert "Z-작업" in titles()[2]

    workspace.task_sort.setCurrentText("상태순")
    assert "M-작업" in titles()[0]
    assert "A-작업" in titles()[1]
    assert "Z-작업" in titles()[2]

    workspace.task_status_filter.setCurrentText("완료")
    assert workspace.task_list.count() == 1
    workspace._open_project_task(workspace.task_list.item(0))
    assert opened[-1].target == older
    assert opened[-1].task_index == 0
    assert opened[-1].task.task_id == "z"

    workspace.task_search.setText("검색결과없음")
    assert workspace.task_list.count() == 0
    assert not workspace.no_results_label.isHidden()
    assert "전체 3" in workspace.summary_label.text()

    workspace._clear_task_filters()
    assert workspace.task_sort.currentText() == "최신순"
    assert workspace.task_status_filter.currentText() == "전체"
    assert workspace.task_search.text() == ""
    assert workspace.task_list.count() == 3


def test_task_sort_preserves_selection_and_never_writes_existing_docs(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("프로젝트")
    reports = MarkdownStore(tmp_path / "reports")
    day = date(2026, 11, 20)
    reports.save(day, DailyDocument(today_tasks=[
        Task("나", task_id="a", project_id=project.id),
        Task("가", task_id="b", project_id=project.id),
    ]))
    path = reports.path_for(day)
    previous = path.read_bytes()
    workspace = ProjectWorkspace(
        projects, QWidget(), lambda _message: None, report_store=reports
    )
    workspace.task_list.setCurrentRow(0)
    selected_id = workspace._task_entries[
        workspace.task_list.currentItem().data(Qt.ItemDataRole.UserRole)
    ].task.task_id

    workspace.task_sort.setCurrentText("제목순")
    chosen = workspace.task_list.currentItem()
    assert chosen is not None
    assert workspace._task_entries[chosen.data(Qt.ItemDataRole.UserRole)].task.task_id == selected_id
    workspace.project_sort.setCurrentText("이름 역순")
    workspace.task_sort.setCurrentText("오래된순")
    assert path.read_bytes() == previous
