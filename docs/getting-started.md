# 빠른 시작

## 1. 준비

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

앱을 실행하면 프로젝트의 `reports/` 폴더를 사용합니다.

오늘 날짜가 2026-09-23이라면 다음 파일이 생성됩니다.

```text
reports/
├─ settings.json
└─ 2026/
   └─ 09/
      └─ 260923.md
```

## 3. 첫 업무 추가

`오늘 해야 할 일` 탭에서 아래 항목을 입력합니다.

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
| 완료 | 이전 업무 영역으로 이동 |
| 진행중 | 오늘 업무 영역에 유지 |
| 예정 | 오늘 업무 영역에 유지 |

## 5. 일일보고

상단의 `일일보고 작성`을 누르면 현재 업무를 기준으로 보고서가 생성됩니다.

- 진행중 / 완료 → 진행 업무
- 예정 → 예정 업무

생성된 텍스트는 `클립보드 복사`로 바로 복사할 수 있습니다.
