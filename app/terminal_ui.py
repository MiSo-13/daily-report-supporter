from __future__ import annotations

from collections import deque
from collections.abc import Callable
from pathlib import Path
import re
import shutil

from PyQt6.QtCore import QEvent, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QFontDatabase,
    QInputMethodEvent,
    QKeyEvent,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.reorderable_list import ReorderableListWidget
from app.terminal_backend import create_terminal_backend, resolve_shell
from app.terminal_store import (
    TERMINAL_LOCAL,
    TERMINAL_SSH,
    TerminalProfile,
)


ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CLEAR_SCREEN_MARKERS = (
    "\x1b[2J",
    "\x1b[3J",
    "\x1bc",
    "\x0c",
)


class SshProfileDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        profile: TerminalProfile | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SSH 연결")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("예: 운영 서버")

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("예: 10.0.1.20 또는 server.example.com")

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("예: ubuntu")

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)

        if profile is not None:
            self.name_input.setText(profile.name)
            self.host_input.setText(profile.host)
            self.port_input.setValue(profile.port)
            self.user_input.setText(profile.user)

        form = QFormLayout()
        form.addRow("이름", self.name_input)
        form.addRow("Host", self.host_input)
        form.addRow("Port", self.port_input)
        form.addRow("User", self.user_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.validation_label)
        layout.addWidget(buttons)

    @property
    def profile_name(self) -> str:
        return self.name_input.text().strip() or "SSH"

    @property
    def host(self) -> str:
        return self.host_input.text().strip()

    @property
    def port(self) -> int:
        return self.port_input.value()

    @property
    def user(self) -> str:
        return self.user_input.text().strip()

    def _accept(self) -> None:
        if not self.host:
            self.validation_label.setText("Host를 입력하세요.")
            self.host_input.setFocus()
            return
        self.accept()


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
            raw_text = raw_text[clear_index + clear_length:]

        text = ANSI_ESCAPE_RE.sub("", raw_text).replace("\x07", "")
        text = text.replace("\r\n", "\n")

        scrollbar = self.verticalScrollBar()
        follow_tail = scrollbar.value() >= scrollbar.maximum() - 4

        if "\r" not in text and "\b" not in text:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text)
            self.setTextCursor(cursor)
        else:
            self._render_control_text(text)

        self._trim_document_chars()

        if follow_tail:
            scrollbar.setValue(scrollbar.maximum())

    def _render_control_text(self, text: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        buffer: list[str] = []

        def flush() -> None:
            if buffer:
                cursor.insertText("".join(buffer))
                buffer.clear()

        for char in text:
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
                    cursor.deletePreviousChar()
            else:
                buffer.append(char)

        flush()
        self.setTextCursor(cursor)

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


class TerminalSessionWidget(QWidget):
    def __init__(self, profile: TerminalProfile) -> None:
        super().__init__()
        self.profile = profile
        self.backend = None

        self.name_label = QLabel(f"<b>{profile.name}</b>")
        self.target_label = QLabel(profile.target_label)
        self.target_label.setObjectName("terminalTarget")
        self.target_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.interrupt_button = QPushButton("중지")
        self.interrupt_button.setToolTip("Ctrl+C")
        self.interrupt_button.setObjectName("dangerButton")
        self.restart_button = QPushButton("재시작")
        self.clear_button = QPushButton("지우기")

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.name_label)
        header.addWidget(self.target_label, 1)
        header.addWidget(self.interrupt_button)
        header.addWidget(self.clear_button)
        header.addWidget(self.restart_button)

        self.output = TerminalDisplay()
        self.output.input_ready.connect(self.send_input)

        hint = QLabel(
            "터미널을 클릭한 뒤 바로 입력 · Ctrl+C 중지 · Ctrl+Shift+C 복사"
        )
        hint.setObjectName("terminalHint")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(self.output, 1)
        layout.addWidget(hint)

        self.interrupt_button.clicked.connect(self.interrupt)
        self.restart_button.clicked.connect(self.restart)
        self.clear_button.clicked.connect(self.output.clear_terminal)

    def set_terminal_font(self, family: str, point_size: int) -> None:
        self.output.set_terminal_font(family, point_size)

    def set_profile(
        self,
        profile: TerminalProfile,
        *,
        restart: bool = False,
    ) -> None:
        self.profile = profile
        self.name_label.setText(f"<b>{profile.name}</b>")
        self.target_label.setText(profile.target_label)
        if restart and self.backend is not None:
            self.restart()

    def start(self) -> None:
        if self.backend is not None and self.backend.is_running():
            return

        if self.backend is not None:
            self.backend.close()

        command = self._command_for_profile()
        self.backend = create_terminal_backend(
            self.profile.cwd,
            command=command,
        )
        self.backend.output.connect(self._read_output)
        self.backend.exited.connect(self._finished)
        self.backend.failed.connect(self._process_error)
        self.backend.start()

        if self.backend.is_running():
            if self.profile.kind == TERMINAL_SSH:
                self.output.append_terminal_text(
                    f"SSH · {self.profile.target_label}\n"
                )
            else:
                program, _arguments = resolve_shell()
                self.output.append_terminal_text(
                    f"{Path(program).name} · {self.profile.cwd}\n"
                )

    def restart(self) -> None:
        self._stop_process()
        self.output.append_terminal_text("\n")
        self.start()
        self.output.setFocus()

    def shutdown(self) -> None:
        self._stop_process()

    def interrupt(self) -> None:
        self.send_input("\x03")

    def send_input(self, text: str) -> None:
        if self.backend is None or not self.backend.is_running():
            self.start()
        if self.backend is None or not self.backend.is_running():
            return
        self.backend.write(text)

    def focus_terminal(self) -> None:
        self.start()
        self.output.flush_pending()
        self.output.setFocus()

    def _command_for_profile(self) -> list[str] | None:
        if self.profile.kind != TERMINAL_SSH:
            return None

        ssh = shutil.which("ssh") or "ssh"
        target = (
            f"{self.profile.user}@{self.profile.host}"
            if self.profile.user
            else self.profile.host
        )
        return [
            ssh,
            "-p",
            str(self.profile.port),
            target,
        ]

    def _read_output(self, raw_text: str) -> None:
        self.output.append_terminal_text(raw_text)

    def _finished(self) -> None:
        self.output.append_terminal_text("\n[종료]\n")

    def _process_error(self, message: str) -> None:
        self.output.append_terminal_text(f"[실행 실패] {message}\n")

    def _stop_process(self) -> None:
        if self.backend is None:
            return
        self.backend.close()
        self.backend = None


