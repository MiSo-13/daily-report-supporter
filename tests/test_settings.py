import json

from app.settings import (
    AppSettings,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FOOTER,
    DEFAULT_GREETING,
    DEFAULT_INPUT_METHOD_MODE,
    DEFAULT_PLANNED_REPORT_TITLE,
    DEFAULT_PREVIOUS_SECTION_TITLE,
    DEFAULT_PROGRESS_REPORT_TITLE,
    DEFAULT_TERMINAL_FONT_FAMILY,
    DEFAULT_TERMINAL_FONT_SIZE,
    DEFAULT_SHOW_RESOURCE_USAGE,
    DEFAULT_THEME,
    DEFAULT_TODAY_SECTION_TITLE,
    INPUT_METHOD_CROSTINI_IBUS,
)


def test_settings_are_saved_under_config_directory(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.theme = "Nord"
    settings.greeting = "YY.MM.DD 업무 공유드립니다."
    settings.footer = "감사합니다."
    settings.previous_section_title = "전일 업무"
    settings.today_section_title = "금일 업무"
    settings.progress_report_title = "진행한 일"
    settings.planned_report_title = "다음 할 일"
    settings.input_method_mode = INPUT_METHOD_CROSTINI_IBUS
    settings.set_font_settings(
        font_family="Pretendard",
        font_size=12,
        terminal_font_family="D2Coding",
        terminal_font_size=11,
    )
    settings.show_resource_usage = False

    config_path = tmp_path / "settings.json"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": "Nord",
        "font_family": "Pretendard",
        "font_size": 12,
        "terminal_font_family": "D2Coding",
        "terminal_font_size": 11,
        "show_resource_usage": False,
        "greeting": "YY.MM.DD 업무 공유드립니다.",
        "footer": "감사합니다.",
        "previous_section_title": "전일 업무",
        "today_section_title": "금일 업무",
        "progress_report_title": "진행한 일",
        "planned_report_title": "다음 할 일",
        "input_method_mode": INPUT_METHOD_CROSTINI_IBUS,
    }

    reloaded = AppSettings(tmp_path)
    assert reloaded.theme == "Nord"
    assert reloaded.font_family == "Pretendard"
    assert reloaded.font_size == 12
    assert reloaded.terminal_font_family == "D2Coding"
    assert reloaded.terminal_font_size == 11
    assert reloaded.show_resource_usage is False
    assert reloaded.greeting == "YY.MM.DD 업무 공유드립니다."
    assert reloaded.footer == "감사합니다."
    assert reloaded.previous_section_title == "전일 업무"
    assert reloaded.today_section_title == "금일 업무"
    assert reloaded.progress_report_title == "진행한 일"
    assert reloaded.planned_report_title == "다음 할 일"
    assert reloaded.input_method_mode == INPUT_METHOD_CROSTINI_IBUS


def test_missing_settings_are_created_with_defaults(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    config_path = tmp_path / "settings.json"

    assert config_path.exists()
    assert settings.theme == DEFAULT_THEME
    assert settings.font_family == DEFAULT_FONT_FAMILY
    assert settings.font_size == DEFAULT_FONT_SIZE
    assert settings.terminal_font_family == DEFAULT_TERMINAL_FONT_FAMILY
    assert settings.terminal_font_size == DEFAULT_TERMINAL_FONT_SIZE
    assert settings.show_resource_usage is DEFAULT_SHOW_RESOURCE_USAGE
    assert settings.greeting == DEFAULT_GREETING
    assert settings.footer == DEFAULT_FOOTER
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE
    assert settings.progress_report_title == DEFAULT_PROGRESS_REPORT_TITLE
    assert settings.planned_report_title == DEFAULT_PLANNED_REPORT_TITLE
    assert settings.input_method_mode == DEFAULT_INPUT_METHOD_MODE

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE,
        "terminal_font_family": DEFAULT_TERMINAL_FONT_FAMILY,
        "terminal_font_size": DEFAULT_TERMINAL_FONT_SIZE,
        "show_resource_usage": DEFAULT_SHOW_RESOURCE_USAGE,
        "greeting": DEFAULT_GREETING,
        "footer": DEFAULT_FOOTER,
        "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
        "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
        "progress_report_title": DEFAULT_PROGRESS_REPORT_TITLE,
        "planned_report_title": DEFAULT_PLANNED_REPORT_TITLE,
        "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
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
    assert settings.font_family == DEFAULT_FONT_FAMILY
    assert settings.font_size == DEFAULT_FONT_SIZE
    assert settings.terminal_font_family == DEFAULT_TERMINAL_FONT_FAMILY
    assert settings.terminal_font_size == DEFAULT_TERMINAL_FONT_SIZE
    assert settings.show_resource_usage is DEFAULT_SHOW_RESOURCE_USAGE
    assert settings.greeting == "안녕하세요."
    assert settings.footer == ""
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE
    assert settings.input_method_mode == DEFAULT_INPUT_METHOD_MODE

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["font_family"] == DEFAULT_FONT_FAMILY
    assert payload["font_size"] == DEFAULT_FONT_SIZE
    assert payload["terminal_font_family"] == DEFAULT_TERMINAL_FONT_FAMILY
    assert payload["terminal_font_size"] == DEFAULT_TERMINAL_FONT_SIZE
    assert payload["show_resource_usage"] is DEFAULT_SHOW_RESOURCE_USAGE
    assert payload["footer"] == ""
    assert payload["previous_section_title"] == DEFAULT_PREVIOUS_SECTION_TITLE
    assert payload["today_section_title"] == DEFAULT_TODAY_SECTION_TITLE
    assert payload["progress_report_title"] == DEFAULT_PROGRESS_REPORT_TITLE
    assert payload["planned_report_title"] == DEFAULT_PLANNED_REPORT_TITLE
    assert payload["input_method_mode"] == DEFAULT_INPUT_METHOD_MODE


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
    assert settings.font_family == DEFAULT_FONT_FAMILY
    assert settings.font_size == DEFAULT_FONT_SIZE
    assert settings.terminal_font_family == DEFAULT_TERMINAL_FONT_FAMILY
    assert settings.terminal_font_size == DEFAULT_TERMINAL_FONT_SIZE
    assert settings.greeting == DEFAULT_GREETING
    assert settings.footer == DEFAULT_FOOTER
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE
    assert settings.progress_report_title == DEFAULT_PROGRESS_REPORT_TITLE
    assert settings.planned_report_title == DEFAULT_PLANNED_REPORT_TITLE
    assert settings.input_method_mode == DEFAULT_INPUT_METHOD_MODE

    payload = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE,
        "terminal_font_family": DEFAULT_TERMINAL_FONT_FAMILY,
        "terminal_font_size": DEFAULT_TERMINAL_FONT_SIZE,
        "show_resource_usage": DEFAULT_SHOW_RESOURCE_USAGE,
        "greeting": DEFAULT_GREETING,
        "footer": DEFAULT_FOOTER,
        "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
        "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
        "progress_report_title": DEFAULT_PROGRESS_REPORT_TITLE,
        "planned_report_title": DEFAULT_PLANNED_REPORT_TITLE,
        "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
    }


