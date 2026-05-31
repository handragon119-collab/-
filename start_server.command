#!/bin/bash
# ─────────────────────────────────────────────
#  인스타 자동발행 스튜디오 — 서버 시작 (더블클릭)
#  터미널을 꺼도 서버가 계속 살아있습니다.
# ─────────────────────────────────────────────
cd "$(dirname "$0")"

# 1) 처음이면 가상환경 + 의존성 설치
if [ ! -d ".venv" ]; then
  echo "🔧 처음 실행이라 환경을 설치합니다... (1~2분 걸려요)"
  python3 -m venv .venv || { echo "❌ python3 가 필요합니다. python.org 에서 설치하세요."; read -n1; exit 1; }
  ./.venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1
  ./.venv/bin/pip install -r requirements.txt || { echo "❌ 설치 실패"; read -n1; exit 1; }
fi

# 2) 이미 켜져 있으면 정리
pkill -f "web.server" 2>/dev/null
sleep 1

# 3) 백그라운드로 분리 실행 (터미널 닫아도 유지: nohup)
nohup ./.venv/bin/python -m web.server > web_server.log 2>&1 < /dev/null &
echo $! > web_server.pid
sleep 3

echo ""
echo "✅ 서버가 백그라운드에서 시작됐습니다."
echo "   주소:  http://localhost:8000"
echo ""
echo "👉 이 창은 닫아도 서버는 계속 켜져 있어요."
echo "👉 끄고 싶을 땐  stop_server.command  를 더블클릭하세요."

# 브라우저 자동 열기
open http://localhost:8000
sleep 1
