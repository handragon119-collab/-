# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
server.py — the FastAPI core of JARVIS.

Responsibilities:
  * Serve the voice WebSocket at /ws/voice (JSON control + base64 audio out)
  * Orchestrate the LLM (Claude Haiku) with a British-butler system prompt
  * Parse and dispatch [ACTION:...] tags to the right integration handlers
  * Synthesize speech (ElevenLabs → macOS `say` fallback)
  * Manage three-tier memory + per-session state
  * Expose a small REST API for the frontend and the wake listener

The model is asked to reply for voice (short, ≤ ~250 tokens) and may emit
action tags like:  [ACTION:CALENDAR]  [ACTION:MAIL]  [ACTION:NOTE: text]
[ACTION:SEARCH: query]  [ACTION:OPEN: app or url]  [ACTION:REMEMBER: fact]
[ACTION:TASK: title]  [ACTION:WORK: brief]
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import ssl
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import calendar_access
import mail_access
import notes_access
import actions
import tts
from memory import get_memory
from browser import get_browser
from work_mode import get_work_session
from planner import get_planner

try:
    from anthropic import AsyncAnthropic
except Exception:  # pragma: no cover
    AsyncAnthropic = None  # type: ignore

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 250
USER_NAME = os.environ.get("USER_NAME", "sir")

app = FastAPI(title="JARVIS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = get_memory()
_anthropic: "AsyncAnthropic | None" = None


def anthropic() -> "AsyncAnthropic":
    global _anthropic
    if _anthropic is None:
        if AsyncAnthropic is None:
            raise RuntimeError("anthropic SDK not installed")
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key or key == "your-anthropic-api-key-here":
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _anthropic = AsyncAnthropic(api_key=key)
    return _anthropic


SYSTEM_PROMPT = f"""You are JARVIS, a voice-first AI assistant with the
personality of a refined, dry-witted British butler. You address the user as
"{USER_NAME}". You are speaking out loud, so:
  * Keep replies short and natural — usually one to three sentences.
  * No markdown, no lists, no emoji — this will be read by a voice.
  * Be warm, precise, and quietly witty. Never grovel.

You can act on the user's Mac by emitting ACTION tags at the END of your reply.
Emit at most one tag. Available tags:
  [ACTION:CALENDAR]            — read today's calendar
  [ACTION:MAIL]                — read unread mail summary
  [ACTION:NOTE: <text>]        — create an Apple Note
  [ACTION:SEARCH: <query>]     — search the web
  [ACTION:OPEN: <app or url>]  — open an app or URL
  [ACTION:REMEMBER: <fact>]    — store a durable fact about the user
  [ACTION:TASK: <title>]       — add a to-do
  [ACTION:WORK: <brief>]       — hand a real build/research job to background work mode

When you emit an action, still speak a short natural sentence first
(e.g. "Let me check your calendar." then the tag). Do not describe the tag."""


# --------------------------------------------------------------------------- #
# Action handling
# --------------------------------------------------------------------------- #

ACTION_RE = re.compile(r"\[ACTION:([A-Z]+)(?::\s*(.*?))?\]\s*$", re.DOTALL)


def strip_action(text: str) -> tuple[str, str | None, str | None]:
    """Split a model reply into (spoken_text, action_name, action_arg)."""
    m = ACTION_RE.search(text)
    if not m:
        return text.strip(), None, None
    spoken = text[: m.start()].strip()
    return spoken, m.group(1), (m.group(2) or "").strip()


async def run_action(name: str, arg: str | None) -> str:
    """Execute an action tag and return a short follow-up line to speak."""
    name = (name or "").upper()
    arg = arg or ""
    try:
        if name == "CALENDAR":
            return calendar_access.summary_line()
        if name == "MAIL":
            return mail_access.summary_line()
        if name == "NOTE":
            ok = notes_access.create("JARVIS", arg)
            memory.add_note(arg)
            return "I've noted that down." if ok else "Saved to memory."
        if name == "SEARCH":
            results = await get_browser().search(arg, limit=3)
            if not results:
                return f"I couldn't find much on {arg}."
            top = results[0]
            return f"Top result: {top['title']}. {top['snippet'][:160]}"
        if name == "OPEN":
            if arg.startswith("http") or "." in arg.split()[0]:
                ok = actions.open_url(arg if arg.startswith("http") else f"https://{arg}")
            else:
                ok = actions.open_app(arg)
            return f"Opening {arg}." if ok else f"I couldn't open {arg}."
        if name == "REMEMBER":
            memory.add_fact(arg)
            return "I'll remember that."
        if name == "TASK":
            memory.add_task(arg)
            return f"Added to your tasks: {arg}."
        if name == "WORK":
            res = get_work_session().run(arg)
            return ("I'm on it — working in the background now."
                    if res.get("ok") else f"I couldn't start that: {res.get('error')}")
    except Exception as exc:  # keep the voice loop alive
        return f"I ran into a problem with that: {exc}"
    return ""


# --------------------------------------------------------------------------- #
# LLM orchestration
# --------------------------------------------------------------------------- #

def build_messages(session: str, prompt: str) -> list[dict[str, str]]:
    ctx = memory.build_context(session, prompt)
    msgs: list[dict[str, str]] = []

    preamble_bits = []
    if ctx["summary"]:
        preamble_bits.append(f"Conversation so far: {ctx['summary']}")
    if ctx["facts"]:
        facts = "; ".join(f["content"] for f in ctx["facts"])
        preamble_bits.append(f"Relevant facts about {USER_NAME}: {facts}")
    if ctx["notes"]:
        notes = "; ".join(n["body"][:120] for n in ctx["notes"])
        preamble_bits.append(f"Relevant notes: {notes}")
    if preamble_bits:
        msgs.append({"role": "user", "content": "[context]\n" + "\n".join(preamble_bits)})
        msgs.append({"role": "assistant", "content": "Understood."})

    for m in ctx["recent"]:
        role = "assistant" if m["role"] == "assistant" else "user"
        msgs.append({"role": role, "content": m["content"]})

    msgs.append({"role": "user", "content": prompt})
    return msgs


async def think(session: str, prompt: str) -> str:
    """Run one LLM turn and return the raw reply (may contain an ACTION tag)."""
    messages = build_messages(session, prompt)
    client = anthropic()
    resp = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "".join(parts).strip()


async def maybe_summarize(session: str) -> None:
    """Roll older messages into the mid-term summary when history grows."""
    recent = memory.recent_messages(session, limit=40)
    if len(recent) < 30:
        return
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent[:-10])
    try:
        client = anthropic()
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=200,
            system="Summarise this conversation in 3-4 sentences, preserving facts and intents.",
            messages=[{"role": "user", "content": convo}],
        )
        summary = "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        ).strip()
        if summary:
            memory.set_summary(session, summary)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Voice WebSocket
