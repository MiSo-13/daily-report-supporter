# 설정 가이드

상단의 `설정 → 일일보고 설정...`에서 일일보고 관련 설정을 변경할 수 있습니다.

## 일일보고 업무 제목

기본값:

```text
진행 업무 제목: 진행 업무
예정 업무 제목: 예정 업무
```

`설정 → 일일보고 설정...`에서 변경할 수 있습니다.

보고서 제목에는 대괄호가 자동으로 붙지 않습니다. 이전 버전에서 오늘 업무 제목을 커스텀했다면 해당 값은 진행 업무 제목으로 승계됩니다.

## 상단 문구

상단 문구는 일일보고의 첫 부분입니다. 상단 문구가 끝나면 설정한 진행 업무 제목이 이어집니다.

고정된 날짜 제목은 따로 추가되지 않습니다. 날짜가 필요하면 날짜 토큰을 상단 문구에 넣습니다. 상단 문구와 꼬리말은 일반 텍스트로 처리하며 줄바꿈과 중간 빈 줄도 그대로 유지됩니다.

기본값:

```text
안녕하세요.
금일 업무 진행사항 공유드립니다.

YYYY년 MM월 DD일 일일보고입니다.
```

예:

```text
안녕하세요.
YY. MM. DD 업무 공유드립니다.
```

## 일일보고 분류

- 진행중 → 진행 업무 + 예정 업무
- 완료 → 진행 업무
- 예정 → 예정 업무

업무는 모두 `오늘 업무`에서 관리합니다. 실제 출력 제목은 위의 진행 업무/예정 업무 제목 설정을 사용합니다.

## 꼬리말

예:

```text
이상입니다.
감사합니다.
```

## 날짜 토큰

일일보고에서 선택한 날짜를 기준으로 변환됩니다.

| 토큰 | 2026-09-23 |
| --- | --- |
| `YY.MM.DD` | `26.09.23` |
| `YY. MM. DD` | `26. 09. 23` |
| `YYYY.MM.DD` | `2026.09.23` |
| `YYYY-MM-DD` | `2026-09-23` |
| `YYYY년 MM월 DD일` | `2026년 09월 23일` |

## 입력기 호환 모드

`설정 → 입력기 호환 모드`에서 선택합니다.

### 시스템 기본값

OS와 실행 환경의 입력기 설정을 그대로 사용합니다. 기본값입니다.

### Crostini 한글 호환 (IBus)

ChromeOS/Crostini에서 한글 입력이 되지 않을 때 사용합니다.

다음 실행부터 아래 환경이 적용됩니다.

```text
QT_IM_MODULE=ibus
XMODIFIERS=@im=ibus
GTK_IM_MODULE=ibus
```

실제 한/영 전환은 ChromeOS 또는 IBus의 단축키를 사용합니다.

## 폰트

`설정 → 폰트...`에서 다음 값을 설정할 수 있습니다.

- 앱 font family
- 앱 font size (8~32pt)
- 터미널 fixed-pitch font family
- 터미널 font size (8~32pt)

family 값이 빈 문자열이면 운영체제 기본 폰트를 사용합니다.

기본값:

```json
{
  "font_family": "",
  "font_size": 10,
  "terminal_font_family": "",
  "terminal_font_size": 10
}
```

저장된 폰트가 다른 PC에 설치되어 있지 않으면 Qt/운영체제의 font fallback이 적용됩니다.

## CPU / RAM 표시

`설정 → CPU / RAM 표시`에서 하단 왼쪽의 WorKing 프로세스 CPU/RAM 사용량 표시를 켜거나 끌 수 있습니다.

기본값은 표시입니다.

```json
{
  "show_resource_usage": true
}
```

표시를 끄면 UI만 숨기는 것이 아니라 리소스 측정 타이머도 중지합니다.

## 테마

`설정 → 테마`에서 변경할 수 있습니다.

- Light
- Dark
- Purple
- Nord
- Solarized Light
- Solarized Dark
- Sepia

## 설정 파일

설정은 아래 파일에 저장됩니다.

```text
reports/settings.json
```

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

파일이 없으면 앱 시작 시 자동으로 생성됩니다.

`previous_section_title`과 `today_section_title`은 기존 일일 Markdown 호환용 내부 설정으로 유지되며 현재 일일보고 설정 화면에서는 변경하지 않습니다.
