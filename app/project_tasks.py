from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable

from app.markdown_store import MarkdownStore
from app.models import Task, TaskStatus


@dataclass(frozen=True, slots=True)
class ProjectTaskEntry:
    target: date
    task_index: int
    task: Task


def _latest_entries(
    snapshots: Iterable[tuple[date, list[Task]]],
) -> dict[tuple[str, str, str], ProjectTaskEntry]:
    # 이월된 업무는 ID로 합치고, ID 없는 옛 업무는 날짜별로 구분한다.
    latest: dict[tuple[str, str, str], ProjectTaskEntry] = {}
    for target, tasks in snapshots:
        for index, task in enumerate(tasks):
            if task.task_id:
                key = ("task", task.task_id, "")
            elif task.project_id:
                key = ("legacy", target.isoformat(), str(index))
            else:
                continue
            latest[key] = ProjectTaskEntry(target, index, task)
    return latest


def _entries_for_project(
    latest: dict[tuple[str, str, str], ProjectTaskEntry],
    project_id: str,
) -> list[ProjectTaskEntry]:
    # 프로젝트 이동·해제는 업무의 가장 최근 기록을 기준으로 판단한다.
    return sorted(
        (entry for entry in latest.values() if entry.task.project_id == project_id),
        key=lambda entry: (entry.target, entry.task_index),
        reverse=True,
    )


def project_tasks(store: MarkdownStore, project_id: str) -> list[ProjectTaskEntry]:
    """기존 호출부에서 사용하는 파일 기반 업무 조회."""
    snapshots = (
        (target, store.load(target).today_tasks)
        for target in sorted(store.list_dates())
    )
    return _entries_for_project(_latest_entries(snapshots), project_id)


def project_task_counts(entries: list[ProjectTaskEntry]) -> dict[str, int]:
    """업무의 가장 최근 상태를 건수로 집계한다."""
    counts = {"전체": len(entries), **{status.value: 0 for status in TaskStatus}}
    for entry in entries:
        counts[entry.task.status.value] += 1
    return counts


class ProjectTaskIndex:
    """변경된 날짜만 다시 읽는 메모리 인덱스."""

    def __init__(self, store: MarkdownStore) -> None:
        self.store = store
        self._snapshots: dict[date, tuple[tuple[int, int, int, int], list[Task]]] = {}
        self._latest: dict[tuple[str, str, str], ProjectTaskEntry] = {}

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
                # 조회 도중 파일이 삭제될 수 있다.
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

        if not changed:
            return

        snapshots = (
            (target, self._snapshots[target][1])
            for target in sorted(self._snapshots)
        )
        self._latest = _latest_entries(snapshots)

    def for_project(self, project_id: str) -> list[ProjectTaskEntry]:
        self._sync()
        return _entries_for_project(self._latest, project_id)
