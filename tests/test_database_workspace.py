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


def test_current_table_column_completion_uses_loaded_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_schema = "public"
    workspace._current_table = "users"
    workspace._current_columns = [
        ColumnInfo("id", "bigint", False),
        ColumnInfo("name", "text", True),
    ]
    applied: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        workspace.panel,
        "apply_sql_completion_lookup",
        lambda prefix, identifiers: applied.append(
            (prefix, tuple(identifiers))
        ),
    )

    handled = workspace._apply_current_table_column_completion("users.")

    assert handled
    assert applied == [
        ("users.", ("users.id", "users.name"))
    ]


def test_current_table_column_completion_supports_schema_prefix(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_schema = "public"
    workspace._current_table = "users"
    workspace._current_columns = [
        ColumnInfo("id", "bigint", False),
    ]
    applied: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        workspace.panel,
        "apply_sql_completion_lookup",
        lambda prefix, identifiers: applied.append(
            (prefix, tuple(identifiers))
        ),
    )

    handled = workspace._apply_current_table_column_completion(
        "public.users."
    )

    assert handled
    assert applied == [
        ("public.users.", ("public.users.id",))
    ]


def test_alias_partial_column_completion_uses_current_table_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_schema = "public"
    workspace._current_table = "scan_scan"
    workspace._current_columns = [
        ColumnInfo("id", "bigint", False),
        ColumnInfo("preset_value", "text", True),
        ColumnInfo("preset_name", "text", True),
    ]
    workspace.panel.sql_editor.setPlainText(
        "SELECT ss.*\n"
        "FROM scan_scan ss\n"
        "WHERE ss.pre"
    )

    applied: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        workspace.panel,
        "apply_sql_completion_lookup",
        lambda prefix, identifiers: applied.append(
            (prefix, tuple(identifiers))
        ),
    )

    relation = workspace._sql_column_relation("ss.pre")
    handled = workspace._apply_current_table_column_completion(
        "ss.pre",
        relation=relation,
    )

    assert relation == "scan_scan"
    assert handled
    assert applied == [
        (
            "ss.pre",
            (
                "ss.id",
                "ss.preset_value",
                "ss.preset_name",
            ),
        )
    ]


def test_alias_dot_completion_uses_alias_in_candidate_names(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_schema = "public"
    workspace._current_table = "scan_scan"
    workspace._current_columns = [
        ColumnInfo("id", "bigint", False),
        ColumnInfo("preset_value", "text", True),
    ]
    workspace.panel.sql_editor.setPlainText(
        "SELECT ss.\nFROM public.scan_scan AS ss"
    )

    applied: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        workspace.panel,
        "apply_sql_completion_lookup",
        lambda prefix, identifiers: applied.append(
            (prefix, tuple(identifiers))
        ),
    )

    relation = workspace._sql_column_relation("ss.")
    handled = workspace._apply_current_table_column_completion(
        "ss.",
        relation=relation,
    )

    assert relation == "public.scan_scan"
    assert handled
    assert applied == [
        ("ss.", ("ss.id", "ss.preset_value"))
    ]


def test_async_partial_column_completion_keeps_original_qualifier(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = _workspace(tmp_path)
    workspace._current_profile_id = "dev"
    workspace._completion_generation = 3

    applied: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        workspace.panel,
        "apply_sql_completion_lookup",
        lambda prefix, identifiers: applied.append(
            (prefix, tuple(identifiers))
        ),
    )

    workspace._sql_column_completion_loaded(
        "dev",
        "ss.pre",
        3,
        [
            ColumnInfo("id", "bigint", False),
            ColumnInfo("preset_value", "text", True),
        ],
    )

    assert applied == [
        (
            "ss.pre",
            ("ss.id", "ss.preset_value"),
        )
    ]
