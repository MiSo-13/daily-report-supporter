from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from app.database_models import DB_MYSQL, DB_POSTGRESQL
from app.database_sql_editor import (
    SqlEditor,
    sql_functions,
    sql_keywords,
    statement_at_cursor,
)


_APP = QApplication.instance() or QApplication([])


def test_statement_at_cursor_returns_only_current_query() -> None:
    sql = (
        "SELECT * FROM users;\n"
        "SELECT * FROM orders WHERE id = 10;\n"
        "SELECT * FROM logs;"
    )

    position = sql.index("orders")

    assert statement_at_cursor(sql, position) == (
        "SELECT * FROM orders WHERE id = 10"
    )


def test_statement_at_cursor_ignores_semicolon_inside_string() -> None:
    sql = (
        "SELECT 'a;b' AS value FROM users;\n"
        "SELECT 2;"
    )

    position = sql.index("value")

    assert statement_at_cursor(sql, position) == (
        "SELECT 'a;b' AS value FROM users"
    )


def test_statement_at_cursor_ignores_semicolon_inside_comments_and_dollar_quote() -> None:
    sql = (
        "SELECT $$a;b$$ AS value /* ; */;\n"
        "SELECT 2 -- ; comment\n"
        "FROM dual;"
    )

    assert statement_at_cursor(sql, sql.index("value")) == (
        "SELECT $$a;b$$ AS value /* ; */"
    )
    assert statement_at_cursor(sql, sql.index("dual")) == (
        "SELECT 2 -- ; comment\nFROM dual"
    )


def test_selected_sql_has_priority_over_cursor_statement() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT 1;\nSELECT 2;")

    cursor = editor.textCursor()
    start = editor.toPlainText().index("SELECT 1")
    cursor.setPosition(start)
    cursor.setPosition(
        start + len("SELECT 1"),
        QTextCursor.MoveMode.KeepAnchor,
    )
    editor.setTextCursor(cursor)

    assert editor.statement_to_execute() == "SELECT 1"


def test_ctrl_enter_executes_only_cursor_statement() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT 1;\nSELECT 2;")
    cursor = editor.textCursor()
    cursor.setPosition(editor.toPlainText().index("SELECT 2") + 3)
    editor.setTextCursor(cursor)

    executed: list[str] = []
    editor.execute_requested.connect(executed.append)

    QTest.keyClick(
        editor,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.ControlModifier,
    )

    assert executed == ["SELECT 2"]


def test_tab_completes_table_identifier() -> None:
    editor = SqlEditor()
    editor.set_identifiers(["audit_log"])
    editor.setPlainText("SELECT * FROM au")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "SELECT * FROM audit_log"


def test_tab_completes_function_and_adds_parenthesis() -> None:
    editor = SqlEditor()
    editor.set_dialect(DB_POSTGRESQL)
    editor.setPlainText("SELECT coa")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "SELECT COALESCE("


def test_tab_completes_distinct_without_parenthesis() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT dis")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "SELECT DISTINCT"


def test_missing_identifier_requests_async_lookup() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT * FROM audit")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    requested: list[str] = []
    editor.completion_lookup_requested.connect(requested.append)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert requested == ["audit"]


def test_async_lookup_single_result_completes_current_prefix() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT * FROM aud")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    editor.apply_lookup_candidates("aud", ["audit_log"])

    assert editor.toPlainText() == "SELECT * FROM audit_log"


def test_database_specific_completion_candidates() -> None:
    assert "COALESCE" in sql_functions(DB_MYSQL)
    assert "COALESCE" in sql_functions(DB_POSTGRESQL)
    assert "DISTINCT" in sql_keywords(DB_MYSQL)
    assert "IFNULL" in sql_functions(DB_MYSQL)
    assert "IFNULL" not in sql_functions(DB_POSTGRESQL)
    assert "DATE_TRUNC" in sql_functions(DB_POSTGRESQL)
    assert "DATE_TRUNC" not in sql_functions(DB_MYSQL)


def test_sql_highlighter_applies_multiple_token_styles() -> None:
    editor = SqlEditor()
    editor.setPlainText(
        "SELECT COALESCE(name, 'unknown'), 10 FROM users -- memo"
    )
    editor.highlighter.rehighlight()
    QApplication.processEvents()

    formats = editor.document().firstBlock().layout().formats()
    colors = {
        item.format.foreground().color().name()
        for item in formats
        if item.format.foreground().style() != Qt.BrushStyle.NoBrush
    }

    assert len(colors) >= 4
