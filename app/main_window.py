from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task, TaskStatus
from app.report_service import ReportService


class TaskEditor(QWidget):
    def __init__(self, title: str, editable: bool = True) -> None:
        super().__init__()
        self.editable = editable
        self.tasks: list[Task] = []

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentRowChanged.connect(self._load_selected)

        self.title_input = QLineEdit()
        self.link_input = QLineEdit()
        self.details_input = QTextEdit()
        self.details_input.setPlaceholderText("주요 내용을 한 줄에 하나씩 입력하세요.")
        self.status_input = QComboBox()
        for status in TaskStatus:
            self.status_input.addItem(status.value, status.value)

        form = QFormLayout()
        form.addRow("제목", self.title_input)
        form.addRow("관련 문서 링크", self.link_input)
        form.addRow("주요 내용", self.details_input)
        form.addRow("상태", self.status_input)

        self.add_button = QPushButton("+ 업무 추가")
        self.delete_button = QPushButton("삭제")
        self.apply_button = QPushButton("변경 적용")
        self.add_button.clicked.connect(self.add_task)
        self.delete_button.clicked.connect(self.delete_task)
        self.apply_button.clicked.connect(self.apply_current)

        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(self.apply_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{title}</b>"))
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(form)
        layout.addLayout(buttons)

        for widget in (
            self.title_input,
            self.link_input,
            self.details_input,
            self.status_input,
            self.add_button,
            self.delete_button,
            self.apply_button,
        ):
            widget.setEnabled(editable)

    def set_tasks(self, tasks: list[Task]) -> None:
        self.tasks = [Task(t.title, t.link, list(t.details), t.status) for t in tasks]
        self.refresh()

    def get_tasks(self) -> list[Task]:
        self.apply_current(silent=True)
        return [Task(t.title, t.link, list(t.details), t.status) for t in self.tasks]

    def refresh(self) -> None:
        selected = self.list_widget.currentRow()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        symbols = {
            TaskStatus.PLANNED: "○",
            TaskStatus.IN_PROGRESS: "▶",
            TaskStatus.COMPLETED: "✓",
        }
        for task in self.tasks:
            prefix = symbols[task.status]
            item = QListWidgetItem(
                f"{prefix} [{task.status.value}] {task.title or '(제목 없음)'}"
            )
            if task.link:
                item.setToolTip(task.link)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

        if self.tasks:
            self.list_widget.setCurrentRow(min(max(selected, 0), len(self.tasks) - 1))
        else:
            self._clear_form()

    def add_task(self) -> None:
        if not self.editable:
            return
        self.apply_current(silent=True)
        self.tasks.append(Task("새 업무", status=TaskStatus.PLANNED))
        self.refresh()
        self.list_widget.setCurrentRow(len(self.tasks) - 1)
        self.title_input.setFocus()
        self.title_input.selectAll()

    def delete_task(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.tasks):
            return
        del self.tasks[row]
        self.refresh()

    def apply_current(self, silent: bool = False) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.tasks) or not self.editable:
            return

        title = self.title_input.text().strip()
        if not title:
            if not silent:
                QMessageBox.warning(self, "입력 확인", "업무 제목을 입력하세요.")
            return

        status = TaskStatus.from_text(
            str(self.status_input.currentData() or TaskStatus.PLANNED.value)
        )
        self.tasks[row] = Task(
            title=title,
            link=self.link_input.text().strip(),
            details=[
                line.strip()
                for line in self.details_input.toPlainText().splitlines()
                if line.strip()
            ],
            status=status,
        )
        self.refresh()
        self.list_widget.setCurrentRow(row)

    def _load_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.tasks):
            self._clear_form()
            return
        task = self.tasks[row]
        self.title_input.setText(task.title)
        self.link_input.setText(task.link)
        self.details_input.setPlainText("\n".join(task.details))
        status_index = self.status_input.findData(task.status.value)
        self.status_input.setCurrentIndex(max(status_index, 0))

    def _clear_form(self) -> None:
        self.title_input.clear()
        self.link_input.clear()
        self.details_input.clear()
        planned_index = self.status_input.findData(TaskStatus.PLANNED.value)
        self.status_input.setCurrentIndex(max(planned_index, 0))


class ReportDialog(QDialog):
    def __init__(self, parent: QWidget, target: date, document: DailyDocument) -> None:
        super().__init__(parent)
        self.setWindowTitle("일일보고 작성")
        self.resize(700, 600)
        self.document = document

        self.date_edit = QDateEdit(QDate(target.year, target.month, target.day))
        self.date_edit.setCalendarPopup(True)
        self.greeting = QTextEdit("안녕하세요.\n금일 업무 진행사항 공유드립니다.")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        generate = QPushButton("일일보고 생성")
        copy = QPushButton("클립보드 복사")
        generate.clicked.connect(self.generate)
        copy.clicked.connect(self.copy_to_clipboard)

        form = QFormLayout()
        form.addRow("날짜", self.date_edit)
        form.addRow("인사말", self.greeting)

        buttons = QHBoxLayout()
        buttons.addWidget(generate)
        buttons.addWidget(copy)
        buttons.addStretch(1)

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.output, 1)
        layout.addWidget(close_buttons)
        self.generate()

    def generate(self) -> None:
        qdate = self.date_edit.date()
        target = date(qdate.year(), qdate.month(), qdate.day())
        self.output.setPlainText(
            ReportService.build(target, self.greeting.toPlainText(), self.document)
        )

    def copy_to_clipboard(self) -> None:
        if not self.output.toPlainText().strip():
            self.generate()
        QGuiApplication.clipboard().setText(self.output.toPlainText())
        QMessageBox.information(self, "복사 완료", "일일보고가 클립보드에 복사되었습니다.")


