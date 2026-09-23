from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_GREETING = "안녕하세요.\n금일 업무 진행사항 공유드립니다."
DEFAULT_FOOTER = ""
DEFAULT_THEME = "Light"
DEFAULT_PREVIOUS_SECTION_TITLE = "어제 했던 일"
DEFAULT_TODAY_SECTION_TITLE = "오늘 해야 할 일"
INPUT_METHOD_SYSTEM = "system"
INPUT_METHOD_CROSTINI_IBUS = "crostini_ibus"
DEFAULT_INPUT_METHOD_MODE = INPUT_METHOD_SYSTEM
SETTINGS_FILE_NAME = "settings.json"


class AppSettings:
    def __init__(self, reports_root: Path | str = "reports") -> None:
        self.path = Path(reports_root) / SETTINGS_FILE_NAME
        self._data, needs_write = self._load()

        if needs_write:
            self._save()

    @property
    def greeting(self) -> str:
        value = self._data.get("greeting")
        return value if isinstance(value, str) and value.strip() else DEFAULT_GREETING

    @greeting.setter
    def greeting(self, value: str) -> None:
        self._data["greeting"] = value.strip() or DEFAULT_GREETING
        self._save()

    @property
    def footer(self) -> str:
        value = self._data.get("footer")
        return value if isinstance(value, str) else DEFAULT_FOOTER

    @footer.setter
    def footer(self, value: str) -> None:
        self._data["footer"] = value.strip()
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
            "greeting": DEFAULT_GREETING,
            "footer": DEFAULT_FOOTER,
            "previous_section_title": DEFAULT_PREVIOUS_SECTION_TITLE,
            "today_section_title": DEFAULT_TODAY_SECTION_TITLE,
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

        data = {
            "theme": payload.get("theme", DEFAULT_THEME),
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
            "input_method_mode": payload.get(
                "input_method_mode",
                DEFAULT_INPUT_METHOD_MODE,
            ),
        }

        needs_write = set(payload) != set(defaults)
        return data, needs_write

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(self.path)
