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


def test_report_date_tokens_and_footer() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(title="업무 확인", status=TaskStatus.PLANNED),
        ]
    )

    report = ReportService.build(
        date(2026, 9, 23),
        "안녕하세요.\nYY. MM. DD 업무 공유드립니다.",
        document,
        "YY.MM.DD 기준입니다.\n감사합니다.",
    )

    assert "26. 09. 23 업무 공유드립니다." in report
    assert "26.09.23 기준입니다." in report
    assert report.endswith("감사합니다.")


def test_report_template_supports_long_date_tokens() -> None:
    target = date(2026, 9, 23)

    assert (
        ReportService.render_template(
            "YYYY.MM.DD / YYYY년 MM월 DD일",
            target,
        )
        == "2026.09.23 / 2026년 09월 23일"
    )


def test_custom_section_titles_are_serialized_and_parsed() -> None:
    document = DailyDocument(
        previous_done=[Task("완료 업무", status=TaskStatus.COMPLETED)],
        today_tasks=[Task("예정 업무", status=TaskStatus.PLANNED)],
    )

    content = MarkdownStore.serialize(
        date(2026, 9, 23),
        document,
        previous_section_title="전일 완료",
        today_section_title="금일 업무",
    )

    assert "## 전일 완료" in content
    assert "## 금일 업무" in content

    parsed = MarkdownStore.parse(
        content,
        previous_section_title="전일 완료",
        today_section_title="금일 업무",
    )
    assert parsed == document


def test_previous_custom_section_titles_remain_readable() -> None:
    content = """# 2026-09-23 일일 업무

## 어제 완료 내역

- [x] 완료 업무
  - 상태: 완료

## 오늘 진행 항목

- [ ] 진행 업무
  - 상태: 진행중
"""

    parsed = MarkdownStore.parse(
        content,
        previous_section_title="전일 완료",
        today_section_title="금일 업무",
    )

    assert [task.title for task in parsed.previous_done] == ["완료 업무"]
    assert [task.title for task in parsed.today_tasks] == ["진행 업무"]
    assert parsed.today_tasks[0].status is TaskStatus.IN_PROGRESS


def test_store_writes_configured_section_titles(tmp_path) -> None:
    store = MarkdownStore(
        tmp_path,
        previous_section_title="완료한 일",
        today_section_title="할 일",
    )
    target = date(2026, 9, 23)
    store.save(target, DailyDocument())

    content = store.path_for(target).read_text(encoding="utf-8")
    assert "## 완료한 일" in content
    assert "## 할 일" in content


def test_identical_custom_section_titles_are_parsed_by_order() -> None:
    document = DailyDocument(
        previous_done=[Task("완료", status=TaskStatus.COMPLETED)],
        today_tasks=[Task("예정", status=TaskStatus.PLANNED)],
    )

    content = MarkdownStore.serialize(
        date(2026, 9, 23),
        document,
        previous_section_title="업무",
        today_section_title="업무",
    )

    parsed = MarkdownStore.parse(
        content,
        previous_section_title="업무",
        today_section_title="업무",
    )

    assert [task.title for task in parsed.previous_done] == ["완료"]
    assert [task.title for task in parsed.today_tasks] == ["예정"]
