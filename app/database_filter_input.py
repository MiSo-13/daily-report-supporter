from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import QStringListModel, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QCompleter, QLineEdit


class DatabaseFilterInput(QLineEdit):
    def __init__(self) -> None:
        super().__init__()
        self._identifiers: set[str] = set()
        self._completion_model = QStringListModel(self)
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self._completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._completer.activated[str].connect(self._insert_completion)

    def set_identifiers(self, values: Iterable[str]) -> None:
        self._identifiers = {
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip()
        }
        self._completion_model.setStringList(
            sorted(
                self._identifiers,
                key=lambda value: (value.casefold(), value),
            )
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        popup = self._completer.popup()

        if popup.isVisible():
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._accept_current_completion():
                    event.accept()
                    return
            if event.key() == Qt.Key.Key_Escape:
                popup.hide()
                event.accept()
                return

        if event.key() == Qt.Key.Key_Tab:
            self._accept_or_show_completion()
            event.accept()
            return

        super().keyPressEvent(event)

        if popup.isVisible():
            prefix = self._completion_prefix()
            if prefix:
                self._show_completion()
            else:
                popup.hide()

    def _accept_current_completion(self) -> bool:
        popup = self._completer.popup()
        index = popup.currentIndex()
        if not index.isValid():
            return False

        completion = str(index.data() or "")
        if not completion:
            return False

        self._insert_completion(completion)
        popup.hide()
        return True

    def _accept_or_show_completion(self) -> None:
        popup = self._completer.popup()
        if popup.isVisible() and self._accept_current_completion():
            return

        prefix = self._completion_prefix()
        matches = self._matches(prefix)

        if len(matches) == 1:
            self._insert_completion(matches[0])
            return

        if len(matches) > 1:
            common = _common_prefix(matches)
            if prefix and len(common) > len(prefix):
                self._insert_completion(common)
                return

        self._show_completion()

    def _show_completion(self) -> None:
        prefix = self._completion_prefix()
        self._completer.setCompletionPrefix(prefix)

        if self._completer.completionCount() <= 0:
            self._completer.popup().hide()
            return

        popup = self._completer.popup()
        popup.setCurrentIndex(
            self._completer.completionModel().index(0, 0)
        )
        rect = self.cursorRect()
        rect.setWidth(
            max(
                popup.sizeHintForColumn(0)
                + popup.verticalScrollBar().sizeHint().width()
                + 24,
                220,
            )
        )
        self._completer.complete(rect)

    def _matches(self, prefix: str) -> list[str]:
        folded = prefix.casefold()
        return [
            value
            for value in self._completion_model.stringList()
            if value.casefold().startswith(folded)
        ]

    def _completion_prefix(self) -> str:
        text = self.text()
        position = self.cursorPosition()
        start = position
        while start > 0:
            char = text[start - 1]
            if char.isalnum() or char in ("_", "$"):
                start -= 1
                continue
            break
        return text[start:position]

    def _insert_completion(self, completion: str) -> None:
        prefix = self._completion_prefix()
        position = self.cursorPosition()
        start = position - len(prefix)
        text = self.text()
        self.setText(text[:start] + completion + text[position:])
        self.setCursorPosition(start + len(completion))


def _common_prefix(values: list[str]) -> str:
    if not values:
        return ""

    common = values[0]
    for value in values[1:]:
        length = min(len(common), len(value))
        index = 0
        while (
            index < length
            and common[index].casefold() == value[index].casefold()
        ):
            index += 1
        common = common[:index]
        if not common:
            break
    return common
