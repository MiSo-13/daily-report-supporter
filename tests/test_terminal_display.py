from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.terminal_display import TerminalDisplay


_APP = QApplication.instance() or QApplication([])


def test_backspace_control_moves_cursor_without_deleting_text() -> None:
    display = TerminalDisplay()

    display._render_terminal_text("abc")
    display._render_terminal_text("\b")

    assert display.toPlainText() == "abc"
    assert display.textCursor().position() == 2

    display._render_terminal_text("c")

    assert display.toPlainText() == "abc"
    assert display.textCursor().position() == 3


def test_insert_character_sequence_preserves_existing_tail() -> None:
    display = TerminalDisplay()

    display._render_terminal_text("abcde")
    display._render_terminal_text("\b\b")
    display._render_terminal_text("\x1b[1@X")

    assert display.toPlainText() == "abcXde"
    assert display.textCursor().position() == 4


def test_delete_character_sequence_matches_shell_backspace_redraw() -> None:
    display = TerminalDisplay()

    display._render_terminal_text("abc")
    display._render_terminal_text("\b")
    display._render_terminal_text("\b\x1b[1Pc\b")

    assert display.toPlainText() == "ac"
    assert display.textCursor().position() == 1


def test_erase_to_end_matches_shell_delete_key_redraw() -> None:
    display = TerminalDisplay()

    display._render_terminal_text("abc")
    display._render_terminal_text("\b")
    display._render_terminal_text("\x1b[K")

    assert display.toPlainText() == "ab"
    assert display.textCursor().position() == 2
