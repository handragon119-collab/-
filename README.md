# 🤖 J.A.R.V.I.S — 아이언맨 스타일 AI 음성 비서

아이언맨의 자비스처럼 **"자비스"라고 부르면 깨어나서 음성으로 대화하고 명령을 수행**하는 파이썬 비서입니다.

영화 속 자비스의 핵심 = **귀(음성인식) + 두뇌(AI) + 입(음성합성)**. 이 프로젝트도 똑같은 3단 구조입니다.

```
  당신의 목소리
      │  🎤 듣기 (SpeechRecognition)        ← voice.py
      ▼
  "자비스, 지금 몇 시야?"
      │  🧠 생각 (기본 명령 → 안되면 Claude AI)  ← commands.py / brain.py
      ▼
  "지금은 5시 30분입니다."
      │  🔊 말하기 (pyttsx3)                ← voice.py
      ▼
  스피커로 음성 출력
```

---

## ✨ 할 수 있는 것

- **호출어로 깨우기**: "자비스" 라고 부르면 응답
- **자연스러운 대화**: Claude AI 두뇌로 어떤 질문이든 대화 (집사 말투)
- **빠른 명령어**: 시간/날짜, 유튜브·구글 검색, 사이트 열기 등은 즉시 처리
- **한국어 음성** 입출력 (영어로도 전환 가능)
- **안전장치**: 마이크나 API 키가 없어도 **텍스트 모드 / 오프라인 모드**로 그냥 실행됨

---

## 🚀 빠른 시작

### 1. 설치
```bash
# (권장) 가상환경
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> **PyAudio 설치 오류가 나면** (마이크 라이브러리):
> - macOS: `brew install portaudio && pip install pyaudio`
> - Ubuntu/Debian: `sudo apt install portaudio19-dev python3-pyaudio`
> - Windows: `pip install pipwin && pipwin install pyaudio`
>
> 그래도 안 되면 무시해도 됩니다 — 자동으로 키보드(텍스트) 모드로 실행됩니다.

### 2. 설정
```bash
cp .env.example .env
```
`.env` 파일을 열어 `ANTHROPIC_API_KEY` 를 넣으세요.
([console.anthropic.com](https://console.anthropic.com) 에서 발급)
키가 없어도 기본 명령어는 동작합니다.

### 3. 실행
```bash
python jarvis.py            # 마이크 있으면 음성 모드, 없으면 텍스트 모드
python jarvis.py --text     # 강제 텍스트(키보드) 모드
```

음성 모드에서는 **"자비스"** 라고 부른 뒤 명령하세요.
예) *"자비스, 오늘 며칠이야?"*, *"자비스, 유튜브에서 아이언맨 검색해줘"*

종료하려면 **"종료"** 또는 Ctrl+C.

---

## 🗂 파일 구조

| 파일 | 역할 |
|------|------|
| `jarvis.py` | 메인 루프 (호출어 대기 → 듣기 → 처리 → 말하기) |
| `voice.py` | 귀와 입 (음성인식 STT / 음성합성 TTS) |
| `brain.py` | 두뇌 (Claude API 대화, 키 없으면 오프라인 응답) |
| `commands.py` | 손발 (시간·검색·앱 열기 등 빠른 명령어) |
| `requirements.txt` | 필요한 라이브러리 |
| `.env.example` | 설정 템플릿 |

---

## 🛠 커스터마이징

- **호출어 바꾸기**: `.env` 의 `JARVIS_WAKE_WORD=프라이데이`
- **영어로 쓰기**: `.env` 의 `JARVIS_LANG=en-US`
- **성격 바꾸기**: `brain.py` 의 `SYSTEM_PROMPT` 수정
- **명령어 추가**: `commands.py` 의 `handle()` 에 `if ...: return "..."` 추가
  (예: 음악 재생, 날씨, 스마트홈 제어, 메모 저장 등)

---

## 💡 더 발전시키는 아이디어

1. **오프라인 음성인식**: 인터넷 없이 쓰려면 [Vosk](https://alphacephei.com/vosk/) 나 OpenAI Whisper 로 교체
2. **더 자연스러운 목소리**: pyttsx3 대신 [ElevenLabs](https://elevenlabs.io) / Google Cloud TTS 같은 고품질 TTS
3. **항상 켜진 호출어 감지**: [openWakeWord](https://github.com/dscripka/openWakeWord) 로 "자비스"를 정확하게 감지
4. **실제 행동(도구 사용)**: Claude의 tool use 로 캘린더 등록, 이메일 발송, 파일 검색 등 실제 작업 연결
5. **얼굴(UI)**: 영화처럼 홀로그램 느낌의 화면을 PyQt / 웹으로 추가

---

## 📚 참고한 자료 (유튜브/블로그 튜토리얼)

이 구조는 공개된 "파이썬으로 자비스 만들기" 튜토리얼들의 공통 패턴(STT + TTS + LLM)을 따랐고, 두뇌를 Claude API로 구성했습니다.

- [freeCodeCamp — How to Build Tony Stark's JARVIS with Python](https://www.freecodecamp.org/news/python-project-how-to-build-your-own-jarvis-using-python/)
- [Medium — Build a Real-Time Voice Assistant in Python (Step-by-Step)](https://medium.com/@dr.shalinigambhir/meet-your-own-jarvis-build-a-real-time-voice-assistant-in-python-step-by-step-d80118878f72)
- [Medium — Integrating Speech Recognition, TTS, and LLMs](https://charanhu.medium.com/building-a-real-time-voice-assistant-integrating-speech-recognition-text-to-speech-and-llms-db6d33914994)
- [GitHub — kunxxl/JARVIS (음성 비서 예제)](https://github.com/kunxxl/JARVIS)
- [Great Learning — Jarvis Desktop Assistant Python Project](https://www.mygreatlearning.com/blog/jarvis-desktop-assistant-python-project/)

> 💬 유튜브에서 더 보고 싶으면 검색어 추천: **"Python JARVIS voice assistant tutorial"**, **"파이썬 음성비서 만들기"**, **"build AI assistant python speech recognition"**
