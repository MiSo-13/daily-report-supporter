# 코드 구조

WorKing은 PyQt6 UI, Markdown 기반 업무 데이터, 독립 메모/터미널 워크스페이스로 구성됩니다.

## 앱 진입점

- `main.py`: 입력기/Qt platform 사전 설정 후 GUI 실행
- `app/main_window.py`: 최상위 화면 전환, 업무 검색/일일보고, 설정 메뉴 연결
- `app/app_meta.py`: 앱 이름, 조직명, bundle identifier, 현재/legacy 데이터 디렉터리 이름

## 경로

- `app/paths.py`: 프로젝트/실행파일 옆 `data/` 기준 Portable 경로와 legacy 경로 정의
- `app/runtime_paths.py`: MainWindow에 전달된 override와 기본 경로를 하나의 `AppRuntimePaths`로 해석
- `app/data_migration.py`: 기존 `DailyReportSupporter`, 전환 `WorKing`, 소스 실행 데이터를 현재 앱 옆 `data/`로 복사

사용자 데이터는 소스/배포 실행 모두 `<app-root>/data/` 아래에만 저장합니다. 홈 디렉터리의 `DailyReportSupporter`/`WorKing` 경로는 기존 사용자 데이터 탐색용 migration source로만 읽습니다.

## 업무

- `app/markdown_store.py`: 일일 Markdown 읽기/쓰기
- `app/task_editor.py`: 업무 편집 UI
- `app/models.py`: 업무/문서 모델
- `app/report_builder.py`: 일일보고 생성

## 메모

- `app/memo_store.py`: Markdown 메모와 사용자 정렬 순서 저장
- `app/memo_sidebar.py`: 메모 검색/목록 UI
- `app/memo_editor.py`: Raw Markdown + 렌더링 편집
- `app/memo_workspace.py`: 메모 생성/선택/저장/삭제 lifecycle 조정

메모 기능을 수정할 때 MainWindow에 CRUD 로직을 추가하지 않고 `MemoWorkspace`에 배치합니다.

## 터미널

- `app/terminal_backend.py`: Unix PTY / Windows ConPTY
- `app/terminal_display.py`: 키 입력, ANSI 기본 처리, 출력 buffer/scrollback 제한
- `app/terminal_dialogs.py`: SSH profile 입력 UI
- `app/terminal_store.py`: local/SSH profile 저장
- `app/terminal_ui.py`: 세션 widget, sidebar, panel
- `app/terminal_workspace.py`: 세션 생성/선택/편집/삭제 lifecycle 조정

PTY/렌더링 로직과 프로필/워크스페이스 로직을 분리해 대량 로그 최적화가 다른 UI에 영향을 주지 않도록 합니다.

## 설정과 스타일

- `app/settings.py`: `config/settings.json` 저장 및 설정 필드 migration
- `app/themes.py`: 앱/터미널 palette
- `app/status_bar.py`: CPU/RAM 표시와 branding
- `app/resource_monitor.py`: 현재 프로세스 CPU/RSS 측정

CPU/RAM 표시 여부, 테마, 폰트, 입력기, 일일보고 설정은 모두 `<app-root>/data/config/settings.json`에 저장합니다.

## UI 책임 원칙

`MainWindow`는 다음 역할만 직접 담당합니다.

1. 업무 워크스페이스와 전체 검색
2. 메모/터미널 워크스페이스 조합
3. 최상위 메뉴/테마/폰트 설정 연결
4. 날짜 전환과 일일보고 실행

메모와 터미널 내부 CRUD는 각 workspace 객체가 담당합니다.
