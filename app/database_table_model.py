from __future__ import annotations

from dataclasses import dataclass
import json

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


MAX_STORED_TEXT_CHARS = 4096
MAX_DISPLAY_CHARS = 512
MAX_TOOLTIP_CHARS = 2048
MAX_BINARY_BYTES = 64


@dataclass(frozen=True, slots=True)
class DatabaseValuePreview:
    text: str
    original_size: int | None
    kind: str = "text"

    @property
    def marker(self) -> str:
        if self.kind == "binary":
            if self.original_size is None:
                return "… [큰 바이너리 미리보기]"
            return f"… [원본 {self.original_size:,} bytes]"

        if self.original_size is None:
            return "… [큰 값 미리보기]"
        return f"… [원본 {self.original_size:,}자]"


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
            return self._render_value(value, MAX_DISPLAY_CHARS)
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._render_value(value, MAX_TOOLTIP_CHARS)
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
                compact = self._compact_value(value)
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
        return DatabaseTableModel._render_value(
            value,
            MAX_STORED_TEXT_CHARS,
        )

    @staticmethod
    def _compact_value(value: object) -> object:
        if isinstance(value, DatabaseValuePreview):
            return value

        if isinstance(value, str):
            if len(value) <= MAX_STORED_TEXT_CHARS:
                return value
            return DatabaseValuePreview(
                text=value[:MAX_STORED_TEXT_CHARS],
                original_size=len(value),
            )

        if isinstance(value, bytes):
            if len(value) <= MAX_BINARY_BYTES:
                return value
            return DatabaseValuePreview(
                text="0x" + value[:MAX_BINARY_BYTES].hex(),
                original_size=len(value),
                kind="binary",
            )

        if isinstance(value, bytearray):
            if len(value) <= MAX_BINARY_BYTES:
                return bytes(value)
            return DatabaseValuePreview(
                text="0x" + bytes(value[:MAX_BINARY_BYTES]).hex(),
                original_size=len(value),
                kind="binary",
            )

        if isinstance(value, memoryview):
            byte_view = value.cast("B")
            if byte_view.nbytes <= MAX_BINARY_BYTES:
                return byte_view.tobytes()
            return DatabaseValuePreview(
                text="0x" + byte_view[:MAX_BINARY_BYTES].tobytes().hex(),
                original_size=byte_view.nbytes,
                kind="binary",
            )

        if isinstance(value, (dict, list)):
            preview = DatabaseTableModel._structured_preview(value)
            if preview is not None:
                return preview

        return value

    @staticmethod
    def _structured_preview(value: object) -> DatabaseValuePreview | None:
        encoder = json.JSONEncoder(
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )
        chunks: list[str] = []
        total = 0

        try:
            for chunk in encoder.iterencode(value):
                remaining = MAX_STORED_TEXT_CHARS - total
                if remaining <= 0:
                    return DatabaseValuePreview(
                        text="".join(chunks),
                        original_size=None,
                        kind="structured",
                    )
                if len(chunk) > remaining:
                    chunks.append(chunk[:remaining])
                    return DatabaseValuePreview(
                        text="".join(chunks),
                        original_size=None,
                        kind="structured",
                    )
                chunks.append(chunk)
                total += len(chunk)
        except (TypeError, ValueError, RecursionError):
            return None

        return None

    @staticmethod
    def _render_value(value: object, limit: int) -> str:
        if value is None:
            return "NULL"

        if isinstance(value, DatabaseValuePreview):
            marker = value.marker
            available = max(0, limit - len(marker))
            return value.text[:available] + marker

        if isinstance(value, bytes):
            return "0x" + value[:MAX_BINARY_BYTES].hex()

        if isinstance(value, memoryview):
            byte_view = value.cast("B")
            return "0x" + byte_view[:MAX_BINARY_BYTES].tobytes().hex()

        if isinstance(value, bytearray):
            return "0x" + bytes(value[:MAX_BINARY_BYTES]).hex()

        text = str(value)
        if len(text) <= limit:
            return text
        marker = "…"
        return text[: max(0, limit - len(marker))] + marker
