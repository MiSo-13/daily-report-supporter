from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QFontDatabase, QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models import DailyDocument
from app.settings import (
    DEFAULT_FONT_SIZE,
    DEFAULT_TERMINAL_FONT_SIZE,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
)
from app.report_service import ReportService


class GreetingSettingsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        greeting: str,
        footer: str,
        progress_report_title: str,
        planned_report_title: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("일일보고 설정")
        self.resize(560, 520)

        self.greeting_editor = QPlainTextEdit()
        self.greeting_editor.setPlainText(greeting)
        self.greeting_editor.setPlaceholderText(
            "예: 안녕하세요.\nYY.MM.DD 일일보고 공유드립니다."
        )

        self.footer_editor = QPlainTextEdit()
        self.footer_editor.setPlainText(footer)
        self.footer_editor.setPlaceholderText("예: 이상입니다. 감사합니다.")

        self.progress_title_input = QLineEdit(progress_report_title)
        self.progress_title_input.setPlaceholderText("예: 진행 업무")

        self.planned_title_input = QLineEdit(planned_report_title)
        self.planned_title_input.setPlaceholderText("예: 예정 업무")

        form = QFormLayout()
        form.addRow("진행 업무 제목", self.progress_title_input)
        form.addRow("예정 업무 제목", self.planned_title_input)
        form.addRow("상단 문구", self.greeting_editor)
        form.addRow("꼬리말", self.footer_editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def greeting(self) -> str:
        return self.greeting_editor.toPlainText()

    @property
    def footer(self) -> str:
        return self.footer_editor.toPlainText()

    @property
    def progress_report_title(self) -> str:
        return self.progress_title_input.text().strip()

    @property
    def planned_report_title(self) -> str:
        return self.planned_title_input.text().strip()


class FontSettingsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        font_family: str,
        font_size: int,
        terminal_font_family: str,
        terminal_font_size: int,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("폰트 설정")
        self.setMinimumWidth(520)

        families = sorted(
            QFontDatabase.families(),
            key=lambda value: value.casefold(),
        )
        fixed_families = [
            family
            for family in families
            if QFontDatabase.isFixedPitch(family)
        ]

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItem("시스템 기본 폰트", "")
        for family in families:
            self.font_family_combo.addItem(family, family)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setValue(font_size)

        self.terminal_font_family_combo = QComboBox()
        self.terminal_font_family_combo.addItem(
            "시스템 기본 고정폭 폰트",
            "",
        )
        for family in fixed_families:
            self.terminal_font_family_combo.addItem(family, family)

        self.terminal_font_size_spin = QSpinBox()
        self.terminal_font_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.terminal_font_size_spin.setSuffix(" pt")
        self.terminal_font_size_spin.setValue(terminal_font_size)

        self._select_family(self.font_family_combo, font_family)
        self._select_family(
            self.terminal_font_family_combo,
            terminal_font_family,
        )

        self.app_preview = QLabel("앱 폰트 미리보기 · 가나다 ABC 123")
        self.terminal_preview = QLabel(
            "터미널 폰트 미리보기 · docker logs -f my_service"
        )
        form = QFormLayout()
        form.addRow("앱 폰트", self.font_family_combo)
        form.addRow("앱 크기", self.font_size_spin)
        form.addRow("", self.app_preview)
        form.addRow("터미널 폰트", self.terminal_font_family_combo)
        form.addRow("터미널 크기", self.terminal_font_size_spin)
        form.addRow("", self.terminal_preview)

        reset_button = QPushButton("기본값")
        reset_button.clicked.connect(self._restore_defaults)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        actions = QHBoxLayout()
        actions.addWidget(reset_button)
        actions.addStretch(1)
        actions.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)

        self.font_family_combo.currentIndexChanged.connect(
            self._update_preview
        )
        self.font_size_spin.valueChanged.connect(self._update_preview)
        self.terminal_font_family_combo.currentIndexChanged.connect(
            self._update_preview
        )
        self.terminal_font_size_spin.valueChanged.connect(
            self._update_preview
        )
        self._update_preview()

    @property
    def font_family(self) -> str:
        value = self.font_family_combo.currentData()
        return str(value) if value else ""

    @property
    def font_size(self) -> int:
        return self.font_size_spin.value()

    @property
    def terminal_font_family(self) -> str:
        value = self.terminal_font_family_combo.currentData()
        return str(value) if value else ""

    @property
    def terminal_font_size(self) -> int:
        return self.terminal_font_size_spin.value()

    def _restore_defaults(self) -> None:
        self.font_family_combo.setCurrentIndex(0)
        self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
        self.terminal_font_family_combo.setCurrentIndex(0)
        self.terminal_font_size_spin.setValue(DEFAULT_TERMINAL_FONT_SIZE)
        self._update_preview()

    def _update_preview(self, *_args: object) -> None:
        app_font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.GeneralFont
        )
        if self.font_family:
            app_font.setFamily(self.font_family)
        app_font.setPointSize(self.font_size)
        self.app_preview.setFont(app_font)

        terminal_font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        if self.terminal_font_family:
            terminal_font.setFamily(self.terminal_font_family)
        terminal_font.setPointSize(self.terminal_font_size)
        self.terminal_preview.setFont(terminal_font)

    @staticmethod
    def _select_family(combo: QComboBox, family: str) -> None:
        if not family:
            combo.setCurrentIndex(0)
            return

        index = combo.findData(family)
        combo.setCurrentIndex(index if index >= 0 else 0)


class DeleteConfirmDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        item_title: str,
        item_name: str = "업무",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{item_name} 삭제")
        self.setModal(True)
        self.setMinimumWidth(380)

        message = QLabel(f"'{item_title}' {item_name}를 삭제할까요?")
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
        progress_report_title: str,
        planned_report_title: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("일일보고 작성")
        self.resize(720, 700)
        self.document = document
        self.progress_report_title = progress_report_title
        self.planned_report_title = planned_report_title

        self.date_edit = QDateEdit(QDate(target.year, target.month, target.day))
        self.date_edit.setCalendarPopup(True)

        self.greeting = QPlainTextEdit()
        self.greeting.setPlainText(greeting)
        self.greeting.setPlaceholderText("예: YY. MM. DD 업무 공유드립니다.")

        self.footer = QPlainTextEdit()
        self.footer.setPlainText(footer)
        self.footer.setPlaceholderText("꼬리말을 입력하세요.")

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.copy_status = QLabel("")

        generate = QPushButton("일일보고 생성")
        generate.setObjectName("primaryButton")
        copy = QPushButton("클립보드 복사")
        generate.clicked.connect(self.generate)
        copy.clicked.connect(self.copy_to_clipboard)

        form = QFormLayout()
        form.addRow("날짜", self.date_edit)
        form.addRow("상단 문구", self.greeting)
        form.addRow("꼬리말", self.footer)

        actions = QHBoxLayout()
        actions.addWidget(generate)
        actions.addWidget(copy)
        actions.addWidget(self.copy_status)
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
            ReportService.build(
                target,
                self.greeting.toPlainText(),
                self.document,
                self.footer.toPlainText(),
                self.progress_report_title,
                self.planned_report_title,
            )
        )
        self.copy_status.clear()

    def copy_to_clipboard(self) -> None:
        if not self.output.toPlainText().strip():
            self.generate()
        QGuiApplication.clipboard().setText(self.output.toPlainText())
        self.copy_status.setText("복사 완료")
