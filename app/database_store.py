from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.database_models import (
    DB_MYSQL,
    DEFAULT_PORTS,
    DatabaseProfile,
    SUPPORTED_DATABASES,
)


class DatabaseStore:
    VERSION = 1

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._profiles = self._load()

    def list_profiles(self) -> list[DatabaseProfile]:
        return list(self._profiles)

    def get(self, connection_id: str) -> DatabaseProfile:
        for profile in self._profiles:
            if profile.connection_id == connection_id:
                return profile
        raise KeyError(connection_id)

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
                self._profiles[index] = updated
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

    def _load(self) -> list[DatabaseProfile]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        raw_profiles = payload.get("connections", [])
        if not isinstance(raw_profiles, list):
            return []

        profiles: list[DatabaseProfile] = []
        for item in raw_profiles:
            if not isinstance(item, dict):
                continue
            profile = DatabaseProfile.from_dict(item)
            if profile.connection_id:
                profiles.append(profile)
        return profiles

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.VERSION,
            "connections": [
                profile.to_dict()
                for profile in self._profiles
            ],
        }
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
