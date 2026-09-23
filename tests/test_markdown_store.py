from datetime import date

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task
from app.report_service import ReportService


def test_round_trip() -> None:
    target = date(2026, 9, 23)
    original = DailyDocument(
        previous_done=[Task("어제 완료", "https://example.com/a", ["완료 내용"], True)],
        today_tasks=[Task("오늘 업무", "https://example.com/b", ["첫 번째", "두 번째"], False)],
    )
    parsed = MarkdownStore.parse(MarkdownStore.serialize(target, original))
    assert parsed == original


def test_rollover_completed_and_pending(tmp_path) -> None:
    store = MarkdownStore(tmp_path)
    first = date(2026, 9, 23)
    store.save(first, DailyDocument(today_tasks=[Task("완료 업무", completed=True), Task("미완료 업무")]))

    next_doc = store.ensure_day(date(2026, 9, 24))
    assert [task.title for task in next_doc.previous_done] == ["완료 업무"]
    assert [task.title for task in next_doc.today_tasks] == ["미완료 업무"]
    assert next_doc.today_tasks[0].completed is False


def test_report_generation() -> None:
    document = DailyDocument(today_tasks=[Task("API 구현", details=["엔드포인트 추가"], completed=True), Task("테스트 작성")])
    report = ReportService.build(date(2026, 9, 23), "안녕하세요.", document)
    assert "[진행 업무]" in report
    assert "1. API 구현" in report
    assert "[예정 업무]" in report
    assert "1. 테스트 작성" in report
