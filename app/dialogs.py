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
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import DailyDocument
from app.report_service import ReportService


class GreetingSettingsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        greeting: str,
        footer: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("일일보고 문구 설정")
        self.resize(560, 520)

        self.greeting_editor = QTextEdit(greeting)
        self.greeting_editor.setPlaceholderText(
            "예: 안녕하세요.\nYY.MM.DD 일일보고 공유드립니다."
        )

        self.footer_editor = QTextEdit(footer)
        self.footer_editor.setPlaceholderText(
            "예: 이상입니다. 감사합니다."
        )

        today = date.today()
        token_help = QLabel(
            f"날짜: YY.MM.DD → {today:%y.%m.%d} / "
            f"YY. MM. DD → {today:%y. %m. %d}"
        )
        token_help.setWordWrap(True)

        form = QFormLayout()
        form.addRow("인사말", self.greeting_editor)
        form.addRow("꼬리말", self.footer_editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(token_help)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def greeting(self) -> str:
        return self.greeting_editor.toPlainText().strip()

    @property
    def footer(self) -> str:
        return self.footer_editor.toPlainText().strip()


class DeleteConfirmDialog(QDialog):
    def __init__(self, parent: QWidget, task_title: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("업무 삭제")
        self.setModal(True)
        self.setMinimumWidth(380)

        message = QLabel(f"'{task_title}' 업무를 삭제할까요?")
        message.setWordWrap(True)

        buttons = QDialogButtonBox()
        delete_button = buttons.addButton(
            "삭제",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        delete_button.setObjectName("dangerButton")
        buttons.addButton(
            "취소",
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(message)
        layout.addWidget(buttons)


class ReportDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        target: date,
        document: DailyDocument,
        greeting: str,
        footer: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("일일보고 작성")
        self.resize(720, 700)
        self.document = document

        self.date_edit = QDateEdit(QDate(target.year, target.month, target.day))
        self.date_edit.setCalendarPopup(True)

        self.greeting = QTextEdit(greeting)
        self.greeting.setPlaceholderText("예: YY. MM. DD 업무 공유드립니다.")
        self.footer = QTextEdit(footer)
        self.footer.setPlaceholderText("꼬리말을 입력하세요.")

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
        form.addRow("꼬리말", self.footer)

        help_label = QLabel(
            "날짜: YY.MM.DD / YY. MM. DD / YYYY.MM.DD"
        )
        help_label.setWordWrap(True)

        actions = QHBoxLayout()
        actions.addWidget(generate)
        actions.addWidget(copy)
        actions.addWidget(self.copy_status)
        actions.addStretch(1)

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(help_label)
        layout.addLayout(actions)
        layout.addWidget(self.output, 1)
        layout.addWidget(close_buttons)
        self.generate()

    def generate(self) -> None:
        qdate = self.date_edit.date()
        target = date(qdate.year(), qdate.month(), qdate.day())
        self.output.setPlainText(
            ReportService.build(
                target,
                self.greeting.toPlainText(),
                self.document,
                self.footer.toPlainText(),
            )
        )
        self.copy_status.clear()

    def copy_to_clipboard(self) -> None:
        if not self.output.toPlainText().strip():
            self.generate()
        QGuiApplication.clipboard().setText(self.output.toPlainText())
        self.copy_status.setText("복사 완료")
