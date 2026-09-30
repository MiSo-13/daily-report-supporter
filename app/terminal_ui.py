from __future__ import annotations

from collections.abc import Callable
import locale
import os
from pathlib import Path
import re
import shutil
import sys

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt
from PyQt6.QtGui import QFontDatabase, QKeyEvent, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.terminal_store import TerminalProfile


ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def resolve_shell() -> tuple[str, list[str]]:
    if sys.platform == "win32":
        return os.environ.get("COMSPEC") or "cmd.exe", ["/Q"]

    configured = os.environ.get("SHELL")
    if configured and Path(configured).exists():
        return configured, []

    bash = shutil.which("bash")
    if bash:
        return bash, []

    return shutil.which("sh") or "/bin/sh", []


class CommandLineEdit(QLineEdit):
    def __init__(self) -> None:
        super().__init__()
        self._history: list[str] = []
        self._history_index = 0

    def add_history(self, command: str) -> None:
        if not command:
            return
        if not self._history or self._history[-1] != command:
            self._history.append(command)
        self._history_index = len(self._history)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up and self._history:
            self._history_index = max(0, self._history_index - 1)
            self.setText(self._history[self._history_index])
            self.end(False)
            return

        if event.key() == Qt.Key.Key_Down and self._history:
            self._history_index = min(len(self._history), self._history_index + 1)
            if self._history_index == len(self._history):
                self.clear()
            else:
                self.setText(self._history[self._history_index])
                self.end(False)
            return

        super().keyPressEvent(event)


class TerminalSessionWidget(QWidget):
    def __init__(self, profile: TerminalProfile) -> None:
        super().__init__()
        self.profile = profile
        self.program, self.arguments = resolve_shell()
        self.encoding = locale.getpreferredencoding(False) or "utf-8"

        self.name_label = QLabel(f"<b>{profile.name}</b>")
        self.cwd_label = QLabel(profile.cwd)
        self.cwd_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.restart_button = QPushButton("재시작")
        self.clear_button = QPushButton("지우기")

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.name_label)
        header.addWidget(self.cwd_label, 1)
        header.addWidget(self.clear_button)
        header.addWidget(self.restart_button)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("terminalOutput")
        self.output.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.output.document().setMaximumBlockCount(5000)

        self.command_input = CommandLineEdit()
        self.command_input.setPlaceholderText("명령어")
        self.run_button = QPushButton("실행")
        self.run_button.setObjectName("primaryButton")

        command_row = QHBoxLayout()
        command_row.setSpacing(8)
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.run_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(self.output, 1)
        layout.addLayout(command_row)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.started.connect(self._started)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)

        self.command_input.returnPressed.connect(self.run_command)
        self.run_button.clicked.connect(self.run_command)
        self.restart_button.clicked.connect(self.restart)
        self.clear_button.clicked.connect(self.output.clear)

        self.start()

    def set_profile(self, profile: TerminalProfile) -> None:
        self.profile = profile
        self.name_label.setText(f"<b>{profile.name}</b>")
        self.cwd_label.setText(profile.cwd)

    def start(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return

        cwd = Path(self.profile.cwd).expanduser()
        if not cwd.is_dir():
            cwd = Path.home()

        environment = QProcessEnvironment.systemEnvironment()
        if sys.platform != "win32":
            environment.insert("TERM", "dumb")
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(cwd))
        self.process.start(self.program, self.arguments)

    def restart(self) -> None:
        self._stop_process()
        self._append_text("\n")
        self.start()

    def shutdown(self) -> None:
        self._stop_process()

    def run_command(self) -> None:
        command = self.command_input.text()
        if not command.strip():
            return

        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.start()
            if not self.process.waitForStarted(1000):
                return

        self.command_input.add_history(command)
        self._append_text(f"> {command}\n")
        self.process.write((command + os.linesep).encode(self.encoding, errors="replace"))
        self.command_input.clear()

    def _started(self) -> None:
        shell_name = Path(self.program).name
        self._append_text(f"{shell_name} · {self.process.workingDirectory()}\n")

    def _read_output(self) -> None:
        raw = bytes(self.process.readAllStandardOutput())
        if not raw:
            return
        text = raw.decode(self.encoding, errors="replace")
        text = ANSI_ESCAPE_RE.sub("", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        self._append_text(text)

    def _finished(
        self,
        _exit_code: int,
        _status: QProcess.ExitStatus,
    ) -> None:
        self._append_text("\n[종료]\n")

    def _process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._append_text(f"[실행 실패] {self.program}\n")

    def _append_text(self, text: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _stop_process(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self.process.terminate()
        if not self.process.waitForFinished(500):
            self.process.kill()
            self.process.waitForFinished(500)


class TerminalSidebar(QWidget):
    def __init__(
        self,
        on_select: Callable[[str], None],
        on_new: Callable[[], None],
        on_rename: Callable[[], None],
        on_delete: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_select = on_select

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._selected)

        self.new_button = QPushButton("+ 새 터미널")
        self.new_button.setObjectName("primaryButton")
        self.new_button.clicked.connect(on_new)

        self.rename_button = QPushButton("이름 변경")
        self.rename_button.clicked.connect(on_rename)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(on_delete)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.new_button)
        actions.addWidget(self.rename_button)
        actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(actions)

    def set_profiles(
        self,
        profiles: list[TerminalProfile],
        *,
        select_id: str | None = None,
    ) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for profile in profiles:
            item = QListWidgetItem(profile.name)
            item.setData(Qt.ItemDataRole.UserRole, profile.terminal_id)
            item.setToolTip(profile.cwd)
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
            widget.command_input.setFocus()

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
