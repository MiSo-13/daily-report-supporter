from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Task:
    title: str
    link: str = ""
    details: list[str] = field(default_factory=list)
    completed: bool = False

    def normalized(self) -> "Task":
        return Task(
            title=self.title.strip(),
            link=self.link.strip(),
            details=[line.strip() for line in self.details if line.strip()],
            completed=self.completed,
        )


@dataclass(slots=True)
class DailyDocument:
    previous_done: list[Task] = field(default_factory=list)
    today_tasks: list[Task] = field(default_factory=list)
