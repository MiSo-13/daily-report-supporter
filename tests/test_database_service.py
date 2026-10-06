from __future__ import annotations

import pytest

from app.database_models import (
    DB_MYSQL,
    DB_POSTGRESQL,
    DatabaseProfile,
)
from app.database_service import (
    DatabaseAdapter,
    MySqlAdapter,
    PostgreSqlAdapter,
    validate_read_only_sql,
    validate_where_clause,
)
from app.database_value_preview import DatabaseValuePreview


def _profile(db_type: str) -> DatabaseProfile:
    return DatabaseProfile(
        connection_id="test",
        name="test",
        db_type=db_type,
        host="localhost",
        port=3306 if db_type == DB_MYSQL else 5432,
        database="app",
        user="viewer",
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM users",
        "WITH recent AS (SELECT * FROM users) SELECT * FROM recent",
        "SHOW TABLES",
        "DESCRIBE users",
        "EXPLAIN SELECT * FROM users",
        "SELECT 'update delete drop' AS message",
        'SELECT "update" FROM users',
    ],
)
def test_read_only_sql_accepts_query_statements(sql: str) -> None:
    assert validate_read_only_sql(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "WITH changed AS (DELETE FROM users RETURNING *) SELECT * FROM changed",
        "SELECT * FROM users; DELETE FROM users",
        "SELECT * FROM users -- comment",
        "SELECT * FROM users INTO OUTFILE '/tmp/users.txt'",
    ],
)
def test_read_only_sql_rejects_mutating_or_multi_statements(sql: str) -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql(sql)


def test_read_only_sql_allows_single_trailing_semicolon() -> None:
    assert validate_read_only_sql("SELECT 1;") == "SELECT 1"


def test_read_only_sql_ignores_semicolon_inside_string() -> None:
    assert (
        validate_read_only_sql("SELECT ';' AS value;")
        == "SELECT ';' AS value"
    )


def test_where_clause_accepts_simple_filter() -> None:
    assert (
        validate_where_clause("status = 'ERROR' AND id > 10")
        == "status = 'ERROR' AND id > 10"
    )


def test_where_clause_ignores_keywords_inside_string() -> None:
    clause = "message = 'delete; update' AND status = 'ERROR'"

    assert validate_where_clause(clause) == clause


def test_postgresql_json_operator_is_not_treated_as_comment() -> None:
    sql = "SELECT payload #>> '{user,name}' FROM events"

    assert validate_read_only_sql(sql) == sql


@pytest.mark.parametrize(
    "where_clause",
    [
        "1 = 1; DELETE FROM users",
        "id > 1 -- bypass",
        "id IN (SELECT id FROM x);",
        "UPDATE users SET x = 1",
    ],
)
def test_where_clause_rejects_unsafe_content(where_clause: str) -> None:
    with pytest.raises(ValueError):
        validate_where_clause(where_clause)


def test_mysql_identifier_quoting() -> None:
    adapter = MySqlAdapter(_profile(DB_MYSQL), "")

    assert adapter.quote_identifier("order") == "`order`"
    assert adapter.quote_identifier("a`b") == "`a``b`"


def test_postgresql_identifier_quoting() -> None:
    adapter = PostgreSqlAdapter(_profile(DB_POSTGRESQL), "")

    assert adapter.quote_identifier("order") == '"order"'
    assert adapter.quote_identifier('a"b') == '"a""b"'


def test_quick_filter_quotes_string_and_null() -> None:
    adapter = MySqlAdapter(_profile(DB_MYSQL), "")

    assert (
        adapter.build_quick_filter("name", "O'Reilly", "equals")
        == "`name` = 'O''Reilly'"
    )
    assert (
        adapter.build_quick_filter("deleted_at", None, "equals")
        == "`deleted_at` IS NULL"
    )
    assert (
        adapter.build_quick_filter("deleted_at", None, "not_equals")
        == "`deleted_at` IS NOT NULL"
    )


class _FakeCursor:
    description = (("id",),)

    def __init__(
        self,
        rows: list[tuple[object, ...]] | None = None,
    ) -> None:
        self.sql = ""
        self.params: object = None
        self.rows = rows if rows is not None else [(3,), (2,)]

    def execute(self, sql: str, params: object = None) -> None:
        self.sql = sql
        self.params = params

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        return list(self.rows[:size])

    def close(self) -> None:
        return None


