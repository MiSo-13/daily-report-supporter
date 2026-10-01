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
