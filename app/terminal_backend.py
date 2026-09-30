from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import struct
import sys
import threading

from PyQt6.QtCore import QObject, pyqtSignal


def resolve_shell() -> tuple[str, list[str]]:
    if sys.platform == "win32":
        return os.environ.get("COMSPEC") or "cmd.exe", ["/Q"]

    configured = os.environ.get("SHELL")
    if configured and Path(configured).exists():
        return configured, []

    bash = shutil.which("bash")
    if bash:
        return bash, []

    return shutil.which("sh") or "/bin/sh", []


def resolve_ssh_command(
    *,
    host: str,
    port: int,
    user: str,
) -> tuple[str, list[str]]:
    program = shutil.which("ssh") or "ssh"
    return program, ["-p", str(port), f"{user}@{host}"]


class TerminalBackend(QObject):
    output = pyqtSignal(bytes)
    exited = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        cwd: Path | str,
        *,
        program: str | None = None,
        arguments: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.cwd = Path(cwd).expanduser()
        if not self.cwd.is_dir():
            self.cwd = Path.home()

        default_program, default_arguments = resolve_shell()
        self.program = program or default_program
        self.arguments = (
            list(arguments)
            if arguments is not None
            else default_arguments
        )

    def start(self) -> None:
        raise NotImplementedError

    def is_running(self) -> bool:
        raise NotImplementedError

    def write(self, data: bytes) -> None:
        raise NotImplementedError

    def interrupt(self) -> None:
        self.write(b"\x03")

    def resize(self, rows: int, cols: int) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class UnixPtyBackend(TerminalBackend):
    def __init__(
        self,
        cwd: Path | str,
        *,
        program: str | None = None,
        arguments: list[str] | None = None,
    ) -> None:
        super().__init__(
            cwd,
            program=program,
            arguments=arguments,
        )
        self.pid: int | None = None
        self.master_fd: int | None = None
        self._running = False
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return

        try:
            import pty

            pid, master_fd = pty.fork()
        except (ImportError, OSError) as exc:
            self.failed.emit(str(exc))
            return

        if pid == 0:
            try:
                os.chdir(self.cwd)
                environment = os.environ.copy()
                environment["TERM"] = "xterm-256color"
                os.execvpe(
                    self.program,
                    [self.program, *self.arguments],
                    environment,
                )
            except BaseException:
                os._exit(127)

        self.pid = pid
        self.master_fd = master_fd
        self._running = True
        self._reader = threading.Thread(
            target=self._read_loop,
            name=f"terminal-pty-{pid}",
            daemon=True,
        )
        self._reader.start()

    def is_running(self) -> bool:
        return self._running

    def write(self, data: bytes) -> None:
        if not self._running or self.master_fd is None:
            return
        try:
            os.write(self.master_fd, data)
        except OSError:
            self._running = False

    def resize(self, rows: int, cols: int) -> None:
        if not self._running or self.master_fd is None:
            return

        try:
            import fcntl
            import termios

            size = struct.pack(
                "HHHH",
                max(1, rows),
                max(1, cols),
                0,
                0,
            )
            fcntl.ioctl(
                self.master_fd,
                termios.TIOCSWINSZ,
                size,
            )
        except (ImportError, OSError):
            return

    def close(self) -> None:
        if not self._running:
            self._close_fd()
            return

        pid = self.pid
        self._running = False
        self._close_fd()

        if pid is not None:
            try:
                os.kill(pid, signal.SIGHUP)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass

    def _read_loop(self) -> None:
        fd = self.master_fd
        if fd is None:
            return

        try:
            while self._running:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                self.output.emit(chunk)
        finally:
            was_running = self._running
            self._running = False
            if was_running:
                self.exited.emit()

    def _close_fd(self) -> None:
        fd = self.master_fd
        self.master_fd = None
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


class WindowsConPtyBackend(TerminalBackend):
    def __init__(
        self,
        cwd: Path | str,
        *,
        program: str | None = None,
        arguments: list[str] | None = None,
    ) -> None:
        super().__init__(
            cwd,
            program=program,
            arguments=arguments,
        )
        self.process = None
        self._running = False
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return

        try:
            from winpty import PtyProcess
        except ImportError:
            self.failed.emit(
                "Windows 터미널에 pywinpty가 필요합니다."
            )
            return

        environment = os.environ.copy()
        try:
            self.process = PtyProcess.spawn(
                [self.program, *self.arguments],
                cwd=str(self.cwd),
                env=environment,
                dimensions=(30, 120),
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self._running = True
        self._reader = threading.Thread(
            target=self._read_loop,
            name="terminal-conpty",
            daemon=True,
        )
        self._reader.start()

    def is_running(self) -> bool:
        process = self.process
        return bool(
            self._running
            and process is not None
            and process.isalive()
        )

    def write(self, data: bytes) -> None:
        if not self.is_running():
            return
        try:
            self.process.write(
                data.decode("utf-8", errors="replace")
            )
        except Exception:
            self._running = False

    def resize(self, rows: int, cols: int) -> None:
        if not self.is_running():
            return
        try:
            self.process.setwinsize(
                max(1, rows),
                max(1, cols),
            )
        except Exception:
            return

    def close(self) -> None:
        process = self.process
        self._running = False
        self.process = None
        if process is None:
            return
        try:
            if process.isalive():
                process.terminate(force=True)
        except Exception:
            pass
        try:
            process.close(force=True)
        except Exception:
            pass

    def _read_loop(self) -> None:
        process = self.process
        if process is None:
            return

        try:
            while self._running and process.isalive():
                try:
                    data = process.read(4096)
                except EOFError:
                    break
                except Exception:
                    break
                if data:
                    self.output.emit(
                        str(data).encode(
                            "utf-8",
                            errors="replace",
                        )
                    )
        finally:
            was_running = self._running
            self._running = False
            if was_running:
                self.exited.emit()


def create_terminal_backend(
    cwd: Path | str,
    *,
    program: str | None = None,
    arguments: list[str] | None = None,
) -> TerminalBackend:
    backend_type = (
        WindowsConPtyBackend
        if sys.platform == "win32"
        else UnixPtyBackend
    )
    return backend_type(
        cwd,
        program=program,
        arguments=arguments,
    )
