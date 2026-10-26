# 사용 가이드

## 업무

업무 탭은 날짜별 Markdown 문서를 편집하는 화면입니다. 업무는 제목, 관련 문서, 주요 내용, 상태로 구성됩니다.

### 추가와 수정

새 업무를 입력하고 `+ 업무 추가`를 누르면 바로 저장됩니다.

기존 업무는 목록에서 선택해 수정합니다. 실제 값이 바뀌면 `변경사항 저장` 버튼이 나타납니다.

저장 단축키:

- Windows/Linux: `Ctrl+S`
- macOS: `Cmd+S`

새 업무 작성 중이면 추가, 기존 업무 편집 중이면 수정 저장으로 동작합니다.

삭제는 업무를 선택한 뒤 `삭제`를 누르면 됩니다. 확인 후 현재 날짜 Markdown에서도 바로 제거됩니다.

### 상태와 다음날 이월

상태는 다섯 가지입니다.

| 상태 | 다음날 | 업무 목록 |
| --- | --- | --- |
| 예정 | 이월 | 표시 |
| 진행중 | 이월 | 표시 |
| 보류 | 이월 | 기본 숨김 |
| 완료 | 이월하지 않음 | 표시 |
| 취소 | 이월하지 않음 | 기본 숨김 |

`보류·취소 업무도 표시`를 켜면 보류와 취소 업무를 다시 확인하고 수정할 수 있습니다. 완료 업무는 완료한 날짜의 목록에 계속 남아 결과를 바로 확인할 수 있지만 다음날 문서를 만들 때는 이월하지 않습니다.

예전 버전에서 만든 `이전 업무` 데이터는 기존 Markdown을 읽기 위해 유지하지만 현재 화면에서는 별도 편집 영역으로 사용하지 않습니다.

### 업무 순서

목록 항목을 위아래로 드래그하면 순서가 바뀝니다. 이 순서가 그대로 Markdown 저장 순서와 일일보고 순서가 됩니다.

편집 중 저장하지 않은 변경사항이 있으면 드래그 정렬은 잠시 꺼집니다. 변경사항을 저장한 뒤 다시 정렬할 수 있습니다.

보류·취소 업무가 숨겨진 상태에서는 보이지 않는 항목의 순서가 섞이지 않도록 정렬이 제한될 수 있습니다. 이 경우 `보류·취소 업무도 표시`를 켠 뒤 전체 목록에서 정렬합니다.

### 상세 보기

업무를 선택하고 `상세 보기`를 누르거나 목록 항목을 더블클릭하면 큰 창으로 볼 수 있습니다.

- 제목과 상태
- 관련 문서 열기
- Markdown 미리보기
- Markdown 원문

상세 창은 읽기 전용입니다.

### 관련 문서

링크 이름과 URL을 따로 입력합니다.

```text
링크 이름: API 문서
URL: https://example.com/auth
```

저장 형식:

```markdown
- 관련 문서: [API 문서](https://example.com/auth)
```

링크 이름을 비우고 URL만 입력하면 URL 자체를 표시 이름으로 사용합니다. 유효한 `http://` 또는 `https://` 주소면 입력란 옆 `열기` 버튼으로 바로 열 수 있습니다.

### 주요 내용

주요 내용은 Markdown으로 저장합니다. 앱이 목록 기호를 자동으로 붙이지 않으므로 원하는 형식으로 직접 작성하면 됩니다.

```markdown
### 확인 내용

- API 구현
- 테스트 추가

**완료 조건 확인**
```

웹 문서에서 복사할 때 `Ctrl+Shift+V`를 사용하면 글꼴, 색상, HTML 서식을 버리고 텍스트만 붙여넣습니다. 일반 `Ctrl+V`는 Qt 기본 붙여넣기를 사용합니다.

업무 목록과 편집 영역 사이 splitter를 드래그해 높이를 조절할 수 있습니다.

## 전체 검색과 과거 문서

왼쪽 `전체 검색`에서 `reports/` 아래의 모든 일일 문서를 검색합니다.

검색 대상:

- 업무 제목
- 링크 이름 / URL
- 주요 내용
- 상태
- 직접 수정한 Markdown 일반 텍스트
- 이전 버전 데이터

검색 결과를 누르면 해당 날짜 문서를 열고, 현재 형식의 업무 결과라면 해당 업무까지 선택합니다.

검색어를 지우면 연도/월/날짜 탐색 화면으로 돌아갑니다. 과거 날짜 문서도 현재 문서와 같은 방식으로 수정할 수 있습니다.

일일 Markdown 위치:

