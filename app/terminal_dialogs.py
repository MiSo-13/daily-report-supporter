from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.terminal_store import TerminalProfile


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
