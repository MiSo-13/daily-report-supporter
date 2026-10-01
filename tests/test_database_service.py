from __future__ import annotations

import pytest

from app.database_models import (
    DB_MYSQL,
    DB_POSTGRESQL,
    DatabaseProfile,
)
from app.database_service import (
    MySqlAdapter,
    PostgreSqlAdapter,
    validate_read_only_sql,
    validate_where_clause,
)


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


def test_where_clause_accepts_simple_filter() -> None:
    assert (
        validate_where_clause("status = 'ERROR' AND id > 10")
        == "status = 'ERROR' AND id > 10"
    )


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
