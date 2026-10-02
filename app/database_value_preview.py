from __future__ import annotations

from dataclasses import dataclass
import json
from collections.abc import Iterable


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


def compact_database_value(value: object) -> object:
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
        preview = _structured_preview(value)
        if preview is not None:
            return preview

    return value


def compact_database_rows(
    rows: Iterable[Iterable[object]],
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        tuple(compact_database_value(value) for value in row)
        for row in rows
    )


def render_database_value(value: object, limit: int) -> str:
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
