#!/bin/bash
# ─────────────────────────────────────────────
#  인스타 자동발행 스튜디오 — 자동 실행 등록 (더블클릭)
#  맥을 켜고 로그인하면 서버가 자동으로 켜지고,
#  꺼지면 알아서 다시 살아납니다. (상시 운영)
# ─────────────────────────────────────────────
cd "$(dirname "$0")"
PROJ="$(pwd)"
PY="$PROJ/.venv/bin/python"
PLIST="$HOME/Library/LaunchAgents/com.instaauto.server.plist"

# 1) 가상환경 없으면 설치
if [ ! -d "$PROJ/.venv" ]; then
  echo "🔧 처음 실행이라 환경을 설치합니다... (1~2분)"
  python3 -m venv "$PROJ/.venv" || { echo "❌ python3 가 필요합니다. python.org 에서 설치하세요."; read -n1; exit 1; }
  "$PY" -m pip install --upgrade pip >/dev/null 2>&1
  "$PY" -m pip install -r "$PROJ/requirements.txt" || { echo "❌ 설치 실패"; read -n1; exit 1; }
fi

# 2) launchd 설정 파일 생성
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.instaauto.server</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>-m</string>
    <string>web.server</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJ</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$PROJ/web_server.log</string>
  <key>StandardErrorPath</key>
  <string>$PROJ/web_server.log</string>
</dict>
</plist>
EOF

# 3) 등록(로드)
pkill -f "web.server" 2>/dev/null
launchctl unload "$PLIST" 2>/dev/null
launchctl load -w "$PLIST" && echo "✅ 자동 실행이 등록됐습니다." || { echo "❌ 등록 실패"; read -n1; exit 1; }
sleep 3

echo ""
echo "이제 맥을 껐다 켜도 서버가 자동으로 켜집니다."
echo "주소:  http://localhost:8000"
echo "끄고 싶으면  uninstall_autostart.command  를 더블클릭하세요."
open http://localhost:8000
sleep 1
