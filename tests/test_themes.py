from app.themes import THEMES, stylesheet_for, theme_names


def test_builtin_themes_are_available() -> None:
    assert theme_names() == [
        "Light",
        "Dark",
        "Purple",
        "Nord",
        "Solarized Light",
        "Solarized Dark",
        "Sepia",
    ]
    assert all(THEMES[name].stylesheet.strip() for name in theme_names())


def test_unknown_theme_falls_back_to_light() -> None:
    assert stylesheet_for("not-a-theme") == stylesheet_for("Light")


def test_table_view_uses_theme_colors_for_alternating_rows() -> None:
    for theme in THEMES.values():
        stylesheet = theme.stylesheet
        assert "QTableView {" in stylesheet
        assert "alternate-background-color:" in stylesheet
        assert "gridline-color:" in stylesheet
        assert "selection-color:" in stylesheet
        assert "QTableCornerButton::section" in stylesheet


def test_dark_theme_table_rows_do_not_fall_back_to_light_palette() -> None:
    stylesheet = stylesheet_for("Dark")

    assert "background-color: #2b2d30;" in stylesheet
    assert "alternate-background-color: #25272a;" in stylesheet
    assert "color: #e8eaed;" in stylesheet
