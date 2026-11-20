from __future__ import annotations

import os
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.project_store import ProjectStore
from app.project_tasks import project_tasks
from app.task_editor import TaskEditor

_APP = QApplication.instance() or QApplication([])


def test_unsaved_project_change_is_preserved_before_date_navigation(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    first = projects.create("첫 프로젝트")
    second = projects.create("두 번째 프로젝트")
    reports = MarkdownStore(tmp_path / "reports")
    yesterday = date.today() - timedelta(days=1)
    reports.save(yesterday, DailyDocument(today_tasks=[
        Task("기존 업무", task_id="stable", project_id=first.id),
    ]))

    window = MainWindow(data_root=tmp_path)
    try:
        assert window.load_date(yesterday)
        editor = window.today_editor
        editor.select_task(0)
        editor._select_project(second.id)
        assert window.load_date(date.today())
        saved = reports.load(yesterday).today_tasks[0]
        assert saved.task_id == "stable"
        assert saved.project_id == second.id
        assert project_tasks(reports, first.id) == []
        assert len(project_tasks(reports, second.id)) == 1
    finally:
        window.close()


def test_invalid_draft_blocks_navigation_without_overwriting_report(tmp_path):
    reports = MarkdownStore(tmp_path / "reports")
    today = date.today()
    yesterday = today - timedelta(days=1)
    reports.save(yesterday, DailyDocument(today_tasks=[Task("이전 업무")]))
    window = MainWindow(data_root=tmp_path)
    try:
        editor = window.today_editor
        editor.enter_add_mode()
        editor.link_text_input.setText("주소 없는 링크")
        before = reports.path_for(today).read_bytes()
        assert not window.load_date(yesterday)
        assert window.current_date == today
        assert editor.link_text_input.text() == "주소 없는 링크"
        assert reports.path_for(today).read_bytes() == before

        editor.title_input.setText("새 업무")
        assert not window.load_date(yesterday)
        assert "URL" in editor.validation_label.text()
        assert reports.path_for(today).read_bytes() == before

        editor.link_url_input.setText("https://example.com")
        assert window.load_date(yesterday)
        saved = reports.load(today).today_tasks
        assert saved[-1].title == "새 업무"
        assert saved[-1].task_id
    finally:
        window.close()


def test_today_reload_keeps_unsaved_task_and_existing_config(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("기존 프로젝트")
    window = MainWindow(data_root=tmp_path)
    try:
        config_file = tmp_path / "config" / "settings.json"
        original_settings = config_file.read_bytes() if config_file.exists() else None
        editor = window.today_editor
        editor.prepare_new_task(project.id)
        editor.title_input.setText("오늘의 새 업무")
        window.open_today()
        tasks = window.store.load(date.today()).today_tasks
        assert any(t.title == "오늘의 새 업무"
                   and t.project_id == project.id and t.task_id for t in tasks)
        assert (config_file.read_bytes() if config_file.exists() else None) == original_settings
    finally:
        window.close()


def test_editor_navigation_without_change_does_not_persist(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("프로젝트")
    persisted = []
    editor = TaskEditor(
        "일일 업무", lambda: persisted.append(True),
        default_status=TaskStatus.PLANNED, project_store=projects,
    )
    editor.set_tasks([Task("기존", task_id="unchanged", project_id=project.id)])
    editor.select_task(0)
    assert editor.save_before_navigation()
    assert persisted == []
    editor.enter_add_mode()
    assert editor.save_before_navigation()
    assert persisted == []


def test_two_tasks_with_same_title_remain_distinct(tmp_path):
    reports = MarkdownStore(tmp_path)
    first = date(2026, 11, 18)
    second = date(2026, 11, 19)
    reports.save(first, DailyDocument(today_tasks=[
        Task("같은 제목", task_id="a", project_id="p"),
        Task("같은 제목", task_id="b", project_id="p"),
    ]))
    reports.save(second, DailyDocument(today_tasks=[
        Task("같은 제목", task_id="a", project_id="p",
             status=TaskStatus.COMPLETED),
        Task("같은 제목", task_id="b", project_id="p",
             status=TaskStatus.IN_PROGRESS),
    ]))
    entries = project_tasks(reports, "p")
    assert len(entries) == 2
    assert {e.task.task_id for e in entries} == {"a", "b"}
    assert {e.task.status for e in entries} == {
        TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS,
    }
