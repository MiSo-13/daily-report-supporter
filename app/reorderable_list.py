from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import QAbstractItemView, QListWidget


class ReorderableListWidget(QListWidget):
    order_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.set_reordering_enabled(True)

    def set_reordering_enabled(self, enabled: bool) -> None:
        mode = (
            QAbstractItemView.DragDropMode.InternalMove
            if enabled
            else QAbstractItemView.DragDropMode.NoDragDrop
        )
        self.setDragDropMode(mode)
        self.setDragEnabled(enabled)
        self.setAcceptDrops(enabled)
        self.viewport().setAcceptDrops(enabled)
        self.setDropIndicatorShown(enabled)
        if enabled:
            self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def dropEvent(self, event: QDropEvent) -> None:
        super().dropEvent(event)
        if event.isAccepted():
            self.order_changed.emit()
