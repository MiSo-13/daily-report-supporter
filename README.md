# WorKing

Markdown 파일을 데이터 원본으로 사용하는 PyQt6 기반 일일 업무/TODO 관리 앱입니다.

## 문서

- [빠른 시작](./docs/getting-started.md)
- [사용 가이드](./docs/user-guide.md)
- [설정 가이드](./docs/settings.md)
- [빌드/배포](./docs/building.md)
- [문서 목록](./docs/README.md)

## 주요 기능

- 실행 시 오늘 날짜 문서가 없으면 `reports/YYYY/MM/YYMMDD.md` 자동 생성
- 업무 상태를 **예정 / 진행중 / 완료** 3단계로 관리
- **예정 / 진행중** 업무는 상태를 유지한 채 다음날 오늘 업무로 자동 이월
- **완료** 업무는 다음날로 이월하지 않음
- 업무 입력은 **오늘 업무** 한 곳에서 관리
- `Ctrl+S` / macOS `Cmd+S` 저장
- 업무 목록과 편집 영역 높이 조절
- 일일보고의 진행 업무/예정 업무 제목 커스텀
- 연도/월별 날짜 목록 조회 및 과거 문서 수정
- 전체 일일 문서 검색 및 검색 결과에서 해당 날짜/업무로 이동
- 독립 메모 관리: 여러 Markdown 메모, 제목 변경, 전체 검색, 편집/미리보기
- 다중 터미널: 로컬 PTY/ConPTY 세션 + 저장형 SSH 프로필, 직접 키 입력, Tab/Ctrl+C
- 앱 하단 왼쪽 CPU / RAM 사용량 표시 및 표시 여부 설정
- 메모/터미널 목록 항목 드래그 순서 변경 및 저장
- 업무별 제목, 관련 문서 표시 문구/실제 URL, 주요 내용, 상태 관리
- 유효한 업무 URL은 입력창 옆 `열기` 버튼으로 바로 실행
- Markdown 체크박스 + `상태` 메타데이터 기반 저장
- 기존 `- [ ]`, `- [x]` 문서도 각각 **예정 / 완료**로 호환
- 상단 문구/꼬리말과 날짜 토큰을 지정해 일일보고 생성
- **진행중 / 완료** 업무는 진행 업무에 분류
- **진행중 / 예정** 업무는 예정 업무에 분류
- 생성된 일일보고 클립보드 복사

## 실행파일 다운로드

