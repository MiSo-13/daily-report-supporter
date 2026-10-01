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


def test_recent_tables_are_persisted_and_deduplicated(tmp_path) -> None:
    path = tmp_path / "database-connections.json"
    store = DatabaseStore(path)
    profile = store.create(
        name="DEV",
        db_type=DB_MYSQL,
        host="localhost",
        port=3306,
        database="app",
        user="viewer",
    )

    store.touch_recent_table(profile.connection_id, "app", "users")
    store.touch_recent_table(profile.connection_id, "app", "orders")
    store.touch_recent_table(profile.connection_id, "app", "users")

    reloaded = DatabaseStore(path)
    recent = reloaded.list_recent_tables(profile.connection_id)

    assert [(item.schema, item.name) for item in recent] == [
        ("app", "users"),
        ("app", "orders"),
    ]


def test_recent_tables_keep_only_latest_ten(tmp_path) -> None:
    store = DatabaseStore(tmp_path / "database-connections.json")
    profile = store.create(
        name="DEV",
        db_type=DB_MYSQL,
        host="localhost",
        port=3306,
        database="app",
        user="viewer",
    )

    for index in range(12):
        store.touch_recent_table(
            profile.connection_id,
            "app",
            f"table_{index}",
        )

    recent = store.list_recent_tables(profile.connection_id)

    assert len(recent) == 10
    assert recent[0].name == "table_11"
    assert recent[-1].name == "table_2"


def test_deleting_profile_removes_recent_tables(tmp_path) -> None:
    store = DatabaseStore(tmp_path / "database-connections.json")
    profile = store.create(
        name="DEV",
        db_type=DB_MYSQL,
        host="localhost",
        port=3306,
        database="app",
        user="viewer",
    )
    store.touch_recent_table(profile.connection_id, "app", "users")

    store.delete(profile.connection_id)

    assert store.list_recent_tables(profile.connection_id) == []
