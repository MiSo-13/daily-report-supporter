from datetime import date
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.task_editor import TaskEditor

_APP = QApplication.instance() or QApplication([])


def test_task_metadata_round_trip_and_legacy_compatibility():
    target = date(2026, 11, 20)
    linked = Task(
        title="프로젝트 업무", status=TaskStatus.IN_PROGRESS,
        task_id="task-123", project_id="project-456",
        details=["기존 내용", "", "다음 줄"],
    )
    text = MarkdownStore.serialize(target, DailyDocument(today_tasks=[linked]))
    assert "  - 업무 ID: task-123" in text
    assert "  - 프로젝트 ID: project-456" in text
    parsed = MarkdownStore.parse(text)
    assert parsed.today_tasks == [linked]
    assert parsed.today_tasks[0].normalized() == linked

    legacy = MarkdownStore.parse(
        "# 2026-11-20 일일 업무\n\n## 오늘 업무\n\n- [ ] 예전 업무\n  - 상태: 예정\n"
    )
    assert legacy.today_tasks[0].task_id is None
    assert legacy.today_tasks[0].project_id is None
    old_text = MarkdownStore.serialize(target, legacy)
    assert "업무 ID:" not in old_text
    assert "프로젝트 ID:" not in old_text


def test_rollover_preserves_project_and_task_ids(tmp_path):
    store = MarkdownStore(tmp_path)
    first = date(2026, 11, 20)
    store.save(first, DailyDocument(today_tasks=[
        Task("진행", status=TaskStatus.IN_PROGRESS,
             task_id="same-task", project_id="same-project"),
        Task("완료", status=TaskStatus.COMPLETED,
             task_id="completed", project_id="same-project"),
    ]))
    following = store.ensure_day(date(2026, 11, 21))
    assert [task.title for task in following.today_tasks] == ["진행"]
    assert following.today_tasks[0].task_id == "same-task"
    assert following.today_tasks[0].project_id == "same-project"


def test_editor_preserves_metadata_when_editing_and_copying():
    editor = TaskEditor("오늘 업무", lambda: None,
                        default_status=TaskStatus.PLANNED)
    editor.set_tasks([Task("기존 업무", task_id="stable",
                           project_id="parent-project")])
    editor.select_task(0)
    assert editor.get_tasks()[0].task_id == "stable"
    assert editor.get_tasks()[0].project_id == "parent-project"

    editor.title_input.setText("수정 업무")
    editor.save_changes()
    updated = editor.get_tasks()[0]
    assert updated.title == "수정 업무"
    assert updated.task_id == "stable"
    assert updated.project_id == "parent-project"


def test_new_editor_tasks_receive_unique_ids():
    editor = TaskEditor("오늘 업무", lambda: None,
                        default_status=TaskStatus.PLANNED)
    editor.title_input.setText("첫 번째")
    editor.add_task()
    editor.title_input.setText("두 번째")
    editor.add_task()

    ids = [task.task_id for task in editor.get_tasks()]
    assert len(ids) == 2
    assert all(ids)
    assert ids[0] != ids[1]
