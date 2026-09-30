from __future__ import annotations

import os

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

try:
    import psutil
except ImportError:  # pragma: no cover - requirements.txt installs psutil
    psutil = None


class ProcessResourceMonitor(QObject):
    updated = pyqtSignal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        interval_ms: int = 1500,
    ) -> None:
        super().__init__(parent)
        self._process = psutil.Process(os.getpid()) if psutil is not None else None
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.sample)

        if self._process is not None:
            self._process.cpu_percent(interval=None)

    def start(self) -> None:
        self.sample()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def sample(self) -> None:
        if self._process is None:
            self.updated.emit("CPU --  ·  RAM --")
            return

        try:
            cpu = self._process.cpu_percent(interval=None)
            rss = self._process.memory_info().rss
        except (psutil.Error, OSError):
            self.updated.emit("CPU --  ·  RAM --")
            return

        self.updated.emit(
            f"CPU {cpu:.1f}%  ·  RAM {self._format_bytes(rss)}"
        )

    @staticmethod
    def _format_bytes(value: int) -> str:
        mib = value / (1024 * 1024)
        if mib < 1024:
            return f"{mib:.0f} MB"
        return f"{mib / 1024:.1f} GB"
