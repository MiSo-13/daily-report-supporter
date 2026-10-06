from __future__ import annotations

from app.database_detail import (
    MAX_DETAIL_BINARY_BYTES,
    MAX_DETAIL_CHARS,
    format_database_detail_value,
)


def test_detail_text_keeps_long_text_up_to_detail_limit() -> None:
    value = "x" * (MAX_DETAIL_CHARS + 500)

    detail = format_database_detail_value(value, "text")

    assert len(detail.text) == MAX_DETAIL_CHARS
    assert detail.truncated
    assert detail.size_label == f"{len(value):,}자"
    assert detail.format_label == "Text"


def test_detail_json_string_is_pretty_printed() -> None:
    detail = format_database_detail_value(
        '{"user":{"name":"Alice"},"active":true}',
        "jsonb",
    )

    assert not detail.truncated
    assert detail.format_label == "JSON"
    assert '"name": "Alice"' in detail.text
    assert "\n" in detail.text


def test_detail_json_object_is_streamed() -> None:
    detail = format_database_detail_value(
        {"items": [{"id": 1}, {"id": 2}]},
        "json",
    )

    assert detail.format_label == "JSON"
    assert '"items"' in detail.text
    assert '"id": 2' in detail.text


def test_detail_binary_is_bounded() -> None:
    value = b"x" * (MAX_DETAIL_BINARY_BYTES + 100)

    detail = format_database_detail_value(value, "bytea")

    assert detail.truncated
    assert detail.format_label == "Binary"
    assert detail.size_label == f"{len(value):,} bytes"
    assert len(detail.text) == 2 + (MAX_DETAIL_BINARY_BYTES * 2)
