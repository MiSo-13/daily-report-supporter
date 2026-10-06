from __future__ import annotations

from dataclasses import dataclass
import json


MAX_DETAIL_CHARS = 2_000_000
MAX_DETAIL_BINARY_BYTES = 512_000


@dataclass(frozen=True, slots=True)
class DatabaseDetailText:
    text: str
    truncated: bool
    size_label: str
    format_label: str


def format_database_detail_value(
    value: object,
    data_type: str = "",
) -> DatabaseDetailText:
    normalized_type = data_type.strip().lower()

    if value is None:
        return DatabaseDetailText(
            text="NULL",
            truncated=False,
            size_label="NULL",
            format_label="NULL",
        )

    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        visible = raw[:MAX_DETAIL_BINARY_BYTES]
        truncated = len(raw) > len(visible)
        return DatabaseDetailText(
            text="0x" + visible.hex(),
            truncated=truncated,
            size_label=f"{len(raw):,} bytes",
            format_label="Binary",
        )

    if isinstance(value, (dict, list)):
        text, truncated = _stream_json(value)
        return DatabaseDetailText(
            text=text,
            truncated=truncated,
            size_label=(
                f"{len(text):,}+자"
                if truncated
                else f"{len(text):,}자"
            ),
            format_label="JSON",
        )

    text = str(value)
    original_length = len(text)

    if "json" in normalized_type and original_length <= MAX_DETAIL_CHARS:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        else:
            pretty, truncated = _stream_json(parsed)
            return DatabaseDetailText(
                text=pretty,
                truncated=truncated,
                size_label=f"{original_length:,}자",
                format_label="JSON",
            )

    truncated = original_length > MAX_DETAIL_CHARS
    visible = text[:MAX_DETAIL_CHARS]
    return DatabaseDetailText(
        text=visible,
        truncated=truncated,
        size_label=f"{original_length:,}자",
        format_label="Text",
    )


def _stream_json(value: object) -> tuple[str, bool]:
    encoder = json.JSONEncoder(
        ensure_ascii=False,
        indent=2,
        default=str,
    )
    chunks: list[str] = []
    used = 0

    try:
        for chunk in encoder.iterencode(value):
            remaining = MAX_DETAIL_CHARS - used
            if remaining <= 0:
                return "".join(chunks), True
            if len(chunk) > remaining:
                chunks.append(chunk[:remaining])
                return "".join(chunks), True
            chunks.append(chunk)
            used += len(chunk)
    except (TypeError, ValueError, RecursionError):
        text = str(value)
        return text[:MAX_DETAIL_CHARS], len(text) > MAX_DETAIL_CHARS

    return "".join(chunks), False
