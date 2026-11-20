from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.project_store import ProjectStore
from app.project_tasks import ProjectTaskIndex, project_tasks
from app.project_workspace import ProjectWorkspace

_APP = QApplication.instance() or QApplication([])


def _save(store, target, *tasks):
    store.save(target, DailyDocument(today_tasks=list(tasks)))


def test_index_loads_only_changed_files_and_matches_existing_search(tmp_path, monkeypatch):
    store = MarkdownStore(tmp_path / "reports")
    days = [date(2026, 11, 17), date(2026, 11, 18), date(2026, 11, 19)]
    for n, day in enumerate(days):
        _save(store, day, Task(f"업무 {n}", task_id=str(n), project_id="A"))

    calls = []
    original_load = store.load

    def counted_load(target):
        calls.append(target)
        return original_load(target)

    monkeypatch.setattr(store, "load", counted_load)
    index = ProjectTaskIndex(store)
    assert len(index.for_project("A")) == 3
    assert sorted(calls) == days
    calls.clear()

    assert len(index.for_project("A")) == 3
    assert index.for_project("B") == []
    assert calls == []

    _save(store, days[1], Task("변경됨", task_id="1", project_id="B"))
    calls.clear()
    assert [entry.task.title for entry in index.for_project("B")] == ["변경됨"]
    assert calls == [days[1]]
    assert [entry.task.title for entry in index.for_project("A")] == [
        "업무 2", "업무 0"
    ]


def test_index_removes_deleted_files_and_detects_new_dates(tmp_path):
    store = MarkdownStore(tmp_path)
    first = date(2026, 11, 18)
    second = date(2026, 11, 19)
    _save(store, first, Task("기존", task_id="one", project_id="A"))
    index = ProjectTaskIndex(store)
    assert len(index.for_project("A")) == 1

    _save(store, second, Task("새 업무", task_id="two", project_id="A"))
    assert [entry.task.title for entry in index.for_project("A")] == [
        "새 업무", "기존"
    ]
    store.path_for(first).unlink()
    assert [entry.task.title for entry in index.for_project("A")] == ["새 업무"]


def test_index_latest_id_state_and_legacy_behave_like_uncached_search(tmp_path):
    store = MarkdownStore(tmp_path)
    before = date(2026, 11, 18)
    after = date(2026, 11, 19)
    _save(store, before,
          Task("이월", task_id="same", project_id="A"),
          Task("같은 제목", project_id="A"))
    _save(store, after,
          Task("이월", task_id="same", project_id="B",
               status=TaskStatus.COMPLETED),
          Task("같은 제목", project_id="A"))
    index = ProjectTaskIndex(store)
    for project_id in ("A", "B", "unknown"):
        assert index.for_project(project_id) == project_tasks(store, project_id)
    assert len(index.for_project("A")) == 2
    assert len(index.for_project("B")) == 1


def test_ui_refresh_uses_cache_without_reloading_unchanged_reports(tmp_path, monkeypatch):
    projects = ProjectStore(tmp_path / "config")
    first = projects.create("첫 번째")
    second = projects.create("두 번째")
    reports = MarkdownStore(tmp_path / "reports")
    target = date(2026, 11, 20)
    _save(reports, target,
          Task("첫 업무", task_id="a", project_id=first.id),
          Task("둘 업무", task_id="b", project_id=second.id))
    original = reports.path_for(target).read_bytes()
    calls = []
    original_load = reports.load

    def counted_load(day):
        calls.append(day)
        return original_load(day)

    monkeypatch.setattr(reports, "load", counted_load)
    workspace = ProjectWorkspace(
        projects, QWidget(), lambda _msg: None, report_store=reports
    )
    assert len(calls) == 1

    def select_project(project_id):
        for row in range(workspace.project_list.count()):
            item = workspace.project_list.item(row)
            if item.data(256) == project_id:
                workspace.project_list.setCurrentRow(row)
                return
        raise AssertionError(f"프로젝트를 찾을 수 없음: {project_id}")

    workspace.refresh()
    select_project(first.id)
    select_project(second.id)
    assert len(calls) == 1
    assert reports.path_for(target).read_bytes() == original

    _save(reports, target,
          Task("이동한 업무", task_id="a", project_id=second.id),
          Task("둘 업무", task_id="b", project_id=second.id))
    select_project(first.id)
    workspace.refresh()
    assert len(calls) == 2
    assert workspace.task_list.count() == 0
    select_project(second.id)
    assert workspace.task_list.count() == 2


def test_index_does_not_modify_original_legacy_markdown(tmp_path):
    store = MarkdownStore(tmp_path)
    day = date(2026, 11, 20)
    _save(store, day, Task("예전 업무"))
    path = store.path_for(day)
    original = path.read_bytes()
    index = ProjectTaskIndex(store)
    assert index.for_project("A") == []
    assert path.read_bytes() == original