```text
<app-root>/data/reports/YYYY/MM/YYMMDD.md
```

## 일일보고

`일일보고 작성`에서 현재 날짜 업무를 보고서 형식으로 만듭니다.

기본 분류:

| 상태 | 진행 업무 | 예정 업무 |
| --- | --- | --- |
| 예정 |  | O |
| 진행중 | O | O |
| 완료 | O |  |
| 보류 |  |  |
| 취소 |  |  |

관련 문서는 업무 제목 옆에 붙고, 주요 내용의 Markdown은 입력한 형태를 유지합니다.

제목, 상단 문구, 꼬리말은 [설정](./settings.md)에서 바꿀 수 있습니다. 생성한 보고서는 클립보드로 복사할 수 있습니다.

## 주간·월간 보고서

`주간·월간 보고`은 여러 날짜의 일일 Markdown을 모아 HTML 형식의 업무보고서를 만드는 기능입니다.

기간 선택:

- 주간: 기준 날짜가 속한 월요일부터 일요일
- 월간: 기준 날짜가 속한 달의 1일부터 말일

보고서에는 완료, 진행중, 예정, 보류, 취소 업무의 건수와 목록이 들어갑니다. 필요하면 다이얼로그에서 다음 내용을 추가할 수 있습니다.

- 주요 성과
- 이슈 및 지원 요청
- 다음 기간 계획

`미리보기 갱신`으로 내용을 확인하고 `HTML 저장`으로 독립된 HTML 파일을 저장합니다. HTML에는 기본 인쇄 스타일도 포함되어 있어 브라우저에서 열거나 인쇄할 수 있습니다.

### 집계 기준과 한계

일일 Markdown은 같은 업무가 다음날로 이월될 때 다시 기록됩니다. 기간 보고서는 이를 매일 새 업무로 세지 않도록 **업무 제목 + 관련 문서 URL**을 기준으로 같은 업무를 묶습니다.

기존 Markdown에는 안정적인 업무 ID나 시작/완료 timestamp가 없기 때문에 다음 제약이 있습니다.

- `기간 내 최초 기록일`은 실제 업무 시작 시각이 아니라 해당 기간의 일일 문서에서 처음 발견된 날짜입니다.
- `완료 기록일`도 정확한 완료 시각이 아니라 처음 완료 상태로 기록된 날짜입니다.
- 제목과 URL이 같은 별개의 업무는 하나로 묶일 수 있습니다.
- 같은 업무의 주요 내용은 기간 내 마지막으로 확인한 내용 일부를 사용합니다.

## 메모

메모 탭은 날짜와 관계없는 Markdown 메모를 관리합니다.

왼쪽 목록에서 새 메모를 만들고 검색하거나 순서를 바꿀 수 있습니다. 저장 위치는 다음과 같습니다.

```text
<app-root>/data/memos/<memo-id>.md
```

### 편집과 미리보기

`편집`은 Raw Markdown, `미리보기`는 렌더링된 문서를 보여줍니다. 미리보기에서도 직접 수정할 수 있지만, 저장 과정에서 Markdown 표현이 정규화될 수 있습니다. 원문 형식을 정확히 유지해야 하면 `편집` 탭을 사용합니다.

미리보기에서 줄 시작에 다음 문법을 입력하고 Space를 누르면 바로 서식으로 바뀝니다.

| 입력 | 동작 |
| --- | --- |
| `# `, `## `, `### ` | 제목 |
| `- `, `* ` | 글머리 목록 |
| `1. ` | 번호 목록 |
| `> ` | 인용 |
| 백틱 3개 + Space | 코드 블록 |
| `--- ` | 수평선 |
| `- [ ] `, `- [x] ` | 체크박스 |

텍스트 선택 후 `Ctrl/Cmd+B`는 굵게, `Ctrl/Cmd+I`는 기울임입니다.

### 메모 순서

메모 목록은 드래그해서 정렬합니다. 순서는 `data/memos/.order.json`에 저장됩니다.

검색 중에는 검색 결과와 실제 목록 순서가 섞이지 않도록 드래그 정렬을 끕니다.

## 터미널

터미널 탭에서는 로컬 shell과 SSH 세션을 여러 개 관리합니다.

### 로컬 / SSH 프로필

`+ 로컬`은 현재 OS의 shell을 엽니다.

- Windows: `cmd.exe`
- macOS/Linux/Crostini: `$SHELL`, 없으면 `bash` 또는 `sh`

`+ SSH`는 이름, Host, Port, User만 저장합니다.

```text
ssh -p <port> <user>@<host>
```

