from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.paths import (
    default_config_root,
    default_database_state_path,
    default_data_root,
    default_memos_root,
    default_reports_root,
    default_terminal_cwd,
    default_terminal_state_path,
)


@dataclass(frozen=True, slots=True)
class AppRuntimePaths:
    data_root: Path
    config_root: Path
    reports_root: Path
    memos_root: Path
    terminal_state_path: Path
    database_state_path: Path
    terminal_cwd: Path


def resolve_runtime_paths(
    *,
    data_root: Path | str | None = None,
    config_root: Path | str | None = None,
    reports_root: Path | str | None = None,
    memos_root: Path | str | None = None,
    terminal_state_path: Path | str | None = None,
    database_state_path: Path | str | None = None,
    terminal_cwd: Path | str | None = None,
) -> AppRuntimePaths:
    if data_root is not None:
        resolved_data_root = Path(data_root)
    elif reports_root is not None:
        resolved_data_root = Path(reports_root).parent
    else:
        resolved_data_root = default_data_root()

    resolved_reports_root = (
        Path(reports_root)
        if reports_root is not None
        else (
            resolved_data_root / "reports"
            if data_root is not None
            else default_reports_root()
        )
    )

    resolved_memos_root = (
        Path(memos_root)
        if memos_root is not None
        else (
            resolved_data_root / "memos"
            if data_root is not None or reports_root is not None
            else default_memos_root()
        )
    )

    resolved_config_root = (
        Path(config_root)
        if config_root is not None
        else (
            resolved_data_root / "config"
            if data_root is not None or reports_root is not None
            else default_config_root()
        )
    )

    resolved_terminal_state_path = (
        Path(terminal_state_path)
        if terminal_state_path is not None
        else (
            resolved_config_root / "terminal-sessions.json"
            if (
                config_root is not None
                or data_root is not None
                or reports_root is not None
            )
            else default_terminal_state_path()
        )
    )

    resolved_database_state_path = (
        Path(database_state_path)
        if database_state_path is not None
        else (
            resolved_config_root / "database-connections.json"
            if (
                config_root is not None
                or data_root is not None
                or reports_root is not None
            )
            else default_database_state_path()
        )
    )

    resolved_terminal_cwd = (
        Path(terminal_cwd)
        if terminal_cwd is not None
        else (
            resolved_data_root
            if data_root is not None or reports_root is not None
            else default_terminal_cwd()
        )
    )

    return AppRuntimePaths(
        data_root=resolved_data_root,
        config_root=resolved_config_root,
        reports_root=resolved_reports_root,
        memos_root=resolved_memos_root,
        terminal_state_path=resolved_terminal_state_path,
        database_state_path=resolved_database_state_path,
        terminal_cwd=resolved_terminal_cwd,
    )
