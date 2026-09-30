from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QDialog, QInputDialog, QWidget

from app.dialogs import DeleteConfirmDialog
from app.terminal_dialogs import SshProfileDialog
from app.terminal_store import TERMINAL_SSH, TerminalStore
from app.terminal_ui import TerminalPanel, TerminalSidebar


class TerminalWorkspace:
    def __init__(
        self,
        state_path: Path | str,
        default_cwd: Path | str,
        parent: QWidget,
        *,
        font_family: str = "",
        font_size: int = 10,
    ) -> None:
        self.store = TerminalStore(state_path)
        self.default_cwd = Path(default_cwd)
        self.parent = parent
        self.current_id: str | None = None

        self.panel = TerminalPanel()
        self.panel.set_terminal_font(font_family, font_size)

        self.sidebar = TerminalSidebar(
            self.select,
            self.create_local,
            self.create_ssh,
            self.edit,
            self.delete,
            self.reorder,
        )

        profiles = self.store.list_profiles()
        for profile in profiles:
            self.panel.add_profile(profile)
        self.sidebar.set_profiles(profiles)

    def activate(self) -> None:
        if self.current_id is not None:
            self.panel.select(self.current_id)
            return

        terminal_id = self.sidebar.first_id()
        if terminal_id is not None:
            self.select(terminal_id)
        else:
            self.create_local()

    def set_font(self, family: str, point_size: int) -> None:
        self.panel.set_terminal_font(family, point_size)

    def shutdown(self) -> None:
        self.panel.shutdown_all()

    def create_local(self) -> None:
        profiles = self.store.list_profiles()
        default_name = f"터미널 {len(profiles) + 1}"
        name, accepted = QInputDialog.getText(
            self.parent,
            "새 터미널",
            "이름",
            text=default_name,
        )
        if not accepted:
            return

        profile = self.store.create(name, self.default_cwd)
        self.panel.add_profile(profile)
        self.current_id = profile.terminal_id
        self.sidebar.set_profiles(
            self.store.list_profiles(),
            select_id=profile.terminal_id,
        )
        self.panel.select(profile.terminal_id)

    def create_ssh(self) -> None:
        dialog = SshProfileDialog(self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        profile = self.store.create_ssh(
            dialog.profile_name,
            dialog.host,
            dialog.port,
            dialog.user,
            self.default_cwd,
        )
        self.panel.add_profile(profile)
        self.current_id = profile.terminal_id
        self.sidebar.set_profiles(
            self.store.list_profiles(),
            select_id=profile.terminal_id,
        )
        self.panel.select(profile.terminal_id)

    def select(self, terminal_id: str) -> None:
        try:
            self.store.get(terminal_id)
        except KeyError:
            return

        self.current_id = terminal_id
        self.sidebar.select_id(terminal_id)
        self.panel.select(terminal_id)

    def edit(self) -> None:
        terminal_id = self.sidebar.selected_id() or self.current_id
        if terminal_id is None:
            return

        try:
            profile = self.store.get(terminal_id)
        except KeyError:
            return

        if profile.kind == TERMINAL_SSH:
            dialog = SshProfileDialog(self.parent, profile)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            updated = self.store.update_ssh(
                terminal_id,
                name=dialog.profile_name,
                host=dialog.host,
                port=dialog.port,
                user=dialog.user,
            )
            self.panel.set_profile(updated, restart=True)
        else:
            name, accepted = QInputDialog.getText(
                self.parent,
                "터미널 이름 변경",
                "이름",
                text=profile.name,
            )
            if not accepted:
                return

            updated = self.store.rename(terminal_id, name)
            self.panel.set_profile(updated)

        self.sidebar.set_profiles(
            self.store.list_profiles(),
            select_id=terminal_id,
        )

    def reorder(self, terminal_ids: list[str]) -> None:
        self.store.reorder(terminal_ids)

    def delete(self) -> None:
        terminal_id = self.sidebar.selected_id() or self.current_id
        if terminal_id is None:
            return

        try:
            profile = self.store.get(terminal_id)
        except KeyError:
            return

        dialog = DeleteConfirmDialog(
            self.parent,
            profile.name,
            item_name="터미널",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.panel.remove(terminal_id)
        self.store.delete(terminal_id)
        self.current_id = None
        self.sidebar.set_profiles(self.store.list_profiles())

        next_id = self.sidebar.first_id()
        if next_id is not None:
            self.select(next_id)
