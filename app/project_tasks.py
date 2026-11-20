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
    """Task ID가 있으면 프로젝트 변경까지 고려한 최신 스냅샷을 조회한다.

    ID가 없는 예전 Task는 동일 제목이라도 서로 다른 업무일 수 있으므로
    날짜와 문서 내 순서를 기준으로 별개 기록으로 유지한다.
    """
    latest: dict[tuple[str, str, str], ProjectTaskEntry] = {}
    for target in sorted(store.list_dates()):
        document = store.load(target)
        for index, task in enumerate(document.today_tasks):
            if task.task_id:
                key = ("task", task.task_id, "")
            elif task.project_id == project_id:
                key = ("legacy", target.isoformat(), str(index))
            else:
                continue
            latest[key] = ProjectTaskEntry(target, index, task)

    return sorted(
        (entry for entry in latest.values() if entry.task.project_id == project_id),
        key=lambda entry: (entry.target, entry.task_index),
        reverse=True,
    )