class TerminalSidebar(QWidget):
    def __init__(
        self,
        on_select: Callable[[str], None],
        on_new_local: Callable[[], None],
        on_new_ssh: Callable[[], None],
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        on_reorder: Callable[[list[str]], None],
    ) -> None:
        super().__init__()
        self.on_select = on_select
        self.on_reorder = on_reorder

        self.list_widget = ReorderableListWidget()
        self.list_widget.itemClicked.connect(self._selected)
        self.list_widget.order_changed.connect(self._persist_order)

        self.new_local_button = QPushButton("+ 로컬")
        self.new_local_button.setObjectName("primaryButton")
        self.new_local_button.clicked.connect(on_new_local)

        self.new_ssh_button = QPushButton("+ SSH")
        self.new_ssh_button.clicked.connect(on_new_ssh)

        self.edit_button = QPushButton("편집")
        self.edit_button.clicked.connect(on_edit)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(on_delete)

        create_actions = QHBoxLayout()
        create_actions.setSpacing(8)
        create_actions.addWidget(self.new_local_button)
        create_actions.addWidget(self.new_ssh_button)

        manage_actions = QHBoxLayout()
        manage_actions.setSpacing(8)
        manage_actions.addWidget(self.edit_button)
        manage_actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(create_actions)
        layout.addLayout(manage_actions)

    def set_profiles(
        self,
        profiles: list[TerminalProfile],
        *,
        select_id: str | None = None,
    ) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for profile in profiles:
            prefix = "[SSH]" if profile.kind == TERMINAL_SSH else "[로컬]"
            item = QListWidgetItem(f"{prefix} {profile.name}")
            item.setData(Qt.ItemDataRole.UserRole, profile.terminal_id)
            item.setToolTip(profile.target_label)
            self.list_widget.addItem(item)
            if profile.terminal_id == select_id:
                self.list_widget.setCurrentItem(item)
        self.list_widget.blockSignals(False)

    def selected_id(self) -> str | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value) if value else None

    def first_id(self) -> str | None:
        if self.list_widget.count() == 0:
            return None
        value = self.list_widget.item(0).data(Qt.ItemDataRole.UserRole)
        return str(value) if value else None

    def select_id(self, terminal_id: str) -> None:
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == terminal_id:
                self.list_widget.setCurrentItem(item)
                return

    def _persist_order(self) -> None:
        terminal_ids: list[str] = []
        for index in range(self.list_widget.count()):
            value = self.list_widget.item(index).data(Qt.ItemDataRole.UserRole)
            if value:
                terminal_ids.append(str(value))
        if terminal_ids:
            self.on_reorder(terminal_ids)

    def _selected(self, item: QListWidgetItem) -> None:
        value = item.data(Qt.ItemDataRole.UserRole)
        if value:
            self.on_select(str(value))


class TerminalPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widgets: dict[str, TerminalSessionWidget] = {}
        self._font_family = ""
        self._font_size = 10
        self.stack = QStackedWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def add_profile(self, profile: TerminalProfile) -> None:
        if profile.terminal_id in self.widgets:
            return
        widget = TerminalSessionWidget(profile)
        widget.set_terminal_font(
            self._font_family,
            self._font_size,
        )
        self.widgets[profile.terminal_id] = widget
        self.stack.addWidget(widget)

    def set_terminal_font(self, family: str, point_size: int) -> None:
        self._font_family = family
        self._font_size = point_size
        for widget in self.widgets.values():
            widget.set_terminal_font(family, point_size)

    def set_profile(
        self,
        profile: TerminalProfile,
        *,
        restart: bool = False,
    ) -> None:
        widget = self.widgets.get(profile.terminal_id)
        if widget is not None:
            widget.set_profile(profile, restart=restart)

    def select(self, terminal_id: str) -> None:
        widget = self.widgets.get(terminal_id)
        if widget is not None:
            self.stack.setCurrentWidget(widget)
            widget.focus_terminal()

    def remove(self, terminal_id: str) -> None:
        widget = self.widgets.pop(terminal_id, None)
        if widget is None:
            return
        widget.shutdown()
        self.stack.removeWidget(widget)
        widget.deleteLater()

    def shutdown_all(self) -> None:
        for widget in list(self.widgets.values()):
            widget.shutdown()
