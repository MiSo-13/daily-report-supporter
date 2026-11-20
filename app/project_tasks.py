from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.markdown_store import MarkdownStore
from app.models import Task


@dataclass(frozen=True, slots=True)
class ProjectTaskEntry:
    target: date
    task_index: int
    task: Task


def project_tasks(store: MarkdownStore, project_id: str) -> list[ProjectTaskEntry]:
    """날짜별 스냅샷 중 프로젝트에 연결된 업무의 가장 최근 기록을 조회한다.

    ID가 있는 업무는 이월된 기록을 하나로 합친다. ID 없는 레거시
    업무는 같은 제목이어도 별개의 기록일 수 있으므로 임의로 합치지 않는다.
    """
    latest: dict[tuple[str, str, str], ProjectTaskEntry] = {}
    for target in sorted(store.list_dates()):
        document = store.load(target)
        for index, task in enumerate(document.today_tasks):
            if task.project_id != project_id:
                continue
            key = (
                "task" if task.task_id else "legacy",
                task.task_id or target.isoformat(),
                "" if task.task_id else str(index),
            )
            latest[key] = ProjectTaskEntry(target, index, task)
    return sorted(
        latest.values(),
        key=lambda entry: (entry.target, entry.task_index),
        reverse=True,
    )
