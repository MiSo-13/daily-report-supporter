from __future__ import annotations

import sys

from PyQt6.QtCore import QObject

from app import terminal_backend


def test_windows_uses_comspec(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")

    program, arguments = terminal_backend.resolve_shell()

    assert program == r"C:\Windows\System32\cmd.exe"
    assert arguments == ["/Q"]


def test_windows_factory_uses_conpty_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "platform", "win32")

    backend = terminal_backend.create_terminal_backend(tmp_path)

    assert isinstance(backend, terminal_backend.WindowsConPtyBackend)


def test_unix_factory_uses_pty_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    backend = terminal_backend.create_terminal_backend(tmp_path)

    assert isinstance(backend, terminal_backend.UnixPtyBackend)


def test_unix_shell_prefers_shell_environment(monkeypatch, tmp_path) -> None:
    shell = tmp_path / "my-shell"
    shell.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("SHELL", str(shell))

    program, arguments = terminal_backend.resolve_shell()

    assert program == str(shell)
    assert arguments == []



def test_terminal_backend_is_qobject_compatible() -> None:
    assert issubclass(terminal_backend.TerminalBackend, QObject)
