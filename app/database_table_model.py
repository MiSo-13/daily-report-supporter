from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class DatabaseTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._headers: list[str] = []
        self._rows: list[list[object]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if not index.isValid():
            return None

        value = self._rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_value(value)
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._display_value(value)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
            return None
        return str(section + 1)

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:
        if not 0 <= column < len(self._headers):
            return

        self.layoutAboutToBeChanged.emit()

        def sort_key(row: list[object]) -> tuple[bool, str]:
            value = row[column]
            return value is None, self._display_value(value).casefold()

        self._rows.sort(
            key=sort_key,
            reverse=order == Qt.SortOrder.DescendingOrder,
        )
        self.layoutChanged.emit()

    def set_result(
        self,
        headers: list[str] | tuple[str, ...],
        rows: list[list[object]] | tuple[tuple[object, ...], ...],
    ) -> None:
        self.beginResetModel()
        self._headers = [str(header) for header in headers]
        self._rows = [list(row) for row in rows]
        self.endResetModel()

    def clear(self) -> None:
        self.set_result([], [])

    @staticmethod
    def _display_value(value: object) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            preview = value[:64].hex()
            suffix = "…" if len(value) > 64 else ""
            return f"0x{preview}{suffix}"
        if isinstance(value, memoryview):
            raw = bytes(value)
            preview = raw[:64].hex()
            suffix = "…" if len(raw) > 64 else ""
            return f"0x{preview}{suffix}"
        return str(value)
