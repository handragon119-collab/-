# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
memory.py — JARVIS persistent memory system.

A small SQLite-backed store providing:
  * facts   — long-term key/value-ish knowledge ("the user likes flat whites")
  * tasks   — to-dos with status + optional due date
  * notes   — free-form notes captured during conversation
  * messages — full conversation log (three-tier memory lives on top of this)

Full-text search is provided by FTS5 virtual tables that mirror the
facts / notes / messages tables via triggers, so JARVIS can recall things
by meaning-ish keyword lookups quickly.

The three-tier conversation memory used by the server:
  1. short-term  — the last N raw messages (verbatim)
  2. mid-term    — a rolling summary of older messages in the session
  3. long-term   — durable facts surfaced by FTS5 relevance to the prompt
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(os.environ.get("JARVIS_DB", "data/jarvis.db"))


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    content   TEXT NOT NULL,
    category  TEXT DEFAULT 'general',
    created   REAL NOT NULL,
    updated   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    detail    TEXT DEFAULT '',
    status    TEXT NOT NULL DEFAULT 'open',   -- open | done | cancelled
    due       REAL,
    created   REAL NOT NULL,
    updated   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT DEFAULT '',
    body      TEXT NOT NULL,
    created   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session   TEXT NOT NULL,
    role      TEXT NOT NULL,                  -- user | assistant | system
    content   TEXT NOT NULL,
    created   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    session   TEXT PRIMARY KEY,
    summary   TEXT NOT NULL,
    updated   REAL NOT NULL
);

-- FTS5 mirrors -----------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
    USING fts5(content, content='facts', content_rowid='id');
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
    USING fts5(title, body, content='notes', content_rowid='id');
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
    USING fts5(content, content='messages', content_rowid='id');

-- keep FTS in sync via triggers -----------------------------------------
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
"""


def _fts_query(text: str) -> str:
    """Turn arbitrary user text into a safe FTS5 OR-query of prefix terms."""
    terms = [t for t in "".join(c if c.isalnum() else " " for c in text).split() if len(t) > 2]
    if not terms:
        return ""
    return " OR ".join(f'"{t}"*' for t in terms[:12])


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #

@dataclass
class Task:
    id: int
    title: str
    detail: str
    status: str
    due: float | None
    created: float
    updated: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Memory store
# --------------------------------------------------------------------------- #

class Memory:
    def __init__(self, path: Path | str = DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL;")
        self.db.executescript(_SCHEMA)
        self.db.commit()

    # -- facts -------------------------------------------------------------
    def add_fact(self, content: str, category: str = "general") -> int:
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO facts(content, category, created, updated) VALUES (?,?,?,?)",
            (content.strip(), category, now, now),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def search_facts(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q = _fts_query(query)
        if not q:
            return []
        rows = self.db.execute(
            """SELECT f.id, f.content, f.category
                 FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid
                WHERE facts_fts MATCH ?
                ORDER BY rank LIMIT ?""",
            (q, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def all_facts(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT id, content, category FROM facts ORDER BY updated DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def forget_fact(self, fact_id: int) -> None:
        self.db.execute("DELETE FROM facts WHERE id=?", (fact_id,))
        self.db.commit()

    # -- tasks -------------------------------------------------------------
    def add_task(self, title: str, detail: str = "", due: float | None = None) -> int:
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO tasks(title, detail, status, due, created, updated) VALUES (?,?,?,?,?,?)",
            (title.strip(), detail, "open", due, now, now),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def list_tasks(self, status: str = "open", limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM tasks WHERE status=? ORDER BY (due IS NULL), due, created LIMIT ?",
            (status, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def complete_task(self, task_id: int) -> bool:
        cur = self.db.execute(
            "UPDATE tasks SET status='done', updated=? WHERE id=? AND status='open'",
            (time.time(), task_id),
        )
        self.db.commit()
        return cur.rowcount > 0

    # -- notes -------------------------------------------------------------
    def add_note(self, body: str, title: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO notes(title, body, created) VALUES (?,?,?)",
            (title, body.strip(), time.time()),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def search_notes(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q = _fts_query(query)
        if not q:
            return []
        rows = self.db.execute(
            """SELECT n.id, n.title, n.body
                 FROM notes_fts JOIN notes n ON n.id = notes_fts.rowid
                WHERE notes_fts MATCH ?
                ORDER BY rank LIMIT ?""",
            (q, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- conversation ------------------------------------------------------
    def add_message(self, session: str, role: str, content: str) -> int:
        cur = self.db.execute(
            "INSERT INTO messages(session, role, content, created) VALUES (?,?,?,?)",
            (session, role, content, time.time()),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def recent_messages(self, session: str, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT role, content FROM messages WHERE session=? ORDER BY id DESC LIMIT ?",
            (session, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def search_messages(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q = _fts_query(query)
        if not q:
            return []
        rows = self.db.execute(
            """SELECT m.role, m.content
                 FROM messages_fts JOIN messages m ON m.id = messages_fts.rowid
                WHERE messages_fts MATCH ?
                ORDER BY rank LIMIT ?""",
            (q, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self, session: str) -> str:
        row = self.db.execute(
            "SELECT summary FROM summaries WHERE session=?", (session,)
        ).fetchone()
        return row["summary"] if row else ""

    def set_summary(self, session: str, summary: str) -> None:
        self.db.execute(
            "INSERT INTO summaries(session, summary, updated) VALUES (?,?,?) "
            "ON CONFLICT(session) DO UPDATE SET summary=excluded.summary, updated=excluded.updated",
            (session, summary, time.time()),
        )
        self.db.commit()

    # -- three-tier context assembly --------------------------------------
    def build_context(self, session: str, prompt: str, short_n: int = 10) -> dict[str, Any]:
        """Return the pieces the server stitches into the LLM context."""
        relevant_facts = self.search_facts(prompt, limit=5)
        relevant_notes = self.search_notes(prompt, limit=3)
        return {
            "facts": relevant_facts,
            "notes": relevant_notes,
            "summary": self.get_summary(session),
            "recent": self.recent_messages(session, limit=short_n),
        }

    def close(self) -> None:
        self.db.close()


# Module-level singleton convenience
_default: Memory | None = None


def get_memory() -> Memory:
    global _default
    if _default is None:
        _default = Memory()
    return _default


if __name__ == "__main__":
    m = Memory(":memory:")
    m.add_fact("The user prefers a flat white in the morning", "preferences")
    m.add_task("Ship the JARVIS demo", "record the YouTube walkthrough")
    print("facts:", m.search_facts("coffee flat white"))
    print("tasks:", m.list_tasks())
