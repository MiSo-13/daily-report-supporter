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
    assert next_doc.previous_done == []
    assert [task.title for task in next_doc.today_tasks] == ["진행 업무", "예정 업무"]
    assert [task.status for task in next_doc.today_tasks] == [
        TaskStatus.IN_PROGRESS,
        TaskStatus.PLANNED,
    ]
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
    assert "\n진행 업무\n" in report
    assert "1. [완료] API 구현 ([1694](http://naver.com))" in report
    assert "\n엔드포인트 추가\n" in report
    assert "2. [진행중] 리뷰 반영" in report
    assert "\n예정 업무\n" in report
    planned_section = report.split("예정 업무", 1)[1]
    assert "1. 리뷰 반영" in planned_section
    assert "2. 테스트 작성" in planned_section
    assert "API 구현" not in planned_section


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
    assert "## 완료한 일" not in content
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


def test_report_does_not_add_fixed_date_title() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(title="업무 확인", status=TaskStatus.IN_PROGRESS),
        ]
    )

    report = ReportService.build(
        date(2026, 9, 23),
        "안녕하세요.\n26. 09. 23 업무 공유드립니다.",
        document,
    )

    assert "2026년 09월 23일 일일보고입니다." not in report
    assert report.startswith("안녕하세요.\n26. 09. 23 업무 공유드립니다.\n진행 업무")


def test_report_header_can_be_defined_in_greeting() -> None:
    document = DailyDocument()

    report = ReportService.build(
        date(2026, 9, 23),
        "안녕하세요.\nYYYY년 MM월 DD일 일일보고입니다.",
        document,
    )

    assert report.startswith(
        "안녕하세요.\n2026년 09월 23일 일일보고입니다.\n진행 업무"
    )


def test_completed_work_is_not_copied_to_next_day(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    first = date(2026, 9, 23)
    store.save(
        first,
        DailyDocument(
            today_tasks=[
                Task(title="오늘 완료", status=TaskStatus.COMPLETED),
                Task(title="계속 진행", status=TaskStatus.IN_PROGRESS),
            ]
        ),
    )

    next_doc = store.ensure_day(date(2026, 9, 24))

    assert next_doc.previous_done == []
    assert [task.title for task in next_doc.today_tasks] == ["계속 진행"]


def test_in_progress_work_appears_in_both_report_sections() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(title="계속 진행", status=TaskStatus.IN_PROGRESS),
        ]
    )

    report = ReportService.build(date(2026, 9, 23), "", document)
    progress_section, planned_section = report.split("예정 업무", 1)

    assert "[진행중] 계속 진행" in progress_section
    assert "1. 계속 진행" in planned_section


def test_single_custom_today_section_remains_readable() -> None:
    content = """# 2026-09-23 일일 업무

## 내가 정한 오늘 업무

- [ ] 진행 업무
  - 상태: 진행중
"""

    parsed = MarkdownStore.parse(
        content,
        today_section_title="다른 새 제목",
    )

    assert parsed.previous_done == []
    assert [task.title for task in parsed.today_tasks] == ["진행 업무"]
    assert parsed.today_tasks[0].status is TaskStatus.IN_PROGRESS


def test_legacy_previous_section_is_preserved_when_it_has_data() -> None:
    document = DailyDocument(
        previous_done=[
            Task(title="기존 이전 업무", status=TaskStatus.COMPLETED),
        ],
        today_tasks=[
            Task(title="오늘 업무", status=TaskStatus.PLANNED),
        ],
    )

    content = MarkdownStore.serialize(date(2026, 9, 23), document)

    assert "## 어제 했던 일" in content
    parsed = MarkdownStore.parse(content)
    assert [task.title for task in parsed.previous_done] == ["기존 이전 업무"]


