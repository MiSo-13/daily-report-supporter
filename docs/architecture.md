# 코드 구조

WorKing은 PyQt6 UI 위에 업무, 메모, 터미널, DB Viewer를 각각 분리된 모듈로 올린 구조입니다. 사용자 데이터는 모두 실행 위치 옆 `data/`를 기준으로 합니다.

## 시작과 공통 설정

- `main.py`: 데이터 경로 확인, 마이그레이션, Qt/입력기 설정 후 앱 시작
- `app/main_window.py`: 최상위 탭, 날짜 탐색, 전체 검색, 설정 메뉴, Qt 앱 이름과 desktop file name 초기화
- `app/app_meta.py`: 앱 이름, bundle identifier, 데이터 디렉터리 이름
- `app/app_icon.py`: SVG 아이콘 로딩과 빌드용 렌더링
- `app/settings.py`: `settings.json` 읽기/쓰기와 이전 설정 migration
- `app/themes.py`: 앱/터미널 테마

## 경로와 데이터 이동

- `app/paths.py`: portable `data/` 경로와 legacy 위치 계산
- `app/runtime_paths.py`: 실제 실행에 사용할 경로 묶음 구성
- `app/data_migration.py`: 이전 데이터 위치에서 현재 `data/`로 복사

홈 디렉터리의 예전 경로는 migration source로만 읽습니다. 현재 사용자 데이터는 `<app-root>/data/`에만 기록합니다.

## 업무와 일일보고

- `app/models.py`: `Task`, `TaskStatus`, `DailyDocument`
- `app/markdown_store.py`: 날짜별 Markdown 읽기/쓰기, 검색, 다음날 이월
- `app/task_editor.py`: 업무 편집, 순서 변경, 상세 보기 진입
- `app/task_detail_dialog.py`: 개별 업무 Markdown 상세 뷰어
- `app/report_service.py`: 일일보고 텍스트 생성

업무의 표시 순서와 저장 순서는 별도 order 파일 없이 Markdown에 적힌 순서를 그대로 사용합니다.

## 메모

- `app/memo_store.py`: 메모 파일과 `.order.json` 관리
- `app/memo_sidebar.py`: 검색/목록/정렬
- `app/memo_editor.py`: Markdown 편집과 미리보기
- `app/memo_workspace.py`: 메모 생성, 선택, 저장, 삭제 흐름

메모 내부 동작은 `MemoWorkspace`에서 조정하고 `MainWindow`에는 세부 CRUD를 넣지 않습니다.

## 터미널

- `app/terminal_store.py`: 로컬/SSH 프로필 저장
- `app/terminal_dialogs.py`: SSH 프로필 편집
- `app/terminal_backend.py`: Unix PTY / Windows ConPTY I/O와 window size 동기화
- `app/terminal_display.py`: 키 입력, ANSI 렌더링, rows/columns 계산, scrollback 제한
- `app/terminal_ui.py`: 세션 화면과 sidebar
- `app/terminal_workspace.py`: 프로필/세션 lifecycle

PTY/ConPTY와 화면 렌더러를 분리해 streaming 출력이나 interactive CLI 처리 변경이 다른 UI에 번지지 않도록 구성되어 있습니다.

## DB Viewer

- `app/database_models.py`: 연결/테이블/조회 관련 모델
- `app/database_store.py`: 연결 프로필, 순서, 최근 테이블, SQL draft 저장
- `app/database_dialogs.py`: 연결 생성/수정 UI
- `app/database_service.py`: MySQL/PostgreSQL 연결, metadata/data/query 조회, table column 자동완성 metadata 조회, Read Only 검증
- `app/database_sql_editor.py`: SQL highlighting, FROM/JOIN relation·alias 해석, prefix 자동완성, 자동완성 키 처리, statement 선택
- `app/database_value_preview.py`: 큰 셀 값을 목록용 preview로 축소
- `app/database_table_model.py`: 결과 테이블 모델
- `app/database_detail.py`: TEXT/JSON/Binary 상세 표시 포맷
- `app/database_filter_input.py`: 데이터 Filter 컬럼 자동완성 입력
- `app/database_ui.py`: DB 화면 위젯과 SQL 입력/결과 splitter
- `app/database_workspace.py`: 비동기 조회, SQL draft, table/alias별 column metadata 자동완성 조정

목록 조회와 큰 셀의 원본 상세 조회는 분리되어 있습니다. 일반 결과는 worker 단계에서 크기를 제한하고, 사용자가 데이터 셀의 `상세 보기`를 열 때만 해당 셀을 다시 조회합니다.

SQL은 조회 전용입니다. UI 검증과 DB connection의 read-only 설정을 함께 사용하며 write SQL 기능은 두지 않습니다. 데이터 Filter의 WHERE 문자열은 그대로 붙이되, 앱 내부에서 관리하는 LIMIT/OFFSET 정수는 SQL에 직접 넣어 DB-API의 `%s` placeholder와 LIKE wildcard `%`가 충돌하지 않도록 합니다.

## 상태바와 리소스

- `app/status_bar.py`: 상태 메시지와 CPU/RAM 표시
- `app/resource_monitor.py`: 현재 WorKing 프로세스의 CPU/RSS 측정

## MainWindow의 역할

`MainWindow`는 워크스페이스를 조합하고 최상위 동작만 연결합니다.

- 업무/메모/터미널/DB 화면 전환
- 날짜와 전체 검색
- 일일보고 실행
- 설정 메뉴
- 앱 종료 시 각 workspace 정리

기능별 상태와 CRUD는 가능한 한 각 store/workspace/widget 쪽에 둡니다.
