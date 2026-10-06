from __future__ import annotations

import struct
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



def test_factory_accepts_direct_command(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    backend = terminal_backend.create_terminal_backend(
        tmp_path,
        command=["ssh", "-p", "2222", "ubuntu@example.com"],
    )

    assert backend.program == "ssh"
    assert backend.arguments == ["-p", "2222", "ubuntu@example.com"]



def test_unix_resize_updates_pty_window_and_sends_sigwinch(
    monkeypatch,
    tmp_path,
) -> None:
    backend = terminal_backend.UnixPtyBackend(tmp_path)
    backend._running = True
    backend.master_fd = 42
    backend.pid = 1234

    ioctl_calls: list[tuple[int, int, bytes]] = []
    kill_calls: list[tuple[int, int]] = []

    import fcntl
    import termios

    monkeypatch.setattr(
        fcntl,
        "ioctl",
        lambda fd, request, payload: ioctl_calls.append(
            (fd, request, payload)
        ),
    )
    monkeypatch.setattr(
        terminal_backend.os,
        "kill",
        lambda pid, sig: kill_calls.append((pid, sig)),
    )

    backend.resize(37, 142)

    assert len(ioctl_calls) == 1
    fd, request, payload = ioctl_calls[0]
    assert fd == 42
    assert request == termios.TIOCSWINSZ
    assert struct.unpack("HHHH", payload)[:2] == (37, 142)
    assert kill_calls == [(1234, terminal_backend.signal.SIGWINCH)]


def test_windows_resize_uses_pywinpty_setwinsize(tmp_path) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[int, int]] = []

        def isalive(self) -> bool:
            return True

        def setwinsize(self, rows: int, columns: int) -> None:
            self.calls.append((rows, columns))

    backend = terminal_backend.WindowsConPtyBackend(tmp_path)
    process = FakeProcess()
    backend.process = process
    backend._running = True

    backend.resize(31, 118)

    assert process.calls == [(31, 118)]
