from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.project_store import ProjectStore
from app.project_tasks import ProjectTaskIndex, project_task_counts, project_tasks
from app.task_editor import TaskEditor

_APP = QApplication.instance() or QApplication([])


def test_task_editor_copies_details_without_losing_project_ids(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.create("개발")
    original = Task(
        "  기존 업무  ", link_text="요청", link_url="https://example.com",
        details=["수정 전"], status=TaskStatus.IN_PROGRESS,
        task_id="task-1", project_id=project.id,
    )
    editor = TaskEditor(
        "업무", lambda: None, default_status=TaskStatus.PLANNED,
        project_store=store,
    )
    editor.set_tasks([original])
    editor.tasks[0].details.append("편집기 내부 변경")
    assert original.details == ["수정 전"]
    result = editor.get_tasks()[0]
    result.details.append("외부 변경")
    assert editor.tasks[0].details == ["수정 전", "편집기 내부 변경"]
    assert result.task_id == original.task_id
    assert result.project_id == original.project_id
    assert result.status == original.status


def test_task_list_looks_up_projects_once_per_refresh(tmp_path, monkeypatch):
    store = ProjectStore(tmp_path)
    first = store.create("첫 번째")
    second = store.create("두 번째")
    get_calls = []
    list_calls = []
    original_list = store.list_projects

    def counted_list(*, include_archived=False):
        list_calls.append(include_archived)
        return original_list(include_archived=include_archived)

    def unexpected_get(project_id):
        get_calls.append(project_id)
        raise AssertionError("업무별 프로젝트 조회는 사용하지 않아야 한다.")

    editor = TaskEditor(
        "업무", lambda: None, default_status=TaskStatus.PLANNED,
        project_store=store,
    )
    monkeypatch.setattr(store, "list_projects", counted_list)
    monkeypatch.setattr(store, "get", unexpected_get)
    editor.set_tasks([
        Task("작업 A", task_id="a", project_id=first.id),
        Task("작업 B", task_id="b", project_id=second.id),
        Task("독립 업무", task_id="c"),
    ])
    assert len(list_calls) == 1
    assert get_calls == []
    assert "첫 번째" in editor.list_widget.item(0).text()
    assert "두 번째" in editor.list_widget.item(1).text()
    assert "독립 업무" in editor.list_widget.item(2).text()


def test_model_normalized_copies_details_and_preserves_metadata():
    raw = Task(
        "  제목  ", " 링크 ", " https://example.com ",
        ["내용"], TaskStatus.COMPLETED, "stable", "project",
    )
    normalized = raw.normalized()
    assert normalized.title == "제목"
    assert normalized.link_text == "링크"
    assert normalized.link_url == "https://example.com"
    assert normalized.details == ["내용"]
    assert normalized.task_id == "stable"
    assert normalized.project_id == "project"
    normalized.details.append("추가")
    assert raw.details == ["내용"]


def test_refactored_index_matches_full_scan_for_project_reassignment(tmp_path):
    store = MarkdownStore(tmp_path)
    older = date(2026, 11, 18)
    newer = date(2026, 11, 19)
    store.save(older, DailyDocument(today_tasks=[
        Task("이월", task_id="a", project_id="p1"),
        Task("이름이 같은 업무", project_id="p1"),
        Task("독립"),
    ]))
    store.save(newer, DailyDocument(today_tasks=[
        Task("이월", task_id="a", project_id="p2",
             status=TaskStatus.COMPLETED),
        Task("이름이 같은 업무", project_id="p1"),
        Task("별도 업무", task_id="b", project_id="p1",
             status=TaskStatus.ON_HOLD),
    ]))
    index = ProjectTaskIndex(store)
    for project_id in ("p1", "p2", "missing"):
        assert index.for_project(project_id) == project_tasks(store, project_id)
    assert project_task_counts(index.for_project("p1")) == {
        "전체": 3, "예정": 2, "진행중": 0,
        "완료": 0, "보류": 1, "취소": 0,
    }
    assert [entry.task.task_id for entry in index.for_project("p2")] == ["a"]


def test_empty_index_refresh_then_new_file(tmp_path):
    store = MarkdownStore(tmp_path)
    index = ProjectTaskIndex(store)
    assert index.for_project("p") == []
    day = date(2026, 11, 20)
    store.save(day, DailyDocument(today_tasks=[
        Task("신규", task_id="new", project_id="p")
    ]))
    assert len(index.for_project("p")) == 1
