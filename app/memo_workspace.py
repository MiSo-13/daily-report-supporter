from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtWidgets import QDialog, QWidget

from app.dialogs import DeleteConfirmDialog
from app.memo_editor import MemoEditor
from app.memo_sidebar import MemoSidebar
from app.memo_store import MemoStore


class MemoWorkspace:
    def __init__(
        self,
        root: Path | str,
        parent: QWidget,
        show_status: Callable[[str, int], None],
    ) -> None:
        self.store = MemoStore(root)
        self.parent = parent
        self.show_status = show_status
        self.current_id: str | None = None

        self.editor = MemoEditor(self._save)
        self.sidebar = MemoSidebar(
            self.store,
            self.load,
            self.create,
            self.delete,
        )

    def activate(self) -> None:
        if self.current_id is not None:
            return

        memo_id = self.sidebar.first_id()
        if memo_id is not None:
            self.load(memo_id)
        else:
            self.editor.clear()

    def save_current(self) -> None:
        self.editor.save()

    def save_if_dirty(self) -> None:
        if self.current_id is not None and self.editor.is_dirty():
            self.editor.save()

    def create(self) -> None:
        self.save_if_dirty()

        memo = self.store.create("새 메모")
        self.current_id = memo.memo_id
        self.sidebar.refresh(select_id=memo.memo_id)
        self.editor.load(memo.title, memo.content)
        self.editor.title_input.selectAll()
        self.editor.title_input.setFocus()

    def load(self, memo_id: str) -> None:
        if (
            self.current_id is not None
            and self.current_id != memo_id
            and self.editor.is_dirty()
        ):
            self.editor.save()

        memo = self.store.load(memo_id)
        self.current_id = memo.memo_id
        self.editor.load(memo.title, memo.content)
        self.sidebar.select_id(memo.memo_id)

    def delete(self) -> None:
        memo_id = self.sidebar.selected_id() or self.current_id
        if memo_id is None:
            return

        memo = self.store.load(memo_id)
        dialog = DeleteConfirmDialog(
            self.parent,
            memo.title,
            item_name="메모",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.store.delete(memo_id)
        self.current_id = None
        self.sidebar.refresh()

        next_id = self.sidebar.first_id()
        if next_id is None:
            self.editor.clear()
        else:
            self.load(next_id)

        self.show_status("메모 삭제", 1800)

    def _save(self, title: str, content: str) -> None:
        if self.current_id is None:
            memo = self.store.create(title, content)
            self.current_id = memo.memo_id
        else:
            memo = self.store.save(self.current_id, title, content)

        self.sidebar.refresh(select_id=memo.memo_id)
        self.show_status("메모 저장", 1800)
