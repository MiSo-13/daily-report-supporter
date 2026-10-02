from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.database_models import (
    DB_MYSQL,
    DEFAULT_PORTS,
    DatabaseProfile,
    SUPPORTED_DATABASES,
    TableInfo,
)


class DatabaseStore:
    VERSION = 3
    RECENT_LIMIT = 10

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        (
            self._profiles,
            self._recent_tables,
            self._sql_drafts,
        ) = self._load()

    def list_profiles(self) -> list[DatabaseProfile]:
        return list(self._profiles)

    def get(self, connection_id: str) -> DatabaseProfile:
        for profile in self._profiles:
            if profile.connection_id == connection_id:
                return profile
        raise KeyError(connection_id)

    def reorder(self, connection_ids: list[str]) -> None:
        existing = [
            profile.connection_id
            for profile in self._profiles
        ]
        if (
            len(connection_ids) != len(existing)
            or len(set(connection_ids)) != len(connection_ids)
            or set(connection_ids) != set(existing)
        ):
            raise ValueError(
                "DB 연결 순서에는 모든 연결이 한 번씩 포함되어야 합니다."
            )

        by_id = {
            profile.connection_id: profile
            for profile in self._profiles
        }
        self._profiles = [
            by_id[connection_id]
            for connection_id in connection_ids
        ]
        self._save()

    def get_sql_draft(self, connection_id: str) -> str | None:
        return self._sql_drafts.get(connection_id)

    def set_sql_draft(self, connection_id: str, sql: str) -> None:
        self.get(connection_id)
        self._sql_drafts[connection_id] = sql
        self._save()

    def list_recent_tables(self, connection_id: str) -> list[TableInfo]:
        return list(self._recent_tables.get(connection_id, []))

    def touch_recent_table(
        self,
        connection_id: str,
        schema: str,
        table: str,
        kind: str = "TABLE",
    ) -> None:
        recent = [
            item
            for item in self._recent_tables.get(connection_id, [])
            if not (item.schema == schema and item.name == table)
        ]
        recent.insert(0, TableInfo(schema=schema, name=table, kind=kind))
        self._recent_tables[connection_id] = recent[: self.RECENT_LIMIT]
        self._save()

    def create(
        self,
        *,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        user: str,
    ) -> DatabaseProfile:
        profile = self._build_profile(
            uuid4().hex,
            name=name,
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            user=user,
        )
        self._profiles.append(profile)
        self._save()
        return profile

    def update(
        self,
        connection_id: str,
        *,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        user: str,
    ) -> DatabaseProfile:
        updated = self._build_profile(
            connection_id,
            name=name,
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            user=user,
        )
        for index, profile in enumerate(self._profiles):
            if profile.connection_id == connection_id:
                target_changed = (
                    profile.db_type != updated.db_type
                    or profile.host != updated.host
                    or profile.port != updated.port
                    or profile.database != updated.database
                    or profile.user != updated.user
                )
                self._profiles[index] = updated
                if target_changed:
                    self._recent_tables.pop(connection_id, None)
                    self._sql_drafts.pop(connection_id, None)
                self._save()
                return updated
        raise KeyError(connection_id)

    def delete(self, connection_id: str) -> None:
        before = len(self._profiles)
        self._profiles = [
            profile
            for profile in self._profiles
            if profile.connection_id != connection_id
        ]
        if len(self._profiles) == before:
            raise KeyError(connection_id)
        self._recent_tables.pop(connection_id, None)
        self._sql_drafts.pop(connection_id, None)
        self._save()

    def _build_profile(
        self,
        connection_id: str,
        *,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        user: str,
    ) -> DatabaseProfile:
        normalized_type = db_type.strip().lower()
        if normalized_type not in SUPPORTED_DATABASES:
            normalized_type = DB_MYSQL

        normalized_name = name.strip() or "Database"
        normalized_host = host.strip() or "localhost"
        normalized_database = database.strip()
        normalized_user = user.strip()
        normalized_port = int(port or DEFAULT_PORTS[normalized_type])

        return DatabaseProfile(
            connection_id=connection_id,
            name=normalized_name,
            db_type=normalized_type,
            host=normalized_host,
            port=normalized_port,
            database=normalized_database,
            user=normalized_user,
        )

    def _load(
        self,
    ) -> tuple[
        list[DatabaseProfile],
        dict[str, list[TableInfo]],
        dict[str, str],
    ]:
        if not self.path.exists():
            return [], {}, {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return [], {}, {}

        raw_profiles = payload.get("connections", [])
        if not isinstance(raw_profiles, list):
            raw_profiles = []

        profiles: list[DatabaseProfile] = []
        for item in raw_profiles:
            if not isinstance(item, dict):
                continue
            profile = DatabaseProfile.from_dict(item)
            if profile.connection_id:
                profiles.append(profile)

        valid_ids = {
            profile.connection_id
            for profile in profiles
        }

        recent_tables: dict[str, list[TableInfo]] = {}
        raw_recent = payload.get("recent_tables", {})
        if isinstance(raw_recent, dict):
            for connection_id, raw_items in raw_recent.items():
                if (
                    connection_id not in valid_ids
                    or not isinstance(raw_items, list)
                ):
                    continue
                items: list[TableInfo] = []
                for raw_item in raw_items[: self.RECENT_LIMIT]:
                    if not isinstance(raw_item, dict):
                        continue
                    schema = str(raw_item.get("schema") or "").strip()
                    name = str(raw_item.get("name") or "").strip()
                    if not schema or not name:
                        continue
                    items.append(
                        TableInfo(
                            schema=schema,
                            name=name,
                            kind=str(raw_item.get("kind") or "TABLE"),
                        )
                    )
                if items:
                    recent_tables[str(connection_id)] = items

        sql_drafts: dict[str, str] = {}
        raw_drafts = payload.get("sql_drafts", {})
        if isinstance(raw_drafts, dict):
            for connection_id, sql in raw_drafts.items():
                if connection_id in valid_ids and isinstance(sql, str):
                    sql_drafts[str(connection_id)] = sql

        return profiles, recent_tables, sql_drafts

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.VERSION,
            "connections": [
                profile.to_dict()
                for profile in self._profiles
            ],
            "recent_tables": {
                connection_id: [
                    {
                        "schema": item.schema,
                        "name": item.name,
                        "kind": item.kind,
                    }
                    for item in items
                ]
                for connection_id, items in self._recent_tables.items()
                if items
            },
            "sql_drafts": dict(self._sql_drafts),
        }
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
