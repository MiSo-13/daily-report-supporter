# WorKing

WorKing은 일일 업무를 Markdown으로 관리하는 PyQt6 데스크톱 앱입니다. 업무 기록 외에 메모, 로컬/SSH 터미널, MySQL/PostgreSQL 조회 기능을 한 화면에서 같이 사용할 수 있습니다.

사용자 데이터는 실행 파일 옆 `data/`에 저장합니다. 별도 서버나 계정 없이 파일 그대로 백업하고 옮길 수 있는 구조입니다.

## 주요 기능

### 업무

- 상태: `예정`, `진행중`, `완료`, `보류`, `취소`
- 업무 제목, 관련 문서 링크, Markdown 주요 내용
- 업무 목록 드래그 순서 변경
- 보류·취소 업무 기본 숨김 / 필요할 때 전체 표시
- 선택 업무 상세 보기: Markdown 미리보기 / 원문
- 전체 일일 문서 검색
- 과거 날짜 조회와 수정
- 다음날 자동 이월
- 일일보고 생성과 클립보드 복사
- 주간·월간 업무를 모아 HTML 보고서 미리보기 및 저장

다음날 문서를 처음 열 때 `예정`, `진행중`, `보류` 업무는 상태를 유지한 채 이월합니다. `완료`와 `취소` 업무는 이월하지 않습니다.

일일보고는 기본적으로 다음처럼 분류합니다.

| 상태 | 진행 업무 | 예정 업무 |
| --- | --- | --- |
| 예정 |  | O |
| 진행중 | O | O |
| 완료 | O |  |
| 보류 |  |  |
| 취소 |  |  |

주간·월간 보고서는 기간 안의 일일 Markdown을 모아 완료/진행중/예정/보류/취소 현황을 HTML로 정리합니다. 기존 데이터에는 업무별 고유 ID나 정확한 시작·완료 시각이 없으므로 제목과 링크를 기준으로 이월된 업무의 중복 집계를 줄입니다.

### 메모

날짜와 관계없는 Markdown 메모를 따로 관리합니다. 편집/미리보기 전환, 검색, 체크박스, 드래그 정렬을 지원합니다.

### 터미널

로컬 shell과 SSH 프로필을 여러 개 열어 둘 수 있습니다. Linux/macOS/Crostini에서는 PTY, Windows에서는 ConPTY를 사용합니다.

일반 CLI와 streaming 로그 확인에 맞춘 터미널이며 `redis-cli`처럼 터미널 크기를 사용하는 interactive CLI도 사용할 수 있습니다. `vim`, `top`, `fzf`처럼 화면 전체를 제어하는 TUI는 완전하게 지원하지 않습니다.

### DB Viewer

MySQL과 PostgreSQL 연결을 여러 개 등록해 schema/table을 탐색하고 데이터를 조회할 수 있습니다.

- 페이지 조회, 정렬, WHERE 필터
- Filter 입력에서 `Tab` 컬럼 자동완성 및 `LIKE '%값%'` 조건
- 컬럼 정보 확인
- Read Only SQL
- SQL syntax highlighting / 테이블·alias 기반 컬럼 자동완성
- `Ctrl+Enter`로 현재 statement 실행
- 큰 TEXT/JSON/BLOB 값 미리보기
- 데이터 셀 우클릭 → 원본 상세 보기

DB 기능은 조회 전용입니다. `INSERT`, `UPDATE`, `DELETE`, DDL은 실행하지 않습니다.

## 다운로드

Python 없이 실행하려면 [GitHub Releases](https://github.com/MiSo-13/daily-report-supporter/releases/latest)에서 운영체제에 맞는 파일을 받으면 됩니다.

| 환경 | 파일 |
| --- | --- |
| Windows x64 | `WorKing.exe` |
| macOS Apple Silicon | `WorKing-macos-arm64.zip` |
| macOS Intel | `WorKing-macos-x64.zip` |
| ChromeOS/Crostini x64 | `WorKing-linux-x64` |
| ChromeOS/Crostini ARM64 | `WorKing-linux-arm64` |

ChromeOS/Crostini에서 아키텍처가 헷갈리면 터미널에서 `uname -m`을 확인합니다. `x86_64`이면 x64, `aarch64`/ARM64이면 arm64 파일을 사용합니다. Linux 앱 목록에 직접 등록할 때는 `WorKing.desktop`과 아이콘 파일을 함께 설정할 수 있습니다.

설치, Crostini desktop 등록, 첫 실행은 [빠른 시작](./docs/getting-started.md)을 참고하세요.

## 소스에서 실행

Python 3.11 이상을 권장합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Windows에서는 가상환경 활성화만 다음처럼 다릅니다.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Crostini에서 Qt/X11 의존성이 부족하면 다음 스크립트를 사용할 수 있습니다.

```bash
bash scripts/setup_crostini.sh
```

플랫폼별 실행 내용은 [빠른 시작](./docs/getting-started.md), 배포 빌드는 [빌드/배포](./docs/building.md)에 정리되어 있습니다.

## 데이터 위치

WorKing은 실행 위치 옆 `data/`만 사용자 데이터 위치로 사용합니다.

```text
WorKing/
├─ WorKing.exe       # Windows
# 또는 WorKing       # Linux/Crostini
# 또는 WorKing.app   # macOS
└─ data/
   ├─ config/
   ├─ reports/
   └─ memos/
```

소스 실행에서는 저장소 루트의 `data/`를 사용합니다.

주요 파일은 다음과 같습니다.

```text
data/
├─ config/
│  ├─ settings.json
│  ├─ terminal-sessions.json
│  └─ database-connections.json
├─ reports/
└─ memos/
```

기존 `~/DailyReportSupporter/`, `~/WorKing/` 또는 이전 소스 실행 위치의 데이터가 있으면 첫 실행 시 현재 `data/`로 복사합니다. 원본은 삭제하지 않습니다.

DB 비밀번호는 `database-connections.json`에 저장하지 않고 앱 실행 중 메모리에만 둡니다.

## 문서

- [빠른 시작](./docs/getting-started.md) — 설치와 첫 실행
- [사용 가이드](./docs/user-guide.md) — 업무, 일일/주간/월간 보고서, 메모, 터미널, DB 사용법
- [설정](./docs/settings.md) — 테마, 폰트, 일일보고, Crostini 입력기
- [빌드/배포](./docs/building.md) — PyInstaller와 GitHub Release
- [코드 구조](./docs/architecture.md) — 주요 모듈과 책임

문서 전체 목록은 [docs/README.md](./docs/README.md)에 있습니다.

## 테스트

```bash
pip install pytest
python -m pytest
```

GitHub Actions에서도 pull request와 `main` push 시 테스트를 실행합니다.
