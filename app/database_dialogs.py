from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.database_models import (
    DB_MYSQL,
    DB_POSTGRESQL,
    DEFAULT_PORTS,
    DatabaseProfile,
)


class DatabaseProfileDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        profile: DatabaseProfile | None = None,
        test_connection: Callable[[DatabaseProfile, str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("DB 연결 편집" if profile else "새 DB 연결")
        self.setMinimumWidth(460)
        self._profile = profile
        self._test_connection = test_connection
        self._last_default_port = DEFAULT_PORTS[
            profile.db_type if profile else DB_MYSQL
        ]

        self.name_edit = QLineEdit(profile.name if profile else "")
        self.type_combo = QComboBox()
        self.type_combo.addItem("MySQL", DB_MYSQL)
        self.type_combo.addItem("PostgreSQL", DB_POSTGRESQL)

        self.host_edit = QLineEdit(profile.host if profile else "localhost")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.database_edit = QLineEdit(profile.database if profile else "")
        self.user_edit = QLineEdit(profile.user if profile else "")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("저장하지 않음 · 실행 중 메모리에만 유지")

        selected_type = profile.db_type if profile else DB_MYSQL
        index = self.type_combo.findData(selected_type)
        self.type_combo.setCurrentIndex(max(index, 0))
        self.port_spin.setValue(
            profile.port if profile else DEFAULT_PORTS[selected_type]
        )

        note = QLabel(
            "WorKing DB Viewer는 Read Only 전용입니다. "
            "비밀번호는 파일에 저장하지 않습니다."
        )
        note.setWordWrap(True)
        note.setObjectName("databaseHint")

        form = QFormLayout()
        form.addRow("이름", self.name_edit)
        form.addRow("DB", self.type_combo)
        form.addRow("Host", self.host_edit)
        form.addRow("Port", self.port_spin)
        form.addRow("Database", self.database_edit)
        form.addRow("User", self.user_edit)
        form.addRow("Password", self.password_edit)

        self.test_button = QPushButton("연결 테스트")
        self.test_button.clicked.connect(self._test)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(form)
        layout.addWidget(self.test_button)
        layout.addWidget(buttons)

        self.type_combo.currentIndexChanged.connect(self._type_changed)

    @property
    def password(self) -> str:
        return self.password_edit.text()

    @property
    def db_type(self) -> str:
        value = self.type_combo.currentData()
        return str(value or DB_MYSQL)

    def build_profile(self) -> DatabaseProfile:
        return DatabaseProfile(
            connection_id=(
                self._profile.connection_id
                if self._profile is not None
                else "preview"
            ),
            name=self.name_edit.text().strip() or "Database",
            db_type=self.db_type,
            host=self.host_edit.text().strip() or "localhost",
            port=self.port_spin.value(),
            database=self.database_edit.text().strip(),
            user=self.user_edit.text().strip(),
        )

    def accept(self) -> None:
        if not self.database_edit.text().strip():
            QMessageBox.warning(self, "DB 연결", "Database를 입력하세요.")
            return
        if not self.user_edit.text().strip():
            QMessageBox.warning(self, "DB 연결", "User를 입력하세요.")
            return
        super().accept()

    def _type_changed(self, _index: int = 0) -> None:
        new_default = DEFAULT_PORTS[self.db_type]
        if self.port_spin.value() == self._last_default_port:
            self.port_spin.setValue(new_default)
        self._last_default_port = new_default

    def _test(self, _checked: bool = False) -> None:
        if self._test_connection is None:
            return
        profile = self.build_profile()
        if not profile.database or not profile.user:
            QMessageBox.warning(
                self,
                "연결 테스트",
                "Database와 User를 입력하세요.",
            )
            return

        self.test_button.setEnabled(False)
        self.test_button.setText("확인 중...")
        try:
            self._test_connection(profile, self.password)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "연결 실패",
                str(exc),
            )
        else:
            QMessageBox.information(
                self,
                "연결 성공",
                f"{profile.name} 연결을 확인했습니다.",
            )
        finally:
            self.test_button.setEnabled(True)
            self.test_button.setText("연결 테스트")
