# 빌드/배포

WorKing 배포 파일은 PyInstaller로 만듭니다. PyInstaller는 크로스컴파일러가 아니므로 Windows, macOS, Linux 빌드는 각각 해당 OS runner에서 수행합니다.

## 로컬 빌드

빌드 의존성을 설치합니다.

```bash
pip install -r requirements.txt -r requirements-build.txt
```

공통 명령:

```bash
python scripts/build_app.py
```

결과는 플랫폼에 따라 다릅니다.

| 환경 | 결과 |
| --- | --- |
| Windows | `dist/WorKing.exe` |
| macOS | `dist/WorKing.app` |
| Linux / Crostini | `dist/WorKing` |

Linux 결과물은 필요하면 실행 권한을 추가합니다.

```bash
chmod +x dist/WorKing
```

## 앱 아이콘

원본 아이콘은 `assets/app-icon.svg` 하나만 관리합니다.

Windows와 macOS에서는 빌드 시 운영체제용 아이콘 파일을 만든 뒤 PyInstaller의 `--icon` 옵션에 넘깁니다.

| 환경 | 처리 |
| --- | --- |
| Windows | 다중 해상도 `.ico` → `WorKing.exe` |
| macOS | `.icns` → `WorKing.app` |
| Linux / Crostini | SVG를 bundle에 포함하고 Qt window icon으로 사용 |

Linux 빌드에서는 아이콘 변환을 위해 QtGui를 미리 로드하지 않습니다. SVG만 bundle에 넣고 실행 시 렌더링합니다.

Linux의 실행 파일 자체에는 Windows `.ico`처럼 desktop launcher용 아이콘이 내장되지 않습니다. 포터블 실행 파일을 직접 등록할 때는 `WorKing.desktop`의 `Icon=`에 별도 SVG/PNG 파일 경로를 지정합니다. WorKing은 Qt desktop file name을 `WorKing`으로 설정하므로 desktop entry 파일명도 `WorKing.desktop`으로 맞춥니다.

`.deb` 패키지는 `assets/app-icon.svg`를 `/usr/share/icons/hicolor/scalable/apps/WorKing.svg`로 설치하고 desktop entry도 함께 설치합니다.

## Debian 패키지

Linux 실행 파일을 만든 뒤 `scripts/build_deb.py`로 x64/ARM64 Debian 패키지를 만들 수 있습니다. 이 명령은 Linux에서 `dpkg-deb`가 필요합니다.

x64 예:

```bash
python scripts/build_deb.py \
  --binary dist/WorKing \
  --architecture amd64 \
  --version 0.2.0 \
  --output release/WorKing-linux-x64.deb
```

ARM64는 `--architecture arm64`와 `WorKing-linux-arm64.deb` 출력명을 사용합니다.

패키지 설치 구조:

```text
/opt/working/WorKing
/usr/bin/working
/usr/share/applications/WorKing.desktop
/usr/share/icons/hicolor/scalable/apps/WorKing.svg
```

`/usr/bin/working` 런처는 `WORKING_DATA_ROOT`를 `${XDG_DATA_HOME:-$HOME/.local/share}/WorKing`으로 설정하고 실제 실행 파일을 시작합니다. 따라서 시스템 설치 파일과 사용자 데이터를 분리할 수 있습니다.

## GitHub Actions

`.github/workflows/build-release.yml`에서 아래 빌드를 실행합니다.

- Windows x64
- macOS Apple Silicon
- macOS Intel
- Linux x64 단일 실행 파일 + Debian amd64 패키지
- Linux ARM64 단일 실행 파일 + Debian arm64 패키지

Actions 화면에서 수동 실행하면 각 결과물을 artifact로 받을 수 있습니다.

`v*` 태그를 push하면 빌드 완료 후 GitHub Release를 만들고 OS별 파일을 첨부합니다.

```bash
git tag v0.1.0
git push origin v0.1.0
```

배포 파일명:

| 환경 | Release 파일 |
| --- | --- |
| Windows x64 | `WorKing.exe` |
| macOS Apple Silicon | `WorKing-macos-arm64.zip` |
| macOS Intel | `WorKing-macos-x64.zip` |
| Linux/Crostini x64 | `WorKing-linux-x64`, `WorKing-linux-x64.deb` |
| Linux/Crostini ARM64 | `WorKing-linux-arm64`, `WorKing-linux-arm64.deb` |

Release job은 소스 checkout 없이 build artifact만 모아 업로드하므로 GitHub CLI 대상 저장소를 `GH_REPO`로 명시합니다.

## 배포 파일과 데이터 폴더

포터블 배포 파일을 옮길 때 `data/`도 함께 옮기면 업무, 메모, 설정, 터미널/DB 프로필이 그대로 따라갑니다.

```text
WorKing/
├─ WorKing.exe       # Windows
# 또는 WorKing       # Linux
# 또는 WorKing.app   # macOS
└─ data/
```

macOS는 app bundle 내부가 아니라 `WorKing.app`이 놓인 폴더의 `data/`를 사용합니다.

Debian 패키지 설치에서는 런처가 사용자별 `WORKING_DATA_ROOT`를 설정하므로 `~/.local/share/WorKing/` 또는 `$XDG_DATA_HOME/WorKing/`을 사용합니다. 패키지 제거/업그레이드는 이 사용자 데이터 디렉터리를 삭제하지 않습니다.

포터블 실행에서는 실행 위치가 쓰기 불가능해도 홈 디렉터리 등으로 자동 fallback하지 않습니다.

## 플랫폼 참고

### Windows

Windows 터미널 backend는 ConPTY를 위해 `pywinpty==3.0.5`를 사용합니다. PyInstaller 빌드에서는 `winpty` native 파일도 함께 수집합니다.

### Linux / Crostini

Linux 배포 파일은 빌드한 환경의 glibc와 시스템 라이브러리 영향을 받습니다. 오래된 Crostini에서 배포 파일이 실행되지 않으면 [빠른 시작](./getting-started.md)의 소스 실행 방식을 사용할 수 있습니다.

### 코드 서명

현재 자동 빌드는 Windows code signing과 macOS notarization을 하지 않습니다. 처음 실행할 때 SmartScreen 또는 Gatekeeper 확인이 나타날 수 있습니다.