SSH 비밀번호나 private-key passphrase는 WorKing에 저장하지 않습니다. SSH가 요청하면 터미널 화면에 직접 입력합니다.

WorKing이 시작하는 SSH 명령에는 다음 client keepalive 옵션을 적용합니다.

```text
-o ServerAliveInterval=30
-o ServerAliveCountMax=3
```

SSH 서버에서 일정 시간 응답이 없거나 중간 네트워크 장비가 idle 연결을 정리하는 상황을 줄이기 위해, 수신 데이터가 없는 동안 OpenSSH가 주기적으로 server-alive 메시지를 보냅니다. 다만 서버의 shell `TMOUT`, 보안 정책에 의한 강제 로그아웃, 서버 종료처럼 서버 측에서 명시적으로 세션을 끝내는 경우까지 유지할 수는 없습니다.

프로필은 다음 파일에 저장됩니다.

```text
<app-root>/data/config/terminal-sessions.json
```

앱을 종료하면 실제 프로세스는 끝나고 프로필만 남습니다. 다음 실행에서는 프로필을 선택할 때 새 세션을 시작합니다.

### 키 입력

터미널 화면을 클릭한 뒤 일반 터미널처럼 입력합니다.

| 키 | 동작 |
| --- | --- |
| `Tab` | shell 자동완성 |
| 방향키 | history / cursor 이동 |
| `Ctrl+C` | foreground 명령 중단 |
| `Ctrl+D` | EOF |
| `Ctrl+Shift+C` | 선택 영역 복사 |
| `Ctrl+Shift+V` | 클립보드 입력 |

`중지`는 `Ctrl+C`, `재시작`은 현재 shell/SSH 세션 재시작, `지우기`는 화면 출력만 비웁니다.

`docker logs -f`, `tail -f` 같은 streaming 명령도 사용할 수 있습니다.

### interactive CLI와 제한

Linux/macOS/Crostini는 PTY, Windows는 ConPTY를 사용합니다. 화면 크기와 폰트에서 계산한 rows/columns를 pseudo-terminal에 동기화하므로 `redis-cli`처럼 터미널 폭을 확인하는 interactive CLI의 prompt와 line editing도 사용할 수 있습니다.

ANSI 색상과 일반적인 cursor 이동은 처리하지만 xterm 전체를 구현한 것은 아닙니다. 다음과 같은 full-screen TUI는 표시가 깨질 수 있습니다.

```text
vim / vi
nano
top / htop
less / more
watch
fzf
```

터미널 하단의 `⚠ 전체화면 TUI 미지원`에 마우스를 올리면 같은 내용을 확인할 수 있습니다.

### 출력량 제한

대량 로그가 앱 전체를 느리게 하지 않도록 화면과 대기 버퍼에 상한을 둡니다.

- 화면: 최근 약 1,800줄 / 약 0.8MB
- 보이는 세션 대기 버퍼: 약 512KB
- 숨겨진 세션 대기 버퍼: 약 128KB
- 출력은 약 50ms 단위로 묶어서 반영

처리 속도보다 출력이 훨씬 빠르면 오래된 대기 로그 일부를 생략하고 화면에 안내를 남깁니다.

## DB Viewer

DB 탭은 MySQL과 PostgreSQL 조회용입니다. write SQL 기능은 없습니다.

### 연결

`+ 연결`에서 다음 값을 입력합니다.

- 이름
- DB 종류
- Host / Port
- Database
- User
- Password

비밀번호는 저장하지 않습니다. 연결 정보, 표시 순서, 최근 테이블, 마지막 SQL draft는 다음 파일에 저장합니다.

```text
<app-root>/data/config/database-connections.json
```

비밀번호는 앱 실행 중 메모리에만 남고 재실행하면 다시 입력해야 합니다.

연결 목록도 드래그해서 순서를 바꿀 수 있습니다.

### Schema와 Table

연결 후 먼저 schema/database 목록을 읽고, schema를 펼칠 때 table/view 목록을 가져옵니다.

- MySQL: 시스템 schema 제외
- PostgreSQL: `information_schema`, `pg_*` 제외
- table/view 표시
- 서버 metadata 기준 테이블 검색
- 연결별 최근 테이블 최대 10개

테이블을 선택하면 `데이터`, `컬럼`, `SQL` 탭을 사용할 수 있습니다.

### 데이터 탭

테이블 전체를 한 번에 읽지 않고 페이지 단위로 조회합니다.

