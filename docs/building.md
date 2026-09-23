# 빌드와 배포

PyInstaller로 실행파일을 만들 수 있습니다.

PyInstaller는 크로스컴파일러가 아니므로 Windows용은 Windows에서, macOS용은 macOS에서, Linux용은 Linux에서 각각 빌드합니다.

## Release에서 받기

GitHub Releases:

https://github.com/MiSo-13/daily-report-supporter/releases/latest

배포 파일:

| 환경 | 파일 |
| --- | --- |
| Windows x64 | `DailyReportSupporter.exe` |
| macOS Apple Silicon | `DailyReportSupporter-macos-arm64.zip` |
| macOS Intel | `DailyReportSupporter-macos-x64.zip` |
| ChromeOS/Crostini x64 | `DailyReportSupporter-linux-x64` |
| ChromeOS/Crostini ARM64 | `DailyReportSupporter-linux-arm64` |

Windows 사용자는 `.exe` 하나만 받아 실행하면 Python 설치가 필요하지 않습니다.

## 직접 빌드

먼저 빌드 의존성을 설치합니다.

```bash
pip install -r requirements.txt -r requirements-build.txt
```

공통 빌드 명령:

```bash
python scripts/build_app.py
```

### Windows

결과:

```text
dist/DailyReportSupporter.exe
```

단일 실행파일이며 콘솔 창 없이 실행됩니다.

### macOS

결과:

```text
dist/DailyReportSupporter.app
```

macOS에서는 PyInstaller 권장 방식에 맞춰 `.app` bundle을 생성합니다.

### Linux / ChromeOS Crostini

결과:

```text
dist/DailyReportSupporter
```

필요하면 실행 권한을 부여합니다.

```bash
chmod +x dist/DailyReportSupporter
```

## GitHub Actions

`.github/workflows/build-release.yml`에서 OS별 빌드를 실행합니다.

Actions 화면에서 수동 실행하면 빌드 artifact를 확인할 수 있습니다.

Release를 만들려면 태그를 push합니다.

```bash
git tag v0.1.0
git push origin v0.1.0
```

태그 빌드가 모두 성공하면 해당 GitHub Release에 OS별 파일이 자동 첨부됩니다.

## 배포판 데이터 위치

소스에서 실행할 때:

```text
<repository>/reports/
```

PyInstaller 실행파일로 실행할 때:

```text
~/DailyReportSupporter/reports/
```

Windows 예:

```text
C:\Users\<사용자>\DailyReportSupporter\reports
```

macOS 예:

```text
/Users/<사용자>/DailyReportSupporter/reports
```

ChromeOS/Crostini 예:

```text
/home/<사용자>/DailyReportSupporter/reports
```

실행파일을 다른 폴더로 옮겨도 업무 파일과 설정은 같은 위치를 사용합니다.

## 서명

현재 자동 빌드는 코드 서명/공증을 하지 않습니다.

따라서 처음 실행할 때:

- Windows: SmartScreen 경고가 표시될 수 있습니다.
- macOS: Gatekeeper 경고가 표시될 수 있습니다.

공개 배포를 본격적으로 할 경우 Windows 코드 서명 인증서와 Apple Developer ID/notarization을 추가하는 것을 권장합니다.

## ChromeOS 참고

Crostini x64와 ARM64 빌드를 각각 제공합니다.

Linux 실행파일은 시스템의 glibc 버전에 영향을 받습니다. 배포 실행파일이 동작하지 않는 오래된 Crostini 환경에서는 [빠른 시작](./getting-started.md)의 Python 실행 방식을 사용하면 됩니다.
