from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from app.models import DailyDocument, Task, TaskStatus

CHECKBOX_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<title>.*)$")
MARKDOWN_LINK_RE = re.compile(r"^\[(?P<text>.*)\]\((?P<url>.+)\)$")
STATUS_PREFIX = "  - 상태:"
LINK_PREFIX = "  - 관련 문서:"
DETAIL_HEADER = "  - 주요 내용:"
DETAIL_PREFIX = "    - "


class MarkdownStore:
    def __init__(self, root: Path | str = "reports") -> None:
        self.root = Path(root)

    def path_for(self, target: date) -> Path:
        return self.root / f"{target:%Y}" / f"{target:%m}" / f"{target:%y%m%d}.md"

    def ensure_day(self, target: date) -> DailyDocument:
        path = self.path_for(target)
        if path.exists():
            return self.load(target)

        _, source = self._latest_document_before(target)
        if source is None:
            document = DailyDocument()
        else:
            completed = [
                replace(task)
                for task in source.today_tasks
                if task.status is TaskStatus.COMPLETED
            ]
            pending = [
                replace(task)
                for task in source.today_tasks
                if task.status is not TaskStatus.COMPLETED
            ]
            document = DailyDocument(previous_done=completed, today_tasks=pending)

        self.save(target, document)
        return document

    def load(self, target: date) -> DailyDocument:
        path = self.path_for(target)
        if not path.exists():
            return DailyDocument()
        return self.parse(path.read_text(encoding="utf-8"))

    def save(self, target: date, document: DailyDocument) -> Path:
        path = self.path_for(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.serialize(target, document), encoding="utf-8")
        return path

    def list_dates(self, year: int | None = None, month: int | None = None) -> list[date]:
        if not self.root.exists():
            return []
        found: list[date] = []
        for path in self.root.glob("*/*/*.md"):
            if len(path.stem) != 6 or not path.stem.isdigit():
                continue
            try:
                parsed = date(int(path.parent.parent.name), int(path.parent.name), int(path.stem[-2:]))
            except ValueError:
                continue
            if year is not None and parsed.year != year:
                continue
            if month is not None and parsed.month != month:
                continue
            found.append(parsed)
        return sorted(set(found), reverse=True)

    def available_years(self) -> list[int]:
        if not self.root.exists():
            return []
        years = [
            int(child.name)
            for child in self.root.iterdir()
            if child.is_dir() and child.name.isdigit() and len(child.name) == 4
        ]
        return sorted(years, reverse=True)

    def available_months(self, year: int) -> list[int]:
        year_dir = self.root / str(year)
        if not year_dir.exists():
            return []
        months: list[int] = []
        for child in year_dir.iterdir():
            if child.is_dir() and child.name.isdigit():
                month = int(child.name)
                if 1 <= month <= 12:
                    months.append(month)
        return sorted(months, reverse=True)

    @staticmethod
    def serialize(target: date, document: DailyDocument) -> str:
        lines = [f"# {target:%Y-%m-%d} 일일 업무", "", "## 어제 했던 일", ""]
        lines.extend(MarkdownStore._tasks_to_lines(document.previous_done))
        lines.extend(["", "## 오늘 해야 할 일", ""])
        lines.extend(MarkdownStore._tasks_to_lines(document.today_tasks))
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def parse(content: str) -> DailyDocument:
        previous_done: list[Task] = []
        today_tasks: list[Task] = []
        section: list[Task] | None = None
        current: Task | None = None
        reading_details = False

        for raw in content.splitlines():
            line = raw.rstrip()
            if line == "## 어제 했던 일":
                section = previous_done
                current = None
                reading_details = False
                continue
            if line == "## 오늘 해야 할 일":
                section = today_tasks
                current = None
                reading_details = False
                continue
            if line.startswith("## "):
                section = None
                current = None
                reading_details = False
                continue
            if section is None:
                continue

            match = CHECKBOX_RE.match(line)
            if match:
                legacy_status = (
                    TaskStatus.COMPLETED
                    if match.group("mark").lower() == "x"
                    else TaskStatus.PLANNED
                )
                current = Task(
                    title=match.group("title").strip(),
                    status=legacy_status,
                )
                section.append(current)
                reading_details = False
                continue
            if current is None:
                continue
            if line.startswith(STATUS_PREFIX):
                current.status = TaskStatus.from_text(
                    line[len(STATUS_PREFIX):],
                    default=current.status,
                )
                reading_details = False
                continue
            if line.startswith(LINK_PREFIX):
                link_value = line[len(LINK_PREFIX):].strip()
                link_match = MARKDOWN_LINK_RE.match(link_value)
                if link_match:
                    current.link_text = link_match.group("text").strip()
                    current.link_url = link_match.group("url").strip()
                else:
                    # 구버전: "관련 문서: https://..." 형식.
                    # 표시 문구도 URL로 채워 다음 저장 시 Markdown link로 마이그레이션한다.
                    current.link_text = link_value
                    current.link_url = link_value
                reading_details = False
                continue
            if line == DETAIL_HEADER:
                reading_details = True
                continue
            if reading_details and line.startswith(DETAIL_PREFIX):
                current.details.append(line[len(DETAIL_PREFIX):].strip())

        return DailyDocument(previous_done=previous_done, today_tasks=today_tasks)

    @staticmethod
    def _tasks_to_lines(tasks: list[Task]) -> list[str]:
        if not tasks:
            return ["_없음_"]
        lines: list[str] = []
        for task in tasks:
            item = task.normalized()
            mark = "x" if item.status is TaskStatus.COMPLETED else " "
            lines.append(f"- [{mark}] {item.title}")
            lines.append(f"  - 상태: {item.status.value}")
            if item.link_url:
                lines.append(f"  - 관련 문서: {item.markdown_link}")
            if item.details:
                lines.append(DETAIL_HEADER)
                lines.extend(f"    - {detail}" for detail in item.details)
            lines.append("")
        return lines[:-1]

    def _latest_document_before(self, target: date) -> tuple[date | None, DailyDocument | None]:
        cursor = target - timedelta(days=1)
        for _ in range(370):
            if self.path_for(cursor).exists():
                return cursor, self.load(cursor)
            cursor -= timedelta(days=1)
        return None, None
