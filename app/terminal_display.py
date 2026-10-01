from __future__ import annotations

from collections import deque
import re

from PyQt6.QtCore import QEvent, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QFontDatabase,
    QInputMethodEvent,
    QKeyEvent,
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

    MAX_BLOCKS = 1800
    MAX_DOCUMENT_CHARS = 800_000
    TRIM_TO_CHARS = 600_000
    MAX_PENDING_CHARS = 512_000
    MAX_HIDDEN_PENDING_CHARS = 128_000
    MAX_FLUSH_CHARS = 64_000
    FLUSH_INTERVAL_MS = 50

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

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(self.FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush_pending)

    def set_terminal_font(self, family: str, point_size: int) -> None:
        font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        if family:
            font.setFamily(family)
        font.setPointSize(point_size)
        self.setFont(font)

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
        self.clear()
        self._reset_terminal_cursor()

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
        clear_index = -1
        clear_length = 0
        for marker in CLEAR_SCREEN_MARKERS:
            index = raw_text.rfind(marker)
            if index > clear_index:
                clear_index = index
                clear_length = len(marker)

        if clear_index >= 0:
            self.clear()
            self._reset_terminal_cursor()
            raw_text = raw_text[clear_index + clear_length:]

        text = raw_text.replace("\x07", "")
        text = text.replace("\r\n", "\n")

        scrollbar = self.verticalScrollBar()
        follow_tail = scrollbar.value() >= scrollbar.maximum() - 4

        if (
            "\r" not in text
            and "\b" not in text
            and "\x1b" not in text
            and self._terminal_cursor.atEnd()
        ):
            self._terminal_cursor.insertText(text)
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
                match = ANSI_ESCAPE_RE.match(text, index)
                if match is not None:
                    self._handle_escape_sequence(cursor, match.group(0))
                    index = match.end()
                    continue
                index += 1
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
            else:
                buffer.append(char)

            index += 1

        flush()
        self._terminal_cursor = cursor
        self.setTextCursor(self._terminal_cursor)

    def _write_printable(self, cursor: QTextCursor, text: str) -> None:
        if not text:
            return

        block_text = cursor.block().text()
        remaining = max(len(block_text) - cursor.positionInBlock(), 0)
        overwrite_count = min(len(text), remaining)

        if overwrite_count:
            start = cursor.position()
            cursor.setPosition(
                start + overwrite_count,
                QTextCursor.MoveMode.KeepAnchor,
            )
            cursor.insertText(text[:overwrite_count])

        if overwrite_count < len(text):
            cursor.insertText(text[overwrite_count:])

    def _handle_escape_sequence(
        self,
        cursor: QTextCursor,
        sequence: str,
    ) -> None:
        if not sequence.startswith("\x1b[") or len(sequence) < 3:
            return

        final = sequence[-1]
        raw_params = sequence[2:-1]
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
            cursor.insertText(" " * count)
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

    @staticmethod
    def _erase_characters(cursor: QTextCursor, count: int) -> None:
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
        cursor.insertText(" " * erase_count)
        cursor.setPosition(start)

    @staticmethod
    def _erase_in_line(cursor: QTextCursor, mode: int) -> None:
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
        cursor.insertText(" " * width)
        cursor.setPosition(
            min(original_position, cursor.block().position() + len(cursor.block().text()))
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
