from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
import math
import re
from typing import Iterator

from app.database_models import (
    DB_MYSQL,
    DB_POSTGRESQL,
    ColumnInfo,
    DatabaseProfile,
    PageResult,
    QueryResult,
    TableInfo,
)
from app.database_value_preview import compact_database_rows


READ_ONLY_START_RE = re.compile(
    r"^\s*(select|with|show|describe|desc|explain)\b",
    re.IGNORECASE,
)
BLOCKED_SQL_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|"
    r"replace|merge|call|copy|load|set|reset|vacuum|analyze|refresh|"
    r"comment|cluster|reindex)\b",
    re.IGNORECASE,
)
FILE_WRITE_RE = re.compile(
    r"\binto\s+(outfile|dumpfile)\b",
    re.IGNORECASE,
)
COMMENT_RE = re.compile(r"--|/\\*|\\*/")


def _mask_quoted_sql(sql: str) -> str:
    """문자열/식별자 내부를 공백으로 치환해 SQL 키워드 검사를 안전하게 한다."""
    masked: list[str] = []
    quote: str | None = None
    index = 0

    while index < len(sql):
        char = sql[index]

        if quote is None:
            if char in ("'", '"', "`"):
                quote = char
                masked.append(" ")
            else:
                masked.append(char)
            index += 1
            continue

        masked.append(" ")

        if char == "\\" and index + 1 < len(sql):
            masked.append(" ")
            index += 2
            continue

        if char == quote:
            if index + 1 < len(sql) and sql[index + 1] == quote:
                masked.append(" ")
                index += 2
                continue
            quote = None

        index += 1

    return "".join(masked)


def _strip_single_trailing_semicolon(
    statement: str,
    masked: str,
) -> tuple[str, str]:
    stripped_mask = masked.rstrip()
    if not stripped_mask.endswith(";"):
        return statement, masked

    semicolon_index = len(stripped_mask) - 1
    statement = statement[:semicolon_index].rstrip()
    masked = masked[:semicolon_index].rstrip()
    return statement, masked


def validate_read_only_sql(sql: str) -> str:
    statement = sql.strip()
    if not statement:
        raise ValueError("실행할 SELECT 문을 입력하세요.")

    masked = _mask_quoted_sql(statement)
    statement, masked = _strip_single_trailing_semicolon(
        statement,
        masked,
    )

    if not statement:
        raise ValueError("실행할 SELECT 문을 입력하세요.")
    if ";" in masked:
        raise ValueError("한 번에 SQL 한 문장만 실행할 수 있습니다.")
    if COMMENT_RE.search(masked):
        raise ValueError("Read Only SQL에서는 주석을 사용할 수 없습니다.")
    if not READ_ONLY_START_RE.search(masked):
        raise ValueError(
            "SELECT/SHOW/DESCRIBE/EXPLAIN 계열만 실행할 수 있습니다."
        )
    if BLOCKED_SQL_RE.search(masked) or FILE_WRITE_RE.search(masked):
        raise ValueError("데이터나 스키마를 변경하는 SQL은 실행할 수 없습니다.")
    return statement


def validate_where_clause(where_clause: str) -> str:
    clause = where_clause.strip()
    if not clause:
        return ""

    masked = _mask_quoted_sql(clause)
    if ";" in masked or COMMENT_RE.search(masked):
        raise ValueError(
            "WHERE 조건에는 세미콜론이나 SQL 주석을 사용할 수 없습니다."
        )
    if BLOCKED_SQL_RE.search(masked) or FILE_WRITE_RE.search(masked):
        raise ValueError("WHERE 조건에 변경 SQL을 넣을 수 없습니다.")
    return clause


