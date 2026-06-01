#!/bin/bash
# 클릭 한 번으로: 최신 코드 받기 → 서버 켜기 → (서버 준비되면) 브라우저 자동 열기
cd "$HOME/threads-auto" || { echo "threads-auto 폴더를 찾을 수 없어요."; exit 1; }

export PATH="$HOME/bin:$PATH"
PORT=5050
URL="http://127.0.0.1:$PORT"

echo "=================================================="
echo "  🧵 스레드 자동 업로드 실행 중…"
echo "=================================================="

# 1) 최신 코드 받기 (실패해도 진행)
echo "🔄 최신 코드 확인…"
git checkout -- topics.txt >/dev/null 2>&1
git pull origin claude/thread-post-automation-poN8e >/dev/null 2>&1 || echo "   (업데이트 건너뜀)"

# 2) 필요한 부품이 없을 때만 설치 (빠르게)
python3 -c "import flask" >/dev/null 2>&1 || {
  echo "📦 필요한 부품 설치 중… (처음 한 번만)"
  python3 -m pip install -q -r requirements.txt >/dev/null 2>&1
}

# 3) 기존에 떠 있던 서버 정리
pkill -f webapp.py >/dev/null 2>&1
sleep 1

# 4) 서버 시작 (백그라운드)
echo "🚀 서버 시작 중…"
python3 webapp.py &
SERVER_PID=$!

# 5) 서버가 응답할 때까지 기다렸다가 브라우저 열기 (최대 ~20초)
for i in $(seq 1 40); do
  if curl -s -o /dev/null "$URL"; then
    open "$URL"
    echo "✅ 브라우저가 열렸어요!  ($URL)"
    break
  fi
  sleep 0.5
done

echo "=================================================="
echo "  이 창을 닫으면 서버가 꺼집니다. (계속 켜두려면 그대로 두세요)"
echo "=================================================="

# 6) 서버 프로세스를 붙잡아 둠 (창 닫으면 같이 종료)
wait $SERVER_PID
