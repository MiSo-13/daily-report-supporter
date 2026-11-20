from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.project_store import ProjectStore
from app.project_tasks import project_task_counts, project_tasks
from app.project_workspace import ProjectWorkspace

_APP = QApplication.instance() or QApplication([])


def _task(title: str, task_id: str, status: TaskStatus, project: str = "p") -> Task:
    return Task(title, task_id=task_id, project_id=project, status=status)


def test_counts_use_latest_task_status_across_dates(tmp_path):
    store = MarkdownStore(tmp_path)
    store.save(date(2026, 11, 18), DailyDocument(today_tasks=[
        _task("진행", "one", TaskStatus.PLANNED),
        _task("완료 예정", "two", TaskStatus.IN_PROGRESS),
        _task("프로젝트 이탈", "three", TaskStatus.PLANNED),
    ]))
    store.save(date(2026, 11, 19), DailyDocument(today_tasks=[
        _task("진행", "one", TaskStatus.IN_PROGRESS),
        _task("완료 예정", "two", TaskStatus.COMPLETED),
        _task("프로젝트 이탈", "three", TaskStatus.PLANNED, "other"),
        _task("보류", "four", TaskStatus.ON_HOLD),
        _task("취소", "five", TaskStatus.CANCELLED),
    ]))
    store.save(date(2026, 11, 20), DailyDocument(today_tasks=[
        _task("독립으로 이동", "five", TaskStatus.PLANNED, ""),
    ]))
    entries = project_tasks(store, "p")
    counts = project_task_counts(entries)
    assert counts == {
        "전체": 3,
        "예정": 0,
        "진행중": 1,
        "완료": 1,
        "보류": 1,
        "취소": 0,
    }
    assert project_task_counts([])["전체"] == 0


def test_project_filters_keep_original_task_target_and_index(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("검색 프로젝트")
    reports = MarkdownStore(tmp_path / "reports")
    day = date(2026, 11, 20)
    reports.save(day, DailyDocument(today_tasks=[
        Task("검색 제외", task_id="a", project_id=project.id,
             status=TaskStatus.PLANNED),
        Task("서버 API 수정", details=["인증 모듈 개선"], task_id="b",
             project_id=project.id, status=TaskStatus.IN_PROGRESS),
        Task("문서 개선", task_id="c", project_id=project.id,
             status=TaskStatus.COMPLETED),
    ]))
    opened = []
    workspace = ProjectWorkspace(
        projects, QWidget(), lambda _message: None,
        report_store=reports, open_task=opened.append,
    )
    assert workspace.task_list.count() == 3
    assert "전체 3" in workspace.summary_label.text()
    assert "진행중 1" in workspace.summary_label.text()
    assert "완료 1" in workspace.summary_label.text()

    workspace.task_status_filter.setCurrentText("진행중")
    assert workspace.task_list.count() == 1
    assert "서버 API 수정" in workspace.task_list.item(0).text()
    workspace._open_project_task(workspace.task_list.item(0))
    assert opened[-1].target == day
    assert opened[-1].task_index == 1

    workspace.task_status_filter.setCurrentText("전체")
    workspace.task_search.setText("인증")
    assert workspace.task_list.count() == 1
    assert "서버 API 수정" in workspace.task_list.item(0).text()
    workspace.task_search.setText("없는 내용")
    assert workspace.task_list.count() == 0
    assert "전체 3" in workspace.summary_label.text()

    workspace.task_search.clear()
    workspace.task_status_filter.setCurrentText("완료")
    assert workspace.task_list.count() == 1
    assert "문서 개선" in workspace.task_list.item(0).text()


def test_project_counts_do_not_modify_existing_markdown(tmp_path):
    projects = ProjectStore(tmp_path / "config")
    project = projects.create("기존 프로젝트")
    reports = MarkdownStore(tmp_path / "reports")
    day = date(2026, 11, 20)
    reports.save(day, DailyDocument(today_tasks=[
        Task("기존 업무", project_id=project.id),
        Task("연결 없는 업무"),
    ]))
    path = reports.path_for(day)
    previous_content = path.read_bytes()
    workspace = ProjectWorkspace(
        projects, QWidget(), lambda _message: None, report_store=reports,
    )
    workspace.task_status_filter.setCurrentText("예정")
    workspace.task_search.setText("기존")
    workspace.refresh()
    assert path.read_bytes() == previous_content
    assert workspace.task_list.count() == 1
