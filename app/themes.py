from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    description: str
    stylesheet: str


def _build_stylesheet(
    *,
    window: str,
    surface: str,
    surface_alt: str,
    text: str,
    muted: str,
    border: str,
    accent: str,
    accent_hover: str,
    selection: str,
) -> str:
    return f"""
QWidget {{
    background-color: {window};
    color: {text};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background-color: {window};
}}
QLabel {{
    background: transparent;
}}
QLineEdit, QTextEdit, QComboBox, QListWidget, QDateEdit {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {selection};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QListWidget:focus, QDateEdit:focus {{
    border: 1px solid {accent};
}}
QListWidget::item {{
    padding: 7px 5px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {selection};
    color: {text};
}}
QPushButton {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 7px 12px;
}}
QPushButton:hover {{
    border-color: {accent};
    background-color: {selection};
}}
QPushButton:pressed {{
    background-color: {selection};
}}
QPushButton#primaryButton {{
    background-color: {accent};
    color: white;
    border-color: {accent};
    font-weight: 600;
}}
QPushButton#primaryButton:hover {{
    background-color: {accent_hover};
}}
QPushButton#dangerButton:hover {{
    border-color: #d75f5f;
}}
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 6px;
    background-color: {window};
}}
QTabBar::tab {{
    background-color: {surface_alt};
    color: {muted};
    border: 1px solid {border};
    padding: 8px 14px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {surface};
    color: {text};
    border-bottom-color: {surface};
}}
QMenuBar, QMenu {{
    background-color: {surface};
    color: {text};
}}
QMenuBar::item:selected, QMenu::item:selected {{
    background-color: {selection};
}}
QStatusBar {{
    color: {muted};
}}
QSplitter::handle {{
    background-color: {border};
}}
QToolTip {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
}}
"""


THEMES: dict[str, Theme] = {
    "Light": Theme(
        "Light",
        "기본 라이트",
        _build_stylesheet(
            window="#f6f7f9",
            surface="#ffffff",
            surface_alt="#f0f2f5",
            text="#20242a",
            muted="#68707c",
            border="#d7dce2",
            accent="#4263eb",
            accent_hover="#3654d4",
            selection="#dce5ff",
        ),
    ),
    "Dark": Theme(
        "Dark",
        "일반 다크",
        _build_stylesheet(
            window="#1e1f22",
            surface="#2b2d30",
            surface_alt="#25272a",
            text="#e8eaed",
            muted="#a9adb4",
            border="#3f4248",
            accent="#4c8dff",
            accent_hover="#3978df",
            selection="#354b69",
        ),
    ),
    "Nord": Theme(
        "Nord",
        "청회색 기반의 차분한 다크 테마",
        _build_stylesheet(
            window="#2e3440",
            surface="#3b4252",
            surface_alt="#353c49",
            text="#eceff4",
            muted="#d8dee9",
            border="#4c566a",
            accent="#5e81ac",
            accent_hover="#4c6f98",
            selection="#434c5e",
        ),
    ),
    "Solarized Light": Theme(
        "Solarized Light",
        "낮은 대비의 따뜻한 라이트 테마",
        _build_stylesheet(
            window="#fdf6e3",
            surface="#fffaf0",
            surface_alt="#eee8d5",
            text="#586e75",
            muted="#657b83",
            border="#d8d1bd",
            accent="#268bd2",
            accent_hover="#1f78b6",
            selection="#d9ebee",
        ),
    ),
    "Solarized Dark": Theme(
        "Solarized Dark",
        "낮은 대비의 다크 테마",
        _build_stylesheet(
            window="#002b36",
            surface="#073642",
            surface_alt="#0a3d48",
            text="#eee8d5",
            muted="#93a1a1",
            border="#15515d",
            accent="#268bd2",
            accent_hover="#1f78b6",
            selection="#164a55",
        ),
    ),
    "Sepia": Theme(
        "Sepia",
        "장시간 읽기에 적합한 따뜻한 베이지 테마",
        _build_stylesheet(
            window="#f2eadc",
            surface="#fbf5e9",
            surface_alt="#e9dfcf",
            text="#453f36",
            muted="#756c60",
            border="#d4c7b5",
            accent="#8a6d3b",
            accent_hover="#735a31",
            selection="#e3d3b8",
        ),
    ),
}


def theme_names() -> list[str]:
    return list(THEMES)


def stylesheet_for(name: str) -> str:
    return THEMES.get(name, THEMES["Light"]).stylesheet
