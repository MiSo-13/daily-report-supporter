from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import GreetingSettingsDialog, ReportDialog
from app.markdown_store import MarkdownStore
from app.models import DailyDocument, TaskStatus
from app.paths import default_reports_root
from app.settings import (
    AppSettings,
    INPUT_METHOD_CROSTINI_IBUS,
    INPUT_METHOD_SYSTEM,
)
from app.task_editor import TaskEditor
from app.themes import THEMES, stylesheet_for, theme_names


class MainWindow(QMainWindow):
    def __init__(self, reports_root: Path | str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Daily Report Supporter")
        self.resize(1180, 760)

        resolved_reports_root = (
            Path(reports_root)
            if reports_root is not None
            else default_reports_root()
        )
        self.settings = AppSettings(resolved_reports_root)
        self.store = MarkdownStore(
            resolved_reports_root,
            previous_section_title=self.settings.previous_section_title,
            today_section_title=self.settings.today_section_title,
        )
        self.current_date = date.today()
        self._theme_actions: dict[str, QAction] = {}
        self._input_method_actions: dict[str, QAction] = {}
        self._pending_theme: str | None = None

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

        self.previous_editor = TaskEditor(
            self.settings.previous_section_title,
            self.persist_current,
            default_status=TaskStatus.COMPLETED,
        )
        self.today_editor = TaskEditor(
            self.settings.today_section_title,
            self.persist_current,
            default_status=TaskStatus.PLANNED,
        )

        self.tabs = QTabWidget()
        self.tabs.addTab(
            self.previous_editor,
            self.settings.previous_section_title,
        )
        self.tabs.addTab(
            self.today_editor,
            self.settings.today_section_title,
        )

        self.current_label = QLabel()
        self.today_button = QPushButton("오늘로 이동")
        self.report_button = QPushButton("일일보고 작성")
        self.report_button.setObjectName("primaryButton")
        self.today_button.clicked.connect(self.open_today)
        self.report_button.clicked.connect(self.open_report)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.current_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.today_button)
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

        self._build_menu()
        self._apply_theme_now(self.settings.theme, persist=False)

        self.brand_label = QLabel("make my MiSo")
        self.statusBar().addPermanentWidget(self.brand_label)

        self.statusBar().showMessage(f"설정 파일: {self.settings.path}")
        self.open_today()

    def _build_menu(self) -> None:
        settings_menu = self.menuBar().addMenu("설정")

        greeting_action = QAction("일일보고 설정...", self)
        greeting_action.triggered.connect(self.open_greeting_settings)
        settings_menu.addAction(greeting_action)

        input_menu = settings_menu.addMenu("입력기 호환 모드")
        input_group = QActionGroup(self)
        input_group.setExclusive(True)

        input_options = (
            (INPUT_METHOD_SYSTEM, "시스템 기본값"),
            (INPUT_METHOD_CROSTINI_IBUS, "Crostini 한글 호환 (IBus)"),
        )
        for mode, label in input_options:
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, selected_mode=mode: self.request_input_method_mode(
                    selected_mode
                )
            )
            input_group.addAction(action)
            input_menu.addAction(action)
            self._input_method_actions[mode] = action

        self._sync_input_method_actions()

        self.theme_menu = settings_menu.addMenu("테마")
        self.theme_menu.aboutToHide.connect(self._schedule_pending_theme_apply)

        group = QActionGroup(self)
        group.setExclusive(True)
        for name in theme_names():
            action = QAction(f"{name} - {THEMES[name].description}", self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, theme_name=name: self.request_theme(theme_name)
            )
            group.addAction(action)
            self.theme_menu.addAction(action)
            self._theme_actions[name] = action

    def request_input_method_mode(self, mode: str) -> None:
        self.settings.input_method_mode = mode
        self._sync_input_method_actions()
        self.statusBar().showMessage("입력기 설정 저장 · 재시작 후 적용", 3500)

    def _sync_input_method_actions(self) -> None:
        current = self.settings.input_method_mode
        for mode, action in self._input_method_actions.items():
            action.setChecked(mode == current)

    def request_theme(self, name: str) -> None:
        if name not in THEMES:
            name = "Light"

        self.settings.theme = name
        self._pending_theme = name
        self._sync_theme_actions(name)

    def _schedule_pending_theme_apply(self) -> None:
        QTimer.singleShot(50, self._apply_pending_theme)

    def _apply_pending_theme(self) -> None:
        if self._pending_theme is None:
            return
        name = self._pending_theme
        self._pending_theme = None
        self._apply_theme_now(name, persist=False)

    def _apply_theme_now(self, name: str, *, persist: bool = True) -> None:
        if name not in THEMES:
            name = "Light"

        self.setStyleSheet(stylesheet_for(name))
        if persist:
            self.settings.theme = name
        self._sync_theme_actions(name)
        self.statusBar().showMessage(f"테마 적용: {name}", 2500)

    def _sync_theme_actions(self, name: str) -> None:
        for theme_name, action in self._theme_actions.items():
            action.setChecked(theme_name == name)

    def open_greeting_settings(self) -> None:
        dialog = GreetingSettingsDialog(
            self,
            self.settings.greeting,
            self.settings.footer,
            self.settings.previous_section_title,
            self.settings.today_section_title,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.settings.greeting = dialog.greeting
        self.settings.footer = dialog.footer
        self.settings.previous_section_title = dialog.previous_section_title
        self.settings.today_section_title = dialog.today_section_title
        self._sync_section_titles()
        self.persist_current()
        self.statusBar().showMessage(
            f"문구 저장 완료 · {self.settings.path}",
            3000,
        )

    def _sync_section_titles(self) -> None:
        previous_title = self.settings.previous_section_title
        today_title = self.settings.today_section_title

        self.store.set_section_titles(previous_title, today_title)
        self.previous_editor.set_title(previous_title)
        self.today_editor.set_title(today_title)
        self.tabs.setTabText(0, previous_title)
        self.tabs.setTabText(1, today_title)

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

    def persist_current(self) -> None:
        document = DailyDocument(
            previous_done=self.previous_editor.get_tasks(),
            today_tasks=self.today_editor.get_tasks(),
        )
        path = self.store.save(self.current_date, document)
        self.statusBar().showMessage(f"자동 저장 완료 · {path}", 2500)

    def _current_document(self) -> DailyDocument:
        return DailyDocument(
            previous_done=self.previous_editor.get_tasks(),
            today_tasks=self.today_editor.get_tasks(),
        )

    def open_report(self) -> None:
        ReportDialog(
            self,
            self.current_date,
            self._current_document(),
            self.settings.greeting,
            self.settings.footer,
        ).exec()

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
        self.year_combo.setCurrentIndex(max(self.year_combo.findData(selected.year), 0))
        self.year_combo.blockSignals(False)
        self._year_changed(select_month=selected.month, select_date=selected)

    def _year_changed(
        self,
        *_args: object,
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
        self.month_combo.setCurrentIndex(max(self.month_combo.findData(wanted), 0))
        self.month_combo.blockSignals(False)
        self._reload_date_list(select_date=select_date)

    def _reload_date_list(
        self,
        *_args: object,
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
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()
