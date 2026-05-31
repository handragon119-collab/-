#!/bin/bash
# 더블클릭하면: 최신 코드 받기 → 웹 서버 켜기 → 브라우저 자동 열기 (macOS 전용)
cd "$(dirname "$0")"

echo "=================================================="
echo "  🧵 스레드 자동 업로드 웹앱을 시작합니다…"
echo "=================================================="

# 0) cloudflared(사진 호스팅용)를 찾을 수 있게 PATH 추가
export PATH="$HOME/bin:$PATH"

# 1) 최신 코드 자동 받기 (실패해도 그냥 진행)
echo "🔄 최신 코드 확인 중…"
git checkout -- topics.txt >/dev/null 2>&1
git pull origin claude/thread-post-automation-poN8e 2>/dev/null || echo "   (코드 업데이트 건너뜀 - 인터넷/충돌)"

# 2) 필요한 부품 설치(이미 있으면 빠르게 넘어감)
python3 -m pip install -q -r requirements.txt >/dev/null 2>&1

# 3) 혹시 이미 떠 있는 웹앱이 있으면 정리
pkill -f webapp.py >/dev/null 2>&1
sleep 1

# 4) 3초 뒤 브라우저 자동 열기
( sleep 3; open "http://127.0.0.1:5000" ) &

echo "✅ 브라우저가 곧 열립니다. (이 창을 닫으면 웹앱이 꺼져요)"
echo "=================================================="

# 5) 웹 서버 실행
python3 webapp.py
