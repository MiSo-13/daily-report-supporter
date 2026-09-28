# Daily Report Supporter

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
- 오늘 업무 제목 커스텀
- 연도/월별 날짜 목록 조회 및 과거 문서 수정
- 전체 일일 문서 검색 및 검색 결과에서 해당 날짜/업무로 이동
- 업무별 제목, 관련 문서 표시 문구/실제 URL, 주요 내용, 상태 관리
- Markdown 체크박스 + `상태` 메타데이터 기반 저장
- 기존 `- [ ]`, `- [x]` 문서도 각각 **예정 / 완료**로 호환
- 인사말/상단 문구와 날짜 토큰을 지정해 `[진행 업무]`, `[예정 업무]` 형식의 일일보고 생성
- **진행중 / 완료** 업무는 진행 업무에 분류
- **진행중 / 예정** 업무는 예정 업무에 분류
- 생성된 일일보고 클립보드 복사

## 실행파일 다운로드

Python 설치 없이 사용하려면 [GitHub Releases](https://github.com/MiSo-13/daily-report-supporter/releases/latest)에서 운영체제에 맞는 파일을 받으면 됩니다.

| 환경 | 다운로드 파일 |
| --- | --- |
| Windows x64 | `DailyReportSupporter.exe` |
| macOS Apple Silicon | `DailyReportSupporter-macos-arm64.zip` |
| macOS Intel | `DailyReportSupporter-macos-x64.zip` |
| ChromeOS/Crostini x64 | `DailyReportSupporter-linux-x64` |
| ChromeOS/Crostini ARM64 | `DailyReportSupporter-linux-arm64` |

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
```

배포 실행파일에서는 `~/DailyReportSupporter/reports/`에 저장됩니다.

`reports/`는 기본적으로 `.gitignore`에 포함되어 개인 일일보고 데이터가 저장소에 자동 커밋되지 않도록 했습니다. 필요하면 `.gitignore`에서 제거해 Git으로 업무 기록을 관리할 수 있습니다.

## 테스트

서비스 계층 테스트는 `pytest`로 실행할 수 있습니다.

```bash
pip install pytest
python -m pytest
```

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

- 새 업무 입력 화면에서 제목/링크/주요 내용/상태를 작성하고 `+ 업무 추가`를 누르면 즉시 Markdown 파일에 저장됩니다.
- 업무 추가 후 입력 폼은 비워져 다음 업무를 바로 작성할 수 있습니다.
- 기존 업무는 목록에서 선택하면 수정 모드로 열립니다.
- 실제 값이 변경된 경우에만 `변경사항 저장` 버튼이 나타납니다.
- 삭제도 확인 후 즉시 Markdown 파일에 반영됩니다.
- 기존의 전역 `저장` 버튼은 제거했습니다.

## 설정

상단 메뉴의 `설정`에서 변경할 수 있습니다.

- **일일보고 설정**: 오늘 업무 제목, 상단 문구, 꼬리말
- **입력기 호환 모드**: 시스템 기본값 / Crostini 한글 호환 (IBus)
- **테마**: Light, Dark, Nord, Solarized Light, Solarized Dark, Sepia
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
  "greeting": "안녕하세요.\n금일 업무 진행사항 공유드립니다.\n\nYYYY년 MM월 DD일 일일보고입니다.",
  "footer": "감사합니다.",
  "previous_section_title": "어제 했던 일",
  "today_section_title": "금일 업무",
  "input_method_mode": "system"
}
```

앱 실행 시 `reports/settings.json`이 없으면 Light 테마와 기본 인사말로 즉시 생성합니다. JSON이 손상되어 읽을 수 없는 경우에도 기본값으로 복구해 다시 저장합니다.

### ChromeOS / Crostini

- Crostini에서는 X11(`xcb`)을 사용합니다.
- 필요한 X11 패키지가 없으면 첫 실행 시 자동 설치를 시도합니다.
- 자동 설치가 실패하면 `bash scripts/setup_crostini.sh`를 실행하면 됩니다.
- Windows/macOS에는 이 설정을 적용하지 않습니다.

## 입력기 호환 모드

`설정 → 입력기 호환 모드`에서 변경할 수 있습니다.

- `시스템 기본값`: OS/실행 환경의 입력기 설정 사용
- `Crostini 한글 호환 (IBus)`: Crostini에서 IBus 환경변수 적용

IBus 모드는 다음 실행부터 적용됩니다.

## 오늘 업무 제목

`설정 → 일일보고 설정`에서 변경할 수 있습니다.

기본값은 `오늘 업무`입니다. 변경한 제목은 앱과 Markdown의 `##` 제목에 같이 적용됩니다.

이전 버전에서 생성한 `이전 업무` 데이터는 기존 Markdown 호환을 위해 읽고 보존하지만, 현재 UI에서는 별도 입력 영역으로 사용하지 않으며 일일보고에도 포함하지 않습니다.

## 일일보고 상단 문구

`설정 → 일일보고 설정 → 상단 문구`에 입력한 내용이 보고서 맨 위에 그대로 들어갑니다.

별도의 고정 `YYYY년 MM월 DD일 일일보고입니다.` 문구는 추가되지 않습니다. 날짜 문구가 필요하면 인사말에 날짜 토큰을 직접 넣습니다.

기본값:

```text
안녕하세요.
금일 업무 진행사항 공유드립니다.

YYYY년 MM월 DD일 일일보고입니다.
```

이 상단 문구 다음에 바로 `[진행 업무]`가 출력됩니다.

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

## 관련 문서 링크

관련 문서는 UI에서 두 값으로 나누어 입력합니다.

- **링크 이름**: `1694`
- **URL**: `http://naver.com`

저장 결과:

```markdown
- 관련 문서: [1694](http://naver.com)
```

기존 버전에서 `- 관련 문서: https://...` 형식으로 저장된 문서는 계속 읽을 수 있습니다. 해당 문서를 다시 저장하면 `[https://...](https://...)` 형태의 Markdown 링크로 자동 변환됩니다.

## App

앱 하단 상태바에 `make my MiSo`가 표시됩니다.
