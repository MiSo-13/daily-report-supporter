from app.themes import THEMES, stylesheet_for, theme_names


def test_builtin_themes_are_available() -> None:
    assert theme_names() == [
        "Light",
        "Dark",
        "Nord",
        "Solarized Light",
        "Solarized Dark",
        "Sepia",
    ]
    assert all(THEMES[name].stylesheet.strip() for name in theme_names())


def test_unknown_theme_falls_back_to_light() -> None:
    assert stylesheet_for("not-a-theme") == stylesheet_for("Light")
