from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import uuid

TERMINAL_LOCAL = "local"
TERMINAL_SSH = "ssh"


@dataclass(slots=True, frozen=True)
class TerminalProfile:
    terminal_id: str
    name: str
    cwd: str
    kind: str = TERMINAL_LOCAL
    host: str = ""
    port: int = 22
    user: str = ""

    @property
    def is_ssh(self) -> bool:
        return self.kind == TERMINAL_SSH

    @property
    def target_label(self) -> str:
        if self.is_ssh:
            target = f"{self.user}@{self.host}" if self.user else self.host
            return f"{target}:{self.port}"
        return self.cwd


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

    def create_ssh(
        self,
        name: str,
        host: str,
        port: int,
        user: str,
        cwd: Path | str,
    ) -> TerminalProfile:
        clean_host = host.strip()
        clean_user = user.strip()
        if not clean_host:
            raise ValueError("host is required")
        if not clean_user:
            raise ValueError("user is required")

        profile = TerminalProfile(
            terminal_id=uuid.uuid4().hex,
            name=self._clean_name(name),
            cwd=str(Path(cwd).expanduser()),
            kind=TERMINAL_SSH,
            host=clean_host,
            port=self._clean_port(port),
            user=clean_user,
        )
        self._profiles.append(profile)
        self._save()
        return profile

    def update_ssh(
        self,
        terminal_id: str,
        *,
        name: str,
        host: str,
        port: int,
        user: str,
    ) -> TerminalProfile:
        profile = self.get(terminal_id)
        if not profile.is_ssh:
            raise ValueError("terminal profile is not SSH")

        clean_host = host.strip()
        clean_user = user.strip()
        if not clean_host:
            raise ValueError("host is required")
        if not clean_user:
            raise ValueError("user is required")

        updated = replace(
            profile,
            name=self._clean_name(name),
            host=clean_host,
            port=self._clean_port(port),
            user=clean_user,
        )
        self._replace(updated)
        return updated

    def rename(self, terminal_id: str, name: str) -> TerminalProfile:
        profile = self.get(terminal_id)
        updated = replace(profile, name=self._clean_name(name))
        self._replace(updated)
        return updated

    def update_cwd(self, terminal_id: str, cwd: Path | str) -> TerminalProfile:
        profile = self.get(terminal_id)
        updated = replace(
            profile,
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
            if not all(
                isinstance(value, str)
                for value in (terminal_id, name, cwd)
            ):
                continue
            if not terminal_id.strip():
                continue

            kind = item.get("kind", TERMINAL_LOCAL)
            if kind not in {TERMINAL_LOCAL, TERMINAL_SSH}:
                kind = TERMINAL_LOCAL

            host = item.get("host", "")
            user = item.get("user", "")
            port = item.get("port", 22)

            if kind == TERMINAL_SSH:
                if not isinstance(host, str) or not host.strip():
                    continue
                if not isinstance(user, str) or not user.strip():
                    continue
                try:
                    port = self._clean_port(port)
                except (TypeError, ValueError):
                    continue
            else:
                host = ""
                user = ""
                port = 22

            profiles.append(
                TerminalProfile(
                    terminal_id=terminal_id,
                    name=self._clean_name(name),
                    cwd=cwd,
                    kind=kind,
                    host=str(host).strip(),
                    port=int(port),
                    user=str(user).strip(),
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

    @staticmethod
    def _clean_port(port: object) -> int:
        value = int(port)
        if not 1 <= value <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return value
