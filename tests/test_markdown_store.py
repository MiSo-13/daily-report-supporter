from datetime import date

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.report_service import ReportService


def test_round_trip_with_three_statuses() -> None:
    target = date(2026, 9, 23)
    original = DailyDocument(
        previous_done=[
            Task(
                "어제 완료",
                "https://example.com/a",
                ["완료 내용"],
                TaskStatus.COMPLETED,
            )
        ],
        today_tasks=[
            Task(
                "진행 업무",
                "https://example.com/b",
                ["첫 번째"],
                TaskStatus.IN_PROGRESS,
            ),
            Task("예정 업무", details=["두 번째"], status=TaskStatus.PLANNED),
        ],
    )
    parsed = MarkdownStore.parse(MarkdownStore.serialize(target, original))
    assert parsed == original


def test_rollover_preserves_incomplete_statuses(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    first = date(2026, 9, 23)
    store.save(
        first,
        DailyDocument(
            today_tasks=[
                Task("완료 업무", status=TaskStatus.COMPLETED),
                Task("진행 업무", status=TaskStatus.IN_PROGRESS),
                Task("예정 업무", status=TaskStatus.PLANNED),
            ]
        ),
    )

    next_doc = store.ensure_day(date(2026, 9, 24))
    assert [task.title for task in next_doc.previous_done] == ["완료 업무"]
    assert [task.title for task in next_doc.today_tasks] == ["진행 업무", "예정 업무"]
    assert [task.status for task in next_doc.today_tasks] == [
        TaskStatus.IN_PROGRESS,
        TaskStatus.PLANNED,
    ]


def test_legacy_checkbox_markdown_is_supported() -> None:
    legacy = """# 2026-09-23 일일 업무

## 어제 했던 일

- [x] 완료 업무

## 오늘 해야 할 일

- [ ] 예정 업무
"""
    document = MarkdownStore.parse(legacy)
    assert document.previous_done[0].status is TaskStatus.COMPLETED
    assert document.today_tasks[0].status is TaskStatus.PLANNED


def test_report_generation_groups_active_and_planned() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(
                "API 구현",
                details=["엔드포인트 추가"],
                status=TaskStatus.COMPLETED,
            ),
            Task("리뷰 반영", status=TaskStatus.IN_PROGRESS),
            Task("테스트 작성", status=TaskStatus.PLANNED),
        ]
    )
    report = ReportService.build(date(2026, 9, 23), "안녕하세요.", document)
    assert "[진행 업무]" in report
    assert "1. [완료] API 구현" in report
    assert "2. [진행중] 리뷰 반영" in report
    assert "[예정 업무]" in report
    assert "1. 테스트 작성" in report
