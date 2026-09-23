from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    PLANNED = "예정"
    IN_PROGRESS = "진행중"
    COMPLETED = "완료"

    @classmethod
    def from_text(cls, value: str, default: "TaskStatus" | None = None) -> "TaskStatus":
        normalized = value.strip()
        for status in cls:
            if status.value == normalized:
                return status
        return default or cls.PLANNED


@dataclass(slots=True)
class Task:
    title: str
    link_text: str = ""
    link_url: str = ""
    details: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PLANNED

    @property
    def completed(self) -> bool:
        return self.status is TaskStatus.COMPLETED

    @property
    def markdown_link(self) -> str:
        url = self.link_url.strip()
        if not url:
            return ""
        text = self.link_text.strip() or url
        return f"[{text}]({url})"

    def normalized(self) -> "Task":
        return Task(
            title=self.title.strip(),
            link_text=self.link_text.strip(),
            link_url=self.link_url.strip(),
            details=[line.strip() for line in self.details if line.strip()],
            status=self.status,
        )


@dataclass(slots=True)
class DailyDocument:
    previous_done: list[Task] = field(default_factory=list)
    today_tasks: list[Task] = field(default_factory=list)
