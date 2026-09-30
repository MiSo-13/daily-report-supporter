from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import uuid


@dataclass(slots=True, frozen=True)
class TerminalProfile:
    terminal_id: str
    name: str
    cwd: str


class TerminalStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._profiles = self._load()

    def list_profiles(self) -> list[TerminalProfile]:
        return list(self._profiles)

    def create(self, name: str, cwd: Path | str) -> TerminalProfile:
        profile = TerminalProfile(
            terminal_id=uuid.uuid4().hex,
            name=self._clean_name(name),
            cwd=str(Path(cwd).expanduser()),
        )
        self._profiles.append(profile)
        self._save()
        return profile

    def rename(self, terminal_id: str, name: str) -> TerminalProfile:
        profile = self.get(terminal_id)
        updated = TerminalProfile(
            terminal_id=profile.terminal_id,
            name=self._clean_name(name),
            cwd=profile.cwd,
        )
        self._replace(updated)
        return updated

    def update_cwd(self, terminal_id: str, cwd: Path | str) -> TerminalProfile:
        profile = self.get(terminal_id)
        updated = TerminalProfile(
            terminal_id=profile.terminal_id,
            name=profile.name,
            cwd=str(Path(cwd).expanduser()),
        )
        self._replace(updated)
        return updated

    def delete(self, terminal_id: str) -> None:
        before = len(self._profiles)
        self._profiles = [
            profile
            for profile in self._profiles
            if profile.terminal_id != terminal_id
        ]
        if len(self._profiles) != before:
            self._save()

    def get(self, terminal_id: str) -> TerminalProfile:
        for profile in self._profiles:
            if profile.terminal_id == terminal_id:
                return profile
        raise KeyError(terminal_id)

    def _replace(self, updated: TerminalProfile) -> None:
        self._profiles = [
            updated if profile.terminal_id == updated.terminal_id else profile
            for profile in self._profiles
        ]
        self._save()

    def _load(self) -> list[TerminalProfile]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(payload, dict):
            return []

        raw_sessions = payload.get("sessions")
        if not isinstance(raw_sessions, list):
            return []

        profiles: list[TerminalProfile] = []
        for item in raw_sessions:
            if not isinstance(item, dict):
                continue
            terminal_id = item.get("terminal_id")
            name = item.get("name")
            cwd = item.get("cwd")
            if not all(isinstance(value, str) for value in (terminal_id, name, cwd)):
                continue
            if not terminal_id.strip():
                continue
            profiles.append(
                TerminalProfile(
                    terminal_id=terminal_id,
                    name=self._clean_name(name),
                    cwd=cwd,
                )
            )
        return profiles

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(
                {"sessions": [asdict(profile) for profile in self._profiles]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temp.replace(self.path)

    @staticmethod
    def _clean_name(name: str) -> str:
        clean = " ".join(name.splitlines()).strip()
        return clean or "터미널"
