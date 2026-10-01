from __future__ import annotations

from contextlib import contextmanager
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
COMMENT_MARKERS = ("--", "/*", "*/")


def validate_read_only_sql(sql: str) -> str:
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()
    if not statement:
        raise ValueError("실행할 SELECT 문을 입력하세요.")
    if ";" in statement:
        raise ValueError("한 번에 SQL 한 문장만 실행할 수 있습니다.")
    if any(marker in statement for marker in COMMENT_MARKERS):
        raise ValueError("Read Only SQL에서는 주석을 사용할 수 없습니다.")
    if not READ_ONLY_START_RE.search(statement):
        raise ValueError("SELECT/SHOW/DESCRIBE/EXPLAIN 계열만 실행할 수 있습니다.")
    if BLOCKED_SQL_RE.search(statement) or FILE_WRITE_RE.search(statement):
        raise ValueError("데이터나 스키마를 변경하는 SQL은 실행할 수 없습니다.")
    return statement


def validate_where_clause(where_clause: str) -> str:
    clause = where_clause.strip()
    if not clause:
        return ""
    if ";" in clause or any(marker in clause for marker in COMMENT_MARKERS):
        raise ValueError("WHERE 조건에는 세미콜론이나 SQL 주석을 사용할 수 없습니다.")
    if BLOCKED_SQL_RE.search(clause) or FILE_WRITE_RE.search(clause):
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
    ) -> PageResult:
        safe_where = validate_where_clause(where_clause)
        sql = f"SELECT * FROM {self.qualified_table(schema, table)}"
        if safe_where:
            sql += f" WHERE {safe_where}"
        sql += " LIMIT %s OFFSET %s"

        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (limit + 1, offset))
                rows = cursor.fetchmany(limit + 1)
                columns = tuple(
                    str(column[0])
                    for column in (cursor.description or ())
                )
            finally:
                cursor.close()

        has_next = len(rows) > limit
        return PageResult(
            columns=columns,
            rows=tuple(tuple(row) for row in rows[:limit]),
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
                rows = cursor.fetchmany(max_rows + 1)
            finally:
                cursor.close()

        return QueryResult(
            columns=columns,
            rows=tuple(tuple(row) for row in rows[:max_rows]),
            truncated=len(rows) > max_rows,
        )

    def select_template(self, schema: str, table: str) -> str:
        return f"SELECT * FROM {self.qualified_table(schema, table)} LIMIT 100;"


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
        return f"`{value.replace('`', '``')}`"

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

    def load_catalog(
        self,
        profile: DatabaseProfile,
        password: str,
    ) -> dict[str, list[TableInfo]]:
        adapter = self.adapter(profile, password)
        result: dict[str, list[TableInfo]] = {}
        for schema in adapter.list_schemas():
            result[schema] = adapter.list_tables(schema)
        return result

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
    ) -> tuple[list[ColumnInfo], PageResult]:
        adapter = self.adapter(profile, password)
        columns = adapter.list_columns(schema, table)
        data = adapter.fetch_page(
            schema,
            table,
            limit=page_size,
            offset=max(page, 0) * page_size,
            where_clause=where_clause,
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
    ) -> PageResult:
        return self.adapter(profile, password).fetch_page(
            schema,
            table,
            limit=page_size,
            offset=max(page, 0) * page_size,
            where_clause=where_clause,
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
