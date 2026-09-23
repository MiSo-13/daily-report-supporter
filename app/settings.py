from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_GREETING = "안녕하세요.\n금일 업무 진행사항 공유드립니다."
DEFAULT_THEME = "Light"
SETTINGS_FILE_NAME = "settings.json"


class AppSettings:
    def __init__(self, reports_root: Path | str = "reports") -> None:
        self.path = Path(reports_root) / SETTINGS_FILE_NAME
        self._data, needs_write = self._load()

        # 앱을 처음 실행한 경우에도 reports/settings.json이 즉시 보이도록
        # 기본값을 바로 파일로 생성한다. 손상된 설정 파일도 기본값으로 복구한다.
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
        }

        # 키가 빠진 구버전 파일도 정규화해서 다시 저장한다.
        needs_write = set(payload) != {"theme", "greeting"}
        return data, needs_write

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(self.path)
