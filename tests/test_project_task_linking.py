from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.project_store import ProjectStore
from app.project_tasks import project_tasks
from app.project_workspace import ProjectWorkspace
from app.task_editor import TaskEditor

_APP = QApplication.instance() or QApplication([])


def test_task_editor_links_and_unlinks_existing_task(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("프로젝트 A")
    editor = TaskEditor(
        "오늘 업무", lambda: None, default_status=TaskStatus.PLANNED,
        project_store=projects,
    )
    editor.set_tasks([Task("기존 업무", task_id="stable")])
    editor.select_task(0)
    editor._select_project(project.id)
    editor.save_changes()
    assert editor.get_tasks()[0].project_id == project.id
    assert editor.get_tasks()[0].task_id == "stable"

    editor.select_task(0)
    editor._select_project(None)
    editor.save_changes()
    assert editor.get_tasks()[0].project_id is None
    assert editor.get_tasks()[0].task_id == "stable"


def test_new_project_task_keeps_project_metadata(tmp_path):
    projects = ProjectStore(tmp_path)
    project = projects.create("프로젝트 B")
    editor = TaskEditor(
        "오늘 업무", lambda: None, default_status=TaskStatus.PLANNED,
        project_store=projects,
    )
    editor.prepare_new_task(project.id)
    editor.title_input.setText("하위 업무")
    editor.add_task()

    task = editor.get_tasks()[0]
    assert task.title == "하위 업무"
    assert task.project_id == project.id
    assert task.task_id


def test_project_task_index_uses_latest_snapshot_and_keeps_legacy_separate(tmp_path):
    store = MarkdownStore(tmp_path)
    first = date(2026, 11, 18)
    second = date(2026, 11, 19)
    store.save(first, DailyDocument(today_tasks=[
        Task("첫 번째", task_id="same", project_id="project-A"),
        Task("같은 제목", project_id="project-A"),
        Task("독립 업무"),
    ]))
    store.save(second, DailyDocument(today_tasks=[
        Task("첫 번째 수정", status=TaskStatus.IN_PROGRESS,
             task_id="same", project_id="project-A"),
        Task("같은 제목", project_id="project-A"),
        Task("다른 프로젝트", task_id="other", project_id="project-B"),
    ]))

    entries = project_tasks(store, "project-A")
    assert len(entries) == 3
    assert entries[0].task.title == "같은 제목"
    assert entries[1].task.title == "첫 번째 수정"
    assert entries[1].target == second
    assert entries[1].task_index == 0
    assert entries[2].target == first


def test_project_workspace_lists_tasks_and_opens_selected(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("프로젝트 C")
    reports = MarkdownStore(tmp_path / "reports")
    day = date(2026, 11, 20)
    reports.save(day, DailyDocument(today_tasks=[
        Task("연결된 업무", project_id=project.id, task_id="task-1"),
        Task("독립 업무"),
    ]))
    opened = []
    created = []
    workspace = ProjectWorkspace(
        projects, QWidget(), lambda _message: None,
        report_store=reports,
        open_task=opened.append,
        new_task=created.append,
    )
    assert workspace.task_list.count() == 1
    assert "연결된 업무" in workspace.task_list.item(0).text()
    workspace._open_project_task(workspace.task_list.item(0))
    assert opened[0].target == day
    assert opened[0].task_index == 0
    workspace._create_project_task()
    assert created == [project.id]


def test_legacy_markdown_and_unlinked_tasks_remain_supported(tmp_path):
    store = MarkdownStore(tmp_path / "reports")
    day = date(2026, 11, 20)
    store.save(day, DailyDocument(today_tasks=[Task("기존 업무")]))
    original = store.path_for(day).read_text(encoding="utf-8")
    projects = ProjectStore(tmp_path / "config")
    projects.create("추가 프로젝트")
    assert store.path_for(day).read_text(encoding="utf-8") == original
    assert store.load(day).today_tasks[0].project_id is None
