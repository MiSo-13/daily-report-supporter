from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QWidget

from app.markdown_store import MarkdownStore
from app.models import DailyDocument, Task
from app.project_store import ProjectStore
from app.project_workspace import ProjectDialog, ProjectWorkspace
from app.settings import AppSettings


_APP = QApplication.instance() or QApplication([])


def test_project_workspace_empty_state_and_create(tmp_path, monkeypatch):
    store = ProjectStore(tmp_path / "config")
    parent = QWidget()
    messages: list[str] = []
    workspace = ProjectWorkspace(store, parent, messages.append)
    assert workspace.project_list.count() == 0
    assert not workspace.edit_button.isEnabled()

    def accept_create(dialog):
        dialog.name_input.setText(" WorKing ")
        dialog.description_input.setPlainText("설명")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ProjectDialog, "exec", accept_create)
    workspace.create_project()
    assert workspace.project_list.count() == 1
    assert workspace.project_list.currentItem().text() == "WorKing"
    assert workspace.title_label.text() == "<b>WorKing</b>"
    assert store.list_projects()[0].description == "설명"
    assert messages[-1] == "프로젝트 생성 완료"


def test_project_workspace_edit_archive_restore_and_search(tmp_path, monkeypatch):
    store = ProjectStore(tmp_path / "config")
    first = store.create("첫 프로젝트")
    store.create("다른 프로젝트")
    parent = QWidget()
    workspace = ProjectWorkspace(store, parent, lambda _: None)
    workspace.selected_id = first.id
    workspace.refresh()

    def accept_edit(dialog):
        dialog.name_input.setText("수정된 이름")
        dialog.description_input.setPlainText("수정된 설명")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ProjectDialog, "exec", accept_edit)
    workspace.edit_project()
    assert store.get(first.id).name == "수정된 이름"
    assert store.get(first.id).description == "수정된 설명"

    workspace.search_input.setText("수정된")
    assert workspace.project_list.count() == 1
    workspace.archive_project()
    assert workspace.project_list.count() == 0
    assert store.get(first.id).archived

    workspace.show_archived.setChecked(True)
    assert workspace.project_list.count() == 1
    assert "보관됨" in workspace.project_list.item(0).text()
    workspace.restore_project()
    assert not store.get(first.id).archived


def test_project_ui_does_not_rewrite_existing_settings_or_reports(tmp_path):
    config = tmp_path / "config"
    reports = tmp_path / "reports"
    settings = AppSettings(config)
    settings.theme = "Dark"
    store = MarkdownStore(reports)
    day = date(2026, 11, 20)
    store.save(day, DailyDocument(today_tasks=[Task("기존 독립 업무")]))
    original_settings = (config / "settings.json").read_bytes()
    original_report = store.path_for(day).read_bytes()

    workspace = ProjectWorkspace(ProjectStore(config), QWidget(), lambda _: None)
    project = workspace.store.create("신규 프로젝트")
    workspace.refresh()
    assert project.id
    assert (config / "settings.json").read_bytes() == original_settings
    assert store.path_for(day).read_bytes() == original_report
    assert store.load(day).today_tasks[0].project_id is None


def test_project_name_is_escaped_in_rich_label(tmp_path):
    store = ProjectStore(tmp_path)
    store.create("<script>alert(1)</script>")
    workspace = ProjectWorkspace(store, QWidget(), lambda _: None)
    assert "<script>" not in workspace.title_label.text()
    assert "&lt;script&gt;" in workspace.title_label.text()