class _FakeConnection:
    def __init__(
        self,
        rows: list[tuple[object, ...]] | None = None,
    ) -> None:
        self.cursor_instance = _FakeCursor(rows)

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance

    def close(self) -> None:
        return None


class _FakeAdapter(DatabaseAdapter):
    def __init__(
        self,
        rows: list[tuple[object, ...]] | None = None,
    ) -> None:
        super().__init__(_profile(DB_POSTGRESQL), "")
        self.fake_connection = _FakeConnection(rows)

    def _connect(self) -> _FakeConnection:
        return self.fake_connection

    def _configure_read_only(self, connection: object) -> None:
        return None

    def quote_identifier(self, value: str) -> str:
        return f'"{value}"'

    def list_schemas(self) -> list[str]:
        return []

    def list_tables(self, schema: str) -> list[object]:
        return []

    def search_tables(
        self,
        query: str,
        *,
        limit: int = 100,
    ) -> list[object]:
        return []

    def list_columns(self, schema: str, table: str) -> list[object]:
        return []


def test_fetch_page_uses_server_side_order_by() -> None:
    adapter = _FakeAdapter()

    adapter.fetch_page(
        "public",
        "users",
        limit=1,
        offset=20,
        order_by="id",
        order_direction="DESC",
    )

    assert (
        adapter.fake_connection.cursor_instance.sql
        == 'SELECT * FROM "public"."users" ORDER BY "id" DESC '
        "LIMIT %s OFFSET %s"
    )
    assert adapter.fake_connection.cursor_instance.params == (2, 20)


def test_fetch_page_rejects_invalid_sort_direction() -> None:
    adapter = _FakeAdapter()

    with pytest.raises(ValueError):
        adapter.fetch_page(
            "public",
            "users",
            limit=100,
            offset=0,
            order_by="id",
            order_direction="DROP",
        )



def test_fetch_page_compacts_large_value_before_ui_model() -> None:
    adapter = _FakeAdapter(rows=[("x" * 200_000,)])

    result = adapter.fetch_page(
        "public",
        "events",
        limit=100,
        offset=0,
    )

    value = result.rows[0][0]
    assert isinstance(value, DatabaseValuePreview)
    assert value.original_size == 200_000


def test_run_query_compacts_large_value_before_ui_model() -> None:
    adapter = _FakeAdapter(rows=[("x" * 200_000,)])

    result = adapter.run_query("SELECT payload FROM events")

    value = result.rows[0][0]
    assert isinstance(value, DatabaseValuePreview)
    assert value.original_size == 200_000



def test_fetch_cell_detail_uses_primary_key_for_exact_lookup() -> None:
    adapter = _FakeAdapter(rows=[("full payload",)])

    result = adapter.fetch_cell_detail(
        "public",
        "events",
        "payload",
        primary_key_values={"id": 42},
    )

    assert (
        adapter.fake_connection.cursor_instance.sql
        == 'SELECT "payload" FROM "public"."events" '
        'WHERE "id" = %s LIMIT 2'
    )
    assert adapter.fake_connection.cursor_instance.params == (42,)
    assert result.value == "full payload"
    assert result.exact
    assert result.source == "Primary Key"


def test_fetch_cell_detail_falls_back_to_current_query_position() -> None:
    adapter = _FakeAdapter(rows=[("full payload",)])

    result = adapter.fetch_cell_detail(
        "public",
        "events",
        "payload",
        offset=201,
        where_clause="status = 'READY'",
        order_by="id",
        order_direction="DESC",
    )

    assert (
        adapter.fake_connection.cursor_instance.sql
        == 'SELECT "payload" FROM "public"."events" '
        "WHERE status = 'READY' ORDER BY \"id\" DESC "
        "LIMIT 1 OFFSET %s"
    )
    assert adapter.fake_connection.cursor_instance.params == (201,)
    assert result.value == "full payload"
    assert not result.exact
    assert result.source == "현재 조회 순서"


def test_fetch_cell_detail_rejects_duplicate_primary_key_result() -> None:
    adapter = _FakeAdapter(rows=[("first",), ("second",)])

    with pytest.raises(ValueError, match="여러 행"):
        adapter.fetch_cell_detail(
            "public",
            "events",
            "payload",
            primary_key_values={"id": 42},
        )
