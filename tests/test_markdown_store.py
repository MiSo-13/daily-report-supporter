from datetime import date

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.report_service import ReportService


def test_round_trip_with_three_statuses_and_markdown_link() -> None:
    target = date(2026, 9, 23)
    original = DailyDocument(
        previous_done=[
            Task(
                title="어제 완료",
                link_text="1694",
                link_url="http://naver.com",
                details=["완료 내용"],
                status=TaskStatus.COMPLETED,
            )
        ],
        today_tasks=[
            Task(
                title="진행 업무",
                link_text="설계 문서",
                link_url="https://example.com/b",
                details=["첫 번째"],
                status=TaskStatus.IN_PROGRESS,
            ),
            Task(
                title="예정 업무",
                details=["두 번째"],
                status=TaskStatus.PLANNED,
            ),
        ],
    )

    serialized = MarkdownStore.serialize(target, original)
    assert "- 관련 문서: [1694](http://naver.com)" in serialized
    assert "- 관련 문서: [설계 문서](https://example.com/b)" in serialized

    parsed = MarkdownStore.parse(serialized)
    assert parsed == original


def test_legacy_plain_url_is_migrated_to_markdown_link() -> None:
    legacy = """# 2026-09-23 일일 업무

## 어제 했던 일

_없음_

## 오늘 해야 할 일

- [ ] 기존 링크
  - 상태: 예정
  - 관련 문서: https://example.com/legacy
"""

    document = MarkdownStore.parse(legacy)
    task = document.today_tasks[0]
    assert task.link_text == "https://example.com/legacy"
    assert task.link_url == "https://example.com/legacy"

    serialized = MarkdownStore.serialize(date(2026, 9, 23), document)
    assert (
        "- 관련 문서: [https://example.com/legacy](https://example.com/legacy)"
        in serialized
    )


def test_rollover_preserves_incomplete_statuses_and_links(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    first = date(2026, 9, 23)
    store.save(
        first,
        DailyDocument(
            today_tasks=[
                Task(
                    title="완료 업무",
                    link_text="완료 문서",
                    link_url="https://example.com/done",
                    status=TaskStatus.COMPLETED,
                ),
                Task(
                    title="진행 업무",
                    link_text="진행 문서",
                    link_url="https://example.com/progress",
                    status=TaskStatus.IN_PROGRESS,
                ),
                Task(title="예정 업무", status=TaskStatus.PLANNED),
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
    assert next_doc.previous_done[0].link_text == "완료 문서"
    assert next_doc.previous_done[0].link_url == "https://example.com/done"
    assert next_doc.today_tasks[0].link_text == "진행 문서"
    assert next_doc.today_tasks[0].link_url == "https://example.com/progress"


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


def test_report_generation_groups_active_and_planned_with_markdown_link() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(
                title="API 구현",
                link_text="1694",
                link_url="http://naver.com",
                details=["엔드포인트 추가"],
                status=TaskStatus.COMPLETED,
            ),
            Task(title="리뷰 반영", status=TaskStatus.IN_PROGRESS),
            Task(title="테스트 작성", status=TaskStatus.PLANNED),
        ]
    )
    report = ReportService.build(date(2026, 9, 23), "안녕하세요.", document)
    assert "[진행 업무]" in report
    assert "1. [완료] API 구현" in report
    assert "   - 관련 문서: [1694](http://naver.com)" in report
    assert "2. [진행중] 리뷰 반영" in report
    assert "[예정 업무]" in report
    assert "1. 테스트 작성" in report
