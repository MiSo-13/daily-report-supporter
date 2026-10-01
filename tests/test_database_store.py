from __future__ import annotations

import json

from app.database_models import DB_MYSQL, DB_POSTGRESQL
from app.database_store import DatabaseStore


def test_database_store_round_trip_without_password(tmp_path) -> None:
    path = tmp_path / "database-connections.json"
    store = DatabaseStore(path)

    created = store.create(
        name="DEV MySQL",
        db_type=DB_MYSQL,
        host="db.example.com",
        port=3306,
        database="app",
        user="viewer",
    )

    reloaded = DatabaseStore(path)
    profile = reloaded.get(created.connection_id)

    assert profile.name == "DEV MySQL"
    assert profile.db_type == DB_MYSQL
    assert profile.host == "db.example.com"
    assert profile.port == 3306
    assert profile.database == "app"
    assert profile.user == "viewer"

    raw = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(raw).lower()
    assert "password" not in serialized


def test_database_store_updates_and_deletes_profile(tmp_path) -> None:
    store = DatabaseStore(tmp_path / "database-connections.json")
    created = store.create(
        name="Local",
        db_type=DB_MYSQL,
        host="localhost",
        port=3306,
        database="old_db",
        user="root",
    )

    updated = store.update(
        created.connection_id,
        name="Postgres",
        db_type=DB_POSTGRESQL,
        host="postgres.internal",
        port=5432,
        database="new_db",
        user="readonly",
    )

    assert updated.connection_id == created.connection_id
    assert updated.db_type == DB_POSTGRESQL
    assert updated.database == "new_db"

    store.delete(created.connection_id)

    assert store.list_profiles() == []


def test_database_store_recovers_from_invalid_json(tmp_path) -> None:
    path = tmp_path / "database-connections.json"
    path.write_text("{invalid", encoding="utf-8")

    store = DatabaseStore(path)

    assert store.list_profiles() == []
