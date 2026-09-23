from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import DailyDocument
from app.report_service import ReportService
from app.settings import AppSettings
from app.themes import THEMES, theme_names


class SettingsPanel(QWidget):
    def __init__(self, settings: AppSettings, on_theme_change) -> None:
        super().__init__()
        self.settings = settings
        self.on_theme_change = on_theme_change
        self.theme_buttons: dict[str, QPushButton] = {}

        greeting_group = QGroupBox("기본 인사말")
        self.greeting_editor = QTextEdit(self.settings.greeting)
        save_greeting = QPushButton("인사말 저장")
        save_greeting.setObjectName("primaryButton")
        self.greeting_status = QLabel("")
        save_greeting.clicked.connect(self.save_greeting)

        greeting_actions = QHBoxLayout()
        greeting_actions.addWidget(save_greeting)
        greeting_actions.addWidget(self.greeting_status)
        greeting_actions.addStretch(1)

        greeting_layout = QVBoxLayout(greeting_group)
        greeting_layout.addWidget(self.greeting_editor)
        greeting_layout.addLayout(greeting_actions)

        theme_group = QGroupBox("테마")
        theme_grid = QGridLayout()
        for index, name in enumerate(theme_names()):
            button = QPushButton(f"{name}\n{THEMES[name].description}")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, theme_name=name: self.select_theme(theme_name)
            )
            self.theme_buttons[name] = button
            theme_grid.addWidget(button, index // 2, index % 2)
        theme_group.setLayout(theme_grid)

        path_group = QGroupBox("설정 파일")
        path_layout = QVBoxLayout(path_group)
        path_layout.addWidget(QLabel(str(self.settings.path)))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Wayland 안전 모드</b> · 팝업 창 없이 설정합니다."))
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


class ReportPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.document = DailyDocument()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(False)
        self.greeting = QTextEdit()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.copy_status = QLabel("")

        generate = QPushButton("일일보고 생성")
        generate.setObjectName("primaryButton")
        copy = QPushButton("클립보드 복사")
        generate.clicked.connect(self.generate)
        copy.clicked.connect(self.copy_to_clipboard)

        form = QFormLayout()
        form.addRow("날짜", self.date_edit)
        form.addRow("인사말", self.greeting)

        actions = QHBoxLayout()
        actions.addWidget(generate)
        actions.addWidget(copy)
        actions.addWidget(self.copy_status)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>일일보고 작성</b> · Wayland 안전 모드"))
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.output, 1)

    def load(
        self,
        target: date,
        document: DailyDocument,
        greeting: str,
    ) -> None:
        self.document = document
        self.date_edit.setDate(QDate(target.year, target.month, target.day))
        self.greeting.setPlainText(greeting)
        self.generate()

    def generate(self) -> None:
        qdate = self.date_edit.date()
        target = date(qdate.year(), qdate.month(), qdate.day())
        self.output.setPlainText(
            ReportService.build(target, self.greeting.toPlainText(), self.document)
        )
        self.copy_status.clear()

    def copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self.output.toPlainText())
        self.copy_status.setText("복사 완료")
