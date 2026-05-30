# JARVIS — Voice AI Assistant

A voice-first AI assistant for **macOS** with a British-butler personality and
an audio-reactive particle orb. You speak, JARVIS thinks (Claude Haiku),
replies in a British voice (ElevenLabs, with macOS `say` as a fallback), and
can act on your Mac — calendar, mail, notes, web search, opening apps, and
handing real build/research jobs to a background work mode.

> Built from a CLAUDE.md specification by **Taoufik** —
> https://www.youtube.com/@TaoufikAI

## Architecture

```
Microphone → Web Speech API → WebSocket → FastAPI → Claude Haiku → ElevenLabs TTS → Browser
                                             ↓
                                  AppleScript (Calendar, Mail, Notes, Terminal)
                                             ↓
                                  Claude Code work mode (background builds/research)
```

| Layer | Tech |
|-------|------|
| Backend | FastAPI + Python (`server.py`) |
| Frontend | Vite + TypeScript + Three.js (audio-reactive orb) |
| Comms | WebSocket (JSON + base64 MP3 audio) |
| AI | Claude Haiku — low-latency voice replies (≤250 tokens) |
| TTS | ElevenLabs (British "George"), macOS `say` fallback |
| System | AppleScript (no OAuth) |
| Storage | SQLite + FTS5 full-text search |

## Prerequisites

- macOS (for the AppleScript integrations + `say` fallback)
- Python 3.11+
- Node.js 18+
- Google Chrome (Web Speech API)
- An **Anthropic API key** (console.anthropic.com)
- An **ElevenLabs API key** (optional — without it, JARVIS uses macOS `say`)

## Quick start (macOS)

```bash
# One-shot: venv, deps, .env (prompts for keys), SSL certs
./scripts/setup.sh

# Run backend + frontend together, opens Chrome
./scripts/run.sh
```

Then click the page to enable audio, and start talking.

### Manual setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env          # then edit in your API keys
cd frontend && npm install && cd ..
./scripts/generate_certs.sh   # self-signed localhost cert
python server.py              # terminal 1  (https://localhost:8340)
cd frontend && npm run dev    # terminal 2  (http://localhost:5173)
```

## Project layout

```
.
├── server.py            # FastAPI core: /ws/voice, LLM, action dispatch, TTS, REST
├── memory.py            # SQLite + FTS5: facts, tasks, notes, 3-tier conversation memory
├── calendar_access.py   # Apple Calendar (read, cached, background refresh)
├── mail_access.py       # Apple Mail (read-only: unread, recent, search)
├── notes_access.py      # Apple Notes (read + create)
├── actions.py           # Open apps/URLs/Terminal, run shell
├── browser.py           # Playwright: search, visit, extract, screenshot
├── work_mode.py         # Background `claude -p --continue` sessions
├── planner.py           # Clarifying-question task planner
├── tts.py               # ElevenLabs → macOS `say` fallback
├── applescript.py       # Shared osascript wrapper (degrades off-macOS)
├── frontend/            # Vite + TS + Three.js app
│   └── src/{main,orb,voice,ws,settings}.ts, style.css
├── helpers/wake_listener.py   # optional double-clap wake (sounddevice)
└── scripts/{setup,run,generate_certs}.sh
```

## Voice actions

JARVIS can emit one action per reply, dispatched by the server:

| Tag | Effect |
|-----|--------|
| `[ACTION:CALENDAR]` | read today's calendar |
| `[ACTION:MAIL]` | unread mail summary |
| `[ACTION:NOTE: …]` | create an Apple Note |
| `[ACTION:SEARCH: …]` | web search (Playwright) |
| `[ACTION:OPEN: …]` | open an app or URL |
| `[ACTION:REMEMBER: …]` | store a durable fact |
| `[ACTION:TASK: …]` | add a to-do |
| `[ACTION:WORK: …]` | hand a build/research job to background work mode |

## Notes

- This runs on **macOS**; off-macOS the AppleScript features degrade gracefully
  so the server still boots (useful for development).
- `.env`, `*.pem`, `node_modules/`, `.venv/`, and the SQLite DB are gitignored.

---

This project was built from a CLAUDE.md specification authored by **Taoufik**
(https://www.youtube.com/@TaoufikAI). Please preserve attribution.
