import main
from app.qt_platform import CrostiniDependencyError
from app.settings import AppSettings, INPUT_METHOD_CROSTINI_IBUS


def test_auto_setup_retries_after_install(monkeypatch) -> None:
    calls = {"count": 0}

    def configure() -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise CrostiniDependencyError(
                "missing",
                ("libxcb-cursor.so.0",),
            )

    monkeypatch.setattr(main, "configure_qt_platform", configure)
    monkeypatch.setattr(
        main,
        "install_crostini_dependencies",
        lambda: True,
    )

    assert main._configure_platform_with_auto_setup()
    assert calls["count"] == 2


def test_auto_setup_stops_when_install_fails(monkeypatch) -> None:
    def configure() -> None:
        raise CrostiniDependencyError(
            "missing",
            ("libxcb-cursor.so.0",),
        )

    monkeypatch.setattr(main, "configure_qt_platform", configure)
    monkeypatch.setattr(
        main,
        "install_crostini_dependencies",
        lambda: False,
    )

    assert not main._configure_platform_with_auto_setup()


def test_auto_setup_does_not_install_for_display_error(monkeypatch) -> None:
    def configure() -> None:
        raise CrostiniDependencyError("DISPLAY missing")

    install_called = {"value": False}

    def install() -> bool:
        install_called["value"] = True
        return True

    monkeypatch.setattr(main, "configure_qt_platform", configure)
    monkeypatch.setattr(main, "install_crostini_dependencies", install)

    assert not main._configure_platform_with_auto_setup()
    assert not install_called["value"]


def test_input_method_setting_is_applied_from_reports(tmp_path, monkeypatch) -> None:
    settings = AppSettings(tmp_path)
    settings.input_method_mode = INPUT_METHOD_CROSTINI_IBUS

    received = {"mode": None}

    monkeypatch.setattr(main, "REPORTS_ROOT", tmp_path)
    monkeypatch.setattr(
        main,
        "configure_input_method",
        lambda mode: received.update(mode=mode),
    )

    main._configure_input_method_from_settings()

    assert received["mode"] == INPUT_METHOD_CROSTINI_IBUS
