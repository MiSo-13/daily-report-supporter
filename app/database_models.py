from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DB_MYSQL = "mysql"
DB_POSTGRESQL = "postgresql"
SUPPORTED_DATABASES = (DB_MYSQL, DB_POSTGRESQL)
DEFAULT_PORTS = {
    DB_MYSQL: 3306,
    DB_POSTGRESQL: 5432,
}


@dataclass(frozen=True, slots=True)
class DatabaseProfile:
    connection_id: str
    name: str
    db_type: str
    host: str
    port: int
    database: str
    user: str

    @property
    def target_label(self) -> str:
        return (
            f"{self.db_type} · {self.user}@{self.host}:{self.port}"
            f"/{self.database}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.connection_id,
            "name": self.name,
            "type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatabaseProfile":
        db_type = str(payload.get("type") or DB_MYSQL).strip().lower()
        if db_type not in SUPPORTED_DATABASES:
            db_type = DB_MYSQL
        default_port = DEFAULT_PORTS[db_type]
        try:
            port = int(payload.get("port") or default_port)
        except (TypeError, ValueError):
            port = default_port

        return cls(
            connection_id=str(payload.get("id") or "").strip(),
            name=str(payload.get("name") or "Database").strip(),
            db_type=db_type,
            host=str(payload.get("host") or "localhost").strip(),
            port=port,
            database=str(payload.get("database") or "").strip(),
            user=str(payload.get("user") or "").strip(),
        )


@dataclass(frozen=True, slots=True)
class TableInfo:
    schema: str
    name: str
    kind: str = "TABLE"


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    default: str | None = None
    key: str = ""


@dataclass(frozen=True, slots=True)
class PageResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    has_next: bool


@dataclass(frozen=True, slots=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    truncated: bool
