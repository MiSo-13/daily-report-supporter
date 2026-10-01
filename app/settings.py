from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEGACY_DEFAULT_GREETING = "안녕하세요.\n금일 업무 진행사항 공유드립니다."
DEFAULT_GREETING = (
    "안녕하세요.\n"
    "금일 업무 진행사항 공유드립니다.\n\n"
    "YYYY년 MM월 DD일 일일보고입니다."
)
DEFAULT_FOOTER = ""
DEFAULT_THEME = "Light"
DEFAULT_FONT_FAMILY = ""
DEFAULT_FONT_SIZE = 10
DEFAULT_TERMINAL_FONT_FAMILY = ""
DEFAULT_TERMINAL_FONT_SIZE = 10
DEFAULT_SHOW_RESOURCE_USAGE = True
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 32
DEFAULT_PREVIOUS_SECTION_TITLE = "어제 했던 일"
LEGACY_DEFAULT_TODAY_SECTION_TITLE = "오늘 해야 할 일"
DEFAULT_TODAY_SECTION_TITLE = "오늘 업무"
DEFAULT_PROGRESS_REPORT_TITLE = "진행 업무"
DEFAULT_PLANNED_REPORT_TITLE = "예정 업무"
INPUT_METHOD_SYSTEM = "system"
INPUT_METHOD_CROSTINI_IBUS = "crostini_ibus"
DEFAULT_INPUT_METHOD_MODE = INPUT_METHOD_SYSTEM
SETTINGS_FILE_NAME = "settings.json"


