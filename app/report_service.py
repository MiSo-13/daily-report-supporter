from __future__ import annotations

from datetime import date

from app.models import DailyDocument, Task, TaskStatus


class ReportService:
    @staticmethod
    def build(target: date, greeting: str, document: DailyDocument) -> str:
        active = [
            task
            for task in document.today_tasks
            if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        ]
        planned = [
            task for task in document.today_tasks if task.status is TaskStatus.PLANNED
        ]

        lines: list[str] = []
        if greeting.strip():
            lines.append(greeting.strip())
            lines.append("")
        lines.append(f"{target:%Y년 %m월 %d일} 일일보고입니다.")
        lines.extend(["", "[진행 업무]", ""])
        lines.extend(ReportService._render_tasks(active, show_status=True))
        lines.extend(["", "[예정 업무]", ""])
        lines.extend(ReportService._render_tasks(planned, show_status=False))
        return "\n".join(lines).rstrip()

    @staticmethod
    def _render_tasks(tasks: list[Task], show_status: bool) -> list[str]:
        if not tasks:
            return ["없음"]
        lines: list[str] = []
        for index, task in enumerate(tasks, start=1):
            status = f"[{task.status.value}] " if show_status else ""
            lines.append(f"{index}. {status}{task.title}")
            if task.link_url:
                lines.append(f"   - 관련 문서: {task.markdown_link}")
            lines.extend(f"   - {detail}" for detail in task.details)
            lines.append("")
        return lines[:-1]
