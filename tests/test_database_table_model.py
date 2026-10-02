from __future__ import annotations

from PyQt6.QtCore import Qt

from app.database_table_model import (
    MAX_BINARY_BYTES,
    MAX_DISPLAY_CHARS,
    MAX_STORED_TEXT_CHARS,
    MAX_TOOLTIP_CHARS,
    DatabaseTableModel,
    DatabaseValuePreview,
)


def test_large_text_is_compacted_in_model() -> None:
    model = DatabaseTableModel()
    original = "x" * 200_000

    model.set_result(["payload"], [[original]])

    stored = model.raw_value(0, 0)
    assert isinstance(stored, DatabaseValuePreview)
    assert stored.original_size == len(original)
    assert len(stored.text) == MAX_STORED_TEXT_CHARS
    assert model.truncated_value_count == 1


def test_large_text_display_and_tooltip_are_bounded() -> None:
    model = DatabaseTableModel()
    model.set_result(["payload"], [["x" * 200_000]])
    index = model.index(0, 0)

    display = str(model.data(index, Qt.ItemDataRole.DisplayRole))
    tooltip = str(model.data(index, Qt.ItemDataRole.ToolTipRole))

    assert len(display) <= MAX_DISPLAY_CHARS
    assert len(tooltip) <= MAX_TOOLTIP_CHARS
    assert "원본 200,000자" in display
    assert "원본 200,000자" in tooltip


def test_copy_value_uses_larger_bounded_preview() -> None:
    model = DatabaseTableModel()
    model.set_result(["payload"], [["x" * 200_000]])

    copied = DatabaseTableModel.display_value(model.raw_value(0, 0))

    assert len(copied) <= MAX_STORED_TEXT_CHARS
    assert len(copied) > MAX_DISPLAY_CHARS
    assert "원본 200,000자" in copied


def test_large_binary_keeps_only_small_preview() -> None:
    model = DatabaseTableModel()
    original = b"x" * 2_000_000

    model.set_result(["blob"], [[original]])

    stored = model.raw_value(0, 0)
    assert isinstance(stored, DatabaseValuePreview)
    assert stored.kind == "binary"
    assert stored.original_size == len(original)
    assert len(stored.text) == 2 + (MAX_BINARY_BYTES * 2)
    assert "2,000,000 bytes" in DatabaseTableModel.display_value(stored)


def test_large_json_structure_is_replaced_with_preview() -> None:
    model = DatabaseTableModel()
    original = {
        "items": [
            {"id": index, "message": "x" * 100}
            for index in range(10_000)
        ]
    }

    model.set_result(["payload"], [[original]])

    stored = model.raw_value(0, 0)
    assert isinstance(stored, DatabaseValuePreview)
    assert stored.kind == "structured"
    assert stored.original_size is None
    assert len(stored.text) <= MAX_STORED_TEXT_CHARS
    assert "큰 값 미리보기" in DatabaseTableModel.display_value(stored)


def test_small_values_keep_existing_behavior() -> None:
    model = DatabaseTableModel()
    model.set_result(
        ["id", "name", "payload"],
        [[1, "Alpha", b"abc"]],
    )

    assert model.raw_value(0, 0) == 1
    assert model.raw_value(0, 1) == "Alpha"
    assert model.raw_value(0, 2) == b"abc"
    assert model.truncated_value_count == 0
    assert model.data(model.index(0, 1)) == "Alpha"
    assert model.data(model.index(0, 2)) == "0x616263"
