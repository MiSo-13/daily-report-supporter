from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QActionGroup, QCloseEvent, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import (
    FontSettingsDialog,
    GreetingSettingsDialog,
    ReportDialog,
)
from app.app_icon import create_app_icon
from app.app_meta import APP_NAME, ORGANIZATION_NAME
from app.database_workspace import DatabaseWorkspace
from app.markdown_store import MarkdownStore
from app.memo_workspace import MemoWorkspace
from app.models import DailyDocument, Task, TaskStatus
from app.runtime_paths import AppRuntimePaths, resolve_runtime_paths
from app.status_bar import AppStatusInfo
from app.settings import (
    AppSettings,
    INPUT_METHOD_CROSTINI_IBUS,
    INPUT_METHOD_SYSTEM,
)
from app.task_editor import TaskEditor
from app.terminal_workspace import TerminalWorkspace
from app.themes import THEMES, stylesheet_for, theme_names


class MainWindow(QMainWindow):
    def __init__(
        self,
        data_root: Path | str | None = None,
        config_root: Path | str | None = None,
        reports_root: Path | str | None = None,
        memos_root: Path | str | None = None,
        terminal_state_path: Path | str | None = None,
        database_state_path: Path | str | None = None,
        terminal_cwd: Path | str | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self._default_application_font = QFont(QApplication.font())

        paths = resolve_runtime_paths(
            data_root=data_root,
            config_root=config_root,
            reports_root=reports_root,
            memos_root=memos_root,
            terminal_state_path=terminal_state_path,
            database_state_path=database_state_path,
            terminal_cwd=terminal_cwd,
        )
        self._initialize_state(paths)
        self._build_work_workspace()
        self._build_memo_workspace()
        self._build_terminal_workspace()
        self._build_database_workspace()
        self._build_workspace_shell()
        self._build_status_area()

        self._build_shortcuts()
        self._build_menu()
        self._apply_theme_now(self.settings.theme, persist=False)
        self.open_today()

    def _initialize_state(self, paths: AppRuntimePaths) -> None:
        self.settings = AppSettings(paths.config_root)
        self._apply_application_font()

        self.store = MarkdownStore(
            paths.reports_root,
            previous_section_title=self.settings.previous_section_title,
            today_section_title=self.settings.today_section_title,
        )
        self.paths = paths
        self.current_date = date.today()
        self._legacy_previous_done: list[Task] = []

        self._theme_actions: dict[str, QAction] = {}
        self._input_method_actions: dict[str, QAction] = {}
        self._pending_theme: str | None = None

    def _build_work_workspace(self) -> None:
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("단어로 전체 문서 검색")
        self.search_input.setClearButtonEnabled(True)

        self.search_count_label = QLabel("")
        self.search_count_label.setVisible(False)

        self.search_results = QListWidget()
        self.search_results.setWordWrap(True)
        self.search_results.setVisible(False)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)

        self.year_combo = QComboBox()
        self.month_combo = QComboBox()
        self.date_list = QListWidget()

        self.search_input.textChanged.connect(self._search_text_changed)
        self.search_timer.timeout.connect(self._run_search)
        self.search_results.itemClicked.connect(self._search_result_selected)
        self.year_combo.currentIndexChanged.connect(self._year_changed)
        self.month_combo.currentIndexChanged.connect(self._reload_date_list)
        self.date_list.itemSelectionChanged.connect(self._date_selected)

        self.work_nav = QWidget()
        nav_layout = QVBoxLayout(self.work_nav)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(8)
        nav_layout.addWidget(QLabel("<b>전체 검색</b>"))
        nav_layout.addWidget(self.search_input)
        nav_layout.addWidget(self.search_count_label)
        nav_layout.addWidget(self.search_results, 1)

        self.date_nav_label = QLabel("<b>일일 문서</b>")
        nav_layout.addWidget(self.date_nav_label)
        nav_layout.addWidget(self.year_combo)
        nav_layout.addWidget(self.month_combo)
        nav_layout.addWidget(self.date_list, 1)

        self.today_editor = TaskEditor(
            self.settings.today_section_title,
            self.persist_current,
            default_status=TaskStatus.PLANNED,
        )

        self.current_label = QLabel()
        self.today_button = QPushButton("오늘로 이동")
        self.report_button = QPushButton("일일보고 작성")
        self.report_button.setObjectName("primaryButton")
        self.today_button.clicked.connect(self.open_today)
        self.report_button.clicked.connect(self.open_report)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.current_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.today_button)
        toolbar.addWidget(self.report_button)

        self.work_content = QWidget()
        content_layout = QVBoxLayout(self.work_content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)
        content_layout.addLayout(toolbar)
        content_layout.addWidget(self.today_editor, 1)

    def _build_memo_workspace(self) -> None:
        self.memo_workspace = MemoWorkspace(
            self.paths.memos_root,
            self,
            self.statusBar().showMessage,
        )
        self.memo_editor = self.memo_workspace.editor
        self.memo_sidebar = self.memo_workspace.sidebar

    def _build_terminal_workspace(self) -> None:
        self.terminal_workspace = TerminalWorkspace(
            self.paths.terminal_state_path,
            self.paths.terminal_cwd,
            self,
            font_family=self.settings.terminal_font_family,
            font_size=self.settings.terminal_font_size,
        )
        self.terminal_panel = self.terminal_workspace.panel
        self.terminal_sidebar = self.terminal_workspace.sidebar

    def _build_database_workspace(self) -> None:
        self.database_workspace = DatabaseWorkspace(
            self.paths.database_state_path,
            self,
            self.statusBar().showMessage,
        )
        self.database_panel = self.database_workspace.panel
        self.database_sidebar = self.database_workspace.sidebar

    def _build_workspace_shell(self) -> None:
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(self.work_nav, "업무")
        self.workspace_tabs.addTab(self.memo_sidebar, "메모")
        self.workspace_tabs.addTab(self.terminal_sidebar, "터미널")
        self.workspace_tabs.addTab(self.database_sidebar, "DB")
        self.workspace_tabs.currentChanged.connect(self._workspace_changed)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.work_content)
        self.content_stack.addWidget(self.memo_editor)
        self.content_stack.addWidget(self.terminal_panel)
        self.content_stack.addWidget(self.database_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.addWidget(self.workspace_tabs)
        splitter.addWidget(self.content_stack)
        splitter.setSizes([280, 900])

        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(10, 10, 10, 10)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _build_status_area(self) -> None:
        self.status_info = AppStatusInfo(self)
        self.statusBar().addPermanentWidget(self.status_info, 1)
        self.status_info.set_resource_visible(
            self.settings.show_resource_usage
        )

    def _build_shortcuts(self) -> None:
        file_menu = self.menuBar().addMenu("파일")
        save_action = QAction("저장", self)
        save_action.setShortcuts(
            QKeySequence.keyBindings(QKeySequence.StandardKey.Save)
        )
        save_action.triggered.connect(self.save_current)
        file_menu.addAction(save_action)

    def save_current(self) -> None:
        workspace_index = self.workspace_tabs.currentIndex()
        if workspace_index == 1:
            self.memo_workspace.save_current()
            return
        if workspace_index in (2, 3):
            return

        self.today_editor.save_current()
        self.statusBar().showMessage("저장 완료", 1800)

    def _workspace_changed(self, index: int) -> None:
        if index != 1:
            self.memo_workspace.save_if_dirty()

        self.content_stack.setCurrentIndex(index)

        if index == 1:
            self.memo_workspace.activate()
        elif index == 2:
            self.terminal_workspace.activate()
        elif index == 3:
            self.database_workspace.activate()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.status_info.shutdown()
        self.memo_workspace.save_if_dirty()
        self.terminal_workspace.shutdown()
        self.database_workspace.shutdown()
        super().closeEvent(event)

    def _build_menu(self) -> None:
        settings_menu = self.menuBar().addMenu("설정")

        greeting_action = QAction("일일보고 설정...", self)
        greeting_action.triggered.connect(self.open_greeting_settings)
        settings_menu.addAction(greeting_action)

        font_action = QAction("폰트...", self)
        font_action.triggered.connect(self.open_font_settings)
        settings_menu.addAction(font_action)

        resource_action = QAction("CPU / RAM 표시", self)
        resource_action.setCheckable(True)
        resource_action.setChecked(self.settings.show_resource_usage)
        resource_action.triggered.connect(
            self.request_resource_usage_visibility
        )
        settings_menu.addAction(resource_action)

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

    def request_resource_usage_visibility(
        self,
        visible: bool,
    ) -> None:
        self.settings.show_resource_usage = visible
        self.status_info.set_resource_visible(visible)

        state = "표시" if visible else "숨김"
        self.statusBar().showMessage(
            f"CPU / RAM 사용량 {state}",
            1800,
        )

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

    def _apply_application_font(self) -> None:
        font = QFont(self._default_application_font)
        if self.settings.font_family:
            font.setFamily(self.settings.font_family)
        font.setPointSize(self.settings.font_size)
        QApplication.setFont(font)

    def _apply_font_settings(self) -> None:
        self._apply_application_font()
        self.memo_editor.apply_font_settings()
        self.terminal_workspace.set_font(
            self.settings.terminal_font_family,
            self.settings.terminal_font_size,
        )

    def open_font_settings(self) -> None:
        dialog = FontSettingsDialog(
            self,
            self.settings.font_family,
            self.settings.font_size,
            self.settings.terminal_font_family,
            self.settings.terminal_font_size,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.settings.set_font_settings(
            font_family=dialog.font_family,
            font_size=dialog.font_size,
            terminal_font_family=dialog.terminal_font_family,
            terminal_font_size=dialog.terminal_font_size,
        )
        self._apply_font_settings()
        self.statusBar().showMessage("폰트 설정 적용", 2500)

    def open_greeting_settings(self) -> None:
        dialog = GreetingSettingsDialog(
            self,
            self.settings.greeting,
            self.settings.footer,
            self.settings.progress_report_title,
            self.settings.planned_report_title,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.settings.greeting = dialog.greeting
        self.settings.footer = dialog.footer
        self.settings.progress_report_title = dialog.progress_report_title
        self.settings.planned_report_title = dialog.planned_report_title
        self.statusBar().showMessage("설정 저장", 1800)

    def _sync_section_titles(self) -> None:
        today_title = self.settings.today_section_title

        self.store.set_section_titles(
            self.settings.previous_section_title,
            today_title,
        )
        self.today_editor.set_title(today_title)

    def open_today(self) -> None:
        self.search_input.clear()
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
        self._legacy_previous_done = document.previous_done
        self.today_editor.set_tasks(document.today_tasks)

    def persist_current(self) -> None:
        document = DailyDocument(
            previous_done=list(self._legacy_previous_done),
            today_tasks=self.today_editor.get_tasks(),
        )
        path = self.store.save(self.current_date, document)
        if self.search_input.text().strip():
            self._run_search()
        self.statusBar().showMessage("저장 완료", 1800)

    def _current_document(self) -> DailyDocument:
        return DailyDocument(
            previous_done=list(self._legacy_previous_done),
            today_tasks=self.today_editor.get_tasks(),
        )

    def open_report(self) -> None:
        ReportDialog(
            self,
            self.current_date,
            self._current_document(),
            self.settings.greeting,
            self.settings.footer,
            self.settings.progress_report_title,
            self.settings.planned_report_title,
        ).exec()


    def _search_text_changed(self, text: str) -> None:
        active = bool(text.strip())
        self._set_search_mode(active)

        if not active:
            self.search_timer.stop()
            self.search_results.clear()
            self.search_count_label.clear()
            return

        self.search_timer.start()

    def _set_search_mode(self, active: bool) -> None:
        self.search_count_label.setVisible(active)
        self.search_results.setVisible(active)

        self.date_nav_label.setVisible(not active)
        self.year_combo.setVisible(not active)
        self.month_combo.setVisible(not active)
        self.date_list.setVisible(not active)

    def _run_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return

        results = self.store.search(query)

        self.search_results.blockSignals(True)
        self.search_results.clear()
        self.search_count_label.setText(f"{len(results)}건")

        if not results:
            self.search_results.addItem("검색 결과 없음")
        else:
            for result in results:
                status = (
                    f"[{result.status.value}] "
                    if result.status is not None
                    else ""
                )
                legacy = " · 이전 데이터" if result.legacy else ""
                item = QListWidgetItem(
                    f"{result.target:%Y-%m-%d} · "
                    f"{status}{result.title}{legacy}\n"
                    f"{result.snippet}"
                )
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "date": result.target.isoformat(),
                        "task_index": result.task_index,
                        "legacy": result.legacy,
                    },
                )
                item.setToolTip(str(self.store.path_for(result.target)))
                self.search_results.addItem(item)

        self.search_results.blockSignals(False)

    def _search_result_selected(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return

        raw_date = payload.get("date")
        if not isinstance(raw_date, str):
            return

        self.load_date(date.fromisoformat(raw_date))

        task_index = payload.get("task_index")
        legacy = bool(payload.get("legacy"))
        if isinstance(task_index, int) and not legacy:
            self.today_editor.select_task(task_index)

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


def run(startup_message: str = "") -> int:
    app = QApplication([])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setStyle("Fusion")
    icon = create_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    if startup_message:
        QTimer.singleShot(
            0,
            lambda: window.statusBar().showMessage(startup_message, 6000),
        )
    return app.exec()