class AppSettings:
    def __init__(self, config_root: Path | str = "config") -> None:
        self.path = Path(config_root) / SETTINGS_FILE_NAME
        self._data, needs_write = self._load()

        if needs_write:
            self._save()

    @property
    def greeting(self) -> str:
        value = self._data.get("greeting")
        return value if isinstance(value, str) else DEFAULT_GREETING

    @greeting.setter
    def greeting(self, value: str) -> None:
        self._data["greeting"] = value
        self._save()

    @property
    def footer(self) -> str:
        value = self._data.get("footer")
        return value if isinstance(value, str) else DEFAULT_FOOTER

    @footer.setter
    def footer(self, value: str) -> None:
        self._data["footer"] = value
        self._save()

    @property
    def progress_report_title(self) -> str:
        value = self._data.get("progress_report_title")
        return (
            value
            if isinstance(value, str) and value.strip()
            else DEFAULT_PROGRESS_REPORT_TITLE
        )

    @progress_report_title.setter
    def progress_report_title(self, value: str) -> None:
        self._data["progress_report_title"] = (
            value.strip() or DEFAULT_PROGRESS_REPORT_TITLE
        )
        self._save()

    @property
    def planned_report_title(self) -> str:
        value = self._data.get("planned_report_title")
        return (
            value
            if isinstance(value, str) and value.strip()
            else DEFAULT_PLANNED_REPORT_TITLE
        )

    @planned_report_title.setter
    def planned_report_title(self, value: str) -> None:
        self._data["planned_report_title"] = (
            value.strip() or DEFAULT_PLANNED_REPORT_TITLE
        )
        self._save()

    @property
    def previous_section_title(self) -> str:
        value = self._data.get("previous_section_title")
        return (
            value
            if isinstance(value, str) and value.strip()
            else DEFAULT_PREVIOUS_SECTION_TITLE
        )

    @previous_section_title.setter
    def previous_section_title(self, value: str) -> None:
        self._data["previous_section_title"] = (
            value.strip() or DEFAULT_PREVIOUS_SECTION_TITLE
        )
        self._save()

    @property
    def today_section_title(self) -> str:
        value = self._data.get("today_section_title")
        return (
            value
            if isinstance(value, str) and value.strip()
            else DEFAULT_TODAY_SECTION_TITLE
        )

    @today_section_title.setter
    def today_section_title(self, value: str) -> None:
        self._data["today_section_title"] = (
            value.strip() or DEFAULT_TODAY_SECTION_TITLE
        )
        self._save()

    @property
    def input_method_mode(self) -> str:
        value = self._data.get("input_method_mode")
        if value in {INPUT_METHOD_SYSTEM, INPUT_METHOD_CROSTINI_IBUS}:
            return str(value)
        return DEFAULT_INPUT_METHOD_MODE

    @input_method_mode.setter
    def input_method_mode(self, value: str) -> None:
        self._data["input_method_mode"] = (
            value
            if value in {INPUT_METHOD_SYSTEM, INPUT_METHOD_CROSTINI_IBUS}
            else DEFAULT_INPUT_METHOD_MODE
        )
        self._save()

    @property
    def font_family(self) -> str:
        value = self._data.get("font_family")
        return value.strip() if isinstance(value, str) else DEFAULT_FONT_FAMILY

    @font_family.setter
    def font_family(self, value: str) -> None:
        self._data["font_family"] = value.strip()
        self._save()

    @property
    def font_size(self) -> int:
        return self._font_size_value("font_size", DEFAULT_FONT_SIZE)

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._data["font_size"] = self._clean_font_size(
            value,
            DEFAULT_FONT_SIZE,
        )
        self._save()

    @property
    def terminal_font_family(self) -> str:
        value = self._data.get("terminal_font_family")
        return (
            value.strip()
            if isinstance(value, str)
            else DEFAULT_TERMINAL_FONT_FAMILY
        )

    @terminal_font_family.setter
    def terminal_font_family(self, value: str) -> None:
        self._data["terminal_font_family"] = value.strip()
        self._save()

    @property
    def terminal_font_size(self) -> int:
        return self._font_size_value(
            "terminal_font_size",
            DEFAULT_TERMINAL_FONT_SIZE,
        )

    @terminal_font_size.setter
    def terminal_font_size(self, value: int) -> None:
        self._data["terminal_font_size"] = self._clean_font_size(
            value,
            DEFAULT_TERMINAL_FONT_SIZE,
        )
        self._save()

    def set_font_settings(
        self,
        *,
        font_family: str,
        font_size: int,
        terminal_font_family: str,
        terminal_font_size: int,
    ) -> None:
        self._data["font_family"] = font_family.strip()
        self._data["font_size"] = self._clean_font_size(
            font_size,
            DEFAULT_FONT_SIZE,
        )
        self._data["terminal_font_family"] = terminal_font_family.strip()
        self._data["terminal_font_size"] = self._clean_font_size(
            terminal_font_size,
            DEFAULT_TERMINAL_FONT_SIZE,
        )
        self._save()

    @property
    def show_resource_usage(self) -> bool:
        value = self._data.get("show_resource_usage")
        return (
            value
            if isinstance(value, bool)
            else DEFAULT_SHOW_RESOURCE_USAGE
        )

    @show_resource_usage.setter
    def show_resource_usage(self, value: bool) -> None:
        self._data["show_resource_usage"] = bool(value)
        self._save()

    @property
    def theme(self) -> str:
        value = self._data.get("theme")
        return value if isinstance(value, str) and value.strip() else DEFAULT_THEME

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value.strip() or DEFAULT_THEME
        self._save()

    def _load(self) -> tuple[dict[str, Any], bool]:
        defaults: dict[str, Any] = {
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

        if not self.path.exists():
            return defaults, True

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults, True

        if not isinstance(payload, dict):
            return defaults, True

        migrated_progress_title = DEFAULT_PROGRESS_REPORT_TITLE
        legacy_today_title = payload.get("today_section_title")
        if (
            "progress_report_title" not in payload
            and isinstance(legacy_today_title, str)
            and legacy_today_title.strip()
            and legacy_today_title
            not in {DEFAULT_TODAY_SECTION_TITLE, LEGACY_DEFAULT_TODAY_SECTION_TITLE}
        ):
            migrated_progress_title = legacy_today_title.strip()

        data = {
            "theme": payload.get("theme", DEFAULT_THEME),
            "font_family": (
                payload.get("font_family", DEFAULT_FONT_FAMILY)
                if isinstance(
                    payload.get("font_family", DEFAULT_FONT_FAMILY),
                    str,
                )
                else DEFAULT_FONT_FAMILY
            ),
            "font_size": self._clean_font_size(
                payload.get("font_size"),
                DEFAULT_FONT_SIZE,
            ),
            "terminal_font_family": (
                payload.get(
                    "terminal_font_family",
                    DEFAULT_TERMINAL_FONT_FAMILY,
                )
                if isinstance(
                    payload.get(
                        "terminal_font_family",
                        DEFAULT_TERMINAL_FONT_FAMILY,
                    ),
                    str,
                )
                else DEFAULT_TERMINAL_FONT_FAMILY
            ),
            "terminal_font_size": self._clean_font_size(
                payload.get("terminal_font_size"),
                DEFAULT_TERMINAL_FONT_SIZE,
            ),
            "show_resource_usage": (
                payload.get(
                    "show_resource_usage",
                    DEFAULT_SHOW_RESOURCE_USAGE,
                )
                if isinstance(
                    payload.get(
                        "show_resource_usage",
                        DEFAULT_SHOW_RESOURCE_USAGE,
                    ),
                    bool,
                )
                else DEFAULT_SHOW_RESOURCE_USAGE
            ),
            "greeting": payload.get("greeting", DEFAULT_GREETING),
            "footer": payload.get("footer", DEFAULT_FOOTER),
            "previous_section_title": payload.get(
                "previous_section_title",
                DEFAULT_PREVIOUS_SECTION_TITLE,
            ),
            "today_section_title": payload.get(
                "today_section_title",
                DEFAULT_TODAY_SECTION_TITLE,
            ),
            "progress_report_title": payload.get(
                "progress_report_title",
                migrated_progress_title,
            ),
            "planned_report_title": payload.get(
                "planned_report_title",
                DEFAULT_PLANNED_REPORT_TITLE,
            ),
            "input_method_mode": payload.get(
                "input_method_mode",
                DEFAULT_INPUT_METHOD_MODE,
            ),
        }

        needs_write = set(payload) != set(defaults)

        for key in (
            "font_family",
            "font_size",
            "terminal_font_family",
            "terminal_font_size",
            "show_resource_usage",
        ):
            if payload.get(key, defaults[key]) != data[key]:
                needs_write = True

        if data["greeting"] == LEGACY_DEFAULT_GREETING:
            data["greeting"] = DEFAULT_GREETING
            needs_write = True

        if data["today_section_title"] == LEGACY_DEFAULT_TODAY_SECTION_TITLE:
            data["today_section_title"] = DEFAULT_TODAY_SECTION_TITLE
            needs_write = True

        return data, needs_write

    def _font_size_value(self, key: str, default: int) -> int:
        return self._clean_font_size(self._data.get(key), default)

    @staticmethod
    def _clean_font_size(value: object, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        if MIN_FONT_SIZE <= value <= MAX_FONT_SIZE:
            return value
        return default

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(self.path)
