#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "이 스크립트는 ChromeOS/Crostini Linux 환경용입니다."
  exit 1
fi

packages=(
  libx11-6
  libx11-xcb1
  libxext6
  libxfixes3
  libxi6
  libxrender1
  libice6
  libsm6
  libfontconfig1
  libfreetype6
  libxcb1
  libxcb-cursor0
  libxcb-icccm4
  libxcb-image0
  libxcb-keysyms1
  libxcb-randr0
  libxcb-render-util0
  libxcb-shape0
  libxcb-shm0
  libxcb-sync1
  libxcb-util1
  libxcb-xfixes0
  libxcb-xkb1
  libxkbcommon0
  libxkbcommon-x11-0
)

echo "Crostini용 Qt/X11 런타임 패키지를 설치합니다."
sudo apt-get update

available=()
for package in "${packages[@]}"; do
  if apt-cache show "$package" >/dev/null 2>&1; then
    available+=("$package")
  else
    echo "주의: 현재 Debian 저장소에서 '$package' 패키지를 찾지 못해 건너뜁니다."
  fi
done

if [[ ${#available[@]} -eq 0 ]]; then
  echo "설치 가능한 X11 패키지를 찾지 못했습니다."
  exit 1
fi

sudo apt-get install -y "${available[@]}"

echo
echo "설치가 완료되었습니다."
echo "가상환경이 활성화되어 있다면 다음 명령으로 앱을 실행하세요:"
echo "  python main.py"
