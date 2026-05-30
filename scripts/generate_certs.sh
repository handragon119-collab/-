#!/usr/bin/env bash
# Generate a self-signed localhost certificate for JARVIS (HTTPS/WSS).
# Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f cert.pem && -f key.pem ]]; then
  echo "cert.pem and key.pem already exist — leaving them in place."
  exit 0
fi

echo "Generating self-signed certificate for localhost…"
openssl req -x509 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem \
  -days 365 -nodes -subj '/CN=localhost'

echo "Done. cert.pem and key.pem created (gitignored)."
echo "Chrome will warn about the self-signed cert the first time — that's expected."