- 페이지 크기: 50 / 100 / 200
- 이전/다음 페이지
- 컬럼 헤더 클릭 정렬
- WHERE 조건
- Filter 입력 중 `Tab`으로 현재 테이블 컬럼명 자동완성
- `LIKE '%값%'` 형태의 wildcard 조건
- 우클릭 빠른 필터
- TSV 복사
- 현재 페이지 CSV 저장

WHERE 입력란에는 `WHERE` 없이 조건만 씁니다.

```sql
status = 'ERROR' AND id > 100
```

세미콜론, SQL 주석, 변경 SQL 키워드는 WHERE 조건에서 차단합니다. `LIKE '%C%'`처럼 문자열 안에 `%` wildcard를 사용하는 조건은 그대로 실행할 수 있습니다.

### 큰 값과 셀 상세 보기

큰 TEXT/JSON/BLOB 때문에 UI가 느려지지 않도록 목록에서는 값의 앞부분만 보관합니다.

- 내부 preview: 최대 약 4,096자
- 셀 표시: 약 512자
- 툴팁: 약 2,048자
- binary preview: 앞부분 64바이트

잘린 셀은 빠른 필터 대상에서 제외됩니다. 복사와 CSV도 현재 보관 중인 preview 범위까지만 출력합니다.

데이터 셀을 우클릭하고 `상세 보기`를 선택하면 DB 탭 안에 별도 상세 탭이 열립니다. preview로 줄어든 값은 해당 셀만 DB에서 다시 조회합니다.

- JSON/JSONB: 가능하면 pretty JSON
- TEXT/JSON 상세 표시: 최대 약 2MB
- binary: 앞부분 최대 약 512KB를 hex로 표시
- 줄바꿈 on/off
- 전체 복사

Primary Key가 있으면 PK 값으로 원본 행을 찾습니다. PK가 없으면 현재 filter/order/offset을 기준으로 다시 조회하므로 조회 사이에 데이터가 바뀌면 다른 행을 가리킬 수 있습니다.

원본 재조회 상세 보기는 table 정보가 확실한 `데이터` 탭에서만 제공합니다. 임의 SQL 결과는 원본 행을 안전하게 식별할 수 없어 같은 방식으로 다시 조회하지 않습니다.

### Read Only SQL

SQL 편집기는 조회 용도만 허용합니다.

허용 시작 구문:

```text
SELECT
WITH
SHOW
DESCRIBE / DESC
EXPLAIN
```

`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE` 등은 앱에서 차단합니다. DB connection에도 read-only 설정을 적용합니다.

편집기 기능:

- SQL 작성 영역과 결과 영역 사이 경계를 드래그해 높이 조절
- syntax highlighting
- `Tab`: 현재 단어 자동완성
- `table.`, `table.pre` 뒤에서 `Tab`: 해당 테이블 column 후보 표시
- `FROM scan_scan ss`, `JOIN users AS u`처럼 선언한 alias를 인식해 `ss.pre`, `u.id` 형태로 column 자동완성
- `schema.table.` / `schema.table.pre`도 지원
- SELECT, WHERE, JOIN ON, GROUP BY, ORDER BY 등 현재 statement 안에서 같은 qualifier 기반 자동완성 사용
- 아직 읽지 않은 테이블의 column metadata는 필요할 때 비동기로 조회
- `Ctrl+Space`: 자동완성 목록 표시
- 자동완성 목록에서 방향키로 이동하고 `Enter`로 확정, `Escape`로 닫기
- MySQL/PostgreSQL별 keyword/function
- `Ctrl+Enter`: 현재 statement 실행
- 선택 영역이 있으면 선택한 SQL을 우선 실행

`SQL 실행` 버튼도 전체 입력을 한꺼번에 실행하지 않고 선택 영역 또는 현재 statement 하나를 실행합니다.

SQL draft는 연결별로 자동 저장합니다. SQL 결과는 최대 500행이고 큰 셀에는 데이터 탭과 같은 preview 제한을 적용합니다.

운영 DB에서는 앱의 read-only 차단과 별개로 DB 계정 자체도 SELECT 권한만 주는 편이 안전합니다.

### 드라이버와 timeout

- MySQL: PyMySQL
- PostgreSQL: psycopg 3
- 연결 timeout: 기본 5초
- statement/read timeout: 약 30초

연결 테스트와 원격 조회는 UI thread 밖에서 처리합니다.

## 설정과 데이터

테마, 폰트, 일일보고 문구, Crostini 입력기는 [설정](./settings.md)에 정리되어 있습니다.

portable 데이터 위치와 첫 실행은 [빠른 시작](./getting-started.md)을 참고하세요.
