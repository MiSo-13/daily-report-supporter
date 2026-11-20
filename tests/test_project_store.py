import json

import pytest

from app.project_store import ProjectStore


def test_projects_are_saved_and_reloaded_under_config(tmp_path):
    store = ProjectStore(tmp_path / "config")
    assert store.list_projects() == []
    assert not store.path.exists()

    created = store.create(" WorKing ", "데스크톱 앱")
    assert created.name == "WorKing"
    assert created.id
    assert store.path == tmp_path / "config" / "projects.json"

    loaded = ProjectStore(tmp_path / "config").get(created.id)
    assert loaded == created
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["projects"][0]["id"] == created.id


def test_project_rename_and_archive_preserve_identity(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.create("기존 이름")
    updated = store.update(project.id, name=" 새 이름 ", description="기획")
    assert updated.id == project.id
    assert updated.name == "새 이름"
    assert updated.description == "기획"

    archived = store.archive(project.id)
    assert archived.archived
    assert store.list_projects() == []
    assert store.list_projects(include_archived=True) == [archived]
    assert store.update(project.id, archived=False).archived is False


def test_invalid_project_changes_are_not_written(tmp_path):
    store = ProjectStore(tmp_path)
    with pytest.raises(ValueError):
        store.create("  ")
    assert not store.path.exists()

    project = store.create("원본")
    with pytest.raises(ValueError):
        store.update(project.id, name=" ")
    with pytest.raises(KeyError):
        store.archive("missing")
    assert store.get(project.id) == project


def test_corrupted_projects_file_is_not_silently_overwritten(tmp_path):
    store = ProjectStore(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        store.create("새 프로젝트")
    assert store.path.read_text(encoding="utf-8") == "{invalid json"


def test_duplicate_project_ids_are_rejected(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.create("첫 프로젝트")
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    payload["projects"].append(dict(payload["projects"][0]))
    store.path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        store.list_projects(include_archived=True)