Python 설치 없이 사용하려면 [GitHub Releases](https://github.com/MiSo-13/daily-report-supporter/releases/latest)에서 운영체제에 맞는 파일을 받으면 됩니다.

| 환경 | 다운로드 파일 |
| --- | --- |
| Windows x64 | `WorKing.exe` |
| macOS Apple Silicon | `WorKing-macos-arm64.zip` |
| macOS Intel | `WorKing-macos-x64.zip` |
| ChromeOS/Crostini x64 | `WorKing-linux-x64` |
| ChromeOS/Crostini ARM64 | `WorKing-linux-arm64` |

Windows는 `.exe` 하나만 받아 실행할 수 있습니다.

빌드 방법과 Release 생성 방법은 [빌드/배포 문서](./docs/building.md)를 참고하세요.

## 소스에서 실행

Python 3.11+ 권장.

### Windows

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

Windows에서는 Qt의 기본 `windows` platform plugin을 그대로 사용합니다.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

macOS에서는 Qt의 기본 `cocoa` platform plugin을 그대로 사용합니다.

### ChromeOS / Crostini

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

필요한 X11 패키지가 없으면 첫 실행 시 `scripts/setup_crostini.sh`를 자동 실행합니다. `sudo` 비밀번호가 필요하면 터미널에서 입력하면 됩니다.

수동 설치가 필요할 때:

```bash
bash scripts/setup_crostini.sh
```

### 일반 Linux

일반 Linux 데스크톱은 Crostini 전용 강제 설정을 적용하지 않고 사용자의 Qt 기본 platform 선택을 존중합니다.

### 플랫폼 동작 요약

| 환경 | Qt platform 처리 |
| --- | --- |
| Windows | Qt 기본 `windows` |
| macOS | Qt 기본 `cocoa` |
| ChromeOS/Crostini | 사전 검사 후 `xcb` |
| 일반 Linux | Qt 기본값 유지 |

## Markdown 저장 예시

```markdown
# 2026-09-23 일일 업무

## 오늘 업무

- [ ] 권한 API 개발
  - 상태: 진행중
  - 관련 문서: [권한 API 문서](https://example.com/auth)
  - 주요 내용:
    ### 구현 내용

    - 권한 조회 API 구현

- [ ] 테스트 코드 작성
  - 상태: 예정
  - 주요 내용:
    - 인증 API 테스트 작성
```

체크박스는 Markdown 뷰어 호환을 위해 유지합니다. `완료` 상태만 `[x]`로 저장되고, `예정` 및 `진행중`은 `[ ]`로 저장됩니다. 실제 상태 구분은 `- 상태:` 값을 사용합니다.

## 다음날 자동 이월

| 오늘 상태 | 다음날 위치 | 다음날 상태 |
| --- | --- | --- |
| 완료 | 이월하지 않음 | - |
| 진행중 | 오늘 업무 | 진행중 |
| 예정 | 오늘 업무 | 예정 |

## 일일보고 분류

- **진행 업무**: 진행중 + 완료
- **예정 업무**: 진행중 + 예정

## 파일 구조

소스 실행 시:

```text
reports/
└─ 2026/
   └─ 09/
      ├─ 260922.md
      └─ 260923.md

memos/
├─ <memo-id>.md
├─ <memo-id>.md
└─ .order.json

terminal-sessions.json
```

배포 실행파일에서는 아래 위치를 사용합니다.

```text
~/DailyReportSupporter/reports/
~/DailyReportSupporter/memos/
```

WorKing으로 이름이 변경되어도 기존 사용자 데이터 호환을 위해 저장 디렉터리 이름은 `DailyReportSupporter`를 유지합니다.

`reports/`, `memos/`, `terminal-sessions.json`은 기본적으로 `.gitignore`에 포함됩니다.

## 테스트

서비스 계층 테스트는 `pytest`로 실행할 수 있습니다.

```bash
pip install pytest
python -m pytest
```

## 메모

왼쪽의 `메모` 탭에서 날짜와 무관한 Markdown 메모를 관리할 수 있습니다.

- 여러 메모 생성/삭제
- 메모 제목 변경
- 제목/본문 전체 검색
- `편집`: Raw Markdown 작성
- `미리보기`: 렌더링된 Markdown을 보면서 직접 편집
- 미리보기에서 Markdown 단축 문법 입력 시 즉시 서식 적용
- `Ctrl+S` / macOS `Cmd+S` 저장

미리보기에서 수정한 내용은 저장할 때 Markdown으로 변환됩니다. Markdown 원문 형식을 정확히 유지하려면 `편집` 탭을 사용합니다.

메모 목록의 항목은 드래그해서 순서를 변경할 수 있습니다. 검색 중에는 검색 결과와 실제 순서가 섞이지 않도록 드래그 정렬이 비활성화됩니다. 메모 순서는 `memos/.order.json`에 저장됩니다.

### 미리보기 Markdown 단축키

줄 시작에서 문법을 입력한 뒤 Space를 누르면 즉시 서식으로 바뀝니다.

| 입력 | 결과 |
| --- | --- |
| `# ` | 제목 1 |
| `## ` | 제목 2 |
| `### ` | 제목 3 |
| `- ` / `* ` | 글머리 목록 |
| `1. ` | 번호 목록 |
| `> ` | 인용 |
| `\`\`\` ` | 코드 블록 |
| `--- ` | 수평선 |
| `- [ ] ` | 미체크 체크박스 |
| `- [x] ` | 체크된 체크박스 |

체크박스는 미리보기에서 직접 클릭해 체크 상태를 바꿀 수 있습니다.

텍스트 선택 후 `Ctrl/Cmd+B`는 굵게, `Ctrl/Cmd+I`는 기울임을 적용합니다.

## 터미널

왼쪽의 `터미널` 탭에서 로컬 shell과 SSH 연결을 함께 관리할 수 있습니다.

- `+ 로컬`: 로컬 shell 프로필 생성
- `+ SSH`: SSH 프로필 생성
- `편집`: 이름 또는 SSH Host/Port/User 수정
- `삭제`: 세션 종료 및 프로필 삭제
- 세션을 전환해도 앱 실행 중인 shell/SSH 프로세스는 유지
- 터미널 목록 항목을 드래그해서 원하는 순서로 정렬

SSH 프로필에는 아래 값만 저장합니다.

```text
이름
Host
Port
User
```

**SSH 비밀번호와 passphrase는 저장하지 않습니다.** SSH 프로필을 선택하면 운영체제의 `ssh` 명령을 PTY/ConPTY에서 직접 실행하고, `password:` 프롬프트가 나오면 터미널 화면에 직접 입력합니다. SSH가 터미널 echo를 끄므로 비밀번호 문자는 화면에 표시되지 않습니다.

터미널 화면을 클릭한 뒤 키보드로 바로 입력합니다. 별도의 명령 입력창을 사용하지 않습니다. Tab 키는 Qt 포커스 이동에 사용하지 않고 PTY/ConPTY로 직접 전달합니다.

- `Tab`: shell/원격 shell의 원래 자동완성
- 방향키: shell history/cursor 이동
- `Ctrl+C`: 현재 foreground 명령 중단
- `Ctrl+D`: EOF
- `Ctrl+Shift+C`: 선택한 출력 복사
- `Ctrl+Shift+V`: 클립보드 내용을 터미널에 입력
- `중지`: Ctrl+C와 동일
- `재시작`: 현재 로컬 shell 또는 SSH 연결 재시작
- `지우기`: 출력 화면만 비우기
- shell의 `clear` / Windows의 `cls`: clear-screen ANSI를 감지해 실제 터미널 화면 비우기

예를 들어 shell에 Docker completion이 설정되어 있다면 아래 입력 뒤 Tab을 눌렀을 때 shell 자체의 completion이 동작합니다.

```bash
docker logs -f my_<Tab>
```

SSH 연결 후 원격 서버에서도 동일한 키 전달 방식을 사용합니다.

```bash
docker logs -f my_service
```

같은 streaming 명령은 `Ctrl+C`로 중단한 뒤 같은 SSH 세션을 계속 사용할 수 있습니다.

터미널 프로필은 `terminal-sessions.json`에 저장됩니다. 터미널 목록 항목을 드래그하면 배열 순서도 함께 저장되어 다음 실행에 유지됩니다. 앱을 종료하면 실제 프로세스는 종료되고, 다음 실행에서는 프로필만 복원됩니다. 프로필을 선택하는 시점에 shell/SSH 연결을 시작합니다.

터미널은 Linux/macOS/Crostini에서 PTY, Windows에서 ConPTY를 사용합니다.

대량 로그 때문에 앱이 멈추는 것을 줄이기 위해 출력은 50ms 단위로 묶어서 렌더링하고, 화면에는 최근 약 1,800줄 / 약 0.8MB까지만 유지합니다. 숨겨진 터미널은 계속 다시 그리지 않고 최근 출력만 제한적으로 버퍼링합니다. 출력량이 렌더링 속도를 크게 초과하면 오래된 대기 로그 일부를 생략하고 화면에 안내합니다.

각 앱 테마는 터미널 전용 배경/텍스트/선택 색상을 함께 가지므로 일반 입력 영역과 터미널을 쉽게 구분할 수 있습니다.

현재 출력 위젯은 ANSI 커서 이동을 완전히 구현한 xterm 수준의 렌더러는 아니므로 `vim`, `top`, `htop` 같은 전체 화면 프로그램은 표시가 제한될 수 있습니다.

## 앱 리소스 사용량

앱 하단 상태바 왼쪽에 현재 WorKing 프로세스의 CPU와 RAM 사용량을 표시합니다.

```text
CPU 3.2% · RAM 148 MB
```

약 1.5초마다 갱신되며 시스템 전체 사용량이 아니라 앱 프로세스 자체의 사용량입니다. `설정 → CPU / RAM 표시`에서 숨길 수 있으며, 숨기면 측정 타이머도 중지됩니다.

## 전체 검색

좌측 `전체 검색`에서 모든 일일 Markdown 문서를 검색할 수 있습니다.

검색 대상:

- 업무 제목
- 링크 이름
- URL
- 주요 내용
- 상태
- 구조화되지 않은 Markdown 원문
- 이전 버전의 이전 업무 데이터

검색 결과는 최신 날짜부터 표시됩니다. 현재 업무 검색 결과를 클릭하면 해당 날짜 문서를 열고 업무를 선택합니다.

## 업무 추가/수정 흐름

- `Ctrl+S`(Windows/Linux) 또는 `Cmd+S`(macOS)로 현재 업무를 저장할 수 있습니다.
- 새 업무 작성 중이면 추가되고, 기존 업무 편집 중이면 변경사항이 저장됩니다.
- 업무 목록과 아래 편집 영역 사이 경계를 드래그해 높이를 조절할 수 있습니다.
- URL이 유효한 `http/https` 주소면 입력창 옆 `열기` 버튼이 활성화됩니다.
- 새 업무 입력 화면에서 제목/링크/주요 내용/상태를 작성하고 `+ 업무 추가`를 누르면 즉시 Markdown 파일에 저장됩니다.
- 업무 추가 후 입력 폼은 비워져 다음 업무를 바로 작성할 수 있습니다.
- 기존 업무는 목록에서 선택하면 수정 모드로 열립니다.
- 실제 값이 변경된 경우에만 `변경사항 저장` 버튼이 나타납니다.
- 삭제도 확인 후 즉시 Markdown 파일에 반영됩니다.
- 기존의 전역 `저장` 버튼은 제거했습니다.

## 설정

상단 메뉴의 `설정`에서 변경할 수 있습니다.

- **일일보고 설정**: 진행 업무 제목, 예정 업무 제목, 상단 문구, 꼬리말
- **입력기 호환 모드**: 시스템 기본값 / Crostini 한글 호환 (IBus)
- **폰트**: 앱 전체 폰트/크기, 터미널 고정폭 폰트/크기
- **CPU / RAM 표시**: 하단 리소스 사용량 표시 여부
- **테마**: Light, Dark, Purple, Nord, Solarized Light, Solarized Dark, Sepia
- 설정은 `reports/settings.json`에 저장됩니다.



## 설정 파일

테마, 상단 문구, 꼬리말은 아래 파일에 저장됩니다.

```text
reports/
├─ settings.json
└─ YYYY/
   └─ MM/
      └─ YYMMDD.md
```

예시:

```json
{
  "theme": "Nord",
  "font_family": "",
  "font_size": 10,
  "terminal_font_family": "",
  "terminal_font_size": 10,
  "show_resource_usage": true,
  "greeting": "안녕하세요.\n금일 업무 진행사항 공유드립니다.\n\nYYYY년 MM월 DD일 일일보고입니다.",
  "footer": "감사합니다.",
  "previous_section_title": "어제 했던 일",
  "today_section_title": "오늘 업무",
  "progress_report_title": "진행 업무",
  "planned_report_title": "예정 업무",
  "input_method_mode": "system"
}
```

앱 실행 시 `reports/settings.json`이 없으면 Light 테마와 기본 상단 문구로 즉시 생성합니다. JSON이 손상되어 읽을 수 없는 경우에도 기본값으로 복구해 다시 저장합니다.

### ChromeOS / Crostini

- Crostini에서는 X11(`xcb`)을 사용합니다.
- 필요한 X11 패키지가 없으면 첫 실행 시 자동 설치를 시도합니다.
- 자동 설치가 실패하면 `bash scripts/setup_crostini.sh`를 실행하면 됩니다.
- Windows/macOS에는 이 설정을 적용하지 않습니다.

## 폰트 설정

`설정 → 폰트...`에서 앱 전체 폰트와 터미널 폰트를 각각 지정할 수 있습니다.

- 앱 폰트: 현재 OS에 설치된 일반 폰트
- 앱 크기: 8~32pt
- 터미널 폰트: 현재 OS의 고정폭 폰트만 표시
- 터미널 크기: 8~32pt
- `기본값`: 시스템 기본 UI 폰트 + 시스템 기본 고정폭 폰트, 10pt

폰트 설정은 저장 즉시 적용됩니다. 특정 OS에 선택한 폰트가 없으면 Qt/OS의 fallback 폰트를 사용합니다.

메모의 Tab/들여쓰기 폭은 앱 폰트에 맞춰 항상 약 4 spaces 기준으로 다시 계산됩니다.

## 입력기 호환 모드

`설정 → 입력기 호환 모드`에서 변경할 수 있습니다.

- `시스템 기본값`: OS/실행 환경의 입력기 설정 사용
- `Crostini 한글 호환 (IBus)`: Crostini에서 IBus 환경변수 적용

IBus 모드는 다음 실행부터 적용됩니다.

## 일일보고 업무 제목

`설정 → 일일보고 설정`에서 일일보고의 두 제목을 변경할 수 있습니다.

- 진행 업무 제목: 기본값 `진행 업무`
- 예정 업무 제목: 기본값 `예정 업무`

생성 결과에는 `[진행 업무]`처럼 대괄호를 붙이지 않습니다.

이전 버전에서 `오늘 업무 제목`을 직접 커스텀한 경우 해당 값은 새 `진행 업무 제목`으로 자동 승계됩니다. 앱 내부의 오늘 업무 Markdown 제목은 기존 문서 호환용 설정으로 유지됩니다.

## 일일보고 상단 문구

`설정 → 일일보고 설정 → 상단 문구`에 입력한 내용이 보고서 맨 위에 그대로 들어갑니다.

별도의 고정 `YYYY년 MM월 DD일 일일보고입니다.` 문구는 추가되지 않습니다. 날짜 문구가 필요하면 인사말에 날짜 토큰을 직접 넣습니다.

기본값:

```text
안녕하세요.
금일 업무 진행사항 공유드립니다.

YYYY년 MM월 DD일 일일보고입니다.
```

이 상단 문구 다음에 설정한 진행 업무 제목이 출력됩니다. 상단 문구와 꼬리말의 줄바꿈은 입력한 그대로 유지됩니다.

## 일일보고 날짜 토큰

상단 문구와 꼬리말에서 날짜 토큰을 사용할 수 있습니다.

| 입력 | 2026-09-23 기준 결과 |
| --- | --- |
| `YY.MM.DD` | `26.09.23` |
| `YY. MM. DD` | `26. 09. 23` |
| `YYYY.MM.DD` | `2026.09.23` |
| `YYYY-MM-DD` | `2026-09-23` |
| `YYYY년 MM월 DD일` | `2026년 09월 23일` |

예:

```text
안녕하세요.
YY. MM. DD 업무 공유드립니다.

...

이상입니다.
감사합니다.
```

## 일일보고 출력 형식

관련 문서는 별도 `관련 문서:` 줄을 만들지 않고 업무 제목 옆에 표시합니다.

```markdown
1. 보고서 개선 문서 확인 ([Confluence](https://example.com/doc))
```

주요 내용은 자동으로 `- `를 붙이지 않습니다. 입력한 Markdown을 그대로 출력합니다.

입력:

```markdown
### 확인 내용

- 첫 번째
  - 하위 항목

**완료**
```

위 Markdown이 같은 형태로 일일보고에 들어갑니다.

## 관련 문서 링크

관련 문서는 UI에서 두 값으로 나누어 입력합니다.

- **링크 이름**: `1694`
- **URL**: `http://naver.com`

일일 Markdown 저장 형식:

```markdown
- 관련 문서: [1694](http://naver.com)
```

일일보고에서는 업무 제목 옆에 `([1694](http://naver.com))` 형태로 표시됩니다.

기존 버전에서 `- 관련 문서: https://...` 형식으로 저장된 문서는 계속 읽을 수 있습니다. 해당 문서를 다시 저장하면 `[https://...](https://...)` 형태의 Markdown 링크로 자동 변환됩니다.

## App

앱 하단 상태바에 `made by MiSo`가 표시됩니다.