def test_invalid_input_method_mode_uses_system_default(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.input_method_mode = "unknown"

    assert settings.input_method_mode == DEFAULT_INPUT_METHOD_MODE


def test_legacy_default_greeting_is_migrated(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "theme": DEFAULT_THEME,
                "greeting": "안녕하세요.\n금일 업무 진행사항 공유드립니다.",
                "footer": DEFAULT_FOOTER,
                "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
                "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
                "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = AppSettings(tmp_path)

    assert settings.greeting == DEFAULT_GREETING
    assert "YYYY년 MM월 DD일 일일보고입니다." in settings.greeting


def test_custom_greeting_is_not_overwritten(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    custom = "직접 작성한 인사말"
    config_path.write_text(
        json.dumps(
            {
                "theme": DEFAULT_THEME,
                "greeting": custom,
                "footer": DEFAULT_FOOTER,
                "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
                "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
                "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = AppSettings(tmp_path)

    assert settings.greeting == custom


def test_legacy_today_section_title_is_migrated(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "theme": DEFAULT_THEME,
                "greeting": DEFAULT_GREETING,
                "footer": DEFAULT_FOOTER,
                "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
                "today_section_title": "오늘 해야 할 일",
                "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = AppSettings(tmp_path)

    assert settings.today_section_title == "오늘 업무"



def test_greeting_and_footer_preserve_line_breaks(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.greeting = "\n안녕하세요.\n\n업무 공유드립니다.\n"
    settings.footer = "\n감사합니다.\n\n"

    reloaded = AppSettings(tmp_path)

    assert reloaded.greeting == "\n안녕하세요.\n\n업무 공유드립니다.\n"
    assert reloaded.footer == "\n감사합니다.\n\n"


def test_custom_today_title_migrates_to_progress_report_title(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "theme": DEFAULT_THEME,
                "greeting": DEFAULT_GREETING,
                "footer": DEFAULT_FOOTER,
                "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
                "today_section_title": "금일 업무",
                "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = AppSettings(tmp_path)

    assert settings.progress_report_title == "금일 업무"
    assert settings.planned_report_title == DEFAULT_PLANNED_REPORT_TITLE



def test_font_settings_are_saved_together(tmp_path) -> None:
    settings = AppSettings(tmp_path)

    settings.set_font_settings(
        font_family="Inter",
        font_size=14,
        terminal_font_family="JetBrains Mono",
        terminal_font_size=12,
    )

    reloaded = AppSettings(tmp_path)
    assert reloaded.font_family == "Inter"
    assert reloaded.font_size == 14
    assert reloaded.terminal_font_family == "JetBrains Mono"
    assert reloaded.terminal_font_size == 12


def test_invalid_font_settings_fall_back_to_defaults(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    settings = AppSettings(tmp_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["font_family"] = 123
    payload["font_size"] = 99
    payload["terminal_font_family"] = ["bad"]
    payload["terminal_font_size"] = 2
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    reloaded = AppSettings(tmp_path)

    assert reloaded.font_family == DEFAULT_FONT_FAMILY
    assert reloaded.font_size == DEFAULT_FONT_SIZE
    assert reloaded.terminal_font_family == DEFAULT_TERMINAL_FONT_FAMILY
    assert reloaded.terminal_font_size == DEFAULT_TERMINAL_FONT_SIZE

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["font_family"] == DEFAULT_FONT_FAMILY
    assert saved["font_size"] == DEFAULT_FONT_SIZE
    assert saved["terminal_font_family"] == DEFAULT_TERMINAL_FONT_FAMILY
    assert saved["terminal_font_size"] == DEFAULT_TERMINAL_FONT_SIZE



def test_resource_monitor_visibility_is_persisted(tmp_path) -> None:
    settings = AppSettings(tmp_path)

    settings.show_resource_usage = False

    reloaded = AppSettings(tmp_path)
    assert reloaded.show_resource_usage is False


def test_invalid_resource_monitor_visibility_uses_default(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    settings = AppSettings(tmp_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["show_resource_usage"] = "yes"
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    reloaded = AppSettings(tmp_path)

    assert reloaded.show_resource_usage is DEFAULT_SHOW_RESOURCE_USAGE
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["show_resource_usage"] is DEFAULT_SHOW_RESOURCE_USAGE
