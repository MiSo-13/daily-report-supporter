from __future__ import annotations

from PyQt6.QtCore import QSettings

DEFAULT_GREETING = "안녕하세요.\n금일 업무 진행사항 공유드립니다."
DEFAULT_THEME = "Light"


class AppSettings:
    def __init__(self) -> None:
        self._settings = QSettings("MiSo-13", "DailyReportSupporter")

    @property
    def greeting(self) -> str:
        value = self._settings.value("report/greeting", DEFAULT_GREETING, type=str)
        return value or DEFAULT_GREETING

    @greeting.setter
    def greeting(self, value: str) -> None:
        self._settings.setValue("report/greeting", value.strip() or DEFAULT_GREETING)

    @property
    def theme(self) -> str:
        value = self._settings.value("appearance/theme", DEFAULT_THEME, type=str)
        return value or DEFAULT_THEME

    @theme.setter
    def theme(self, value: str) -> None:
        self._settings.setValue("appearance/theme", value)
