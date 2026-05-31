#!/bin/bash
# ─────────────────────────────────────────────
#  인스타 자동발행 스튜디오 — 자동 실행 해제 (더블클릭)
# ─────────────────────────────────────────────
PLIST="$HOME/Library/LaunchAgents/com.instaauto.server.plist"

launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST"
pkill -f "web.server" 2>/dev/null

echo "✅ 자동 실행을 해제하고 서버를 종료했습니다."
echo "   (다시 켜려면 install_autostart.command 또는 start_server.command 더블클릭)"
sleep 1
