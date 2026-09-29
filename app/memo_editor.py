from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MemoEditor(QWidget):
    def __init__(
        self,
        on_save: Callable[[str, str], None],
    ) -> None:
        super().__init__()
        self.on_save = on_save
        self._loading = False
        self._dirty = False
        self._preview_dirty = False

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("제목")

        self.markdown_input = QPlainTextEdit()
        self.markdown_input.setPlaceholderText("Markdown")

        self.preview = QTextEdit()
        self.preview.setAcceptRichText(True)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.markdown_input, "편집")
        self.tabs.addTab(self.preview, "미리보기")
        self.tabs.currentChanged.connect(self._tab_changed)
        self.preview.textChanged.connect(self._preview_changed)

        self.save_button = QPushButton("저장")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save)

        self.validation_label = QLabel("")

        actions = QHBoxLayout()
        actions.addWidget(self.validation_label)
        actions.addStretch(1)
        actions.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_input)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(actions)

        self.title_input.textChanged.connect(self._changed)
        self.markdown_input.textChanged.connect(self._changed)

    def load(self, title: str, content: str) -> None:
        self._loading = True
        self.title_input.setText(title)
        self.markdown_input.setPlainText(content)
        self.validation_label.clear()
        self._loading = False
        self._dirty = False
        self._preview_dirty = False
        self._update_preview()

    def clear(self) -> None:
        self._loading = True
        self.title_input.clear()
        self.markdown_input.clear()
        self.preview.clear()
        self.validation_label.clear()
        self._loading = False
        self._dirty = False
        self._preview_dirty = False
        self.tabs.setCurrentIndex(0)
        self.title_input.setFocus()

    def save(self) -> None:
        if self.tabs.currentIndex() == 1:
            self._sync_markdown_from_preview()

        title = self.title_input.text().strip()
        if not title:
            self.validation_label.setText("제목을 입력하세요.")
            self.title_input.setFocus()
            return
        self.on_save(title, self.markdown_input.toPlainText())
        self._dirty = False
        self._preview_dirty = False
        self.validation_label.clear()

    def is_dirty(self) -> bool:
        return self._dirty

    def _changed(self) -> None:
        if self._loading:
            return
        self.validation_label.clear()
        self._dirty = True
        if self.tabs.currentIndex() == 1 and not self._preview_dirty:
            self._update_preview()

    def _tab_changed(self, index: int) -> None:
        if self._loading:
            return

        if index == 1:
            self._update_preview()
        elif self._preview_dirty:
            self._sync_markdown_from_preview()

    def _preview_changed(self) -> None:
        if self._loading or self.tabs.currentIndex() != 1:
            return
        self._dirty = True
        self._preview_dirty = True
        self.validation_label.clear()

    def _update_preview(self) -> None:
        self._loading = True
        self.preview.setMarkdown(self.markdown_input.toPlainText())
        self._loading = False
        self._preview_dirty = False

    def _sync_markdown_from_preview(self) -> None:
        self._loading = True
        self.markdown_input.setPlainText(self.preview.toMarkdown().rstrip("\n"))
        self._loading = False
        self._preview_dirty = False
        self._dirty = True