class MainWindow(QMainWindow):
    def __init__(self, reports_root: Path | str = "reports") -> None:
        super().__init__()
        self.setWindowTitle("Daily Report Supporter")
        self.resize(1180, 760)
        self.store = MarkdownStore(reports_root)
        self.current_date = date.today()

        self.year_combo = QComboBox()
        self.month_combo = QComboBox()
        self.date_list = QListWidget()
        self.year_combo.currentIndexChanged.connect(self._year_changed)
        self.month_combo.currentIndexChanged.connect(self._reload_date_list)
        self.date_list.itemSelectionChanged.connect(self._date_selected)

        nav = QWidget()
        nav_layout = QVBoxLayout(nav)
        nav_layout.addWidget(QLabel("<b>일일 문서</b>"))
        nav_layout.addWidget(self.year_combo)
        nav_layout.addWidget(self.month_combo)
        nav_layout.addWidget(self.date_list, 1)

        self.previous_editor = TaskEditor("어제 했던 일", editable=True)
        self.today_editor = TaskEditor("오늘 해야 할 일", editable=True)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.previous_editor, "어제 했던 일")
        self.tabs.addTab(self.today_editor, "오늘 해야 할 일")

        self.current_label = QLabel()
        self.save_button = QPushButton("저장")
        self.today_button = QPushButton("오늘로 이동")
        self.report_button = QPushButton("일일보고 작성")
        self.save_button.clicked.connect(self.save_current)
        self.today_button.clicked.connect(self.open_today)
        self.report_button.clicked.connect(self.open_report)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.current_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.today_button)
        toolbar.addWidget(self.save_button)
        toolbar.addWidget(self.report_button)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addLayout(toolbar)
        content_layout.addWidget(self.tabs, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(nav)
        splitter.addWidget(content)
        splitter.setSizes([260, 920])
        self.setCentralWidget(splitter)

        self.open_today()

    def open_today(self) -> None:
        self.store.ensure_day(date.today())
        self._refresh_filters(select_date=date.today())
        self.load_date(date.today())

    def load_date(self, target: date) -> None:
        document = (
            self.store.ensure_day(target)
            if target == date.today()
            else self.store.load(target)
        )
        self.current_date = target
        self.current_label.setText(
            f"<b>{target:%Y-%m-%d}</b>  ·  {self.store.path_for(target)}"
        )
        self.previous_editor.set_tasks(document.previous_done)
        self.today_editor.set_tasks(document.today_tasks)

    def save_current(self) -> None:
        document = DailyDocument(
            previous_done=self.previous_editor.get_tasks(),
            today_tasks=self.today_editor.get_tasks(),
        )
        self.store.save(self.current_date, document)
        self._refresh_filters(select_date=self.current_date)
        QMessageBox.information(
            self,
            "저장 완료",
            f"{self.current_date:%y%m%d}.md 파일을 저장했습니다.",
        )

    def open_report(self) -> None:
        document = DailyDocument(
            previous_done=self.previous_editor.get_tasks(),
            today_tasks=self.today_editor.get_tasks(),
        )
        ReportDialog(self, self.current_date, document).exec()

    def _refresh_filters(self, select_date: date | None = None) -> None:
        years = self.store.available_years()
        if date.today().year not in years:
            years.append(date.today().year)
            years.sort(reverse=True)
        selected = select_date or self.current_date

        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        for year in years:
            self.year_combo.addItem(f"{year}년", year)
        idx = self.year_combo.findData(selected.year)
        self.year_combo.setCurrentIndex(max(idx, 0))
        self.year_combo.blockSignals(False)

        self._year_changed(select_month=selected.month, select_date=selected)

    def _year_changed(
        self,
        *args,
        select_month: int | None = None,
        select_date: date | None = None,
    ) -> None:
        year = self.year_combo.currentData()
        if year is None:
            return

        months = self.store.available_months(int(year))
        if date.today().year == int(year) and date.today().month not in months:
            months.append(date.today().month)
            months.sort(reverse=True)

        self.month_combo.blockSignals(True)
        self.month_combo.clear()
        for month in months:
            self.month_combo.addItem(f"{month:02d}월", month)
        wanted = select_month if select_month is not None else date.today().month
        idx = self.month_combo.findData(wanted)
        self.month_combo.setCurrentIndex(max(idx, 0))
        self.month_combo.blockSignals(False)

        self._reload_date_list(select_date=select_date)

    def _reload_date_list(
        self,
        *args,
        select_date: date | None = None,
    ) -> None:
        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        if year is None or month is None:
            return

        dates = self.store.list_dates(int(year), int(month))
        self.date_list.blockSignals(True)
        self.date_list.clear()
        for value in dates:
            item = QListWidgetItem(value.strftime("%Y-%m-%d (%a)"))
            item.setData(Qt.ItemDataRole.UserRole, value.isoformat())
            self.date_list.addItem(item)
            if select_date == value:
                self.date_list.setCurrentItem(item)
        self.date_list.blockSignals(False)

    def _date_selected(self) -> None:
        item = self.date_list.currentItem()
        if item is None:
            return
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            self.load_date(date.fromisoformat(raw))


def run() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
