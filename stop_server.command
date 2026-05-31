#!/bin/bash
# ─────────────────────────────────────────────
#  인스타 자동발행 스튜디오 — 서버 종료 (더블클릭)
# ─────────────────────────────────────────────
cd "$(dirname "$0")"

if pkill -f "web.server" 2>/dev/null; then
  echo "✅ 서버를 종료했습니다."
else
  echo "ℹ️  실행 중인 서버가 없습니다."
fi
rm -f web_server.pid
sleep 1
