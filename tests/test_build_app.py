from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = ROOT / "scripts" / "build_app.py"


def _load_build_module(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "app.app_icon":
            raise AssertionError(
                "Linux 빌드 스크립트 import 시 app.app_icon을 선행 로드하면 안 됩니다."
            )
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    spec = importlib.util.spec_from_file_location(
        "working_build_app_test",
        BUILD_SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_script_import_does_not_require_qt_icon_module(monkeypatch) -> None:
    module = _load_build_module(monkeypatch)

    assert module.APP_ICON_SOURCE == ROOT / "assets" / "app-icon.svg"


def test_linux_build_skips_package_icon_rendering(monkeypatch) -> None:
    module = _load_build_module(monkeypatch)
    commands: list[list[str]] = []

    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(
        module,
        "_prepare_build_icon",
        lambda: (_ for _ in ()).throw(
            AssertionError("Linux에서는 패키지 아이콘 변환을 호출하면 안 됩니다.")
        ),
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda args, **_kwargs: commands.append(args),
    )

    module.build()

    assert len(commands) == 1
    command = commands[0]
    assert "--onefile" in command
    assert "--icon" not in command
    assert (
        f"{module.APP_ICON_SOURCE}:{module.APP_ICON_BUNDLE_DIR}"
        in command
    )
