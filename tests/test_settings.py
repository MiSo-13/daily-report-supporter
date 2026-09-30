import json

from app.settings import (
    AppSettings,
    DEFAULT_FOOTER,
    DEFAULT_GREETING,
    DEFAULT_INPUT_METHOD_MODE,
    DEFAULT_WORKSPACE_TAB_ORDER,
    DEFAULT_PLANNED_REPORT_TITLE,
    DEFAULT_PREVIOUS_SECTION_TITLE,
    DEFAULT_PROGRESS_REPORT_TITLE,
    DEFAULT_THEME,
    DEFAULT_TODAY_SECTION_TITLE,
    INPUT_METHOD_CROSTINI_IBUS,
)


def test_settings_are_saved_under_reports(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    settings.theme = "Nord"
    settings.greeting = "YY.MM.DD 업무 공유드립니다."
    settings.footer = "감사합니다."
    settings.previous_section_title = "전일 업무"
    settings.today_section_title = "금일 업무"
    settings.progress_report_title = "진행한 일"
    settings.planned_report_title = "다음 할 일"
    settings.input_method_mode = INPUT_METHOD_CROSTINI_IBUS
    settings.workspace_tab_order = ["work", "terminal", "memo"]

    config_path = tmp_path / "settings.json"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": "Nord",
        "greeting": "YY.MM.DD 업무 공유드립니다.",
        "footer": "감사합니다.",
        "previous_section_title": "전일 업무",
        "today_section_title": "금일 업무",
        "progress_report_title": "진행한 일",
        "planned_report_title": "다음 할 일",
        "input_method_mode": INPUT_METHOD_CROSTINI_IBUS,
        "workspace_tab_order": ["work", "terminal", "memo"],
    }

    reloaded = AppSettings(tmp_path)
    assert reloaded.theme == "Nord"
    assert reloaded.greeting == "YY.MM.DD 업무 공유드립니다."
    assert reloaded.footer == "감사합니다."
    assert reloaded.previous_section_title == "전일 업무"
    assert reloaded.today_section_title == "금일 업무"
    assert reloaded.progress_report_title == "진행한 일"
    assert reloaded.planned_report_title == "다음 할 일"
    assert reloaded.input_method_mode == INPUT_METHOD_CROSTINI_IBUS
    assert reloaded.workspace_tab_order == ["work", "terminal", "memo"]


def test_missing_settings_are_created_with_defaults(tmp_path) -> None:
    settings = AppSettings(tmp_path)
    config_path = tmp_path / "settings.json"

    assert config_path.exists()
    assert settings.theme == DEFAULT_THEME
    assert settings.greeting == DEFAULT_GREETING
    assert settings.footer == DEFAULT_FOOTER
    assert settings.previous_section_title == DEFAULT_PREVIOUS_SECTION_TITLE
    assert settings.today_section_title == DEFAULT_TODAY_SECTION_TITLE
    assert settings.progress_report_title == DEFAULT_PROGRESS_REPORT_TITLE
    assert settings.planned_report_title == DEFAULT_PLANNED_REPORT_TITLE
    assert settings.input_method_mode == DEFAULT_INPUT_METHOD_MODE
    assert settings.workspace_tab_order == DEFAULT_WORKSPACE_TAB_ORDER

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "theme": DEFAULT_THEME,
        "greeting": DEFAULT_GREETING,
        "footer": DEFAULT_FOOTER,
        "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
        "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
        "progress_report_title": DEFAULT_PROGRESS_REPORT_TITLE,
        "planned_report_title": DEFAULT_PLANNED_REPORT_TITLE,
        "input_method_mode": DEFAULT_INPUT_METHOD_MODE,
        "workspace_tab_order": DEFAULT_WORKSPACE_TAB_ORDER,
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
    assert settings.input_method_mode == DEFAULT_INPUT_METHOD_MODE

    payload = json.loads(config_path.read_text(encoding="utf-8"))
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



def test_workspace_tab_order_is_persisted(tmp_path) -> None:
    settings = AppSettings(tmp_path)

    settings.workspace_tab_order = ["terminal", "work", "memo"]

    assert AppSettings(tmp_path).workspace_tab_order == [
        "terminal",
        "work",
        "memo",
    ]


def test_invalid_workspace_tab_order_uses_default(tmp_path) -> None:
    settings = AppSettings(tmp_path)

    settings.workspace_tab_order = ["terminal", "memo"]

    assert settings.workspace_tab_order == DEFAULT_WORKSPACE_TAB_ORDER
