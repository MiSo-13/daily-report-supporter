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


class SshProfileDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        name: str = "",
        host: str = "",
        port: int = 22,
        user: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SSH 연결")

        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("예: 운영 서버")

        self.host_input = QLineEdit(host)
        self.host_input.setPlaceholderText("예: 10.0.1.20")

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(port)

        self.user_input = QLineEdit(user)
        self.user_input.setPlaceholderText("예: ubuntu")

        form = QFormLayout()
        form.addRow("이름", self.name_input)
        form.addRow("Host", self.host_input)
        form.addRow("Port", self.port_input)
        form.addRow("User", self.user_input)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.validation_label)
        layout.addWidget(self.buttons)

    @property
    def profile_name(self) -> str:
        return self.name_input.text().strip()

    @property
    def host(self) -> str:
        return self.host_input.text().strip()

    @property
    def port(self) -> int:
        return self.port_input.value()

    @property
    def user(self) -> str:
        return self.user_input.text().strip()

    def _validate_and_accept(self) -> None:
        if not self.host:
            self.validation_label.setText("Host를 입력하세요.")
            self.host_input.setFocus()
            return

        if not self.user:
            self.validation_label.setText("User를 입력하세요.")
            self.user_input.setFocus()
            return

        if not self.profile_name:
            self.name_input.setText(
                f"{self.user}@{self.host}"
            )

        self.accept()
