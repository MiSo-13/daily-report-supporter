from __future__ import annotations

from html import escape

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.models import Task


class TaskDetailDialog(QDialog):
    def __init__(self, parent: QWidget, task: Task) -> None:
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("업무 상세 보기")
        self.resize(900, 700)
        self.setMinimumSize(620, 460)

        self.title_label = QLabel(
            f"<h2>{escape(task.title or '(제목 없음)')}</h2>"
        )
        self.title_label.setWordWrap(True)

        self.status_label = QLabel(f"상태: {task.status.value}")
        self.status_label.setObjectName("taskDetailStatus")

        header = QHBoxLayout()
        header.addWidget(self.status_label)
        header.addStretch(1)

        if task.link_url.strip():
            link_label = task.link_text.strip() or task.link_url.strip()
            self.open_link_button = QPushButton(
                f"관련 문서 열기 · {link_label}"
            )
            self.open_link_button.setObjectName("openUrlButton")
            self.open_link_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(task.link_url.strip()))
            )
            header.addWidget(self.open_link_button)

        details = "\n".join(task.details)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setMarkdown(details or "_주요 내용이 없습니다._")

        self.source = QPlainTextEdit()
        self.source.setReadOnly(True)
        self.source.setPlainText(details)
        self.source.setPlaceholderText("주요 내용이 없습니다.")

        self.tabs = QTabWidget()
        self.tabs.addTab(self.preview, "미리보기")
        self.tabs.addTab(self.source, "원문")

        close_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        close_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addLayout(header)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(close_buttons)
