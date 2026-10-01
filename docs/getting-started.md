# 빠른 시작

## 실행파일로 시작

Python 설치 없이 사용하려면 [GitHub Releases](https://github.com/MiSo-13/daily-report-supporter/releases/latest)에서 운영체제에 맞는 파일을 받습니다.

- Windows: `WorKing.exe`
- macOS: `WorKing-macos-*.zip`
- ChromeOS/Crostini: `WorKing-linux-*`

소스 실행과 배포 실행파일 모두 사용자 홈의 `~/WorKing/` 아래에 업무/메모/설정 데이터를 저장합니다. 기존 `~/DailyReportSupporter/` 데이터는 첫 실행 시 자동으로 새 위치에 복사됩니다.

## 1. 소스 실행 준비

Python 3.11 이상을 권장합니다.

저장소를 받은 뒤 프로젝트 폴더에서 가상환경을 만듭니다.

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### ChromeOS / Crostini

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

필요한 X11 패키지가 없으면 첫 실행 시 자동 설치를 시도합니다.

수동 설치가 필요한 경우:

```bash
bash scripts/setup_crostini.sh
```

한글 입력이 되지 않으면 앱에서 `설정 → 입력기 호환 모드 → Crostini 한글 호환 (IBus)`를 선택한 뒤 앱을 다시 실행합니다.

## 2. 첫 실행

앱을 실행하면 사용자 홈에 통합 데이터 폴더를 준비합니다.

오늘 날짜가 2026-09-23이라면 주요 파일은 다음 위치에 생성됩니다.

```text
~/WorKing/
├─ config/
│  ├─ settings.json
│  └─ migration-v1.json
├─ reports/
│  └─ 2026/
│     └─ 09/
│        └─ 260923.md
└─ memos/
```

기존 버전을 사용한 적이 있으면 첫 실행 전에 `~/DailyReportSupporter/` 또는 소스 저장소의 기존 데이터를 확인해 새 구조로 복사합니다. 새 위치의 파일은 덮어쓰지 않으며 기존 폴더도 삭제하지 않습니다.

## 3. 첫 업무 추가

`오늘 업무` 영역에서 아래 항목을 입력합니다.

- 제목
- 링크 이름
- URL
- 주요 내용
- 상태

입력 후 `+ 업무 추가`를 누르면 바로 Markdown 파일에 저장됩니다.

예:

```text
제목: 권한 API 개발
링크 이름: 1694
URL: http://naver.com
상태: 진행중
```

Markdown:

```markdown
- [ ] 권한 API 개발
  - 상태: 진행중
  - 관련 문서: [1694](http://naver.com)
```

## 4. 다음날

새 날짜 문서가 만들어질 때:

| 상태 | 다음날 |
| --- | --- |
| 완료 | 이월하지 않음 |
| 진행중 | 오늘 업무에 유지 |
| 예정 | 오늘 업무에 유지 |

## 5. 일일보고

상단의 `일일보고 작성`을 누르면 현재 업무를 기준으로 보고서가 생성됩니다.

- 진행중 / 완료 → 진행 업무
- 진행중 / 예정 → 예정 업무

생성된 텍스트는 `클립보드 복사`로 바로 복사할 수 있습니다.


## 6. 메모

왼쪽의 `메모` 탭에서 날짜와 무관한 Markdown 메모를 만들 수 있습니다.

`+ 새 메모`를 누르고 제목과 내용을 작성합니다. `편집`에서는 Raw Markdown을, `미리보기`에서는 렌더링된 내용을 보면서 수정할 수 있습니다.


## 7. 터미널

왼쪽의 `터미널` 탭에서 여러 shell 세션을 만들 수 있습니다.

`+ 로컬`을 눌러 로컬 shell 프로필을 만들 수 있습니다. `+ SSH`에서는 이름/Host/Port/User만 저장해 원격 서버 프로필을 만들 수 있습니다.

SSH 비밀번호는 저장하지 않습니다. SSH 프로필을 선택한 뒤 터미널의 `password:` 프롬프트에서 직접 입력합니다.

터미널 화면을 클릭하고 바로 명령을 입력하며 Tab 자동완성, 방향키, `Ctrl+C`를 PTY/ConPTY에 그대로 전달합니다.
