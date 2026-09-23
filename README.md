# Daily Report Supporter

Markdown 파일을 데이터 원본으로 사용하는 PyQt6 기반 일일 업무/TODO 관리 앱입니다.

## 주요 기능

- 실행 시 오늘 날짜 문서가 없으면 `reports/YYYY/MM/YYMMDD.md` 자동 생성
- 업무 상태를 **예정 / 진행중 / 완료** 3단계로 관리
- 가장 최근 문서의 **완료** 업무는 새 문서의 **어제 했던 일**로 복사
- **예정 / 진행중** 업무는 상태를 유지한 채 새 문서의 **오늘 해야 할 일**로 자동 이월
- 연도/월별 날짜 목록 조회 및 과거 문서 수정
- 업무별 제목, 관련 문서 링크, 주요 내용, 상태 관리
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
  - 관련 문서: https://example.com/spec
  - 주요 내용:
    - JWT 인증 구현

## 오늘 해야 할 일

- [ ] 권한 API 개발
  - 상태: 진행중
  - 관련 문서: https://example.com/auth
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
