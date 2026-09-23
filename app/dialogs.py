from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import DailyDocument
from app.report_service import ReportService


class GreetingSettingsDialog(QDialog):
    def __init__(self, parent: QWidget, greeting: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("기본 인사말 설정")
        self.resize(520, 320)

        self.editor = QTextEdit(greeting)
        self.editor.setPlaceholderText("일일보고에 사용할 기본 인사말을 입력하세요.")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("일일보고 창을 열 때 기본으로 사용할 인사말입니다."))
        layout.addWidget(self.editor, 1)
        layout.addWidget(buttons)

    @property
    def greeting(self) -> str:
        return self.editor.toPlainText().strip()


class ReportDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        target: date,
        document: DailyDocument,
        greeting: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("일일보고 작성")
        self.resize(700, 600)
        self.document = document

        self.date_edit = QDateEdit(QDate(target.year, target.month, target.day))
        self.date_edit.setCalendarPopup(True)
        self.greeting = QTextEdit(greeting)
        self.output = QTextEdit()
        self.output.setReadOnly(True)

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
        actions.addStretch(1)

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.output, 1)
        layout.addWidget(close_buttons)
        self.generate()

    def generate(self) -> None:
        qdate = self.date_edit.date()
        target = date(qdate.year(), qdate.month(), qdate.day())
        self.output.setPlainText(
            ReportService.build(target, self.greeting.toPlainText(), self.document)
        )

    def copy_to_clipboard(self) -> None:
        if not self.output.toPlainText().strip():
            self.generate()
        QGuiApplication.clipboard().setText(self.output.toPlainText())
        QMessageBox.information(self, "복사 완료", "일일보고가 클립보드에 복사되었습니다.")
