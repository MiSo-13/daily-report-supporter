from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QIcon, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


APP_ICON_RELATIVE_PATH = Path("assets") / "app-icon.svg"
APP_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def resource_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parent.parent


def app_icon_path() -> Path:
    return resource_root() / APP_ICON_RELATIVE_PATH


def _render_icon_image(size: int) -> QImage:
    renderer = QSvgRenderer(str(app_icon_path()))
    if not renderer.isValid():
        return QImage()

    image = QImage(
        size,
        size,
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(
        painter,
        QRectF(0.0, 0.0, float(size), float(size)),
    )
    painter.end()
    return image


def create_app_icon() -> QIcon:
    icon = QIcon()
    for size in APP_ICON_SIZES:
        image = _render_icon_image(size)
        if image.isNull():
            continue
        icon.addPixmap(QPixmap.fromImage(image))
    return icon


def render_app_icon_png(
    destination: Path | str,
    *,
    size: int = 1024,
) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)

    image = _render_icon_image(size)
    if image.isNull():
        raise RuntimeError(
            f"WorKing 앱 아이콘을 읽을 수 없습니다: {app_icon_path()}"
        )
    if not image.save(str(output), "PNG"):
        raise RuntimeError(
            f"WorKing 앱 아이콘 PNG 생성에 실패했습니다: {output}"
        )
    return output
