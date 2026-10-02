from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.database_value_preview import (
    MAX_DISPLAY_CHARS,
    MAX_STORED_TEXT_CHARS,
    MAX_TOOLTIP_CHARS,
    DatabaseValuePreview,
    compact_database_value,
    render_database_value,
)


class DatabaseTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._headers: list[str] = []
        self._rows: list[tuple[object, ...]] = []
        self._truncated_value_count = 0

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
            return render_database_value(value, MAX_DISPLAY_CHARS)
        if role == Qt.ItemDataRole.ToolTipRole:
            return render_database_value(value, MAX_TOOLTIP_CHARS)
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

        def sort_key(row: tuple[object, ...]) -> tuple[bool, str]:
            value = row[column]
            return value is None, self.display_value(value).casefold()

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
        normalized_rows: list[tuple[object, ...]] = []
        truncated_count = 0

        for row in rows:
            normalized: list[object] = []
            for value in row:
                compact = compact_database_value(value)
                if isinstance(compact, DatabaseValuePreview):
                    truncated_count += 1
                normalized.append(compact)
            normalized_rows.append(tuple(normalized))

        self.beginResetModel()
        self._headers = [str(header) for header in headers]
        self._rows = normalized_rows
        self._truncated_value_count = truncated_count
        self.endResetModel()

    def clear(self) -> None:
        self.set_result([], [])

    def headers(self) -> list[str]:
        return list(self._headers)

    def rows(self) -> list[list[object]]:
        return [list(row) for row in self._rows]

    @property
    def truncated_value_count(self) -> int:
        return self._truncated_value_count

    def header_name(self, column: int) -> str | None:
        if 0 <= column < len(self._headers):
            return self._headers[column]
        return None

    def raw_value(self, row: int, column: int) -> object | None:
        if not 0 <= row < len(self._rows):
            return None
        if not 0 <= column < len(self._headers):
            return None
        return self._rows[row][column]

    @staticmethod
    def is_preview_value(value: object) -> bool:
        return isinstance(value, DatabaseValuePreview)

    @staticmethod
    def display_value(value: object) -> str:
        return render_database_value(value, MAX_STORED_TEXT_CHARS)
