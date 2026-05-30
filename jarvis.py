"""
jarvis.py - 자비스 메인 루프.

흐름 (기본: 박수 모드):
  1. 👏 박수를 기다린다              →  wait_for_clap
  2. 🎸 Back in Black 재생          →  music.play_wake_music
  3. 🇬🇧 영어로 웰컴 멘트            →  speak(..., lang="en")
  4. 🇰🇷 이후 한국어로 대화/명령 수행  →  commands / brain  → speak (자동 한국어)
  5. 조용해지거나 '종료'라고 하면 다시 대기

실행:
  python jarvis.py            # 박수 모드(마이크 있으면) / 텍스트 모드
  python jarvis.py --text     # 강제 텍스트(키보드) 모드
  python jarvis.py --word     # 박수 대신 호출어('자비스') 모드
"""
from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

import commands
import music
from brain import Brain
from voice import Voice

EXIT_WORDS = ["종료", "그만", "잘 자", "꺼져", "exit", "quit", "bye"]

# 깨어날 때 영어 웰컴 멘트 (영화 속 자비스 톤)
WELCOME_EN = os.getenv(
    "JARVIS_WELCOME",
    "Good day, sir. J.A.R.V.I.S. online and at your service.",
)


def _is_exit(text: str) -> bool:
    return any(w in text.lower() for w in EXIT_WORDS)


def _handle_command(command: str, voice: Voice, brain: Brain) -> None:
    """기본 명령 우선 처리, 아니면 LLM 두뇌가 답하고 한국어로 말한다."""
    reply = commands.handle(command)
    if reply is None:
        reply = brain.think(command)
    voice.speak(reply, lang="ko")


def _conversation(voice: Voice, brain: Brain) -> bool:
    """
    깨어난 뒤의 한국어 대화 세션.
    종료 명령이면 True(프로그램 종료)를 반환, 조용해지면 False(다시 대기).
    """
    silent_count = 0
    while True:
        command = voice.listen("🎤 말씀하세요...")
        if not command:
            silent_count += 1
            if silent_count >= 2:
                voice.speak("대기 모드로 돌아가겠습니다.", lang="ko")
                return False
            continue
        silent_count = 0
        if _is_exit(command):
            voice.speak("시스템을 종료합니다. 좋은 하루 되세요.", lang="ko")
            return True
        _handle_command(command, voice, brain)


def main() -> None:
    force_text = "--text" in sys.argv
    wake_mode = "word" if "--word" in sys.argv else os.getenv("JARVIS_WAKE_MODE", "clap").lower()
    wake_word = os.getenv("JARVIS_WAKE_WORD", "자비스")
    lang = os.getenv("JARVIS_LANG", "ko-KR")

    voice = Voice(lang=lang)
    if force_text:
        voice._audio_ready = False
    brain = Brain()

    print("=" * 56)
    print("  J.A.R.V.I.S  —  Just A Rather Very Intelligent System")
    print("=" * 56)
    mode = "음성" if voice.audio_ready else "텍스트(키보드)"
    state = "온라인(Claude)" if brain.online else "오프라인(규칙기반)"
    trigger = "박수 👏" if (wake_mode == "clap" and voice.audio_ready) else f"호출어 '{wake_word}'"
    if not voice.audio_ready:
        trigger = "Enter 키"
    print(f"  입력: {mode}  |  두뇌: {state}  |  깨우기: {trigger}")
    print("=" * 56)

    while True:
        # --- 1) 깨우기 (박수 또는 호출어) ---
        if wake_mode == "clap" or not voice.audio_ready:
            if not voice.wait_for_clap():
                break  # Ctrl+C 등
        else:  # 호출어 모드
            heard = voice.listen(f"🎤 '{wake_word}' 대기 중...")
            if not heard or wake_word.lower() not in heard.lower():
                continue

        # --- 2) 음악 재생 + 3) 영어 웰컴 ---
        music.play_wake_music()
        voice.speak(WELCOME_EN, lang="en")

        # --- 4) 한국어 대화 세션 ---
        should_exit = _conversation(voice, brain)
        if should_exit:
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 자비스를 종료합니다.")
