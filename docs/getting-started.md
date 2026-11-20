# 빠른 시작

## Release 파일로 실행

[GitHub Releases](https://github.com/MiSo-13/daily-report-supporter/releases/latest)에서 운영체제에 맞는 파일을 받습니다.

| 환경 | 파일 |
| --- | --- |
| Windows x64 | `WorKing.exe` |
| macOS Apple Silicon | `WorKing-macos-arm64.zip` |
| macOS Intel | `WorKing-macos-x64.zip` |
| ChromeOS/Crostini x64 | `WorKing-linux-x64.deb` 또는 `WorKing-linux-x64` |
| ChromeOS/Crostini ARM64 | `WorKing-linux-arm64.deb` 또는 `WorKing-linux-arm64` |

### Windows

다운로드한 `WorKing.exe`를 쓰기 가능한 폴더에 두고 실행합니다. WorKing은 실행 파일 옆에 `data/`를 만들기 때문에 `Program Files`보다는 사용자 폴더 아래 전용 디렉터리가 편합니다.

### macOS

zip을 풀어 `WorKing.app`을 실행합니다. 현재 자동 빌드는 Apple notarization을 하지 않으므로 처음 실행할 때 Gatekeeper 확인이 필요할 수 있습니다.

### ChromeOS / Crostini

먼저 Crostini 터미널에서 아키텍처를 확인합니다.

```bash
uname -m
```

- `x86_64`: x64 패키지
- `aarch64` 또는 ARM64: ARM64 패키지

#### .deb 설치 — 권장

x64:

```bash
sudo apt install ./WorKing-linux-x64.deb
```

ARM64:

```bash
sudo apt install ./WorKing-linux-arm64.deb
```

설치하면 다음 항목이 함께 등록됩니다.

- `/opt/working/WorKing`: 앱 실행 파일
- `/usr/bin/working`: 터미널 실행 명령
- `/usr/share/applications/WorKing.desktop`: Linux 앱 메뉴
- `/usr/share/icons/hicolor/scalable/apps/WorKing.svg`: SVG 아이콘
- Qt/X11 및 SSH client runtime dependency

설치 후 ChromeOS의 Linux 앱 목록에서 `WorKing`을 실행하거나 터미널에서 다음 명령을 사용할 수 있습니다.

```bash
working
```

새 버전은 같은 방식으로 새 `.deb`를 설치하면 업그레이드됩니다.

```bash
sudo apt install ./WorKing-linux-x64.deb
```

앱 패키지를 제거하려면:

```bash
sudo apt remove working
```

사용자 데이터는 패키지 제거 시 삭제하지 않습니다.

`.deb` 설치 버전은 시스템 설치 경로가 아닌 다음 사용자 경로에 데이터를 저장합니다.

```text
~/.local/share/WorKing/
├─ config/
├─ reports/
└─ memos/
```

`XDG_DATA_HOME`이 설정되어 있으면 `$XDG_DATA_HOME/WorKing/`을 사용합니다.

기존에 `~/apps/WorKing/data/` 같은 포터블 위치를 사용했다면 앱을 종료한 상태에서 데이터를 한 번 복사할 수 있습니다.

```bash
mkdir -p ~/.local/share/WorKing
cp -a ~/apps/WorKing/data/. ~/.local/share/WorKing/
```

포터블 앱의 위치는 사용자마다 다르므로 이 이동은 자동으로 추정하지 않습니다.

#### 단일 실행 파일로 사용

설치하지 않고 포터블 파일을 계속 사용할 수도 있습니다. 예를 들어 x64 파일을 `~/apps/WorKing/`에 둘 경우:

```bash
mkdir -p ~/apps/WorKing
mv WorKing-linux-x64 ~/apps/WorKing/
chmod +x ~/apps/WorKing/WorKing-linux-x64
~/apps/WorKing/WorKing-linux-x64
```

단일 실행 파일은 기존처럼 실행 파일 옆 `data/`를 사용합니다.

Qt/X11 라이브러리가 부족하면 저장소의 `scripts/setup_crostini.sh`와 같은 패키지 구성이 필요합니다. 소스 실행 환경에서는 아래처럼 설치할 수 있습니다.

```bash
bash scripts/setup_crostini.sh
```

한글 입력이 불안정하면 앱에서 `설정 → 입력기 호환 모드 → Crostini 한글 호환 (IBus)`를 선택하고 재시작합니다.

단일 실행 파일을 ChromeOS Linux 앱 목록에 직접 등록하려면 desktop entry 파일명을 `WorKing.desktop`으로 맞춥니다. WorKing도 Qt desktop file name을 `WorKing`으로 사용합니다.

SVG 아이콘을 쓰려면 아이콘 파일을 실행 파일과 함께 보관한 뒤 `Icon=`에 절대 경로를 지정합니다.

예:

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=WorKing
Exec=/home/<user>/apps/WorKing/WorKing-linux-x64
Path=/home/<user>/apps/WorKing
Icon=/home/<user>/apps/WorKing/app-icon.svg
Terminal=false
Categories=Office;Utility;
StartupNotify=true
```

저장 위치:

```text
~/.local/share/applications/WorKing.desktop
```

desktop entry나 아이콘을 바꾼 뒤에는 `update-desktop-database ~/.local/share/applications`를 실행하고 WorKing을 완전히 종료한 뒤 Linux 앱 목록에서 다시 실행합니다.

## 소스에서 실행

Python 3.11 이상을 권장합니다.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### macOS / Linux / Crostini

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Crostini에서 Qt 의존성이 없으면:

```bash
bash scripts/setup_crostini.sh
```

일반 Linux에서는 Crostini 전용 `xcb` 설정을 강제하지 않고 시스템의 Qt platform 설정을 따릅니다.

## 첫 실행과 데이터 폴더

WorKing은 현재 실행 위치 옆 `data/`를 사용합니다.

소스 실행:

```text
daily-report-supporter/
├─ main.py
└─ data/
   ├─ config/
   ├─ reports/
   └─ memos/
```

포터블 배포 파일:

```text
WorKing/
├─ WorKing.exe       # Windows
# 또는 WorKing-linux-x64 / WorKing-linux-arm64
# 또는 WorKing.app
└─ data/
   ├─ config/
   ├─ reports/
   └─ memos/
```

macOS는 `WorKing.app/Contents` 내부가 아니라 `.app`이 놓인 폴더를 기준으로 합니다. Crostini `.deb` 설치는 예외로 `~/.local/share/WorKing/` 또는 `$XDG_DATA_HOME/WorKing/`을 사용합니다.

기존 버전의 `~/DailyReportSupporter/`, `~/WorKing/` 또는 예전 소스 실행 위치에 데이터가 있으면 첫 실행 시 현재 `data/`로 복사합니다. 기존 파일은 지우지 않고, 새 위치에 이미 있는 파일도 덮어쓰지 않습니다.

실행 위치에 쓰기 권한이 없으면 다른 디렉터리로 자동 우회하지 않고 오류를 표시합니다.

## 첫 업무 작성

업무 탭에서 제목과 상태를 입력하고 `+ 업무 추가`를 누릅니다. 관련 문서나 주요 내용이 있으면 함께 입력할 수 있습니다.

예:

```text
제목: 권한 API 개발
링크 이름: API 문서
URL: https://example.com/auth
상태: 진행중
```

저장되는 Markdown은 대략 다음 형태입니다.

```markdown
- [ ] 권한 API 개발
  - 상태: 진행중
  - 관련 문서: [API 문서](https://example.com/auth)
```

업무 목록은 드래그해서 순서를 바꿀 수 있고, 선택한 업무는 `상세 보기` 또는 더블클릭으로 크게 볼 수 있습니다.

## 다음날 이월

새 날짜 문서를 처음 만들 때 상태에 따라 다음처럼 처리합니다.

| 상태 | 다음날 |
| --- | --- |
| 예정 | 그대로 이월 |
| 진행중 | 그대로 이월 |
| 보류 | 그대로 이월 |
| 완료 | 이월하지 않음 |
| 취소 | 이월하지 않음 |

완료 업무는 완료한 날짜의 업무 목록에 계속 표시되지만 다음날로 이월하지 않습니다. 보류·취소 업무는 `보류·취소 업무도 표시`를 켰을 때 다시 볼 수 있습니다.

## 일일보고

`일일보고 작성`을 누르면 현재 날짜의 업무를 보고서 형식으로 정리합니다.

기본 분류는 다음과 같습니다.

- 진행 업무: `진행중` + `완료`
- 예정 업무: `진행중` + `예정`

생성한 내용은 클립보드로 복사할 수 있습니다. 제목, 상단 문구, 꼬리말은 설정에서 바꿀 수 있습니다.

## 주간·월간 보고서

`주간·월간 보고`에서는 기준 날짜를 선택해 해당 주 또는 월의 일일 Markdown을 모아 HTML 보고서를 만듭니다.

- 완료 / 진행중 / 예정 / 보류 / 취소 건수와 목록
- 주요 성과
- 이슈 및 지원 요청
- 다음 기간 계획
- HTML 미리보기와 파일 저장

이월된 같은 업무를 매일 별도 건으로 세지 않도록 제목과 관련 문서 URL을 기준으로 묶습니다. 기존 Markdown에는 업무별 고유 ID와 정확한 시작·완료 시각이 없으므로 보고서의 최초 기록일과 완료 기록일은 실제 시각이 아니라 일일 문서에 나타난 날짜 기준입니다.

업무 외 기능은 [사용 가이드](./user-guide.md), 설정 항목은 [설정](./settings.md)을 참고하세요.
