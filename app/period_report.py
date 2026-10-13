"""Offline HTML summaries built from historical daily Markdown snapshots."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from html import escape

from app.models import TaskStatus


def report_range(anchor: date, period: str) -> tuple[date, date]:
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "monthly":
        start = anchor.replace(day=1)
        if anchor.month == 12:
            following = date(anchor.year + 1, 1, 1)
        else:
            following = date(anchor.year, anchor.month + 1, 1)
        return start, following - timedelta(days=1)
    raise ValueError("보고 기간은 weekly 또는 monthly여야 합니다.")


def collect_period_tasks(store, start: date, end: date):
    """Summarize snapshots by title/link. No invented per-task timestamps.

    Since old Markdown does not carry stable task IDs, title and URL act as an
    approximate identity. Do not sum daily carryovers as independent tasks.
    """
    if end < start:
        raise ValueError("종료 날짜는 시작 날짜보다 빠를 수 없습니다.")
    records = {}
    for day in sorted(d for d in store.list_dates() if start <= d <= end):
        document = store.load(day)
        for task in document.today_tasks:
            key = (task.title.strip().casefold(), task.link_url.strip())
            if not key[0]:
                continue
            if key not in records:
                records[key] = {"title": task.title, "link": task.link_url,
                                "first_seen": day, "last_seen": day,
                                "status": task.status, "details": [],
                                "completed_on": None}
            entry = records[key]
            entry["last_seen"] = day
            entry["status"] = task.status
            entry["details"] = task.details[:12]
            if task.status is TaskStatus.COMPLETED and entry["completed_on"] is None:
                entry["completed_on"] = day
    groups = defaultdict(list)
    for entry in records.values():
        if entry["completed_on"] is not None:
            groups["완료"].append(entry)
        elif entry["status"] is TaskStatus.CANCELLED:
            groups["취소"].append(entry)
        elif entry["status"] is TaskStatus.ON_HOLD:
            groups["보류"].append(entry)
        elif entry["status"] is TaskStatus.IN_PROGRESS:
            groups["진행중"].append(entry)
        else:
            groups["예정"].append(entry)
    for values in groups.values():
        values.sort(key=lambda task: (task["first_seen"], task["title"]))
    return groups


def build_period_html(store, anchor: date, period: str, *,
                      achievements: str = "", issues: str = "", next_plan: str = "") -> str:
    start, end = report_range(anchor, period)
    groups = collect_period_tasks(store, start, end)
    title = "주간 업무보고서" if period == "weekly" else "월간 업무보고서"

    def lines(text):
        return "<p>" + escape(text.strip()).replace("\n", "<br>") + "</p>" if text.strip() else "<p class='muted'>작성된 내용 없음</p>"

    def task_table(entries):
        if not entries:
            return "<p class='muted'>해당 업무 없음</p>"
        rows = []
        for task in entries:
            link = ""
            if task["link"].startswith(("https://", "http://")):
                link = f" <a href='{escape(task['link'], quote=True)}'>관련 문서</a>"
            details = " / ".join(x.strip() for x in task["details"] if x.strip())[:260]
            finished = task["completed_on"].isoformat() if task["completed_on"] else "—"
            rows.append(
                f"<tr><td>{escape(task['title'])}{link}</td>"
                f"<td>{task['first_seen']:%Y-%m-%d}</td><td>{finished}</td>"
                f"<td>{escape(details)}</td></tr>")
        return ("<table><thead><tr><th>업무</th><th>기간 내 최초 기록일</th>"
                "<th>완료 기록일</th><th>주요 내용</th></tr></thead><tbody>"
                + "".join(rows) + "</tbody></table>")

    order = ("완료", "진행중", "예정", "보류", "취소")
    cards = "".join(f"<div class='kpi'><strong>{len(groups[name])}</strong><span>{name}</span></div>"
                    for name in order)
    sections = "".join(f"<section><h2>{escape(name)} 업무</h2>{task_table(groups[name])}</section>"
                       for name in order)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{color-scheme:light}}body{{font-family:system-ui,'Malgun Gothic',sans-serif;background:#f4f7fb;color:#243248;line-height:1.6;margin:0}}
main{{max-width:1100px;margin:35px auto;padding:0 24px 50px}}
header,section{{background:white;border:1px solid #dfe5ee;border-radius:12px;padding:22px;margin-bottom:18px}}
h1{{margin:0;font-size:26px}}h2{{font-size:18px;margin-top:0}}
.subtitle,.muted{{color:#67778b}}.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}}
.kpi{{background:white;border:1px solid #dfe5ee;border-radius:10px;padding:14px;min-width:115px;display:flex;flex-direction:column}}
.kpi strong{{font-size:26px}}.kpi span{{font-size:13px;color:#67778b}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{border-bottom:1px solid #e5e9f0;padding:10px;text-align:left;vertical-align:top;word-break:break-word}}
th{{background:#edf2fa}}a{{color:#2463ad}}
.note{{padding:12px;background:#fff6df;border-left:4px solid #d8a535;font-size:12px}}
@media print{{body{{background:white}}main{{margin:0;padding:0}}header,section,.kpi{{break-inside:avoid}}}}
</style></head><body><main>
<header><h1>{title}</h1><div class="subtitle">{start:%Y.%m.%d} ~ {end:%Y.%m.%d}</div>
<div class="note">기존 Markdown의 날짜별 기록을 기반으로 집계했습니다. 최초 기록일은 실제 시작 시각이 아니며,
완료 기록일도 정확한 완료 시각을 의미하지 않습니다. 제목과 링크가 같은 업무는 하나로 집계합니다.</div></header>
<div class="kpis">{cards}</div>
<section><h2>주요 성과</h2>{lines(achievements)}</section>
{sections}
<section><h2>이슈 및 지원 요청</h2>{lines(issues)}</section>
<section><h2>다음 기간 계획</h2>{lines(next_plan)}</section>
</main></body></html>"""
