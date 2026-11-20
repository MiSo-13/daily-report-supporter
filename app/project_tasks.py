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



def project_task_counts(
    entries: list[ProjectTaskEntry],
) -> dict[str, int]:
    """최신 업무 상태를 기준으로 프로젝트 업무 수를 집계한다."""
    counts = {"전체": len(entries)}
    for status in ("예정", "진행중", "완료", "보류", "취소"):
        counts[status] = 0
    for entry in entries:
        counts[entry.task.status.value] += 1
    return counts


class ProjectTaskIndex:
    """변경된 날짜의 Markdown만 다시 읽는 프로젝트 업무 인덱스.

    메모리에만 유지하고 원본 보고서나 별도 인덱스 파일을 수정하지 않는다.
    """

    def __init__(self, store: MarkdownStore) -> None:
        self.store = store
        self._snapshots: dict[date, tuple[tuple[int, int, int, int], list[Task]]] = {}
        self._latest: dict[tuple[str, str, str], ProjectTaskEntry] = {}
        self._dirty = True

    def _sync(self) -> None:
        dates = set(self.store.list_dates())
        changed = False
        for target in set(self._snapshots) - dates:
            del self._snapshots[target]
            changed = True

        for target in dates:
            path = self.store.path_for(target)
            try:
                stat = path.stat()
            except FileNotFoundError:
                # 목록을 생성한 직후 삭제된 파일도 안전하게 건너뛴다.
                if target in self._snapshots:
                    del self._snapshots[target]
                    changed = True
                continue
            signature = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino)
            cached = self._snapshots.get(target)
            if cached is not None and cached[0] == signature:
                continue
            document = self.store.load(target)
            self._snapshots[target] = (signature, document.today_tasks)
            changed = True

        if not (changed or self._dirty):
            return

        latest: dict[tuple[str, str, str], ProjectTaskEntry] = {}
        for target in sorted(self._snapshots):
            for index, task in enumerate(self._snapshots[target][1]):
                if task.task_id:
                    key = ("task", task.task_id, "")
                elif task.project_id:
                    key = ("legacy", target.isoformat(), str(index))
                else:
                    continue
                latest[key] = ProjectTaskEntry(target, index, task)
        self._latest = latest
        self._dirty = False

    def for_project(self, project_id: str) -> list[ProjectTaskEntry]:
        self._sync()
        return sorted(
            (entry for entry in self._latest.values()
             if entry.task.project_id == project_id),
            key=lambda entry: (entry.target, entry.task_index),
            reverse=True,
        )
