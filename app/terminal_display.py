from __future__ import annotations

from collections import deque
import re

from PyQt6.QtCore import QEvent, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QInputMethodEvent,
    QKeyEvent,
    QResizeEvent,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import QApplication, QPlainTextEdit


ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CLEAR_SCREEN_MARKERS = (
    "\x1b[2J",
    "\x1b[3J",
    "\x1bc",
    "\x0c",
)


class TerminalDisplay(QPlainTextEdit):
    input_ready = pyqtSignal(str)
    terminal_size_changed = pyqtSignal(int, int)

    MAX_BLOCKS = 1800
    MAX_DOCUMENT_CHARS = 800_000
    TRIM_TO_CHARS = 600_000
    MAX_PENDING_CHARS = 512_000
    MAX_HIDDEN_PENDING_CHARS = 128_000
    MAX_FLUSH_CHARS = 64_000
    FLUSH_INTERVAL_MS = 50

    ANSI_COLORS = (
        "#000000",
        "#cd0000",
        "#00cd00",
        "#cdcd00",
        "#0000ee",
        "#cd00cd",
        "#00cdcd",
        "#e5e5e5",
        "#7f7f7f",
        "#ff0000",
        "#00ff00",
        "#ffff00",
        "#5c5cff",
        "#ff00ff",
        "#00ffff",
        "#ffffff",
    )
    COLOR_CUBE_LEVELS = (0, 95, 135, 175, 215, 255)

    KEY_SEQUENCES = {
        Qt.Key.Key_Up: "\x1b[A",
        Qt.Key.Key_Down: "\x1b[B",
        Qt.Key.Key_Right: "\x1b[C",
        Qt.Key.Key_Left: "\x1b[D",
        Qt.Key.Key_Home: "\x1b[H",
        Qt.Key.Key_End: "\x1b[F",
        Qt.Key.Key_Delete: "\x1b[3~",
        Qt.Key.Key_PageUp: "\x1b[5~",
        Qt.Key.Key_PageDown: "\x1b[6~",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("terminalOutput")
        self.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.document().setMaximumBlockCount(self.MAX_BLOCKS)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setTabChangesFocus(False)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        self._pending_output: deque[str] = deque()
        self._pending_chars = 0
        self._overloaded = False
        self._drop_notice_pending = False
        self._terminal_cursor = QTextCursor(self.document())
        self._terminal_cursor.movePosition(QTextCursor.MoveOperation.End)
        self._escape_buffer = ""
        self._reset_ansi_style()

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(self.FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush_pending)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(40)
        self._resize_timer.timeout.connect(self._emit_terminal_size)

    def set_terminal_font(self, family: str, point_size: int) -> None:
        font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        if family:
            font.setFamily(family)
        font.setPointSize(point_size)
        self.setFont(font)
        self._schedule_terminal_resize()

    def terminal_dimensions(self) -> tuple[int, int]:
        metrics = self.fontMetrics()
        char_width = max(metrics.horizontalAdvance("M"), 1)
        line_height = max(metrics.lineSpacing(), 1)
        viewport = self.viewport()
        usable_width = max(viewport.width() - 8, char_width)
        usable_height = max(viewport.height() - 8, line_height)
        rows = max(usable_height // line_height, 1)
        columns = max(usable_width // char_width, 1)
        return rows, columns

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._schedule_terminal_resize()

    def _schedule_terminal_resize(self) -> None:
        if hasattr(self, "_resize_timer"):
            self._resize_timer.start()

    def _emit_terminal_size(self) -> None:
        rows, columns = self.terminal_dimensions()
        self.terminal_size_changed.emit(rows, columns)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Tab:
                self.input_ready.emit("\t")
                event.accept()
                return True
            if event.key() == Qt.Key.Key_Backtab:
                self.input_ready.emit("\x1b[Z")
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        modifiers = event.modifiers()
        key = event.key()

        if (
            modifiers & Qt.KeyboardModifier.ControlModifier
            and modifiers & Qt.KeyboardModifier.ShiftModifier
            and key == Qt.Key.Key_C
        ):
            self.copy()
            return

        if (
            modifiers & Qt.KeyboardModifier.ControlModifier
            and modifiers & Qt.KeyboardModifier.ShiftModifier
            and key == Qt.Key.Key_V
        ):
            self._paste_to_terminal()
            return

        if (
            modifiers & Qt.KeyboardModifier.MetaModifier
            and key == Qt.Key.Key_C
        ):
            self.copy()
            return

        if (
            modifiers & Qt.KeyboardModifier.MetaModifier
            and key == Qt.Key.Key_V
        ):
            self._paste_to_terminal()
            return

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            key_a = int(Qt.Key.Key_A)
            key_z = int(Qt.Key.Key_Z)
            if key_a <= key <= key_z:
                self.input_ready.emit(chr(key - key_a + 1))
                return

        sequence = self.KEY_SEQUENCES.get(key)
        if sequence is not None:
            self.input_ready.emit(sequence)
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.input_ready.emit("\r")
            return
        if key == Qt.Key.Key_Backspace:
            self.input_ready.emit("\x7f")
            return
        if key == Qt.Key.Key_Tab:
            self.input_ready.emit("\t")
            return
        if key == Qt.Key.Key_Escape:
            self.input_ready.emit("\x1b")
            return

        text = event.text()
        if (
            text
            and not modifiers
            & (
                Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.AltModifier
                | Qt.KeyboardModifier.MetaModifier
            )
        ):
            self.input_ready.emit(text)
            return

        super().keyPressEvent(event)

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:
        commit = event.commitString()
        if commit:
            self.input_ready.emit(commit)
        event.accept()

    def append_terminal_text(self, raw_text: str) -> None:
        if not raw_text:
            return

        self._pending_output.append(raw_text)
        self._pending_chars += len(raw_text)

        limit = (
            self.MAX_PENDING_CHARS
            if self.isVisible()
            else self.MAX_HIDDEN_PENDING_CHARS
        )
        while self._pending_chars > limit and self._pending_output:
            dropped = self._pending_output.popleft()
            self._pending_chars -= len(dropped)
            if not self._overloaded:
                self._overloaded = True
                self._drop_notice_pending = True

        if self.isVisible() and not self._flush_timer.isActive():
            self._flush_timer.start()

    def flush_pending(self) -> None:
        self._flush_pending(force=True)

    def clear_terminal(self) -> None:
        self._pending_output.clear()
        self._pending_chars = 0
        self._overloaded = False
        self._drop_notice_pending = False
        self._escape_buffer = ""
        self._reset_ansi_style()
        self.clear()
        self._reset_terminal_cursor()

    def _reset_ansi_style(self) -> None:
        self._ansi_foreground: QColor | None = None
        self._ansi_background: QColor | None = None
        self._ansi_bold = False
        self._ansi_underline = False
        self._ansi_italic = False

    def _reset_terminal_cursor(self) -> None:
        self._terminal_cursor = QTextCursor(self.document())
        self._terminal_cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(self._terminal_cursor)

    def _flush_pending(self, force: bool = False) -> None:
        if not self._pending_output:
            return
        if not force and not self.isVisible():
            return

        budget = (
            self.MAX_HIDDEN_PENDING_CHARS
            if force
            else self.MAX_FLUSH_CHARS
        )
        parts: list[str] = []
        used = 0

        while self._pending_output and used < budget:
            chunk = self._pending_output.popleft()
            remaining = budget - used
            if len(chunk) <= remaining:
                parts.append(chunk)
                used += len(chunk)
                self._pending_chars -= len(chunk)
                continue

            parts.append(chunk[:remaining])
            self._pending_output.appendleft(chunk[remaining:])
            self._pending_chars -= remaining
            used += remaining
            break

        if self._drop_notice_pending:
            parts.insert(
                0,
                "\n[출력량이 많아 오래된 터미널 로그 일부를 생략했습니다.]\n",
            )
            self._drop_notice_pending = False

        if self._overloaded and self._pending_chars < self.MAX_PENDING_CHARS // 2:
            self._overloaded = False

        if parts:
            self._render_terminal_text("".join(parts))

        if self._pending_output and self.isVisible():
            self._flush_timer.start()

    def _render_terminal_text(self, raw_text: str) -> None:
        if self._escape_buffer:
            raw_text = self._escape_buffer + raw_text
            self._escape_buffer = ""

        clear_index = -1
        clear_length = 0
        clear_marker = ""
        for marker in CLEAR_SCREEN_MARKERS:
            index = raw_text.rfind(marker)
            if index > clear_index:
                clear_index = index
                clear_length = len(marker)
                clear_marker = marker

        if clear_index >= 0:
            self.clear()
            self._reset_terminal_cursor()
            if clear_marker == "\x1bc":
                self._reset_ansi_style()
            raw_text = raw_text[clear_index + clear_length:]

        text = raw_text.replace("\r\n", "\n")

        scrollbar = self.verticalScrollBar()
        follow_tail = scrollbar.value() >= scrollbar.maximum() - 4

        if (
            "\r" not in text
            and "\b" not in text
            and "\x1b" not in text
            and "\x07" not in text
            and self._terminal_cursor.atEnd()
        ):
            self._write_printable(self._terminal_cursor, text)
            self.setTextCursor(self._terminal_cursor)
        else:
            self._render_control_text(text)

        self._trim_document_chars()

        if follow_tail:
            scrollbar.setValue(scrollbar.maximum())

    def _render_control_text(self, text: str) -> None:
        cursor = QTextCursor(self._terminal_cursor)
        buffer: list[str] = []

        def flush() -> None:
            if buffer:
                self._write_printable(cursor, "".join(buffer))
                buffer.clear()

        index = 0
        while index < len(text):
            char = text[index]

            if char == "\x1b":
                flush()
                next_index = self._consume_escape_sequence(
                    cursor,
                    text,
                    index,
                )
                if next_index is None:
                    self._escape_buffer = text[index:]
                    break
                index = next_index
                continue

            if char == "\r":
                flush()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            elif char == "\n":
                flush()
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                cursor.insertBlock()
            elif char == "\b":
                flush()
                if cursor.positionInBlock() > 0:
                    cursor.movePosition(
                        QTextCursor.MoveOperation.PreviousCharacter
                    )
            elif char == "\x07":
                flush()
            else:
                buffer.append(char)

            index += 1

        flush()
        self._terminal_cursor = cursor
        self.setTextCursor(self._terminal_cursor)

    def _consume_escape_sequence(
        self,
        cursor: QTextCursor,
        text: str,
        index: int,
    ) -> int | None:
        if index + 1 >= len(text):
            return None

        marker = text[index + 1]
        if marker == "[":
            match = ANSI_ESCAPE_RE.match(text, index)
            if match is None:
                return None
            self._handle_escape_sequence(cursor, match.group(0))
            return match.end()

        if marker == "]":
            bel_index = text.find("\x07", index + 2)
            st_index = text.find("\x1b\\", index + 2)
            endings = [
                value
                for value in (bel_index, st_index)
                if value >= 0
            ]
            if not endings:
                return None
            end = min(endings)
            return end + (2 if end == st_index else 1)

        return min(index + 2, len(text))

    def _current_char_format(self) -> QTextCharFormat:
        char_format = QTextCharFormat()
        char_format.setFontWeight(
            QFont.Weight.Bold
            if self._ansi_bold
            else QFont.Weight.Normal
        )
        char_format.setFontUnderline(self._ansi_underline)
        char_format.setFontItalic(self._ansi_italic)

        if self._ansi_foreground is not None:
            char_format.setForeground(self._ansi_foreground)
        if self._ansi_background is not None:
            char_format.setBackground(self._ansi_background)

        return char_format

    def _write_printable(self, cursor: QTextCursor, text: str) -> None:
        if not text:
            return

        char_format = self._current_char_format()
        block_text = cursor.block().text()
        remaining = max(len(block_text) - cursor.positionInBlock(), 0)
        overwrite_count = min(len(text), remaining)

        if overwrite_count:
            start = cursor.position()
            cursor.setPosition(
                start + overwrite_count,
                QTextCursor.MoveMode.KeepAnchor,
            )
            cursor.insertText(text[:overwrite_count], char_format)

        if overwrite_count < len(text):
            cursor.insertText(text[overwrite_count:], char_format)

    def _handle_escape_sequence(
        self,
        cursor: QTextCursor,
        sequence: str,
    ) -> None:
        if not sequence.startswith("\x1b[") or len(sequence) < 3:
            return

        final = sequence[-1]
        raw_params = sequence[2:-1]

        if final == "m":
            self._apply_sgr(raw_params)
            return

        if raw_params and any(
            char not in "0123456789;" for char in raw_params
        ):
            return

        params = [
            int(part) if part else 0
            for part in raw_params.split(";")
        ] if raw_params else []
        first = params[0] if params else 0
        count = first if first > 0 else 1

        if final == "D":
            steps = min(count, cursor.positionInBlock())
            if steps:
                cursor.movePosition(
                    QTextCursor.MoveOperation.PreviousCharacter,
                    QTextCursor.MoveMode.MoveAnchor,
                    steps,
                )
            return

        if final == "C":
            remaining = max(
                len(cursor.block().text()) - cursor.positionInBlock(),
                0,
            )
            steps = min(count, remaining)
            if steps:
                cursor.movePosition(
                    QTextCursor.MoveOperation.NextCharacter,
                    QTextCursor.MoveMode.MoveAnchor,
                    steps,
                )
            return

        if final == "G":
            column = max(count - 1, 0)
            block = cursor.block()
            cursor.setPosition(
                block.position() + min(column, len(block.text()))
            )
            return

        if final == "@":
            position = cursor.position()
            cursor.insertText(
                " " * count,
                self._current_char_format(),
            )
            cursor.setPosition(position)
            return

        if final == "P":
            self._delete_characters(cursor, count)
            return

        if final == "X":
            self._erase_characters(cursor, count)
            return

        if final == "K":
            self._erase_in_line(cursor, first)

    def _apply_sgr(self, raw_params: str) -> None:
        if not raw_params:
            self._reset_ansi_style()
            return

        if any(char not in "0123456789;" for char in raw_params):
            return

        params = [
            int(part) if part else 0
            for part in raw_params.split(";")
        ]
        index = 0

        while index < len(params):
            code = params[index]

            if code == 0:
                self._reset_ansi_style()
            elif code == 1:
                self._ansi_bold = True
            elif code == 3:
                self._ansi_italic = True
            elif code == 4:
                self._ansi_underline = True
            elif code == 22:
                self._ansi_bold = False
            elif code == 23:
                self._ansi_italic = False
            elif code == 24:
                self._ansi_underline = False
            elif 30 <= code <= 37:
                self._ansi_foreground = self._ansi_color(code - 30)
            elif code == 39:
                self._ansi_foreground = None
            elif 40 <= code <= 47:
                self._ansi_background = self._ansi_color(code - 40)
            elif code == 49:
                self._ansi_background = None
            elif 90 <= code <= 97:
                self._ansi_foreground = self._ansi_color(code - 90 + 8)
            elif 100 <= code <= 107:
                self._ansi_background = self._ansi_color(code - 100 + 8)
            elif code in (38, 48):
                color, consumed = self._extended_color(params, index + 1)
                if color is not None:
                    if code == 38:
                        self._ansi_foreground = color
                    else:
                        self._ansi_background = color
                index += consumed

            index += 1

    def _extended_color(
        self,
        params: list[int],
        start: int,
    ) -> tuple[QColor | None, int]:
        if start >= len(params):
            return None, 0

        mode = params[start]
        if mode == 5 and start + 1 < len(params):
            color_index = params[start + 1]
            if 0 <= color_index <= 255:
                return self._ansi_color(color_index), 2
            return None, 2

        if mode == 2 and start + 3 < len(params):
            red, green, blue = params[start + 1:start + 4]
            if all(0 <= value <= 255 for value in (red, green, blue)):
                return QColor(red, green, blue), 4
            return None, 4

        return None, 0

    def _ansi_color(self, index: int) -> QColor:
        if 0 <= index < 16:
            return QColor(self.ANSI_COLORS[index])

        if 16 <= index <= 231:
            cube = index - 16
            red_index = cube // 36
            green_index = (cube % 36) // 6
            blue_index = cube % 6
            return QColor(
                self.COLOR_CUBE_LEVELS[red_index],
                self.COLOR_CUBE_LEVELS[green_index],
                self.COLOR_CUBE_LEVELS[blue_index],
            )

        if 232 <= index <= 255:
            level = 8 + (index - 232) * 10
            return QColor(level, level, level)

        return QColor()

    @staticmethod
    def _delete_characters(cursor: QTextCursor, count: int) -> None:
        available = max(
            len(cursor.block().text()) - cursor.positionInBlock(),
            0,
        )
        delete_count = min(count, available)
        if not delete_count:
            return

        start = cursor.position()
        cursor.setPosition(
            start + delete_count,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()

    def _erase_characters(self, cursor: QTextCursor, count: int) -> None:
        available = max(
            len(cursor.block().text()) - cursor.positionInBlock(),
            0,
        )
        erase_count = min(count, available)
        if not erase_count:
            return

        start = cursor.position()
        cursor.setPosition(
            start + erase_count,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(
            " " * erase_count,
            self._current_char_format(),
        )
        cursor.setPosition(start)

    def _erase_in_line(self, cursor: QTextCursor, mode: int) -> None:
        block = cursor.block()
        block_start = block.position()
        block_end = block_start + len(block.text())
        position = cursor.position()

        if mode == 0:
            start, end = position, block_end
        elif mode == 1:
            start, end = block_start, min(position + 1, block_end)
        elif mode == 2:
            start, end = block_start, block_end
        else:
            return

        if end <= start:
            return

        if mode == 0:
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            return

        width = end - start
        original_position = position
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(
            " " * width,
            self._current_char_format(),
        )
        cursor.setPosition(
            min(
                original_position,
                cursor.block().position() + len(cursor.block().text()),
            )
        )

    def _trim_document_chars(self) -> None:
        document = self.document()
        char_count = document.characterCount()
        if char_count <= self.MAX_DOCUMENT_CHARS:
            return

        remove_count = max(char_count - self.TRIM_TO_CHARS, 0)
        cursor = QTextCursor(document)
        cursor.setPosition(0)
        cursor.setPosition(
            remove_count,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()
        cursor.insertText("[오래된 터미널 출력 생략]\n")

    def _paste_to_terminal(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            self.input_ready.emit(text)
