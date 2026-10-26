from __future__ import annotations

from app import terminal_ui
from app.terminal_store import TERMINAL_SSH, TerminalProfile


def test_ssh_command_enables_server_alive_keepalive(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        terminal_ui.shutil,
        "which",
        lambda name: "/usr/bin/ssh" if name == "ssh" else None,
    )
    profile = TerminalProfile(
        terminal_id="ssh-1",
        name="운영 서버",
        cwd=str(tmp_path),
        kind=TERMINAL_SSH,
        host="server.example.com",
        port=2222,
        user="ubuntu",
    )

    command = terminal_ui.build_ssh_command(profile)

    assert command == [
        "/usr/bin/ssh",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-p",
        "2222",
        "ubuntu@server.example.com",
    ]


def test_ssh_command_supports_host_without_user(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(terminal_ui.shutil, "which", lambda _name: None)
    profile = TerminalProfile(
        terminal_id="ssh-2",
        name="서버",
        cwd=str(tmp_path),
        kind=TERMINAL_SSH,
        host="10.0.0.10",
        port=22,
    )

    command = terminal_ui.build_ssh_command(profile)

    assert command[-1] == "10.0.0.10"
    assert command[0] == "ssh"
