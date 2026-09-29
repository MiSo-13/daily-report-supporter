from __future__ import annotations

from collections.abc import Callable
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QFont,
    QFontDatabase,
    QKeyEvent,
    QKeySequence,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QTextListFormat,
)
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


class RichMarkdownEdit(QTextEdit):
    HEADING_SCALES = {
        1: 1.8,
        2: 1.5,
        3: 1.3,
    }

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.StandardKey.Bold):
            self._toggle_bold()
            return

        if event.matches(QKeySequence.StandardKey.Italic):
            self._toggle_italic()
            return

        if event.key() == Qt.Key.Key_Space and self._apply_block_shortcut():
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._current_block_text() == "---":
                self._apply_horizontal_rule()
                return

            block_format = self.textCursor().blockFormat()
            if block_format.headingLevel() > 0:
                self._insert_plain_block()
                return

            marker = block_format.marker()
            checkbox_markers = {
                QTextBlockFormat.MarkerType.Unchecked,
                QTextBlockFormat.MarkerType.Checked,
            }
            if marker in checkbox_markers and self._current_block_text():
                super().keyPressEvent(event)
                cursor = self.textCursor()
                next_format = cursor.blockFormat()
                next_format.setMarker(QTextBlockFormat.MarkerType.Unchecked)
                cursor.setBlockFormat(next_format)
                return

        super().keyPressEvent(event)

    def _apply_block_shortcut(self) -> bool:
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()

        if cursor.positionInBlock() != len(text):
            return False

        if text in {"#", "##", "###"}:
            self._apply_heading(len(text))
            return True

        if text in {"-", "*"}:
            self._apply_list(QTextListFormat.Style.ListDisc)
            return True

        ordered_match = re.fullmatch(r"(\d+)\.", text)
        if ordered_match:
            self._apply_list(
                QTextListFormat.Style.ListDecimal,
                start=int(ordered_match.group(1)),
            )
            return True

        if text == ">":
            self._apply_quote()
            return True

        if text == "```":
            self._apply_code_block()
            return True

        if text == "---":
            self._apply_horizontal_rule()
            return True

        if text.lower() == "- [ ]":
            self._apply_list(
                QTextListFormat.Style.ListDisc,
                marker=QTextBlockFormat.MarkerType.Unchecked,
            )
            return True

        if text.lower() == "- [x]":
            self._apply_list(
                QTextListFormat.Style.ListDisc,
                marker=QTextBlockFormat.MarkerType.Checked,
            )
            return True

        return False

    def _consume_current_marker(self) -> QTextCursor:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(
            QTextCursor.MoveOperation.StartOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()
        return cursor

    def _apply_heading(self, level: int) -> None:
        cursor = self._consume_current_marker()

        block_format = cursor.blockFormat()
        block_format.setHeadingLevel(level)
        cursor.setBlockFormat(block_format)

        base_size = self.font().pointSizeF()
        char_format = QTextCharFormat()
        char_format.setFontPointSize(base_size * self.HEADING_SCALES[level])
        cursor.setBlockCharFormat(char_format)
        cursor.setCharFormat(char_format)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _apply_list(
        self,
        style: QTextListFormat.Style,
        *,
        start: int = 1,
        marker: QTextBlockFormat.MarkerType = QTextBlockFormat.MarkerType.NoMarker,
    ) -> None:
        cursor = self._consume_current_marker()

        list_format = QTextListFormat()
        list_format.setStyle(style)
        list_format.setIndent(1)
        if style == QTextListFormat.Style.ListDecimal:
            list_format.setStart(max(start, 1))

        cursor.createList(list_format)

        block_format = cursor.blockFormat()
        block_format.setMarker(marker)
        cursor.setBlockFormat(block_format)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _apply_quote(self) -> None:
        cursor = self._consume_current_marker()

        block_format = cursor.blockFormat()
        block_format.setProperty(QTextFormat.Property.BlockQuoteLevel, 1)
        block_format.setLeftMargin(24)
        block_format.setRightMargin(8)
        cursor.setBlockFormat(block_format)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _apply_code_block(self) -> None:
        cursor = self._consume_current_marker()

        block_format = cursor.blockFormat()
        block_format.setNonBreakableLines(True)
        block_format.setProperty(QTextFormat.Property.BlockCodeFence, "`")
        cursor.setBlockFormat(block_format)

        char_format = QTextCharFormat()
        char_format.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        cursor.setBlockCharFormat(char_format)
        cursor.setCharFormat(char_format)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _apply_horizontal_rule(self) -> None:
        cursor = self._consume_current_marker()

        ruler_format = cursor.blockFormat()
        ruler_format.setProperty(
            QTextFormat.Property.BlockTrailingHorizontalRulerWidth,
            1.0,
        )
        cursor.setBlockFormat(ruler_format)
        cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _insert_plain_block(self) -> None:
        cursor = self.textCursor()
        cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())
        self.setTextCursor(cursor)

    def _toggle_bold(self) -> None:
        cursor = self.textCursor()
        current = cursor.charFormat()
        char_format = QTextCharFormat()
        is_bold = current.fontWeight() >= QFont.Weight.Bold.value
        char_format.setFontWeight(
            QFont.Weight.Normal.value if is_bold else QFont.Weight.Bold.value
        )
        self._merge_char_format(cursor, char_format)

    def _toggle_italic(self) -> None:
        cursor = self.textCursor()
        current = cursor.charFormat()
        char_format = QTextCharFormat()
        char_format.setFontItalic(not current.fontItalic())
        self._merge_char_format(cursor, char_format)

    def _merge_char_format(
        self,
        cursor: QTextCursor,
        char_format: QTextCharFormat,
    ) -> None:
        if cursor.hasSelection():
            cursor.mergeCharFormat(char_format)
            self.setTextCursor(cursor)
        else:
            self.mergeCurrentCharFormat(char_format)

    def _current_block_text(self) -> str:
        return self.textCursor().block().text()


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

        self.preview = RichMarkdownEdit()
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
        if self.tabs.currentIndex() == 1 and self._preview_dirty:
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
