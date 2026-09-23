from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.settings import AppSettings
from app.themes import THEMES, theme_names


class SettingsPanel(QWidget):
    def __init__(
        self,
        settings: AppSettings,
        on_theme_change: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.settings = settings
        self.on_theme_change = on_theme_change
        self.theme_buttons: dict[str, QPushButton] = {}

        greeting_group = QGroupBox("기본 인사말")
        self.greeting_editor = QTextEdit(self.settings.greeting)
        self.greeting_editor.setPlaceholderText(
            "일일보고에 기본으로 사용할 인사말을 입력하세요."
        )
        self.save_greeting_button = QPushButton("인사말 저장")
        self.save_greeting_button.setObjectName("primaryButton")
        self.save_greeting_button.clicked.connect(self.save_greeting)
        self.greeting_status = QLabel("")

        greeting_actions = QHBoxLayout()
        greeting_actions.addWidget(self.save_greeting_button)
        greeting_actions.addWidget(self.greeting_status)
        greeting_actions.addStretch(1)

        greeting_layout = QVBoxLayout(greeting_group)
        greeting_layout.addWidget(self.greeting_editor)
        greeting_layout.addLayout(greeting_actions)

        theme_group = QGroupBox("테마")
        theme_description = QLabel(
            "팝업 메뉴를 사용하지 않고 아래 버튼에서 바로 테마를 선택합니다."
        )
        theme_description.setWordWrap(True)

        theme_grid = QGridLayout()
        for index, name in enumerate(theme_names()):
            theme = THEMES[name]
            button = QPushButton(f"{name}\n{theme.description}")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, theme_name=name: self.select_theme(theme_name)
            )
            theme_grid.addWidget(button, index // 2, index % 2)
            self.theme_buttons[name] = button

        theme_layout = QVBoxLayout(theme_group)
        theme_layout.addWidget(theme_description)
        theme_layout.addLayout(theme_grid)

        path_group = QGroupBox("설정 파일")
        path_label = QLabel(str(self.settings.path))
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_layout = QVBoxLayout(path_group)
        path_layout.addWidget(QLabel("테마와 인사말은 아래 JSON 파일에 저장됩니다."))
        path_layout.addWidget(path_label)

        layout = QVBoxLayout(self)
        layout.addWidget(greeting_group)
        layout.addWidget(theme_group)
        layout.addWidget(path_group)
        layout.addStretch(1)

        self.sync_theme(self.settings.theme)

    def save_greeting(self) -> None:
        self.settings.greeting = self.greeting_editor.toPlainText()
        self.greeting_status.setText("저장 완료")

    def select_theme(self, name: str) -> None:
        self.settings.theme = name
        self.sync_theme(name)
        self.on_theme_change(name)

    def sync_theme(self, name: str) -> None:
        for theme_name, button in self.theme_buttons.items():
            button.setChecked(theme_name == name)
