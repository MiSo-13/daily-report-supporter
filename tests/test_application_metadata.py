from __future__ import annotations

from app.app_meta import APP_NAME, ORGANIZATION_NAME
from app.main_window import _configure_application_metadata


class _FakeApplication:
    def __init__(self) -> None:
        self.application_name = ""
        self.display_name = ""
        self.desktop_file_name = ""
        self.organization_name = ""

    def setApplicationName(self, value: str) -> None:
        self.application_name = value

    def setApplicationDisplayName(self, value: str) -> None:
        self.display_name = value

    def setDesktopFileName(self, value: str) -> None:
        self.desktop_file_name = value

    def setOrganizationName(self, value: str) -> None:
        self.organization_name = value


def test_application_metadata_matches_working_desktop_entry() -> None:
    app = _FakeApplication()

    _configure_application_metadata(app)  # type: ignore[arg-type]

    assert app.application_name == APP_NAME
    assert app.display_name == APP_NAME
    assert app.desktop_file_name == APP_NAME
    assert app.organization_name == ORGANIZATION_NAME