# --------------------------------------------------------------------------- #

class EchoFilter:
    """Avoid JARVIS hearing and responding to its own spoken output."""

    def __init__(self) -> None:
        self.last_spoken = ""

    def is_echo(self, heard: str) -> bool:
        if not self.last_spoken:
            return False
        a = re.sub(r"\W+", " ", heard.lower()).strip()
        b = re.sub(r"\W+", " ", self.last_spoken.lower()).strip()
        if not a:
            return True
        # crude containment / overlap check
        return a in b or b in a


async def handle_turn(ws: WebSocket, session: str, echo: EchoFilter, text: str) -> None:
    text = (text or "").strip()
    if not text or echo.is_echo(text):
        return

    await ws.send_json({"type": "state", "state": "thinking"})
    memory.add_message(session, "user", text)

    try:
        raw = await think(session, text)
    except Exception as exc:
        await ws.send_json({"type": "error", "message": str(exc)})
        await ws.send_json({"type": "state", "state": "idle"})
        return

    spoken, action, arg = strip_action(raw)
    if action:
        follow = await run_action(action, arg)
        spoken = (spoken + " " + follow).strip() if spoken else follow

    memory.add_message(session, "assistant", spoken)
    echo.last_spoken = spoken
    await maybe_summarize(session)

    await ws.send_json({"type": "transcript", "role": "assistant", "text": spoken})
    await ws.send_json({"type": "state", "state": "speaking"})

    result = await tts.synthesize(spoken)
    if result.audio:
        b64 = base64.b64encode(result.audio).decode("ascii")
        await ws.send_json({"type": "audio", "format": "mp3", "data": b64})
    else:
        # macOS `say` already spoke locally, or no audio available.
        await ws.send_json({"type": "spoken_locally", "engine": result.engine})

    await ws.send_json({"type": "state", "state": "idle"})


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket) -> None:
    await ws.accept()
    session = uuid.uuid4().hex[:12]
    echo = EchoFilter()
    await ws.send_json({"type": "ready", "session": session, "user": USER_NAME})
    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")
            if mtype == "transcript":
                await handle_turn(ws, session, echo, msg.get("text", ""))
            elif mtype == "ping":
                await ws.send_json({"type": "pong"})
            elif mtype == "reset":
                session = uuid.uuid4().hex[:12]
                echo.last_spoken = ""
                await ws.send_json({"type": "ready", "session": session})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        try:
            await ws.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# REST API
# --------------------------------------------------------------------------- #

class WakeBody(BaseModel):
    key: str | None = None


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "jarvis",
        "macos": calendar_access.available(),
        "has_anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()
                                  not in ("", "your-anthropic-api-key-here")),
        "has_elevenlabs_key": bool(os.environ.get("ELEVENLABS_API_KEY", "").strip()
                                   not in ("", "your-elevenlabs-api-key-here")),
    }


@app.get("/api/tasks")
async def get_tasks() -> dict[str, Any]:
    return {"tasks": memory.list_tasks()}


@app.get("/api/facts")
async def get_facts() -> dict[str, Any]:
    return {"facts": memory.all_facts()}


@app.get("/api/work/status")
async def work_status() -> dict[str, Any]:
    return get_work_session().status()


@app.post("/api/wake")
async def wake(body: WakeBody) -> JSONResponse:
    expected = os.environ.get("JARVIS_WAKE_KEY", "")
    if expected and body.key != expected:
        return JSONResponse({"ok": False, "error": "bad key"}, status_code=403)
    return JSONResponse({"ok": True, "message": "Awake."})


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #

def _ssl_context() -> ssl.SSLContext | None:
    cert, key = Path("cert.pem"), Path("key.pem")
    if cert.exists() and key.exists():
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert), str(key))
        return ctx
    return None


def main() -> None:
    print("JARVIS server · Built from CLAUDE.md by Taoufik — https://www.youtube.com/@TaoufikAI")
    if calendar_access.available():
        calendar_access.start_background_refresh()
    cert, key = Path("cert.pem"), Path("key.pem")
    ssl_kwargs: dict[str, Any] = {}
    if cert.exists() and key.exists():
        ssl_kwargs = {"ssl_certfile": str(cert), "ssl_keyfile": str(key)}
        scheme = "https"
    else:
        scheme = "http"
        print("⚠️  No cert.pem/key.pem found — starting WITHOUT TLS.")
        print("   Run ./scripts/generate_certs.sh to enable HTTPS (required by the frontend).")
    print(f"   Listening on {scheme}://localhost:8340")
    uvicorn.run(app, host="0.0.0.0", port=8340, **ssl_kwargs)


if __name__ == "__main__":
    main()
