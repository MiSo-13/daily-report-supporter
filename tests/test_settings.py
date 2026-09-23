import json

from app.settings import AppSettings, DEFAULT_GREETING, DEFAULT_THEME


def test_settings_are_saved_under_reports(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.theme = "Nord"
    settings.greeting = "안녕하세요. 테스트입니다."

    config_path = tmp_path / "settings.json"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": "Nord",
        "greeting": "안녕하세요. 테스트입니다.",
    }

    reloaded = AppSettings(tmp_path)
    assert reloaded.theme == "Nord"
    assert reloaded.greeting == "안녕하세요. 테스트입니다."


def test_missing_settings_are_created_with_defaults(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    config_path = tmp_path / "settings.json"

    assert config_path.exists()
    assert settings.theme == DEFAULT_THEME
    assert settings.greeting == DEFAULT_GREETING

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "greeting": DEFAULT_GREETING,
    }


def test_corrupt_settings_fall_back_to_defaults(tmp_path) -> None:
    (tmp_path / "settings.json").write_text("{broken", encoding="utf-8")
    settings = AppSettings(tmp_path)
    assert settings.theme == DEFAULT_THEME
    assert settings.greeting == DEFAULT_GREETING

    payload = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "greeting": DEFAULT_GREETING,
    }
