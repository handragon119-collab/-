# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
planner.py — conversational task planning.

Before JARVIS hands a big "build me X" request to work mode, the planner asks
a couple of clarifying questions so the eventual brief is concrete. It keeps a
tiny per-session state machine: gathering → ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Plan:
    goal: str = ""
    answers: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    asked: int = 0
    state: str = "idle"  # idle | gathering | ready

    def brief(self) -> str:
        lines = [f"Goal: {self.goal}", ""]
        for q, a in zip(self.questions, self.answers):
            lines.append(f"- {q} → {a}")
        return "\n".join(lines)


# A small generic set of clarifying questions that work for most "build" asks.
_DEFAULT_QUESTIONS = [
    "What's the single most important outcome you want from this?",
    "Any constraints I should respect — language, tools, or deadline?",
    "Should I optimise for a quick prototype or something production-ready?",
]


class Planner:
    def __init__(self) -> None:
        self.plan = Plan()

    def start(self, goal: str, questions: list[str] | None = None) -> str:
        self.plan = Plan(goal=goal, state="gathering",
                         questions=questions or list(_DEFAULT_QUESTIONS))
        return self.next_question()

    def next_question(self) -> str:
        if self.plan.asked >= len(self.plan.questions):
            self.plan.state = "ready"
            return ""
        q = self.plan.questions[self.plan.asked]
        return q

    def answer(self, text: str) -> dict[str, Any]:
        """Record an answer and advance. Returns next prompt or final brief."""
        if self.plan.state != "gathering":
            return {"state": self.plan.state, "message": "No active plan."}
        self.plan.answers.append(text.strip())
        self.plan.asked += 1
        nxt = self.next_question()
        if self.plan.state == "ready":
            return {"state": "ready", "brief": self.plan.brief()}
        return {"state": "gathering", "question": nxt}

    def reset(self) -> None:
        self.plan = Plan()


_default: Planner | None = None


def get_planner() -> Planner:
    global _default
    if _default is None:
        _default = Planner()
    return _default
