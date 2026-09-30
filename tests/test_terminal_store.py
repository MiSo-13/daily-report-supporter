import json

from app.terminal_store import TERMINAL_LOCAL, TERMINAL_SSH, TerminalStore


def test_terminal_profiles_persist(tmp_path) -> None:
    state_path = tmp_path / "terminal-sessions.json"
    store = TerminalStore(state_path)

    first = store.create("서버", tmp_path)
    second = store.create("프론트", tmp_path / "frontend")

    reloaded = TerminalStore(state_path)

    assert [item.name for item in reloaded.list_profiles()] == ["서버", "프론트"]
    assert reloaded.get(first.terminal_id).cwd == str(tmp_path)
    assert reloaded.get(second.terminal_id).cwd == str(tmp_path / "frontend")


def test_terminal_profile_can_be_renamed(tmp_path) -> None:
    store = TerminalStore(tmp_path / "terminal-sessions.json")
    profile = store.create("터미널 1", tmp_path)

    updated = store.rename(profile.terminal_id, "백엔드")

    assert updated.name == "백엔드"
    assert store.get(profile.terminal_id).name == "백엔드"


def test_terminal_profile_delete_is_persisted(tmp_path) -> None:
    state_path = tmp_path / "terminal-sessions.json"
    store = TerminalStore(state_path)
    profile = store.create("삭제 대상", tmp_path)

    store.delete(profile.terminal_id)

    assert TerminalStore(state_path).list_profiles() == []


def test_invalid_terminal_state_is_ignored(tmp_path) -> None:
    state_path = tmp_path / "terminal-sessions.json"
    state_path.write_text("{broken", encoding="utf-8")

    store = TerminalStore(state_path)

    assert store.list_profiles() == []


def test_blank_terminal_name_uses_default(tmp_path) -> None:
    store = TerminalStore(tmp_path / "terminal-sessions.json")

    profile = store.create("   ", tmp_path)

    assert profile.name == "터미널"



def test_ssh_profile_persists_without_password(tmp_path) -> None:
    state_path = tmp_path / "terminal-sessions.json"
    store = TerminalStore(state_path)

    profile = store.create_ssh(
        "운영 서버",
        "10.0.1.20",
        2222,
        "ubuntu",
        tmp_path,
    )

    reloaded = TerminalStore(state_path).get(profile.terminal_id)

    assert reloaded.kind == TERMINAL_SSH
    assert reloaded.host == "10.0.1.20"
    assert reloaded.port == 2222
    assert reloaded.user == "ubuntu"

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert "password" not in payload["sessions"][0]
    assert "passphrase" not in payload["sessions"][0]


def test_ssh_profile_can_be_updated(tmp_path) -> None:
    store = TerminalStore(tmp_path / "terminal-sessions.json")
    profile = store.create_ssh(
        "운영",
        "old.example.com",
        22,
        "ubuntu",
        tmp_path,
    )

    updated = store.update_ssh(
        profile.terminal_id,
        name="개발",
        host="dev.example.com",
        port=2200,
        user="deploy",
    )

    assert updated.name == "개발"
    assert updated.host == "dev.example.com"
    assert updated.port == 2200
    assert updated.user == "deploy"


def test_legacy_terminal_profile_defaults_to_local(tmp_path) -> None:
    state_path = tmp_path / "terminal-sessions.json"
    state_path.write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "terminal_id": "legacy",
                        "name": "기존 터미널",
                        "cwd": str(tmp_path),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profile = TerminalStore(state_path).get("legacy")

    assert profile.kind == TERMINAL_LOCAL
