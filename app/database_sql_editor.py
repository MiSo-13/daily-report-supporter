from __future__ import annotations

import re
from collections.abc import Iterable

from PyQt6.QtCore import QEvent, QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPalette,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit

from app.database_models import DB_MYSQL, DB_POSTGRESQL


COMMON_KEYWORDS = {
    "ALL",
    "AND",
    "AS",
    "ASC",
    "BETWEEN",
    "BY",
    "CASE",
    "CURRENT_DATE",
    "CURRENT_TIMESTAMP",
    "DESC",
    "DISTINCT",
    "ELSE",
    "END",
    "EXISTS",
    "EXPLAIN",
    "FROM",
    "FULL",
    "GROUP",
    "HAVING",
    "ILIKE",
    "IN",
    "INNER",
    "IS",
    "JOIN",
    "LEFT",
    "LIKE",
    "LIMIT",
    "NOT",
    "NULL",
    "NULLS",
    "OFFSET",
    "ON",
    "OR",
    "ORDER",
    "OUTER",
    "OVER",
    "PARTITION",
    "RIGHT",
    "SELECT",
    "SHOW",
    "THEN",
    "UNION",
    "WHEN",
    "WHERE",
    "WITH",
}

COMMON_FUNCTIONS = {
    "ABS",
    "AVG",
    "CAST",
    "CEIL",
    "COALESCE",
    "CONCAT",
    "COUNT",
    "FLOOR",
    "GREATEST",
    "LEAST",
    "LOWER",
    "MAX",
    "MIN",
    "NULLIF",
    "ROUND",
    "SUM",
    "TRIM",
    "UPPER",
}

MYSQL_KEYWORDS = {
    "DESCRIBE",
    "DESC",
    "REGEXP",
}

MYSQL_FUNCTIONS = {
    "CURDATE",
    "DATE_ADD",
    "DATE_FORMAT",
    "DATE_SUB",
    "FIND_IN_SET",
    "GROUP_CONCAT",
    "IF",
    "IFNULL",
    "JSON_EXTRACT",
    "JSON_UNQUOTE",
    "NOW",
    "STR_TO_DATE",
    "TIMESTAMPDIFF",
    "UNIX_TIMESTAMP",
}

POSTGRESQL_KEYWORDS = {
    "ILIKE",
    "SIMILAR",
}

POSTGRESQL_FUNCTIONS = {
    "AGE",
    "ARRAY_AGG",
    "DATE_TRUNC",
    "GENERATE_SERIES",
    "JSON_AGG",
    "JSONB_AGG",
    "JSONB_BUILD_OBJECT",
    "NOW",
    "STRING_AGG",
    "TO_CHAR",
}


def sql_keywords(db_type: str) -> set[str]:
    keywords = set(COMMON_KEYWORDS)
    if db_type == DB_MYSQL:
        keywords.update(MYSQL_KEYWORDS)
    elif db_type == DB_POSTGRESQL:
        keywords.update(POSTGRESQL_KEYWORDS)
    return keywords


def sql_functions(db_type: str) -> set[str]:
    functions = set(COMMON_FUNCTIONS)
    if db_type == DB_MYSQL:
        functions.update(MYSQL_FUNCTIONS)
    elif db_type == DB_POSTGRESQL:
        functions.update(POSTGRESQL_FUNCTIONS)
    return functions


def statement_at_cursor(sql: str, cursor_position: int) -> str:
    """세미콜론으로 구분된 SQL 중 커서가 위치한 statement를 반환한다."""
    if not sql:
        return ""

    position = max(0, min(cursor_position, len(sql)))
    separators = _statement_separators(sql)
    ranges: list[tuple[int, int]] = []
    start = 0
    for separator in separators:
        ranges.append((start, separator))
        start = separator + 1
    ranges.append((start, len(sql)))

    previous_non_empty = ""
    for start, end in ranges:
        raw = sql[start:end]
        stripped = raw.strip()
        if not stripped:
            continue

        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        content_start = start + leading
        content_end = start + trailing

        if content_start <= position <= content_end:
            return stripped

        if position < content_start:
            return previous_non_empty or stripped

        previous_non_empty = stripped

    return previous_non_empty


