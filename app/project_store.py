from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from app.models import Project

PROJECTS_FILE_NAME = "projects.json"


class ProjectStore:
    """프로젝트 정의를 config/projects.json에 보관한다."""

    def __init__(self, config_root: Path | str) -> None:
        self.path = Path(config_root) / PROJECTS_FILE_NAME

    def list_projects(self, *, include_archived: bool = False) -> list[Project]:
        projects = self._load()
        if include_archived:
            return projects
        return [project for project in projects if not project.archived]

    def get(self, project_id: str) -> Project | None:
        return next(
            (project for project in self._load() if project.id == project_id),
            None,
        )

    def create(self, name: str, description: str = "") -> Project:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("프로젝트 이름을 입력하세요.")
        projects = self._load()
        project = Project(
            id=str(uuid4()),
            name=normalized_name,
            description=description,
        )
        projects.append(project)
        self._save(projects)
        return project

    def update(
        self,
        project_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        archived: bool | None = None,
    ) -> Project:
        projects = self._load()
        for index, project in enumerate(projects):
            if project.id != project_id:
                continue
            if name is not None and not name.strip():
                raise ValueError("프로젝트 이름을 입력하세요.")
            updated = replace(
                project,
                name=project.name if name is None else name.strip(),
                description=project.description if description is None else description,
                archived=project.archived if archived is None else archived,
            )
            projects[index] = updated
            self._save(projects)
            return updated
        raise KeyError(f"존재하지 않는 프로젝트: {project_id}")

    def archive(self, project_id: str) -> Project:
        return self.update(project_id, archived=True)

    def _load(self) -> list[Project]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("지원하지 않는 프로젝트 저장 형식입니다.")
        records = data.get("projects")
        if not isinstance(records, list):
            raise ValueError("프로젝트 목록 형식이 올바르지 않습니다.")
        projects: list[Project] = []
        seen: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("프로젝트 항목 형식이 올바르지 않습니다.")
            project_id = record.get("id")
            name = record.get("name")
            description = record.get("description", "")
            archived = record.get("archived", False)
            if (
                not isinstance(project_id, str) or not project_id
                or project_id in seen
                or not isinstance(name, str) or not name.strip()
                or not isinstance(description, str)
                or not isinstance(archived, bool)
            ):
                raise ValueError("프로젝트 데이터가 손상되었습니다.")
            seen.add(project_id)
            projects.append(Project(project_id, name, description, archived))
        return projects

    def _save(self, projects: list[Project]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "archived": project.archived,
                }
                for project in projects
            ],
        }
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=".projects-", suffix=".tmp", delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
