from datetime import date
from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.period_report import report_range, collect_period_tasks, build_period_html


def test_week_and_month_boundaries():
    assert report_range(date(2026, 10, 13), "weekly") == (
        date(2026, 10, 12), date(2026, 10, 18))
    assert report_range(date(2026, 12, 12), "monthly") == (
        date(2026, 12, 1), date(2026, 12, 31))


def test_history_dedup_and_status_groups(tmp_path):
    store = MarkdownStore(tmp_path)
    store.save(date(2026, 10, 12), DailyDocument(today_tasks=[
        Task("진행 업무", status=TaskStatus.IN_PROGRESS),
        Task("완료 업무", status=TaskStatus.IN_PROGRESS),
        Task("중단 업무", status=TaskStatus.ON_HOLD),
        Task("취소 업무", status=TaskStatus.CANCELLED)]))
    store.save(date(2026, 10, 13), DailyDocument(today_tasks=[
        Task("진행 업무", status=TaskStatus.IN_PROGRESS),
        Task("완료 업무", status=TaskStatus.COMPLETED),
        Task("중단 업무", status=TaskStatus.ON_HOLD)]))
    groups = collect_period_tasks(store, date(2026, 10, 12), date(2026, 10, 18))
    assert len(groups["진행중"]) == 1
    assert len(groups["완료"]) == 1
    assert groups["완료"][0]["completed_on"] == date(2026, 10, 13)
    assert len(groups["보류"]) == 1
    assert len(groups["취소"]) == 1
    html = build_period_html(store, date(2026, 10, 13), "weekly",
                             achievements="<script>alert(1)</script>")
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "2026.10.12 ~ 2026.10.18" in html


def test_cancelled_does_not_carry_but_on_hold_does(tmp_path):
    store = MarkdownStore(tmp_path)
    store.save(date(2026, 10, 12), DailyDocument(today_tasks=[
        Task("hold", status=TaskStatus.ON_HOLD),
        Task("cancel", status=TaskStatus.CANCELLED)]))
    following = store.ensure_day(date(2026, 10, 13))
    assert [task.title for task in following.today_tasks] == ["hold"]
