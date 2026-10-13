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
    resolve_sql_relation,
    sql_functions,
    sql_keywords,
    sql_relation_aliases,
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


def test_tab_requests_column_lookup_after_table_dot() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT users.")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    requested: list[str] = []
    editor.completion_lookup_requested.connect(requested.append)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert requested == ["users."]


def test_tab_completes_known_table_column() -> None:
    editor = SqlEditor()
    editor.set_identifiers(["users.id"])
    editor.setPlainText("SELECT users.")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "SELECT users.id"


def test_async_table_column_candidates_open_completion_list() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT users.")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    editor.apply_lookup_candidates(
        "users.",
        ["users.id", "users.name"],
    )

    assert editor._completer.completionPrefix() == "users."
    assert editor._completer.completionCount() == 2


def test_enter_accepts_selected_completion_without_newline() -> None:
    editor = SqlEditor()
    editor.resize(640, 320)
    editor.show()
    editor.set_identifiers(["users.id", "users.name"])
    editor.setPlainText("SELECT users.")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    editor._show_completion()
    QApplication.processEvents()

    popup = editor._completer.popup()
    second = editor._completer.completionModel().index(1, 0)
    popup.setCurrentIndex(second)

    QTest.keyClick(editor, Qt.Key.Key_Return)

    assert editor.toPlainText() == "SELECT users.name"
    assert "\n" not in editor.toPlainText()


def test_enter_inserts_newline_when_completion_popup_is_closed() -> None:
    editor = SqlEditor()
    editor.setPlainText("SELECT 1")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    QTest.keyClick(editor, Qt.Key.Key_Return)

    assert editor.toPlainText() == "SELECT 1\n"


def test_sql_relation_aliases_resolves_from_alias() -> None:
    sql = (
        "SELECT ss.*\n"
        "FROM scan_scan ss\n"
        "WHERE ss.preset_value IS NOT NULL"
    )

    aliases = sql_relation_aliases(sql)

    assert aliases["ss"] == "scan_scan"
    assert aliases["scan_scan"] == "scan_scan"
    assert resolve_sql_relation(sql, "ss") == "scan_scan"


def test_sql_relation_aliases_supports_schema_as_and_join() -> None:
    sql = (
        "SELECT u.id, o.status\n"
        "FROM public.users AS u\n"
        "LEFT JOIN audit.orders o ON o.user_id = u.id"
    )

    assert resolve_sql_relation(sql, "u") == "public.users"
    assert resolve_sql_relation(sql, "o") == "audit.orders"
    assert resolve_sql_relation(sql, "orders") == "audit.orders"


def test_sql_relation_aliases_ignores_string_and_comment_content() -> None:
    sql = (
        "SELECT 'FROM fake_table f' AS memo\n"
        "FROM users u -- JOIN ignored_table x\n"
        "WHERE u.name = 'JOIN nope n'"
    )

    aliases = sql_relation_aliases(sql)

    assert aliases["u"] == "users"
    assert "f" not in aliases
    assert "x" not in aliases
    assert "n" not in aliases


def test_alias_partial_column_prefix_requests_lookup() -> None:
    editor = SqlEditor()
    editor.setPlainText(
        "SELECT ss.*\n"
        "FROM scan_scan ss\n"
        "WHERE ss.pre"
    )
    editor.moveCursor(QTextCursor.MoveOperation.End)

    requested: list[str] = []
    editor.completion_lookup_requested.connect(requested.append)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert requested == ["ss.pre"]
