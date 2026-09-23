from __future__ import annotations

from datetime import date

from app.models import DailyDocument, Task


class ReportService:
    @staticmethod
    def build(target: date, greeting: str, document: DailyDocument) -> str:
        completed = [task for task in document.today_tasks if task.completed]
        pending = [task for task in document.today_tasks if not task.completed]

        lines: list[str] = []
        if greeting.strip():
            lines.append(greeting.strip())
            lines.append("")
        lines.append(f"{target:%Y년 %m월 %d일} 일일보고입니다.")
        lines.extend(["", "[진행 업무]", ""])
        lines.extend(ReportService._render_tasks(completed))
        lines.extend(["", "[예정 업무]", ""])
        lines.extend(ReportService._render_tasks(pending))
        return "\n".join(lines).rstrip()

    @staticmethod
    def _render_tasks(tasks: list[Task]) -> list[str]:
        if not tasks:
            return ["없음"]
        lines: list[str] = []
        for index, task in enumerate(tasks, start=1):
            lines.append(f"{index}. {task.title}")
            if task.link:
                lines.append(f"   - 관련 문서: {task.link}")
            lines.extend(f"   - {detail}" for detail in task.details)
            lines.append("")
        return lines[:-1]
