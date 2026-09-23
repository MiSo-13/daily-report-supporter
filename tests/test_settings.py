import json

from app.settings import (
    AppSettings,
    DEFAULT_FOOTER,
    DEFAULT_GREETING,
    DEFAULT_PREVIOUS_SECTION_TITLE,
    DEFAULT_THEME,
    DEFAULT_TODAY_SECTION_TITLE,
)


def test_settings_are_saved_under_reports(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.theme = "Nord"
    settings.greeting = "YY.MM.DD 업무 공유드립니다."
    settings.footer = "감사합니다."
    settings.previous_section_title = "전일 업무"
    settings.today_section_title = "금일 업무"

    config_path = tmp_path / "settings.json"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": "Nord",
        "greeting": "YY.MM.DD 업무 공유드립니다.",
        "footer": "감사합니다.",
        "previous_section_title": "전일 업무",
        "today_section_title": "금일 업무",
    }

    reloaded = AppSettings(tmp_path)
    assert reloaded.theme == "Nord"
    assert reloaded.greeting == "YY.MM.DD 업무 공유드립니다."
    assert reloaded.footer == "감사합니다."
    assert reloaded.previous_section_title == "전일 업무"
    assert reloaded.today_section_title == "금일 업무"


def test_missing_settings_are_created_with_defaults(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    config_path = tmp_path / "settings.json"

    assert config_path.exists()
    assert settings.theme == DEFAULT_THEME
    assert settings.greeting == DEFAULT_GREETING
    assert settings.footer == DEFAULT_FOOTER
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "greeting": DEFAULT_GREETING,
        "footer": DEFAULT_FOOTER,
        "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
        "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
    }


def test_old_settings_are_migrated_with_new_fields(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "theme": "Dark",
                "greeting": "안녕하세요.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = AppSettings(tmp_path)

    assert settings.theme == "Dark"
    assert settings.greeting == "안녕하세요."
    assert settings.footer == ""
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["footer"] == ""
    assert payload["previous_section_title"] == DEFAULT_PREVIOUS_SECTION_TITLE
    assert payload["today_section_title"] == DEFAULT_TODAY_SECTION_TITLE


def test_blank_section_titles_use_defaults(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.previous_section_title = "   "
    settings.today_section_title = ""

    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE


def test_corrupt_settings_fall_back_to_defaults(tmp_path) -> None:
    (tmp_path / "settings.json").write_text("{broken", encoding="utf-8")
    settings = AppSettings(tmp_path)

    assert settings.theme == DEFAULT_THEME
    assert settings.greeting == DEFAULT_GREETING
    assert settings.footer == DEFAULT_FOOTER
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE

    payload = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "greeting": DEFAULT_GREETING,
        "footer": DEFAULT_FOOTER,
        "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
        "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
    }
