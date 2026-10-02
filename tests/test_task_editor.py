from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from app.models import TaskStatus
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
