# 빌드와 배포

PyInstaller로 실행파일을 만들 수 있습니다.

PyInstaller는 크로스컴파일러가 아니므로 Windows용은 Windows에서, macOS용은 macOS에서, Linux용은 Linux에서 각각 빌드합니다.

## Release에서 받기

GitHub Releases:

https://github.com/MiSo-13/daily-report-supporter/releases/latest

배포 파일:

| 환경 | 파일 |
| --- | --- |
| Windows x64 | `WorKing.exe` |
| macOS Apple Silicon | `WorKing-macos-arm64.zip` |
| macOS Intel | `WorKing-macos-x64.zip` |
| ChromeOS/Crostini x64 | `WorKing-linux-x64` |
| ChromeOS/Crostini ARM64 | `WorKing-linux-arm64` |

Windows 사용자는 `.exe` 하나만 받아 실행하면 Python 설치가 필요하지 않습니다.

## 직접 빌드

먼저 빌드 의존성을 설치합니다.

```bash
pip install -r requirements.txt -r requirements-build.txt
```

공통 빌드 명령:

```bash
python scripts/build_app.py
```

### Windows

결과:

```text
dist/WorKing.exe
```

단일 실행파일이며 콘솔 창 없이 실행됩니다.

### macOS

결과:

```text
dist/WorKing.app
```

macOS에서는 PyInstaller 권장 방식에 맞춰 `.app` bundle을 생성합니다.

### Linux / ChromeOS Crostini

결과:

```text
dist/WorKing
```

필요하면 실행 권한을 부여합니다.

```bash
chmod +x dist/WorKing
```

## 앱 아이콘

앱 아이콘 원본은 `assets/app-icon.svg` 하나로 관리합니다. 투명 배경의 초록색 WorKing 로고이며 소스 실행과 배포 실행에서 동일하게 사용합니다.

빌드 시 `scripts/build_app.py`가 SVG를 1024px PNG로 렌더링한 뒤 운영체제에 맞는 패키지 아이콘을 생성합니다.

| 환경 | 빌드 아이콘 |
| --- | --- |
| Windows | 다중 해상도 `.ico` 생성 후 `WorKing.exe`에 포함 |
| macOS | `.icns` 생성 후 `WorKing.app` bundle icon으로 포함 |
| Linux / Crostini | Qt 실행 창/Taskbar 아이콘에 동일 SVG 사용 |

Windows/macOS 변환에는 빌드 의존성인 Pillow를 사용합니다. 생성되는 `build/app-icon.*` 파일은 임시 빌드 산출물이므로 Git에 저장하지 않습니다.

PyInstaller onefile/onedir 실행에서도 런타임 아이콘을 사용할 수 있도록 `assets/app-icon.svg`를 bundle data에 포함합니다.

Linux 빌드에서는 패키지용 `.ico`/`.icns` 변환이 필요하지 않으므로 `scripts/build_app.py`가 Qt 아이콘 렌더러를 import하지 않습니다. SVG는 그대로 bundle data에 포함하고, 실행 시 Qt가 창/Taskbar 아이콘으로 렌더링합니다. 따라서 Linux 빌드 runner가 아이콘 변환 때문에 `libEGL.so.1` 같은 GUI native library를 선행 요구하지 않습니다.

## GitHub Actions

`.github/workflows/build-release.yml`에서 OS별 빌드를 실행합니다.

Actions 화면에서 수동 실행하면 빌드 artifact를 확인할 수 있습니다.

Release를 만들려면 태그를 push합니다.

```bash
git tag v0.1.0
git push origin v0.1.0
```

태그 빌드가 모두 성공하면 해당 GitHub Release에 OS별 파일이 자동 첨부됩니다.

Release job은 소스 checkout 없이 artifact만 모아 업로드하므로 GitHub CLI 대상 저장소를 `GH_REPO=${{ github.repository }}`로 명시합니다. 이 설정이 없으면 `gh release`가 현재 디렉터리에서 Git 저장소를 찾다가 `fatal: not a git repository` 오류로 실패할 수 있습니다.

기존 설치본의 `DailyReportSupporter` 데이터는 첫 실행 시 현재 앱 옆 Portable `data/`로 자동 복사합니다.

## Portable 데이터 위치

WorKing은 실행 위치 옆의 `data/`만 사용자 데이터 저장소로 사용합니다.

소스 실행:

```text
<repository>/
├─ main.py
└─ data/
```

Windows:

```text
WorKing/
├─ WorKing.exe
└─ data/
```

Linux / ChromeOS Crostini:

```text
WorKing/
├─ WorKing
└─ data/
```

macOS:

```text
WorKing/
├─ WorKing.app
└─ data/
```

macOS에서는 PyInstaller bundle 내부의 `Contents/MacOS`가 아니라 `WorKing.app`이 놓인 외부 폴더를 기준으로 합니다.

앱을 다른 폴더로 옮길 때 `data/`도 같이 옮기면 업무/메모/설정/터미널/DB 프로필이 함께 이동합니다. 실행 위치에 쓰기 권한이 없으면 다른 사용자 디렉터리로 fallback하지 않고 오류를 표시합니다.

기존 사용자 데이터는 첫 실행 시 `~/DailyReportSupporter/`, 전환 `~/WorKing/`, 또는 소스 저장소의 기존 파일을 읽어 현재 앱 옆 `data/`로 복사합니다. 기존 원본은 그대로 보존합니다.

## 서명

현재 자동 빌드는 코드 서명/공증을 하지 않습니다.

따라서 처음 실행할 때:

- Windows: SmartScreen 경고가 표시될 수 있습니다.
- macOS: Gatekeeper 경고가 표시될 수 있습니다.

공개 배포를 본격적으로 할 경우 Windows 코드 서명 인증서와 Apple Developer ID/notarization을 추가하는 것을 권장합니다.

## ChromeOS 참고

Crostini x64와 ARM64 빌드를 각각 제공합니다.

Linux 실행파일은 시스템의 glibc 버전에 영향을 받습니다. 배포 실행파일이 동작하지 않는 오래된 Crostini 환경에서는 [빠른 시작](./getting-started.md)의 Python 실행 방식을 사용하면 됩니다.


## Windows 터미널 빌드

Windows 터미널은 ConPTY를 위해 `pywinpty==3.0.5`를 사용합니다. `requirements.txt`의 platform marker로 Windows에서만 설치됩니다.

PyInstaller Windows 빌드는 `winpty`의 native binary를 포함하기 위해 `--collect-all winpty`를 사용합니다.
