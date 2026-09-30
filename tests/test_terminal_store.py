from app.terminal_store import TerminalStore


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
