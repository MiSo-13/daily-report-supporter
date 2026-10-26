from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QAbstractItemView

from app.models import Task, TaskStatus
from app.task_editor import PlainTextPasteEdit, TaskEditor


_APP = QApplication.instance() or QApplication([])


def _rich_clipboard(text: str, html: str) -> None:
    mime = QMimeData()
    mime.setText(text)
    mime.setHtml(html)
    QApplication.clipboard().setMimeData(mime)


def test_plain_text_paste_shortcut_ignores_rich_text_formatting() -> None:
    editor = PlainTextPasteEdit()
    _rich_clipboard(
        "굵은 텍스트",
        "<p><b style='color:red'>굵은 텍스트</b></p>",
    )

    QTest.keyClick(
        editor,
        Qt.Key.Key_V,
        Qt.KeyboardModifier.ControlModifier
        | Qt.KeyboardModifier.ShiftModifier,
    )

    assert editor.toPlainText() == "굵은 텍스트"
    html = editor.toHtml().lower()
    assert "color:red" not in html
    assert "#ff0000" not in html
    assert "font-weight:700" not in html
    assert "font-weight:600" not in html


def test_plain_text_paste_replaces_selected_text() -> None:
    editor = PlainTextPasteEdit()
    editor.setPlainText("앞 기존 뒤")
    cursor = editor.textCursor()
    start = editor.toPlainText().index("기존")
    cursor.setPosition(start)
    cursor.setPosition(
        start + len("기존"),
        QTextCursor.MoveMode.KeepAnchor,
    )
    editor.setTextCursor(cursor)
    _rich_clipboard("새 내용", "<b>새 내용</b>")

    QTest.keyClick(
        editor,
        Qt.Key.Key_V,
        Qt.KeyboardModifier.ControlModifier
        | Qt.KeyboardModifier.ShiftModifier,
    )

    assert editor.toPlainText() == "앞 새 내용 뒤"


def test_task_editor_uses_plain_text_paste_editor() -> None:
    editor = TaskEditor(
        "오늘 업무",
        lambda: None,
        default_status=TaskStatus.PLANNED,
    )

    assert isinstance(editor.details_input, PlainTextPasteEdit)
    assert "Ctrl+Shift+V" in editor.details_input.toolTip()


def test_task_editor_reorders_tasks_and_persists() -> None:
    persisted: list[list[str]] = []
    editor: TaskEditor

    def persist() -> None:
        persisted.append([task.title for task in editor.get_tasks()])

    editor = TaskEditor(
        "오늘 업무",
        persist,
        default_status=TaskStatus.PLANNED,
    )
    editor.set_tasks(
        [
            Task("첫 번째"),
            Task("두 번째"),
            Task("세 번째"),
        ]
    )

    moved = editor.list_widget.takeItem(0)
    editor.list_widget.insertItem(2, moved)
    editor.list_widget.setCurrentItem(moved)
    editor._persist_reordered_tasks()

    assert [task.title for task in editor.get_tasks()] == [
        "두 번째",
        "세 번째",
        "첫 번째",
    ]
    assert persisted[-1] == ["두 번째", "세 번째", "첫 번째"]


def test_task_editor_disables_reorder_while_edit_has_unsaved_changes() -> None:
    editor = TaskEditor(
        "오늘 업무",
        lambda: None,
        default_status=TaskStatus.PLANNED,
    )
    editor.set_tasks([Task("기존 업무")])
    editor.select_task(0)

    assert (
        editor.list_widget.dragDropMode()
        == QAbstractItemView.DragDropMode.InternalMove
    )

    editor.title_input.setText("수정 중 업무")

    assert (
        editor.list_widget.dragDropMode()
        == QAbstractItemView.DragDropMode.NoDragDrop
    )

    editor.save_changes()

    assert (
        editor.list_widget.dragDropMode()
        == QAbstractItemView.DragDropMode.InternalMove
    )


def test_completed_task_remains_visible_in_current_day_list() -> None:
    editor = TaskEditor(
        "오늘 업무",
        lambda: None,
        default_status=TaskStatus.PLANNED,
    )
    editor.set_tasks(
        [
            Task("진행 업무", status=TaskStatus.IN_PROGRESS),
            Task("완료 업무", status=TaskStatus.COMPLETED),
            Task("보류 업무", status=TaskStatus.ON_HOLD),
            Task("취소 업무", status=TaskStatus.CANCELLED),
        ]
    )

    assert not editor.list_widget.item(0).isHidden()
    assert not editor.list_widget.item(1).isHidden()
    assert editor.list_widget.item(2).isHidden()
    assert editor.list_widget.item(3).isHidden()


def test_inactive_toggle_reveals_hold_and_cancel_without_hiding_completed() -> None:
    editor = TaskEditor(
        "오늘 업무",
        lambda: None,
        default_status=TaskStatus.PLANNED,
    )
    editor.set_tasks(
        [
            Task("완료 업무", status=TaskStatus.COMPLETED),
            Task("보류 업무", status=TaskStatus.ON_HOLD),
            Task("취소 업무", status=TaskStatus.CANCELLED),
        ]
    )

    editor.show_inactive.setChecked(True)

    assert not editor.list_widget.item(0).isHidden()
    assert not editor.list_widget.item(1).isHidden()
    assert not editor.list_widget.item(2).isHidden()
