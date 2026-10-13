"""Weekly/monthly report preview and portable HTML export dialog."""
from datetime import date
from pathlib import Path

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from app.period_report import build_period_html, report_range


class PeriodReportDialog(QDialog):
    def __init__(self, store, current_date: date, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("주간·월간 업무보고서")
        self.resize(1050, 760)
        layout = QVBoxLayout(self)
        options = QHBoxLayout()
        options.addWidget(QLabel("기간"))
        self.period = QComboBox()
        self.period.addItem("주간", "weekly")
        self.period.addItem("월간", "monthly")
        options.addWidget(self.period)
        options.addWidget(QLabel("기준 날짜"))
        self.anchor = QDateEdit(QDate(current_date.year, current_date.month, current_date.day))
        self.anchor.setCalendarPopup(True)
        self.anchor.setDisplayFormat("yyyy-MM-dd")
        options.addWidget(self.anchor)
        self.range_label = QLabel()
        options.addWidget(self.range_label, 1)
        layout.addLayout(options)

        self.achievements = QTextEdit()
        self.issues = QTextEdit()
        self.next_plan = QTextEdit()
        self.achievements.setPlaceholderText("주요 성과 또는 공유할 핵심 결과 (선택 입력)")
        self.issues.setPlaceholderText("지연 원인, 보류 사유, 지원이 필요한 사항 (선택 입력)")
        self.next_plan.setPlaceholderText("다음 주 또는 다음 달 계획 (선택 입력)")
        for label, editor in (("주요 성과", self.achievements),
                              ("이슈 및 지원 요청", self.issues),
                              ("다음 기간 계획", self.next_plan)):
            layout.addWidget(QLabel(label))
            editor.setMaximumHeight(60)
            layout.addWidget(editor)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        actions = QHBoxLayout()
        self.refresh_button = QPushButton("미리보기 갱신")
        self.save_button = QPushButton("HTML 저장")
        self.refresh_button.clicked.connect(self.refresh)
        self.save_button.clicked.connect(self.save_html)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
        self.period.currentIndexChanged.connect(self.refresh)
        self.anchor.dateChanged.connect(self.refresh)
        self.refresh()

    def current_html(self):
        value = self.anchor.date().toPyDate()
        return build_period_html(
            self.store, value, self.period.currentData(),
            achievements=self.achievements.toPlainText(),
            issues=self.issues.toPlainText(),
            next_plan=self.next_plan.toPlainText())

    def refresh(self, *_):
        start, end = report_range(self.anchor.date().toPyDate(), self.period.currentData())
        self.range_label.setText(f"{start:%Y-%m-%d} ~ {end:%Y-%m-%d}")
        self.preview.setHtml(self.current_html())

    def save_html(self):
        anchor = self.anchor.date().toPyDate()
        default = f"work-report-{self.period.currentData()}-{anchor:%Y%m%d}.html"
        filename, _ = QFileDialog.getSaveFileName(self, "HTML 보고서 저장", default, "HTML (*.html)")
        if not filename:
            return
        try:
            path = Path(filename)
            path.write_text(self.current_html(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "저장 실패", str(exc))
            return
        QMessageBox.information(self, "저장 완료", f"HTML 보고서를 저장했습니다.\n{path}")
