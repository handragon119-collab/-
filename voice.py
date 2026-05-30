"""
voice.py - 자비스의 귀(STT)와 입(TTS), 그리고 박수 감지.

- 듣기   : SpeechRecognition + 구글 음성인식(무료, 인터넷 필요)
- 말하기 : pyttsx3 (오프라인)
           · 영어 문장 → 영국식 남성 음성(영화 속 자비스에 가깝게)
           · 한국어 문장 → 한국어 음성  (언어를 자동 감지해 전환)
- 박수   : 마이크 입력의 음량 스파이크를 감지해 자비스를 깨운다.

마이크/라이브러리가 없는 환경에서는 자동으로 '텍스트 모드'로 동작한다.
"""
from __future__ import annotations

import array
import math
import os
import time


def _has_hangul(text: str) -> bool:
    """문자열에 한글이 들어있으면 True (한국어 판별용)."""
    for ch in text:
        if "가" <= ch <= "힣" or "㄰" <= ch <= "㆏":
            return True
    return False


def _rms(frame: bytes) -> float:
    """16bit PCM 청크의 RMS(평균 음량) 계산. audioop 없이 순수 파이썬."""
    samples = array.array("h")
    samples.frombytes(frame)
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class Voice:
    def __init__(self, lang: str = "ko-KR"):
        self.lang = lang
        self._recognizer = None
        self._mic = None
        self._tts = None
        self._audio_ready = False
        self._ko_voice = None   # 한국어 음성 id
        self._en_voice = None   # 영어(영국식) 음성 id
        self._setup_audio()

    # ------------------------------------------------------------------ setup
    def _setup_audio(self) -> None:
        try:
            import speech_recognition as sr  # type: ignore

            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._audio_ready = True
        except Exception as exc:
            print(f"[voice] 마이크를 사용할 수 없어 텍스트 모드로 전환합니다. ({exc})")
            self._audio_ready = False

        try:
            import pyttsx3  # type: ignore

            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", 172)
            self._tts.setProperty("volume", 1.0)
            self._select_voices()
        except Exception as exc:
            print(f"[voice] TTS 엔진을 사용할 수 없어 화면 출력만 합니다. ({exc})")
            self._tts = None

    def _select_voices(self) -> None:
        """설치된 음성들 중 자비스용(영국 남성)과 한국어 음성을 골라 둔다."""
        if not self._tts:
            return
        # 사용자가 .env로 직접 지정한 음성 id가 있으면 우선
        self._en_voice = os.getenv("JARVIS_VOICE_EN") or None
        self._ko_voice = os.getenv("JARVIS_VOICE_KO") or None
        try:
            voices = self._tts.getProperty("voices")
        except Exception:
            return

        for v in voices:
            meta = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
            langs = " ".join(
                b.decode(errors="ignore") if isinstance(b, bytes) else str(b)
                for b in (getattr(v, "languages", []) or [])
            ).lower()
            blob = f"{meta} {langs}"

            # 한국어 음성
            if self._ko_voice is None and (
                "korea" in blob or "ko_kr" in blob or "ko-kr" in blob
                or "yuna" in blob or "heami" in blob
            ):
                self._ko_voice = v.id

            # 영국식 남성 음성 (영화 자비스 = 영국 집사 톤)
            if self._en_voice is None and (
                "en_gb" in blob or "en-gb" in blob or "british" in blob
                or any(n in blob for n in ["daniel", "george", "oliver", "arthur", "rishi"])
            ):
                self._en_voice = v.id

        # 영국식이 없으면 아무 영어 남성 음성이라도
        if self._en_voice is None:
            for v in voices:
                blob = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                if "english" in blob or "en_us" in blob or "en-us" in blob:
                    self._en_voice = v.id
                    break

    @property
    def audio_ready(self) -> bool:
        return self._audio_ready

    # ------------------------------------------------------------------ speak
    def speak(self, text: str, lang: str | None = None) -> None:
        """
        text를 말한다. lang이 'en'/'ko'면 그 음성으로, 없으면 한글 여부로 자동 판별.
        """
        print(f"🤖 자비스: {text}")
        if not self._tts:
            return
        is_korean = (lang == "ko") or (lang is None and _has_hangul(text))
        voice_id = self._ko_voice if is_korean else self._en_voice
        try:
            if voice_id:
                self._tts.setProperty("voice", voice_id)
            self._tts.say(text)
            self._tts.runAndWait()
        except Exception:
            pass

    # ----------------------------------------------------------------- listen
    def listen(self, prompt: str = "🎤 듣는 중...") -> str:
        if not self._audio_ready:
            try:
                return input("⌨️  입력> ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""

        import speech_recognition as sr  # type: ignore

        print(prompt)
        try:
            with self._mic as source:
                audio = self._recognizer.listen(source, timeout=6, phrase_time_limit=10)
            text = self._recognizer.recognize_google(audio, language=self.lang)
            print(f"🗣️  당신: {text}")
            return text.strip()
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as exc:
            print(f"[voice] 인식 오류: {exc}")
            return ""

    # -------------------------------------------------------------- clap wake
    def wait_for_clap(self) -> bool:
        """
        박수(짧고 큰 소리)를 감지할 때까지 기다린다. 감지하면 True.
        텍스트 모드에서는 Enter 키로 대신 깨운다.
        """
        if not self._audio_ready:
            try:
                input("👏 (박수 대신) Enter를 누르면 자비스가 깨어납니다 > ")
                return True
            except (EOFError, KeyboardInterrupt):
                return False

        try:
            import pyaudio  # type: ignore
        except Exception:
            # 마이크 스트림을 못 열면 그냥 호출어 듣기로 대체
            return bool(self.listen("👏 박수 대기(또는 '자비스'라고 부르기)..."))

        CHUNK, RATE = 1024, 16000
        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                         input=True, frames_per_buffer=CHUNK)
        try:
            # 주변 소음 기준선 측정 (약 0.4초)
            ambient = 1.0
            for _ in range(6):
                ambient = max(ambient, _rms(stream.read(CHUNK, exception_on_overflow=False)))
            # 박수 임계값: 소음 대비 충분히 크고, 절대값도 어느 정도 이상
            threshold = max(ambient * 6.0, 3000.0)

            print("👏 박수를 치면 자비스가 깨어납니다... (Ctrl+C로 종료)")
            quiet_seen = True
            while True:
                level = _rms(stream.read(CHUNK, exception_on_overflow=False))
                if level < threshold * 0.4:
                    quiet_seen = True  # 박수 전 조용한 구간 확인
                elif level > threshold and quiet_seen:
                    time.sleep(0.05)   # 디바운스
                    return True
        except KeyboardInterrupt:
            return False
        finally:
            try:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            except Exception:
                pass
