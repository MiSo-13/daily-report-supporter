from __future__ import annotations

from collections.abc import Callable
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from termqt import Terminal

from app.terminal_backend import (
    create_terminal_backend,
    resolve_shell,
    resolve_ssh_command,
)
from app.terminal_store import TerminalProfile


class InteractiveTerminal(Terminal):
    def __init__(self) -> None:
        super().__init__(
            360,
            240,
            font_size=11,
            padding=6,
        )
        self.maximum_line_history = 5000
        self.enable_auto_wrap(sys.platform != "win32")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        modifiers = event.modifiers()

        ctrl = bool(
            modifiers
            & Qt.KeyboardModifier.ControlModifier
        )
        shift = bool(
            modifiers
            & Qt.KeyboardModifier.ShiftModifier
        )

        if ctrl and shift and key == Qt.Key.Key_C:
            self.copy_selection()
            return

        if ctrl and shift and key == Qt.Key.Key_V:
            self.paste_clipboard()
            return

        if key == Qt.Key.Key_Tab and not ctrl:
            if shift:
                self.input(b"\x1b[Z")
            else:
                self.input(b"\t")
            return

        if key == Qt.Key.Key_Backspace and not ctrl:
            self.input(b"\x7f")
            return

        if key == Qt.Key.Key_Home and not ctrl:
            self.input(b"\x1b[H")
            return

        if key == Qt.Key.Key_End and not ctrl:
            self.input(b"\x1b[F")
            return

        if (
            key == Qt.Key.Key_Insert
            and shift
            and not ctrl
        ):
            self.paste_clipboard()
            return

        super().keyPressEvent(event)

    def copy_selection(self) -> None:
        text = self._get_selected_text_rstrip()
        if text:
            QApplication.clipboard().setText(text)

    def paste_clipboard(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            self.input(text.encode("utf-8"))

    def clear_screen(self) -> None:
        self.stdout(b"\x1b[2J\x1b[H")


class TerminalSessionWidget(QWidget):
    def __init__(self, profile: TerminalProfile) -> None:
        super().__init__()
        self.profile = profile
        self.backend = None

        self.name_label = QLabel(f"<b>{profile.name}</b>")
        self.target_label = QLabel(profile.target_label)
        self.target_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.kind_label = QLabel(
            "SSH" if profile.is_ssh else "LOCAL"
        )
        self.kind_label.setObjectName("terminalKindLabel")

        self.interrupt_button = QPushButton("중지")
        self.interrupt_button.setToolTip("Ctrl+C")
        self.interrupt_button.setObjectName("dangerButton")

        self.restart_button = QPushButton(
            "재연결" if profile.is_ssh else "재시작"
        )
        self.clear_button = QPushButton("지우기")

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.kind_label)
        header.addWidget(self.name_label)
        header.addWidget(self.target_label, 1)
        header.addWidget(self.interrupt_button)
        header.addWidget(self.clear_button)
        header.addWidget(self.restart_button)

        self.terminal = InteractiveTerminal()
        self.scrollbar = QScrollBar(
            Qt.Orientation.Vertical,
            self,
        )
        self.terminal.connect_scroll_bar(self.scrollbar)
        self.terminal.stdin_callback = self._write_input
        self.terminal.resize_callback = self._resize_backend

        terminal_row = QHBoxLayout()
        terminal_row.setContentsMargins(0, 0, 0, 0)
        terminal_row.setSpacing(0)
        terminal_row.addWidget(self.terminal, 1)
        terminal_row.addWidget(self.scrollbar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addLayout(terminal_row, 1)

        self.interrupt_button.clicked.connect(self.interrupt)
        self.restart_button.clicked.connect(self.restart)
        self.clear_button.clicked.connect(
            self.terminal.clear_screen
        )

    def set_profile(self, profile: TerminalProfile) -> None:
        old = self.profile
        launch_changed = (
            old.kind,
            old.cwd,
            old.host,
            old.port,
            old.user,
        ) != (
            profile.kind,
            profile.cwd,
            profile.host,
            profile.port,
            profile.user,
        )

        self.profile = profile
        self.name_label.setText(f"<b>{profile.name}</b>")
        self.target_label.setText(profile.target_label)
        self.kind_label.setText(
            "SSH" if profile.is_ssh else "LOCAL"
        )
        self.restart_button.setText(
            "재연결" if profile.is_ssh else "재시작"
        )

        if launch_changed and self.is_running():
            self.restart()

    def is_running(self) -> bool:
        return bool(
            self.backend is not None
            and self.backend.is_running()
        )

    def start(self) -> None:
        if self.is_running():
            self.terminal.setFocus()
            return

        if self.backend is not None:
            self.backend.close()

        if self.profile.is_ssh:
            program, arguments = resolve_ssh_command(
                host=self.profile.host,
                port=self.profile.port,
                user=self.profile.user,
            )
        else:
            program, arguments = resolve_shell()

        self.backend = create_terminal_backend(
            self.profile.cwd,
            program=program,
            arguments=arguments,
        )
        self.backend.output.connect(self.terminal.stdout)
        self.backend.exited.connect(self._finished)
        self.backend.failed.connect(self._process_error)
        self.backend.start()

        if self.backend.is_running():
            self._resize_backend(
                self.terminal.col_len,
                self.terminal.row_len,
            )
            self.terminal.setFocus()

    def restart(self) -> None:
        self._stop_process()
        self.terminal.stdout(b"\r\n")
        self.start()

    def shutdown(self) -> None:
        self._stop_process()

    def interrupt(self) -> None:
        if self.backend is None:
            return
        self.backend.interrupt()

    def _write_input(self, data: bytes) -> None:
        if not self.is_running():
            self.start()
        if self.backend is not None:
            self.backend.write(data)

    def _resize_backend(
        self,
        rows: int,
        cols: int,
    ) -> None:
        if self.backend is None:
            return
        self.backend.resize(rows, cols)

    def _finished(self) -> None:
        self.terminal.stdout(
            b"\r\n[session ended]\r\n"
        )

    def _process_error(self, message: str) -> None:
        text = (
            f"\r\n[launch failed] {message}\r\n"
        ).encode("utf-8", errors="replace")
        self.terminal.stdout(text)

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
    ) -> None:
        super().__init__()
        self.on_select = on_select

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._selected)

        self.new_local_button = QPushButton("+ 로컬")
        self.new_local_button.setObjectName("primaryButton")
        self.new_local_button.clicked.connect(on_new_local)

        self.new_ssh_button = QPushButton("+ SSH")
        self.new_ssh_button.setObjectName("primaryButton")
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
            prefix = "SSH" if profile.is_ssh else "로컬"
            item = QListWidgetItem(
                f"{prefix}  ·  {profile.name}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                profile.terminal_id,
            )
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

        value = self.list_widget.item(0).data(
            Qt.ItemDataRole.UserRole
        )
        return str(value) if value else None

    def select_id(self, terminal_id: str) -> None:
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if (
                item.data(Qt.ItemDataRole.UserRole)
                == terminal_id
            ):
                self.list_widget.setCurrentItem(item)
                return

    def _selected(self, item: QListWidgetItem) -> None:
        value = item.data(Qt.ItemDataRole.UserRole)
        if value:
            self.on_select(str(value))


class TerminalPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widgets: dict[str, TerminalSessionWidget] = {}
        self.stack = QStackedWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def add_profile(self, profile: TerminalProfile) -> None:
        if profile.terminal_id in self.widgets:
            return

        widget = TerminalSessionWidget(profile)
        self.widgets[profile.terminal_id] = widget
        self.stack.addWidget(widget)

    def set_profile(self, profile: TerminalProfile) -> None:
        widget = self.widgets.get(profile.terminal_id)
        if widget is not None:
            widget.set_profile(profile)

    def select(self, terminal_id: str) -> None:
        widget = self.widgets.get(terminal_id)
        if widget is not None:
            self.stack.setCurrentWidget(widget)
            widget.start()

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
