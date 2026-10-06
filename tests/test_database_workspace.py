from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from app.database_models import ColumnInfo, PageResult
from app.database_workspace import DatabaseWorkspace


_APP = QApplication.instance() or QApplication([])


def _workspace(tmp_path) -> DatabaseWorkspace:
    return DatabaseWorkspace(
        tmp_path / "database-connections.json",
        QWidget(),
    )


def test_primary_key_values_are_collected_from_selected_row(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_columns = [
        ColumnInfo("tenant_id", "integer", False, key="PRI"),
        ColumnInfo("id", "bigint", False, key="PRI"),
        ColumnInfo("payload", "jsonb", True),
    ]
    workspace.panel.set_data(
        PageResult(
            columns=("tenant_id", "id", "payload"),
            rows=((7, 42, {"value": "x"}),),
            has_next=False,
        ),
        page=0,
    )

    assert workspace._primary_key_values_for_row(0) == {
        "tenant_id": 7,
        "id": 42,
    }


def test_preview_primary_key_disables_exact_detail_lookup(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_columns = [
        ColumnInfo("id", "text", False, key="PRI"),
        ColumnInfo("payload", "text", True),
    ]
    workspace.panel.set_data(
        PageResult(
            columns=("id", "payload"),
            rows=(("x" * 10_000, "value"),),
            has_next=False,
        ),
        page=0,
    )

    assert workspace._primary_key_values_for_row(0) is None