def test_global_search_finds_task_fields(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    target = date(2026, 9, 23)
    store.save(
        target,
        DailyDocument(
            today_tasks=[
                Task(
                    title="권한 API 개발",
                    link_text="JIRA-1694",
                    link_url="https://example.com/auth",
                    details=["관리자 권한 조회 구현"],
                    status=TaskStatus.IN_PROGRESS,
                )
            ]
        ),
    )

    assert store.search("권한")[0].title == "권한 API 개발"
    assert store.search("jira-1694")[0].snippet == "링크 이름: JIRA-1694"
    assert store.search("EXAMPLE.COM")[0].snippet == "URL: https://example.com/auth"
    assert store.search("관리자")[0].snippet == "주요 내용: 관리자 권한 조회 구현"
    assert store.search("진행중")[0].snippet == "상태: 진행중"


def test_global_search_returns_newest_results_first(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    for target in (date(2026, 9, 22), date(2026, 9, 24)):
        store.save(
            target,
            DailyDocument(
                today_tasks=[
                    Task(title="검색 대상", status=TaskStatus.PLANNED),
                ]
            ),
        )

    results = store.search("검색 대상")

    assert [result.target for result in results] == [
        date(2026, 9, 24),
        date(2026, 9, 22),
    ]


def test_global_search_includes_legacy_previous_data(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    target = date(2026, 9, 23)
    store.save(
        target,
        DailyDocument(
            previous_done=[
                Task(
                    title="레거시 배포 작업",
                    details=["이전 버전 기록"],
                    status=TaskStatus.COMPLETED,
                )
            ],
            today_tasks=[],
        ),
    )

    result = store.search("레거시")[0]

    assert result.target == target
    assert result.legacy
    assert result.task_index is None


def test_global_search_falls_back_to_raw_markdown_text(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    target = date(2026, 9, 23)
    path = store.path_for(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# 2026-09-23 일일 업무

수동으로 남긴 회의 메모

## 오늘 업무

_없음_
""",
        encoding="utf-8",
    )

    result = store.search("회의 메모")[0]

    assert result.target == target
    assert result.title == "문서 내용"
    assert result.snippet == "수동으로 남긴 회의 메모"


def test_global_search_blank_query_returns_empty(tmp_path) -> None:
    store = MarkdownStore(tmp_path)

    assert store.search("") == []
    assert store.search("   ") == []



def test_report_section_titles_are_customizable_without_brackets() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(title="작업", status=TaskStatus.IN_PROGRESS),
        ]
    )

    report = ReportService.build(
        date(2026, 9, 23),
        "",
        document,
        "",
        "오늘 진행",
        "다음 작업",
    )

    assert report.startswith("오늘 진행\n")
    assert "\n다음 작업\n" in report
    assert "[오늘 진행]" not in report
    assert "[다음 작업]" not in report


def test_report_preserves_greeting_and_footer_line_breaks() -> None:
    document = DailyDocument()

    report = ReportService.build(
        date(2026, 9, 23),
        "첫 줄\n\n둘째 줄\n\n",
        document,
        "\n\n끝\n\n",
    )

    assert report.startswith("첫 줄\n\n둘째 줄\n\n진행 업무")
    assert report.endswith("\n\n끝\n\n")


def test_report_renders_link_next_to_task_title() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(
                title="보고서 개선 문서 확인",
                link_text="Confluence",
                link_url="https://example.com/confluence",
                status=TaskStatus.COMPLETED,
            )
        ]
    )

    report = ReportService.build(date(2026, 9, 23), "", document)

    assert (
        "1. [완료] 보고서 개선 문서 확인 "
        "([Confluence](https://example.com/confluence))"
        in report
    )
    assert "관련 문서:" not in report


def test_report_renders_task_detail_markdown_as_entered() -> None:
    document = DailyDocument(
        today_tasks=[
            Task(
                title="Markdown 확인",
                details=[
                    "### 세부 내용",
                    "",
                    "- 첫 번째",
                    "  - 하위 항목",
                    "",
                    "**강조**",
                ],
                status=TaskStatus.COMPLETED,
            )
        ]
    )

    report = ReportService.build(date(2026, 9, 23), "", document)

    assert (
        "1. [완료] Markdown 확인\n"
        "### 세부 내용\n"
        "\n"
        "- 첫 번째\n"
        "  - 하위 항목\n"
        "\n"
        "**강조**"
        in report
    )
    assert "   - ### 세부 내용" not in report


def test_markdown_detail_round_trip_preserves_formatting() -> None:
    target = date(2026, 9, 23)
    details = [
        "### 제목",
        "",
        "- 항목",
        "  - 하위 항목",
        "두 칸 뒤 공백  ",
        "",
    ]
    original = DailyDocument(
        today_tasks=[
            Task(
                title="Markdown",
                details=details,
                status=TaskStatus.IN_PROGRESS,
            )
        ]
    )

    serialized = MarkdownStore.serialize(target, original)
    parsed = MarkdownStore.parse(serialized)

    assert parsed.today_tasks[0].details == details


def test_legacy_detail_bullet_is_kept_as_markdown() -> None:
    legacy = """# 2026-09-23 일일 업무

## 오늘 업무

- [ ] 기존 업무
  - 상태: 진행중
  - 주요 내용:
    - 기존 내용
"""

    parsed = MarkdownStore.parse(legacy)

    assert parsed.today_tasks[0].details == ["- 기존 내용"]



def test_report_preserves_blank_line_inside_greeting_example() -> None:
    document = DailyDocument()

    report = ReportService.build(
        date(2026, 9, 28),
        "안녕하십니까\n\nYY. MM. DD 일일보고 보고 드립니다. ",
        document,
    )

    assert report.startswith(
        "안녕하십니까\n\n"
        "26. 09. 28 일일보고 보고 드립니다. \n"
        "진행 업무"
    )


def test_report_normalizes_qt_paragraph_separator_without_losing_blank_line() -> None:
    document = DailyDocument()

    report = ReportService.build(
        date(2026, 9, 28),
        "안녕하십니까\u2029\u2029YY. MM. DD 일일보고 보고 드립니다.",
        document,
    )

    assert report.startswith(
        "안녕하십니까\n\n"
        "26. 09. 28 일일보고 보고 드립니다.\n"
        "진행 업무"
    )
