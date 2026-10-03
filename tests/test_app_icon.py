from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from app.app_icon import (
    app_icon_path,
    create_app_icon,
    render_app_icon_png,
)


_APP = QApplication.instance() or QApplication([])


def test_app_icon_source_exists() -> None:
    path = app_icon_path()

    assert path.exists()
    assert path.name == "app-icon.svg"
    assert path.read_text(encoding="utf-8").startswith("<svg")


def test_create_app_icon_returns_renderable_icon() -> None:
    icon = create_app_icon()

    assert not icon.isNull()
    pixmap = icon.pixmap(64, 64)
    assert not pixmap.isNull()

    image = pixmap.toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(32, 20).alpha() > 0


def test_render_app_icon_png(tmp_path) -> None:
    output = render_app_icon_png(
        tmp_path / "working-icon.png",
        size=256,
    )

    assert output.exists()
    image = QImage(str(output))
    assert not image.isNull()
    assert image.width() == 256
    assert image.height() == 256
    assert image.pixelColor(0, 0).alpha() == 0
