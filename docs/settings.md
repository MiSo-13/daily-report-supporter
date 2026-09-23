# 설정 가이드

상단의 `설정 → 일일보고 설정...`에서 일일보고 관련 설정을 변경할 수 있습니다.

## 업무 영역 제목

기본값:

```text
이전 업무 제목: 어제 했던 일
오늘 업무 제목: 오늘 해야 할 일
```

예:

```text
이전 업무 제목: 전일 업무
오늘 업무 제목: 금일 업무
```

변경된 값은 앱 탭과 Markdown의 `##` 제목에 같이 적용됩니다.

## 인사말

예:

```text
안녕하세요.
YY. MM. DD 업무 공유드립니다.
```

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

## 테마

`설정 → 테마`에서 변경할 수 있습니다.

- Light
- Dark
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
  "greeting": "안녕하세요.\nYY. MM. DD 업무 공유드립니다.",
  "footer": "감사합니다.",
  "previous_section_title": "전일 업무",
  "today_section_title": "금일 업무",
  "input_method_mode": "system"
}
```

파일이 없으면 앱 시작 시 자동으로 생성됩니다.
