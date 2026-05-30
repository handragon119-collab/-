#!/usr/bin/env bash
# One-shot setup for JARVIS on macOS.
# Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
#
# Creates the venv, installs Python + frontend deps, generates SSL certs,
# and scaffolds .env (prompting for API keys if they're not already set).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setting up JARVIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Python virtual environment ------------------------------------------
if [[ ! -d .venv ]]; then
  echo "→ Creating Python virtual environment (.venv)…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2. Python dependencies --------------------------------------------------
echo "→ Installing Python dependencies…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "→ Installing Playwright Chromium…"
python -m playwright install chromium || echo "  (skip: install Playwright browsers later with 'python -m playwright install chromium')"

# 3. .env -----------------------------------------------------------------
if [[ ! -f .env ]]; then
  echo "→ Creating .env from .env.example…"
  cp .env.example .env

  read -r -p "Enter your ANTHROPIC_API_KEY (blank to edit .env later): " ANTH || true
  if [[ -n "${ANTH:-}" ]]; then
    /usr/bin/sed -i '' "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${ANTH}|" .env
  fi
  read -r -p "Enter your ELEVENLABS_API_KEY (blank to use macOS 'say' fallback): " ELEVEN || true
  if [[ -n "${ELEVEN:-}" ]]; then
    /usr/bin/sed -i '' "s|^ELEVENLABS_API_KEY=.*|ELEVENLABS_API_KEY=${ELEVEN}|" .env
  fi
else
  echo "→ .env already exists — leaving it untouched."
fi

# 4. Frontend dependencies ------------------------------------------------
echo "→ Installing frontend dependencies…"
( cd frontend && npm install )

# 5. SSL certs ------------------------------------------------------------
echo "→ Generating SSL certificates…"
bash scripts/generate_certs.sh

echo
echo "✅ Setup complete. Start JARVIS with:"
echo "     ./scripts/run.sh        (backend + frontend together)"
echo "   or run them separately:"
echo "     source .venv/bin/activate && python server.py"
echo "     cd frontend && npm run dev"
