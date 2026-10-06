from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.database_models import DatabaseProfile, PageResult
from app.database_ui import (
    KIND_SCHEMA,
    ROLE_KIND,
    DatabasePanel,
    DatabaseSidebar,
)


_APP = QApplication.instance() or QApplication([])


def _profile() -> DatabaseProfile:
    return DatabaseProfile(
        connection_id="dev",
        name="DEV",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="app",
        user="viewer",
    )


def test_database_panel_server_sort_toggle() -> None:
    panel = DatabasePanel()
    events: list[tuple[str, str]] = []
    panel.sort_requested.connect(
        lambda column, direction: events.append((column, direction))
    )
    panel.set_data(
        PageResult(
            columns=("id", "name"),
            rows=((1, "A"), (2, "B")),
            has_next=False,
        ),
        page=0,
    )

    panel._request_server_sort(0)
    panel._request_server_sort(0)

    assert events == [("id", "ASC"), ("id", "DESC")]
    assert panel.sort_column == "id"
    assert panel.sort_direction == "DESC"


def test_database_sidebar_emits_lazy_schema_request() -> None:
    sidebar = DatabaseSidebar()
    events: list[tuple[str, str]] = []
    sidebar.schema_expand_requested.connect(
        lambda profile_id, schema: events.append((profile_id, schema))
    )
    sidebar.set_profiles([_profile()], select_id="dev")
    sidebar.set_schemas("dev", ["public"])

    profile_item = sidebar.tree.topLevelItem(0)
    schema_item = next(
        profile_item.child(index)
        for index in range(profile_item.childCount())
        if profile_item.child(index).data(0, ROLE_KIND) == KIND_SCHEMA
    )

    sidebar._item_expanded(schema_item)
    sidebar._item_expanded(schema_item)

    assert events == [("dev", "public")]


def test_database_panel_copy_selection_uses_tsv() -> None:
    panel = DatabasePanel()
    panel.set_data(
        PageResult(
            columns=("id", "name"),
            rows=((1, "Alpha"),),
            has_next=False,
        ),
        page=0,
    )
    panel.data_table.selectAll()

    panel._copy_selection(panel.data_table, include_headers=True)

    assert QApplication.clipboard().text() == "id\tname\n1\tAlpha"


def test_database_panel_programmatic_sql_restore_does_not_emit_draft() -> None:
    panel = DatabasePanel()
    drafts: list[str] = []
    panel.sql_draft_changed.connect(drafts.append)

    panel.set_sql_text("SELECT * FROM users;")

    assert panel.sql_text == "SELECT * FROM users;"
    assert drafts == []


def test_database_panel_user_sql_edit_emits_draft() -> None:
    panel = DatabasePanel()
    drafts: list[str] = []
    panel.sql_draft_changed.connect(drafts.append)

    panel.sql_editor.setPlainText("SELECT 1;")

    assert drafts == ["SELECT 1;"]


def test_database_sidebar_emits_reordered_connection_ids() -> None:
    sidebar = DatabaseSidebar()
    first = _profile()
    second = DatabaseProfile(
        connection_id="stage",
        name="STG",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="stage",
        user="viewer",
    )
    events: list[list[str]] = []
    sidebar.profile_reorder_requested.connect(events.append)
    sidebar.set_profiles([first, second])

    moved = sidebar.tree.takeTopLevelItem(1)
    sidebar.tree.insertTopLevelItem(0, moved)
    sidebar._persist_profile_order()

    assert events == [["stage", "dev"]]



def test_database_panel_runs_only_sql_at_cursor() -> None:
    panel = DatabasePanel()
    panel.sql_editor.setPlainText("SELECT 1;\nSELECT 2;")
    cursor = panel.sql_editor.textCursor()
    cursor.setPosition(
        panel.sql_editor.toPlainText().index("SELECT 2") + 3
    )
    panel.sql_editor.setTextCursor(cursor)

    executed: list[str] = []
    panel.sql_requested.connect(executed.append)

    panel._request_sql_execution()

    assert executed == ["SELECT 2"]



def test_database_result_tables_use_bounded_interactive_widths() -> None:
    panel = DatabasePanel()

    data_header = panel.data_table.horizontalHeader()
    sql_header = panel.sql_table.horizontalHeader()

    assert data_header.maximumSectionSize() == 360
    assert sql_header.maximumSectionSize() == 360
    assert data_header.defaultSectionSize() == 160
    assert sql_header.defaultSectionSize() == 160


def test_large_database_value_is_reported_as_preview() -> None:
    panel = DatabasePanel()
    panel.set_data(
        PageResult(
            columns=("id", "payload"),
            rows=((1, "x" * 200_000),),
            has_next=False,
        ),
        page=0,
    )

    assert "큰 값 1개 미리보기" in panel.data_status.text()
    assert panel.data_model.truncated_value_count == 1


def test_copy_selection_uses_stored_preview_not_full_large_value() -> None:
    panel = DatabasePanel()
    panel.set_data(
        PageResult(
            columns=("payload",),
            rows=(("x" * 200_000,),),
            has_next=False,
        ),
        page=0,
    )
    panel.data_table.selectAll()

    panel._copy_selection(panel.data_table)

    copied = QApplication.clipboard().text()
    assert len(copied) <= 4096
    assert "원본 200,000자" in copied



def test_database_panel_detail_tab_formats_json() -> None:
    panel = DatabasePanel()

    panel.show_detail_value(
        "public",
        "events",
        "payload",
        "jsonb",
        {"user": {"name": "Alice"}, "active": True},
        exact=True,
        source="Primary Key",
    )

    assert panel.tabs.isTabVisible(panel._detail_tab_index)
    assert panel.tabs.currentIndex() == panel._detail_tab_index
    assert panel.tabs.tabText(panel._detail_tab_index) == "상세 · payload"
    assert '"name": "Alice"' in panel.detail_viewer.toPlainText()
    assert "JSON" in panel.detail_meta.text()
    assert "Primary Key" in panel.detail_status.text()


def test_database_panel_detail_tab_marks_fallback_lookup() -> None:
    panel = DatabasePanel()

    panel.show_detail_value(
        "public",
        "logs",
        "message",
        "text",
        "hello",
        exact=False,
        source="현재 조회 순서",
    )

    assert "PK 없음" in panel.detail_status.text()
    assert "현재 조회 순서" in panel.detail_status.text()


def test_database_panel_hides_detail_when_table_changes() -> None:
    panel = DatabasePanel()
    panel.show_detail_value(
        "public",
        "events",
        "payload",
        "text",
        "hello",
        exact=True,
        source="현재 페이지",
    )

    panel.set_table_context(
        _profile(),
        "public",
        "users",
        "SELECT * FROM users;",
    )

    assert not panel.tabs.isTabVisible(panel._detail_tab_index)
