from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.app_meta import APP_NAME, ORGANIZATION_NAME
from app.resource_monitor import ProcessResourceMonitor


class AppStatusInfo(QWidget):
    LEFT_MARGIN = 12
    VERTICAL_MARGIN = 2
    RIGHT_MARGIN = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.resource_label = QLabel("CPU --  ·  RAM --")
        self.resource_label.setObjectName("resourceMonitor")
        self.resource_label.setToolTip(
            f"{APP_NAME} 프로세스의 CPU / 메모리 사용량"
        )

        self.brand_label = QLabel(f"made by {ORGANIZATION_NAME}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            self.LEFT_MARGIN,
            self.VERTICAL_MARGIN,
            self.RIGHT_MARGIN,
            self.VERTICAL_MARGIN,
        )
        layout.setSpacing(8)
        layout.addWidget(self.resource_label)
        layout.addStretch(1)
        layout.addWidget(self.brand_label)

        self.resource_monitor = ProcessResourceMonitor(self)
        self.resource_monitor.updated.connect(self.resource_label.setText)

    def set_resource_visible(self, visible: bool) -> None:
        self.resource_label.setVisible(visible)
        if visible:
            self.resource_monitor.start()
        else:
            self.resource_monitor.stop()

    def shutdown(self) -> None:
        self.resource_monitor.stop()
