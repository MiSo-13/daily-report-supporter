from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.reorderable_list import ReorderableListWidget
from app.terminal_backend import create_terminal_backend, resolve_shell
from app.terminal_display import TerminalDisplay
from app.terminal_store import TERMINAL_SSH, TerminalProfile


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
