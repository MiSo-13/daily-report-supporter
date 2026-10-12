# 설정

설정은 상단 `설정` 메뉴에서 변경합니다. 저장 파일은 `<app-root>/data/config/settings.json`입니다.

## 일일보고

`설정 → 일일보고 설정...`에서 보고서 제목과 상단/하단 문구를 바꿀 수 있습니다.

기본 제목:

```text
진행 업무
예정 업무
```

업무 분류는 고정입니다.

| 상태 | 진행 업무 | 예정 업무 |
| --- | --- | --- |
| 예정 |  | O |
| 진행중 | O | O |
| 완료 | O |  |

상단 문구와 꼬리말은 입력한 줄바꿈을 그대로 유지합니다. 날짜가 필요하면 토큰을 넣습니다.

| 토큰 | 2026-09-23 기준 |
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
```

이전 버전에서 사용하던 `previous_section_title`, `today_section_title` 값은 기존 Markdown 호환을 위해 설정 파일에 남아 있지만 현재 설정 화면에서는 직접 바꾸지 않습니다.

## 테마

`설정 → 테마`에서 선택합니다.

- Light
- Dark
- Purple
- Nord
- Solarized Light
- Solarized Dark
- Sepia

테마 변경은 바로 적용됩니다.

## 폰트

`설정 → 폰트...`에서 앱 UI와 터미널 폰트를 따로 지정합니다.

- 앱 폰트: 일반 폰트, 8~32pt
- 터미널 폰트: 고정폭 폰트, 8~32pt
- 빈 family 값: 운영체제 기본 폰트

다른 PC에 같은 폰트가 없으면 Qt/운영체제의 fallback 폰트를 사용합니다.

## CPU / RAM 표시

`설정 → CPU / RAM 표시`에서 하단 리소스 표시를 켜거나 끕니다.

표시되는 값은 시스템 전체가 아니라 WorKing 프로세스의 CPU/RAM 사용량입니다. 옵션을 끄면 표시뿐 아니라 측정 타이머도 중지합니다.

## 입력기 호환 모드

`설정 → 입력기 호환 모드`에는 두 가지 옵션이 있습니다.

- `시스템 기본값`: OS의 입력기 설정 사용
- `Crostini 한글 호환 (IBus)`: ChromeOS/Crostini용 IBus 환경변수 적용

IBus 모드는 다음 실행부터 적용됩니다.

```text
QT_IM_MODULE=ibus
XMODIFIERS=@im=ibus
GTK_IM_MODULE=ibus
```

실제 한/영 전환 키는 ChromeOS/IBus 설정을 따릅니다.

## settings.json

예:

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

파일이 없으면 앱 시작 시 기본값으로 생성합니다. 읽을 수 없는 JSON이면 기본 설정으로 복구합니다.
