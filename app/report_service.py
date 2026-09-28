from __future__ import annotations

from datetime import date

from app.models import DailyDocument, Task, TaskStatus
from app.settings import (
    DEFAULT_PLANNED_REPORT_TITLE,
    DEFAULT_PROGRESS_REPORT_TITLE,
)


class ReportService:
    DATE_TOKENS = {
        "YYYY. MM. DD": "%Y. %m. %d",
        "YY. MM. DD": "%y. %m. %d",
        "YYYY.MM.DD": "%Y.%m.%d",
        "YY.MM.DD": "%y.%m.%d",
        "YYYY-MM-DD": "%Y-%m-%d",
        "YY-MM-DD": "%y-%m-%d",
        "YYYY/MM/DD": "%Y/%m/%d",
        "YY/MM/DD": "%y/%m/%d",
        "YYYY년 MM월 DD일": "%Y년 %m월 %d일",
    }

    @classmethod
    def render_template(cls, text: str, target: date) -> str:
        rendered = text
        for token, fmt in sorted(
            cls.DATE_TOKENS.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            rendered = rendered.replace(token, target.strftime(fmt))
        return rendered

    @classmethod
    def build(
        cls,
        target: date,
        greeting: str,
        document: DailyDocument,
        footer: str = "",
        progress_title: str = DEFAULT_PROGRESS_REPORT_TITLE,
        planned_title: str = DEFAULT_PLANNED_REPORT_TITLE,
    ) -> str:
        active = [
            task
            for task in document.today_tasks
            if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        ]
        planned = [
            task
            for task in document.today_tasks
            if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.PLANNED)
        ]

        rendered_greeting = cls.render_template(greeting, target)
        rendered_footer = cls.render_template(footer, target)
        progress_heading = progress_title.strip() or DEFAULT_PROGRESS_REPORT_TITLE
        planned_heading = planned_title.strip() or DEFAULT_PLANNED_REPORT_TITLE

        lines: list[str] = [progress_heading, ""]
        lines.extend(cls._render_tasks(active, show_status=True))
        lines.extend(["", planned_heading, ""])
        lines.extend(cls._render_tasks(planned, show_status=False))

        report = "\n".join(lines)
        if rendered_greeting:
            report = cls._join_preserving_line_breaks(rendered_greeting, report)
        if rendered_footer:
            report = cls._join_preserving_line_breaks(report, rendered_footer)
        return report

    @staticmethod
    def _join_preserving_line_breaks(left: str, right: str) -> str:
        if not left:
            return right
        if not right:
            return left
        if left.endswith("\n") or right.startswith("\n"):
            return left + right
        return left + "\n" + right

    @staticmethod
    def _render_tasks(tasks: list[Task], show_status: bool) -> list[str]:
        if not tasks:
            return ["없음"]
        lines: list[str] = []
        for index, task in enumerate(tasks, start=1):
            status = f"[{task.status.value}] " if show_status else ""
            title = f"{index}. {status}{task.title}"
            if task.link_url:
                title += f" ({task.markdown_link})"
            lines.append(title)
            lines.extend(task.details)
            lines.append("")
        return lines[:-1]