class DatabaseAdapter:
    def __init__(self, profile: DatabaseProfile, password: str) -> None:
        self.profile = profile
        self.password = password

    @contextmanager
    def connection(self) -> Iterator[object]:
        connection = self._connect()
        try:
            self._configure_read_only(connection)
            yield connection
        finally:
            try:
                connection.close()
            except Exception:
                pass

    def _connect(self) -> object:
        raise NotImplementedError

    def _configure_read_only(self, connection: object) -> None:
        raise NotImplementedError

    def list_schemas(self) -> list[str]:
        raise NotImplementedError

    def list_tables(self, schema: str) -> list[TableInfo]:
        raise NotImplementedError

    def search_tables(
        self,
        query: str,
        *,
        limit: int = 100,
    ) -> list[TableInfo]:
        raise NotImplementedError

    def list_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        raise NotImplementedError

    def quote_identifier(self, value: str) -> str:
        raise NotImplementedError

    def qualified_table(self, schema: str, table: str) -> str:
        return (
            f"{self.quote_identifier(schema)}."
            f"{self.quote_identifier(table)}"
        )

    def test_connection(self) -> None:
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                cursor.close()

    def fetch_page(
        self,
        schema: str,
        table: str,
        *,
        limit: int,
        offset: int,
        where_clause: str = "",
        order_by: str = "",
        order_direction: str = "ASC",
    ) -> PageResult:
        safe_where = validate_where_clause(where_clause)
        sql = f"SELECT * FROM {self.qualified_table(schema, table)}"

        if safe_where:
            sql += f" WHERE {safe_where}"

        if order_by:
            direction = order_direction.upper()
            if direction not in ("ASC", "DESC"):
                raise ValueError("정렬 방향은 ASC 또는 DESC만 사용할 수 있습니다.")
            sql += (
                f" ORDER BY {self.quote_identifier(order_by)} "
                f"{direction}"
            )

        sql += " LIMIT %s OFFSET %s"

        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (limit + 1, offset))
                raw_rows = cursor.fetchmany(limit + 1)
                columns = tuple(
                    str(column[0])
                    for column in (cursor.description or ())
                )
            finally:
                cursor.close()

        has_next = len(raw_rows) > limit
        rows = compact_database_rows(raw_rows[:limit])
        del raw_rows
        return PageResult(
            columns=columns,
            rows=rows,
            has_next=has_next,
        )

    def run_query(
        self,
        sql: str,
        *,
        max_rows: int = 500,
    ) -> QueryResult:
        statement = validate_read_only_sql(sql)
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(statement)
                columns = tuple(
                    str(column[0])
                    for column in (cursor.description or ())
                )
                raw_rows = cursor.fetchmany(max_rows + 1)
            finally:
                cursor.close()

        truncated = len(raw_rows) > max_rows
        rows = compact_database_rows(raw_rows[:max_rows])
        del raw_rows
        return QueryResult(
            columns=columns,
            rows=rows,
            truncated=truncated,
        )

    def select_template(self, schema: str, table: str) -> str:
        return f"SELECT * FROM {self.qualified_table(schema, table)} LIMIT 100;"

    def build_quick_filter(
        self,
        column: str,
        value: object,
        mode: str,
    ) -> str:
        identifier = self.quote_identifier(column)

        if mode == "is_null" or (mode == "equals" and value is None):
            return f"{identifier} IS NULL"
        if mode == "not_null" or (
            mode == "not_equals" and value is None
        ):
            return f"{identifier} IS NOT NULL"

        literal = self._sql_literal(value)
        if mode == "equals":
            return f"{identifier} = {literal}"
        if mode == "not_equals":
            return f"{identifier} <> {literal}"
        raise ValueError(f"지원하지 않는 빠른 필터입니다: {mode}")

    def _sql_literal(self, value: object) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("NaN/Infinity 값은 빠른 필터를 지원하지 않습니다.")
            return repr(value)
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("NaN/Infinity 값은 빠른 필터를 지원하지 않습니다.")
            return str(value)
        if isinstance(value, datetime):
            return self._quote_string(value.isoformat(sep=" "))
        if isinstance(value, (date, time)):
            return self._quote_string(value.isoformat())
        if isinstance(value, (bytes, bytearray, memoryview)):
            raise ValueError("바이너리 값은 빠른 필터를 지원하지 않습니다.")
        return self._quote_string(str(value))

    @staticmethod
    def _quote_string(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"


class MySqlAdapter(DatabaseAdapter):
    SYSTEM_SCHEMAS = (
        "information_schema",
        "mysql",
        "performance_schema",
        "sys",
    )

    def _connect(self) -> object:
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError(
                "MySQL 연결 드라이버 PyMySQL이 설치되어 있지 않습니다."
            ) from exc

        return pymysql.connect(
            host=self.profile.host,
            port=self.profile.port,
            user=self.profile.user,
            password=self.password,
            database=self.profile.database or None,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
            read_timeout=30,
            write_timeout=30,
        )

    def _configure_read_only(self, connection: object) -> None:
        cursor = connection.cursor()
        try:
            try:
                cursor.execute("SET SESSION TRANSACTION READ ONLY")
            except Exception:
                pass
            try:
                cursor.execute("SET SESSION MAX_EXECUTION_TIME = 30000")
            except Exception:
                pass
        finally:
            cursor.close()

    def quote_identifier(self, value: str) -> str:
        return "`" + value.replace("`", "``") + "`"

    def list_schemas(self) -> list[str]:
        placeholders = ", ".join(["%s"] * len(self.SYSTEM_SCHEMAS))
        sql = (
            "SELECT schema_name FROM information_schema.schemata "
            f"WHERE schema_name NOT IN ({placeholders}) "
            "ORDER BY schema_name"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, self.SYSTEM_SCHEMAS)
                return [str(row[0]) for row in cursor.fetchall()]
            finally:
                cursor.close()

    def list_tables(self, schema: str) -> list[TableInfo]:
        sql = (
            "SELECT table_name, table_type "
            "FROM information_schema.tables "
            "WHERE table_schema = %s "
            "ORDER BY table_name"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (schema,))
                return [
                    TableInfo(schema, str(row[0]), str(row[1]))
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()

    def search_tables(
        self,
        query: str,
        *,
        limit: int = 100,
    ) -> list[TableInfo]:
        placeholders = ", ".join(["%s"] * len(self.SYSTEM_SCHEMAS))
        sql = (
            "SELECT table_schema, table_name, table_type "
            "FROM information_schema.tables "
            f"WHERE table_schema NOT IN ({placeholders}) "
            "AND table_name LIKE %s "
            "ORDER BY table_schema, table_name "
            "LIMIT %s"
        )
        params = (
            *self.SYSTEM_SCHEMAS,
            f"%{query}%",
            max(1, min(limit, 200)),
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, params)
                return [
                    TableInfo(
                        schema=str(row[0]),
                        name=str(row[1]),
                        kind=str(row[2]),
                    )
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()

    def list_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        sql = (
            "SELECT column_name, column_type, is_nullable, "
            "column_default, column_key "
            "FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s "
            "ORDER BY ordinal_position"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (schema, table))
                return [
                    ColumnInfo(
                        name=str(row[0]),
                        data_type=str(row[1]),
                        nullable=str(row[2]).upper() == "YES",
                        default=None if row[3] is None else str(row[3]),
                        key=str(row[4] or ""),
                    )
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()


class PostgreSqlAdapter(DatabaseAdapter):
    def _connect(self) -> object:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL 연결 드라이버 psycopg가 설치되어 있지 않습니다."
            ) from exc

        return psycopg.connect(
            host=self.profile.host,
            port=self.profile.port,
            dbname=self.profile.database,
            user=self.profile.user,
            password=self.password,
            connect_timeout=5,
            autocommit=True,
            application_name="WorKing",
        )

    def _configure_read_only(self, connection: object) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("SET default_transaction_read_only = on")
            cursor.execute("SET statement_timeout = 30000")
        finally:
            cursor.close()

    def quote_identifier(self, value: str) -> str:
        return f'"{value.replace(chr(34), chr(34) * 2)}"'

    def list_schemas(self) -> list[str]:
        sql = (
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name <> 'information_schema' "
            "AND schema_name NOT LIKE 'pg_%' "
            "ORDER BY schema_name"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql)
                return [str(row[0]) for row in cursor.fetchall()]
            finally:
                cursor.close()

    def list_tables(self, schema: str) -> list[TableInfo]:
        sql = (
            "SELECT table_name, table_type "
            "FROM information_schema.tables "
            "WHERE table_schema = %s "
            "ORDER BY table_name"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (schema,))
                return [
                    TableInfo(schema, str(row[0]), str(row[1]))
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()

    def search_tables(
        self,
        query: str,
        *,
        limit: int = 100,
    ) -> list[TableInfo]:
        sql = (
            "SELECT table_schema, table_name, table_type "
            "FROM information_schema.tables "
            "WHERE table_schema <> 'information_schema' "
            "AND table_schema NOT LIKE 'pg_%' "
            "AND table_name ILIKE %s "
            "ORDER BY table_schema, table_name "
            "LIMIT %s"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    sql,
                    (f"%{query}%", max(1, min(limit, 200))),
                )
                return [
                    TableInfo(
                        schema=str(row[0]),
                        name=str(row[1]),
                        kind=str(row[2]),
                    )
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()

    def list_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        sql = (
            "SELECT c.column_name, c.data_type, c.is_nullable, "
            "c.column_default, "
            "CASE WHEN pk.column_name IS NULL THEN '' ELSE 'PRI' END "
            "FROM information_schema.columns c "
            "LEFT JOIN ("
            "  SELECT kcu.table_schema, kcu.table_name, kcu.column_name "
            "  FROM information_schema.table_constraints tc "
            "  JOIN information_schema.key_column_usage kcu "
            "    ON tc.constraint_name = kcu.constraint_name "
            "   AND tc.constraint_schema = kcu.constraint_schema "
            "  WHERE tc.constraint_type = 'PRIMARY KEY'"
            ") pk "
            "ON pk.table_schema = c.table_schema "
            "AND pk.table_name = c.table_name "
            "AND pk.column_name = c.column_name "
            "WHERE c.table_schema = %s AND c.table_name = %s "
            "ORDER BY c.ordinal_position"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (schema, table))
                return [
                    ColumnInfo(
                        name=str(row[0]),
                        data_type=str(row[1]),
                        nullable=str(row[2]).upper() == "YES",
                        default=None if row[3] is None else str(row[3]),
                        key=str(row[4] or ""),
                    )
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()


class DatabaseService:
    def adapter(
        self,
        profile: DatabaseProfile,
        password: str,
    ) -> DatabaseAdapter:
        if profile.db_type == DB_MYSQL:
            return MySqlAdapter(profile, password)
        if profile.db_type == DB_POSTGRESQL:
            return PostgreSqlAdapter(profile, password)
        raise ValueError(f"지원하지 않는 DB 종류입니다: {profile.db_type}")

    def test_connection(
        self,
        profile: DatabaseProfile,
        password: str,
    ) -> None:
        self.adapter(profile, password).test_connection()

    def load_schemas(
        self,
        profile: DatabaseProfile,
        password: str,
    ) -> list[str]:
        return self.adapter(profile, password).list_schemas()

    def load_tables(
        self,
        profile: DatabaseProfile,
        password: str,
        schema: str,
    ) -> list[TableInfo]:
        return self.adapter(profile, password).list_tables(schema)

    def search_tables(
        self,
        profile: DatabaseProfile,
        password: str,
        query: str,
        *,
        limit: int = 100,
    ) -> list[TableInfo]:
        normalized = query.strip()
        if not normalized:
            return []
        return self.adapter(profile, password).search_tables(
            normalized,
            limit=limit,
        )

    def load_catalog(
        self,
        profile: DatabaseProfile,
        password: str,
    ) -> dict[str, list[TableInfo]]:
        adapter = self.adapter(profile, password)
        return {
            schema: adapter.list_tables(schema)
            for schema in adapter.list_schemas()
        }

    def load_table(
        self,
        profile: DatabaseProfile,
        password: str,
        schema: str,
        table: str,
        *,
        page: int,
        page_size: int,
        where_clause: str = "",
        order_by: str = "",
        order_direction: str = "ASC",
    ) -> tuple[list[ColumnInfo], PageResult]:
        adapter = self.adapter(profile, password)
        columns = adapter.list_columns(schema, table)
        data = adapter.fetch_page(
            schema,
            table,
            limit=page_size,
            offset=max(page, 0) * page_size,
            where_clause=where_clause,
            order_by=order_by,
            order_direction=order_direction,
        )
        return columns, data

    def load_page(
        self,
        profile: DatabaseProfile,
        password: str,
        schema: str,
        table: str,
        *,
        page: int,
        page_size: int,
        where_clause: str = "",
        order_by: str = "",
        order_direction: str = "ASC",
    ) -> PageResult:
        return self.adapter(profile, password).fetch_page(
            schema,
            table,
            limit=page_size,
            offset=max(page, 0) * page_size,
            where_clause=where_clause,
            order_by=order_by,
            order_direction=order_direction,
        )

    def run_query(
        self,
        profile: DatabaseProfile,
        password: str,
        sql: str,
    ) -> QueryResult:
        return self.adapter(profile, password).run_query(sql)

    def select_template(
        self,
        profile: DatabaseProfile,
        schema: str,
        table: str,
    ) -> str:
        return self.adapter(profile, "").select_template(schema, table)

    def build_quick_filter(
        self,
        profile: DatabaseProfile,
        column: str,
        value: object,
        mode: str,
    ) -> str:
        return self.adapter(profile, "").build_quick_filter(
            column,
            value,
            mode,
        )
