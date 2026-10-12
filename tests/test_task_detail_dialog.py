from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.models import Task, TaskStatus
from app.task_detail_dialog import TaskDetailDialog


_APP = QApplication.instance() or QApplication([])


def test_task_detail_dialog_shows_task_content() -> None:
    task = Task(
        title="긴 업무 확인",
        link_text="문서",
        link_url="https://example.com/doc",
        details=[
            "## 확인 내용",
            "",
            "- 첫 번째",
            "- 두 번째",
        ],
        status=TaskStatus.IN_PROGRESS,
    )

    dialog = TaskDetailDialog(None, task)

    assert "긴 업무 확인" in dialog.title_label.text()
    assert dialog.status_label.text() == "상태: 진행중"
    assert dialog.tabs.count() == 2
    assert dialog.tabs.tabText(0) == "미리보기"
    assert dialog.tabs.tabText(1) == "원문"
    assert "첫 번째" in dialog.preview.toPlainText()
    assert dialog.source.toPlainText() == "\n".join(task.details)
    assert dialog.source.isReadOnly()
    assert "관련 문서 열기" in dialog.open_link_button.text()


def test_task_detail_dialog_handles_empty_details() -> None:
    dialog = TaskDetailDialog(
        None,
        Task(
            title="내용 없는 업무",
            status=TaskStatus.PLANNED,
        ),
    )

    assert "주요 내용이 없습니다." in dialog.preview.toPlainText()
    assert dialog.source.toPlainText() == ""
