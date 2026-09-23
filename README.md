# Daily Report Supporter

Markdown 파일을 데이터 원본으로 사용하는 PyQt6 기반 일일 업무/TODO 관리 앱입니다.

## 주요 기능

- 실행 시 오늘 날짜 문서가 없으면 `reports/YYYY/MM/YYMMDD.md` 자동 생성
- 업무 상태를 **예정 / 진행중 / 완료** 3단계로 관리
- 가장 최근 문서의 **완료** 업무는 새 문서의 **어제 했던 일**로 복사
- **예정 / 진행중** 업무는 상태를 유지한 채 새 문서의 **오늘 해야 할 일**로 자동 이월
- 연도/월별 날짜 목록 조회 및 과거 문서 수정
- 업무별 제목, 관련 문서 표시 문구/실제 URL, 주요 내용, 상태 관리
- Markdown 체크박스 + `상태` 메타데이터 기반 저장
- 기존 `- [ ]`, `- [x]` 문서도 각각 **예정 / 완료**로 호환
- 날짜와 인사말을 지정해 `[진행 업무]`, `[예정 업무]` 형식의 일일보고 생성
- **진행중 / 완료** 업무는 진행 업무에, **예정** 업무는 예정 업무에 분류
- 생성된 일일보고 클립보드 복사

## 실행

Python 3.11+ 권장.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Markdown 저장 예시

```markdown
# 2026-09-23 일일 업무

## 어제 했던 일

- [x] 로그인 API 개발
  - 상태: 완료
  - 관련 문서: [로그인 API 문서](https://example.com/spec)
  - 주요 내용:
    - JWT 인증 구현

## 오늘 해야 할 일

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
| 완료 | 어제 했던 일 | 완료 |
| 진행중 | 오늘 해야 할 일 | 진행중 |
| 예정 | 오늘 해야 할 일 | 예정 |

## 일일보고 분류

- **진행 업무**: 진행중 + 완료
- **예정 업무**: 예정

## 파일 구조

```text
reports/
└─ 2026/
   └─ 09/
      ├─ 260922.md
      └─ 260923.md
```

`reports/`는 기본적으로 `.gitignore`에 포함되어 개인 일일보고 데이터가 저장소에 자동 커밋되지 않도록 했습니다. 필요하면 `.gitignore`에서 제거해 Git으로 업무 기록을 관리할 수 있습니다.

## 테스트

서비스 계층 테스트는 `pytest`로 실행할 수 있습니다.

```bash
pip install pytest
python -m pytest
```

## 업무 추가/수정 흐름

- 새 업무 입력 화면에서 제목/링크/주요 내용/상태를 작성하고 `+ 업무 추가`를 누르면 즉시 Markdown 파일에 저장됩니다.
- 업무 추가 후 입력 폼은 비워져 다음 업무를 바로 작성할 수 있습니다.
- 기존 업무는 목록에서 선택하면 수정 모드로 열립니다.
- 실제 값이 변경된 경우에만 `변경사항 저장` 버튼이 나타납니다.
- 삭제도 확인 후 즉시 Markdown 파일에 반영됩니다.
- 기존의 전역 `저장` 버튼은 제거했습니다.

## 인사말 및 테마 설정

상단 메뉴의 `설정`에서 변경할 수 있습니다.

- **인사말 설정**: 일일보고 창의 기본 인사말을 저장합니다.
- **테마**: Light(기본), Dark, Nord, Solarized Light, Solarized Dark, Sepia를 제공합니다.
- 인사말과 선택한 테마는 `reports/settings.json`에 저장되어 앱을 재실행해도 유지됩니다.



## 설정 파일

테마와 기본 인사말은 OS별 Qt 설정 저장소를 사용하지 않고 아래 파일에 저장됩니다.

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
  "greeting": "안녕하세요.\n금일 업무 진행사항 공유드립니다."
}
```

앱 실행 시 `reports/settings.json`이 없으면 Light 테마와 기본 인사말로 즉시 생성합니다. JSON이 손상되어 읽을 수 없는 경우에도 기본값으로 복구해 다시 저장합니다.

### Linux / Wayland 안정성

Linux에서는 앱 시작 전에 PyQt6의 `libqxcb.so` 의존성을 `ldd`로 검사합니다.

- xcb native dependency가 모두 있으면 X11(`xcb`) backend를 사용하며 기존 설정 메뉴와 QDialog를 그대로 사용합니다.
- `libxcb-cursor0` 등 xcb dependency가 하나라도 없으면 xcb를 강제하지 않습니다.
- 이 경우 Wayland로 실행하면서 자동으로 **안전 UI 모드**가 활성화됩니다.
- 안전 UI 모드에서는 설정/일일보고를 메인 창 내부 탭으로 열고, 삭제 확인도 화면 내부 버튼으로 처리해 QMenu/QDialog popup surface를 만들지 않습니다.
- `reports/settings.json`은 앱 시작 시 없으면 즉시 생성됩니다.

Qt 공식 X11 요구사항에는 `xcb-cursor0`를 포함한 여러 XCB 라이브러리가 xcb platform plugin dependency로 명시되어 있습니다.

고급 사용자는 `DAILY_REPORT_QT_PLATFORM`으로 platform을 직접 지정할 수 있습니다.

```bash
DAILY_REPORT_QT_PLATFORM=wayland python main.py
```

## 관련 문서 링크

관련 문서는 UI에서 두 값으로 나누어 입력합니다.

- **관련 문서 문구**: Markdown에서 보일 텍스트. 예: `1694`
- **관련 문서 주소**: 실제 URL. 예: `http://naver.com`

저장 결과:

```markdown
- 관련 문서: [1694](http://naver.com)
```

기존 버전에서 `- 관련 문서: https://...` 형식으로 저장된 문서는 계속 읽을 수 있습니다. 해당 문서를 다시 저장하면 `[https://...](https://...)` 형태의 Markdown 링크로 자동 변환됩니다.