def _statement_separators(sql: str) -> list[int]:
    separators: list[int] = []
    quote: str | None = None
    dollar_tag: str | None = None
    line_comment = False
    block_depth = 0
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if line_comment:
            if char in "\r\n        string_pattern = r"""'(?:''|\\.|[^'])*'|"(?:""|\\.|[^"])*"|\`(?:\`\`|[^\`])*\`"""\n").strip()
            if selected:
                return selected

        return statement_at_cursor(
            self.toPlainText(),
            cursor.position(),
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        modifiers = event.modifiers()
        if (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and modifiers & Qt.KeyboardModifier.ControlModifier
        ):
            statement = self.statement_to_execute()
            if statement:
                self.execute_requested.emit(statement)
            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_Space
            and modifiers & Qt.KeyboardModifier.ControlModifier
        ):
            self._show_completion(force=True)
            event.accept()
            return

        if event.key() == Qt.Key.Key_Tab:
            if self._accept_or_show_completion():
                event.accept()
                return

        super().keyPressEvent(event)

        if self._completer.popup().isVisible():
            prefix = self._completion_prefix()
            if prefix:
                self._show_completion()
            else:
                self._completer.popup().hide()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if (
            hasattr(self, "highlighter")
            and event.type() in (
                QEvent.Type.PaletteChange,
                QEvent.Type.StyleChange,
            )
        ):
            self.highlighter.refresh_palette()

    def _accept_or_show_completion(self) -> bool:
        popup = self._completer.popup()
        if popup.isVisible():
            index = popup.currentIndex()
            if index.isValid():
                completion = str(index.data() or "")
                if completion:
                    self._insert_completion(completion)
                    popup.hide()
                    return True

        prefix = self._completion_prefix()
        if not prefix:
            return False

        matches = self._matches(prefix)
        if not matches:
            if len(prefix) >= 2:
                self.completion_lookup_requested.emit(prefix)
                return True
            return False

        if len(matches) == 1:
            self._insert_completion(matches[0])
            return True

        common = _common_prefix(matches)
        if len(common) > len(prefix):
            self._insert_completion(common)
            return True

        self._show_completion()
        return True

    def _show_completion(self, *, force: bool = False) -> None:
        prefix = self._completion_prefix()
        if not prefix and not force:
            return

        self._completer.setCompletionPrefix(prefix)
        if self._completer.completionCount() <= 0:
            self._completer.popup().hide()
            return

        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        rect = self.cursorRect()
        width = max(
            popup.sizeHintForColumn(0)
            + popup.verticalScrollBar().sizeHint().width()
            + 24,
            220,
        )
        rect.setWidth(width)
        self._completer.complete(rect)

    def _matches(self, prefix: str) -> list[str]:
        folded = prefix.casefold()
        return [
            candidate
            for candidate in self.completion_candidates()
            if candidate.casefold().startswith(folded)
        ]

    def _completion_prefix(self) -> str:
        text = self.toPlainText()
        position = self.textCursor().position()
        start = position
        while start > 0:
            char = text[start - 1]
            if char.isalnum() or char in ("_", ".", "$"):
                start -= 1
                continue
            break
        return text[start:position]

    def _insert_completion(self, completion: str) -> None:
        prefix = self._completion_prefix()
        cursor = self.textCursor()

        if prefix:
            cursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.KeepAnchor,
                len(prefix),
            )

        replacement = completion
        if (
            completion.upper() in self._functions
            and not self._next_character_is_open_paren()
        ):
            replacement += "("

        cursor.insertText(replacement)
        self.setTextCursor(cursor)

    def _next_character_is_open_paren(self) -> bool:
        text = self.toPlainText()
        position = self.textCursor().position()
        return position < len(text) and text[position] == "("

    def _refresh_completion_model(self) -> None:
        static = sql_keywords(self._db_type) | sql_functions(self._db_type)
        candidates = sorted(
            static | self._identifiers,
            key=lambda value: (value.casefold(), value),
        )
        self._completion_model.setStringList(candidates)


def _format(
    color: QColor,
    *,
    bold: bool = False,
    italic: bool = False,
) -> QTextCharFormat:
    text_format = QTextCharFormat()
    text_format.setForeground(color)
    if bold:
        text_format.setFontWeight(QFont.Weight.Bold)
    if italic:
        text_format.setFontItalic(True)
    return text_format


def _common_prefix(values: list[str]) -> str:
    if not values:
        return ""

    common = values[0]
    for value in values[1:]:
        length = min(len(common), len(value))
        index = 0
        while (
            index < length
            and common[index].casefold() == value[index].casefold()
        ):
            index += 1
        common = common[:index]
        if not common:
            break
    return common
