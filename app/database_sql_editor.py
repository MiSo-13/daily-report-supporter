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
    """세미콜론으렜 구분된 SQL 중 커서가 위치한 statement를 반환한다."""
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
            if char in "\r\n":
                line_comment = False
            index += 1
            continue

        if block_depth:
            if char == "/" and next_char == "*":
                block_depth += 1
                index += 2
                continue
            if char == "*" and next_char == "/":
                block_depth -= 1
                index += 2
                continue
            index += 1
            continue

        if dollar_tag is not None:
            if sql.startswith(dollar_tag, index):
                index += len(dollar_tag)
                dollar_tag = None
            else:
                index += 1
            continue

        if quote is not None:
            if char == "\\" and index + 1 < len(sql):
                index += 2
                continue
            if char == quote:
                if next_char == quote:
                    index += 2
                    continue
                quote = None
            index += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            index += 1
            continue

        if char == "-" and next_char == "-":
            line_comment = True
            index += 2
            continue

        if char == "/" and next_char == "*":
            block_depth = 1
            index += 2
            continue

        if char == "$":
            match = re.match(
                r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$",
                sql[index:],
            )
            if match is not None:
                dollar_tag = match.group(0)
                index += len(dollar_tag)
                continue

        if char == ";":
            separators.append(index)

        index += 1

    return separators


class SqlSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, editor: QPlainTextEdit) -> None:
        super().__init__(editor.document())
        self._editor = editor
        self._db_type = DB_MYSQL
        self._keywords = sql_keywords(self._db_type)
        self._functions = sql_functions(self._db_type)
        self._keyword_format = QTextCharFormat()
        self._function_format = QTextCharFormat()
        self._string_format = QTextCharFormat()
        self._number_format = QTextCharFormat()
        self._comment_format = QTextCharFormat()
        self.refresh_palette()

    def set_dialect(self, db_type: str) -> None:
        self._db_type = db_type
        self._keywords = sql_keywords(db_type)
        self._functions = sql_functions(db_type)
        self.rehighlight()

    def refresh_palette(self) -> None:
        base = self._editor.palette().color(QPalette.ColorRole.Base)
        dark = base.lightness() < 128

        if dark:
            keyword = QColor("#6ea8fe")
            function = QColor("#dcdcaa")
            string = QColor("#ce9178")
            number = QColor("#b5cea8")
            comment = QColor("#7ca668")
        else:
            keyword = QColor("#0000cc")
            function = QColor("#795e26")
            string = QColor("#a31515")
            number = QColor("#098658")
            comment = QColor("#008000")

        self._keyword_format = _format(keyword, bold=True)
        self._function_format = _format(function)
        self._string_format = _format(string)
        self._number_format = _format(number)
        self._comment_format = _format(comment, italic=True)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for word in self._keywords:
            self._apply_word(text, word, self._keyword_format)

        for word in self._functions:
            self._apply_word(text, word, self._function_format)

        for match in re.finditer(r"\b(?:\d+(?:\.\d+)?)\b", text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._number_format,
            )

        string_pattern = (
            r"'(?:''|\\.|[^'])*'"
            r'e"|"(?:""|\\.|[^"])*"'
            r|"(`(?:``|[^`])*`)"
        )
        for match in re.finditer(string_pattern, text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._string_format,
            )

        self._highlight_comments(text)

    def _highlight_comments(self, text: str) -> None:
        self.setCurrentBlockState(0)

        if self.previousBlockState() == 1:
            start = 0
        else:
            start = text.find("/*")

        while start >= 0:
            end = text.find("*/", start + 2)
            if end < 0:
                self.setCurrentBlockState(1)
                self.setFormat(
                    start,
                    len(text) - start,
                    self._comment_format,
                )
                break

            length = end - start + 2
            self.setFormat(start, length, self._comment_format)
            start = text.find("/*", end + 2)

        for match in re.finditer(r"--.*$", text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._comment_format,
            )

    def _apply_word(
        self,
        text: str,
        word: str,
        text_format: QTextCharFormat,
    ) -> None:
        pattern = rf"\b{re.escape(word)}\b"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                text_format,
            )


class SqlEditor(QPlainTextEdit):
    execute_requested = pyqtSignal(str)
    completion_lookup_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._db_type = DB_MYSQL
        self._identifiers: set[str] = set()
        self._functions = sql_functions(self._db_type)

        self._completion_model = QStringListModel(self)
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._completer.activated[str].connect(self._insert_completion)

        self.highlighter = SqlSyntaxHighlighter(self)
        self._refresh_completion_model()

    def set_dialect(self, db_type: str) -> None:
        self._db_type = db_type
        self._functions = sql_functions(db_type)
        self.highlighter.set_dialect(db_type)
        self._refresh_completion_model()

    def set_identifiers(self, values: Iterable[str]) -> None:
        self._identifiers = {
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip()
        }
        self._refresh_completion_model()

    def add_identifiers(self, values: Iterable[str]) -> None:
        for value in values:
            if isinstance(value, str) and value.strip():
                self._identifiers.add(value.strip())
        self._refresh_completion_model()

    def completion_candidates(self) -> list[str]:
        return self._completion_model.stringList()

    def apply_lookup_candidates(
        self,
        prefix: str,
        values: Iterable[str],
    ) -> None:
        self.add_identifiers(values)
        current_prefix = self._completion_prefix()
        if current_prefix.casefold() != prefix.casefold():
            return

        matches = self._matches(current_prefix)
        if len(matches) == 1:
            self._insert_completion(matches[0])
        elif matches:
            self._show_completion()

    def statement_to_execute(self) -> str:
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n").strip()
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
