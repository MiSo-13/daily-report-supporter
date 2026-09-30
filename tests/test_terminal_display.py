from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont, QTextCursor
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


def _format_at(display: TerminalDisplay, position: int):
    cursor = display.textCursor()
    cursor.setPosition(position)
    cursor.movePosition(
        QTextCursor.MoveOperation.NextCharacter,
        QTextCursor.MoveMode.KeepAnchor,
    )
    return cursor.charFormat()


def test_basic_ansi_color_and_text_style_are_rendered() -> None:
    display = TerminalDisplay()

    display._render_terminal_text(
        "\x1b[1;4;31mERROR\x1b[0m normal"
    )

    assert display.toPlainText() == "ERROR normal"

    error_format = _format_at(display, 0)
    assert error_format.foreground().color().name() == "#cd0000"
    assert error_format.fontWeight() == int(QFont.Weight.Bold)
    assert error_format.fontUnderline()

    normal_format = _format_at(display, 6)
    assert normal_format.fontWeight() == int(QFont.Weight.Normal)
    assert not normal_format.fontUnderline()


def test_bright_and_background_colors_are_rendered() -> None:
    display = TerminalDisplay()

    display._render_terminal_text(
        "\x1b[93;44mWARN\x1b[0m"
    )

    char_format = _format_at(display, 0)
    assert char_format.foreground().color().name() == "#ffff00"
    assert char_format.background().color().name() == "#0000ee"


def test_256_color_palette_is_rendered() -> None:
    display = TerminalDisplay()

    display._render_terminal_text(
        "\x1b[38;5;196;48;5;17mX\x1b[0m"
    )

    char_format = _format_at(display, 0)
    assert char_format.foreground().color().name() == "#ff0000"
    assert char_format.background().color().name() == "#00005f"


def test_true_color_is_rendered() -> None:
    display = TerminalDisplay()

    display._render_terminal_text(
        "\x1b[38;2;12;34;56;48;2;78;90;123mX\x1b[0m"
    )

    char_format = _format_at(display, 0)
    assert char_format.foreground().color().name() == "#0c2238"
    assert char_format.background().color().name() == "#4e5a7b"


def test_ansi_style_persists_across_output_chunks() -> None:
    display = TerminalDisplay()

    display._render_terminal_text("\x1b[32mgreen")
    display._render_terminal_text(" text")
    display._render_terminal_text("\x1b[0m plain")

    assert display.toPlainText() == "green text plain"
    assert _format_at(display, 0).foreground().color().name() == "#00cd00"
    assert _format_at(display, 8).foreground().color().name() == "#00cd00"


def test_split_escape_sequence_is_buffered_until_complete() -> None:
    display = TerminalDisplay()

    display._render_terminal_text("\x1b[38;2;255;")
    assert display.toPlainText() == ""

    display._render_terminal_text("128;0morange")

    assert display.toPlainText() == "orange"
    assert _format_at(display, 0).foreground().color().name() == "#ff8000"


def test_osc_title_sequence_is_ignored_without_leaking_text() -> None:
    display = TerminalDisplay()

    display._render_terminal_text(
        "\x1b]0;server logs\x07ready"
    )

    assert display.toPlainText() == "ready"
