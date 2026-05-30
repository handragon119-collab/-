"""
voice.py - 자비스의 귀(STT)와 입(TTS).

- 듣기: SpeechRecognition + 구글 음성인식(무료, 인터넷 필요)
- 말하기: pyttsx3 (오프라인)

마이크/스피커나 라이브러리가 없는 환경(서버, CI 등)에서는
자동으로 '텍스트 모드'로 떨어져서 키보드로 입력하고 화면에 출력합니다.
"""
from __future__ import annotations


class Voice:
    def __init__(self, lang: str = "ko-KR"):
        self.lang = lang
        self._recognizer = None
        self._mic = None
        self._tts = None
        self._audio_ready = False
        self._setup_audio()

    def _setup_audio(self) -> None:
        """마이크와 TTS 엔진을 준비한다. 실패하면 텍스트 모드로 동작."""
        try:
            import speech_recognition as sr  # type: ignore

            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()
            # 주변 소음에 한 번 적응시켜 인식률을 높인다.
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._audio_ready = True
        except Exception as exc:  # 마이크 없음 / PyAudio 미설치 등
            print(f"[voice] 마이크를 사용할 수 없어 텍스트 모드로 전환합니다. ({exc})")
            self._audio_ready = False

        try:
            import pyttsx3  # type: ignore

            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", 175)   # 말하는 속도
            self._tts.setProperty("volume", 1.0)  # 음량
            self._pick_korean_voice()
        except Exception as exc:
            print(f"[voice] TTS 엔진을 사용할 수 없어 화면 출력만 합니다. ({exc})")
            self._tts = None

    def _pick_korean_voice(self) -> None:
        """설치된 음성 중 한국어 보이스가 있으면 골라준다."""
        if not self._tts or not self.lang.startswith("ko"):
            return
        try:
            for v in self._tts.getProperty("voices"):
                meta = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                if "korea" in meta or "ko-" in meta or "yuna" in meta or "heami" in meta:
                    self._tts.setProperty("voice", v.id)
                    return
        except Exception:
            pass

    @property
    def audio_ready(self) -> bool:
        return self._audio_ready

    def speak(self, text: str) -> None:
        """text를 소리내어 말한다. (TTS 없으면 화면에만 출력)"""
        print(f"🤖 자비스: {text}")
        if self._tts:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception:
                pass

    def listen(self, prompt: str = "🎤 듣는 중...") -> str:
        """
        음성을 받아 텍스트로 돌려준다.
        오디오를 쓸 수 없으면 키보드 입력을 받는다.
        """
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
            return ""  # 알아듣지 못함
        except Exception as exc:
            print(f"[voice] 인식 오류: {exc}")
            return ""
