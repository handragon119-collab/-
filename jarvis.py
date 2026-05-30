"""
jarvis.py - 자비스 메인 루프.

흐름:
  1. 호출어("자비스")를 기다린다  →  wake
  2. 명령을 듣는다                →  listen
  3. 기본 명령이면 직접 처리       →  commands.handle
  4. 아니면 LLM 두뇌가 답한다      →  Brain.think
  5. 소리내어 답한다              →  Voice.speak

실행:
  python jarvis.py            # 음성 모드(마이크 있으면) 또는 텍스트 모드
  python jarvis.py --text     # 강제로 텍스트(키보드) 모드
"""
from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass  # python-dotenv 미설치 시 환경변수는 OS에서만 읽음

import commands
from brain import Brain
from voice import Voice

EXIT_WORDS = ["종료", "그만", "잘 자", "꺼져", "exit", "quit", "bye"]


def contains_wake_word(text: str, wake: str) -> bool:
    return wake.lower() in text.lower()


def main() -> None:
    force_text = "--text" in sys.argv
    wake_word = os.getenv("JARVIS_WAKE_WORD", "자비스")
    lang = os.getenv("JARVIS_LANG", "ko-KR")

    voice = Voice(lang=lang)
    if force_text:
        voice._audio_ready = False  # 강제 텍스트 모드
    brain = Brain()

    print("=" * 56)
    print("  J.A.R.V.I.S  —  Just A Rather Very Intelligent System")
    print("=" * 56)
    mode = "음성" if voice.audio_ready else "텍스트(키보드)"
    state = "온라인(Claude)" if brain.online else "오프라인(규칙기반)"
    print(f"  입력 모드: {mode}   |   두뇌: {state}")
    if voice.audio_ready:
        print(f"  '{wake_word}' 라고 부른 뒤 명령하세요. ('종료'로 끝)")
    else:
        print(f"  명령을 입력하세요. (호출어 없이 바로 입력, '종료'로 끝)")
    print("=" * 56)

    voice.speak("자비스가 준비되었습니다. 무엇을 도와드릴까요?")

    while True:
        # --- 1) 호출어 대기 (음성 모드일 때만) ---
        if voice.audio_ready:
            heard = voice.listen("🎤 호출어 대기 중...")
            if not heard:
                continue
            if not contains_wake_word(heard, wake_word):
                continue
            # 호출어 뒤에 명령이 붙어 있으면 그대로 사용
            after = heard.lower().split(wake_word.lower(), 1)[-1].strip()
            command = after if after else None
            if command is None:
                voice.speak("네, 말씀하세요.")
                command = voice.listen()
        else:
            command = voice.listen()

        if not command:
            continue

        # --- 종료 ---
        if any(w in command.lower() for w in EXIT_WORDS):
            voice.speak("시스템을 종료합니다. 좋은 하루 되세요.")
            break

        # --- 2) 기본 명령 우선 처리 ---
        reply = commands.handle(command)

        # --- 3) 아니면 LLM 두뇌에게 ---
        if reply is None:
            reply = brain.think(command)

        voice.speak(reply)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 자비스를 종료합니다.")
