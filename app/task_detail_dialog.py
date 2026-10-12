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

        title = QLabel(
            f"<h2>{escape(task.title or '(제목 없음)')}</h2>"
        )
        title.setWordWrap(True)

        status = QLabel(f"상태: {task.status.value}")
        status.setObjectName("taskDetailStatus")

        header = QHBoxLayout()
        header.addWidget(status)
        header.addStretch(1)

        if task.link_url.strip():
            link_label = task.link_text.strip() or task.link_url.strip()
            open_link = QPushButton(f"관련 문서 열기 · {link_label}")
            open_link.setObjectName("openUrlButton")
            open_link.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(task.link_url.strip()))
            )
            header.addWidget(open_link)

        details = "\n".join(task.details)
        preview = QTextBrowser()
        preview.setOpenExternalLinks(True)
        preview.setMarkdown(details or "_주요 내용이 없습니다._")

        source = QPlainTextEdit()
        source.setReadOnly(True)
        source.setPlainText(details)
        source.setPlaceholderText("주요 내용이 없습니다.")

        tabs = QTabWidget()
        tabs.addTab(preview, "미리보기")
        tabs.addTab(source, "원문")

        close_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        close_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addLayout(header)
        layout.addWidget(tabs, 1)
        layout.addWidget(close_buttons)
