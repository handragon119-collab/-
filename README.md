# 📸 인스타그램 AI 자동 업로드

주제(topic) 하나만 입력하면 **AI가 캡션 + 해시태그 + 이미지를 만들고 인스타그램에 자동 업로드**합니다.

```
주제 입력  →  Claude 캡션·해시태그  →  AI 이미지 생성  →  인스타그램 업로드
```

## ✨ 특징

- **캡션 생성**: Claude(Anthropic)가 감성적인 한국어 캡션과 해시태그를 작성
- **이미지 생성**: OpenAI(DALL·E 3 / gpt-image-1), Google Gemini 지원. API 키가 없어도 **로컬 placeholder**로 전체 흐름 테스트 가능
- **업로드**: 개인 계정(instagrapi) 또는 비즈니스 계정(공식 Graph API) 선택
- **일괄 처리**: 주제 목록 파일로 여러 게시물 한 번에 생성
- **플러그인 구조**: 제공자/업로드 방식을 환경변수만 바꿔 교체

## 🚀 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
#   .env 를 열어 ANTHROPIC_API_KEY 등을 채웁니다.

# 3. 실행 (업로드 없이 이미지/캡션만 - 안전하게 테스트)
python -m instagram_auto "가을 캠핑 감성" --dry-run

# 4. 실제 업로드 (.env 에서 PUBLISHER 설정 후)
python -m instagram_auto "홈카페 라떼아트"
```

## ⚙️ 설정 (.env)

| 변수 | 설명 | 값 |
|------|------|----|
| `ANTHROPIC_API_KEY` | 캡션 생성용 Claude 키 | 필수 |
| `CAPTION_MODEL` | 캡션 모델 | `claude-sonnet-4-6` |
| `IMAGE_PROVIDER` | 이미지 제공자 | `openai` / `gemini` / `placeholder` |
| `OPENAI_API_KEY` | OpenAI 이미지 키 | openai 사용 시 |
| `GEMINI_API_KEY` | Gemini 키 | gemini 사용 시 |
| `PUBLISHER` | 업로드 방식 | `instagrapi` / `graph` / `none` |
| `IG_USERNAME` / `IG_PASSWORD` | 개인 계정 로그인 | instagrapi 사용 시 |
| `IG_GRAPH_ACCESS_TOKEN` / `IG_GRAPH_USER_ID` | 비즈니스 계정 | graph 사용 시 |

## 📦 사용법

```bash
# 단일 주제
python -m instagram_auto "비 오는 날 카페"

# 톤 지정
python -m instagram_auto "운동 동기부여" --tone "강렬하고 동기부여되는"

# 업로드 없이 생성만
python -m instagram_auto "강아지 일상" --dry-run

# 여러 주제 일괄 처리 (topics.txt: 한 줄에 하나)
python -m instagram_auto --topics-file topics.txt
```

생성 결과는 `output/` 폴더에 이미지(`.jpg`)와 메타데이터(`.json`)로 저장됩니다.

## 🧩 코드에서 직접 사용

```python
from instagram_auto import Pipeline

result = Pipeline().run("가을 캠핑 감성", dry_run=True)
print(result.full_text)   # 캡션 + 해시태그
print(result.image_path)  # 생성된 이미지 경로
```

## 🏗️ 구조

```
instagram_auto/
├── config.py      # 환경변수 설정 로더
├── caption.py     # Claude 캡션·해시태그·이미지 프롬프트 생성
├── image_gen.py   # 이미지 생성 (openai / gemini / placeholder)
├── publisher.py   # 업로드 (instagrapi / graph / none)
├── pipeline.py    # 전체 오케스트레이션
└── cli.py         # 커맨드라인 인터페이스
```

## ⚠️ 주의사항

- **instagrapi**는 인스타그램 비공식 API를 사용합니다. 과도한 자동 업로드는 계정 제한·차단을 유발할 수 있으니 **하루 게시 빈도를 적절히 조절**하고, 가능하면 **공식 Graph API(비즈니스 계정)** 사용을 권장합니다.
- 인스타그램 [자동화 정책](https://help.instagram.com/581066165581870)을 준수하세요.
- API 키와 비밀번호가 담긴 `.env` 파일은 절대 커밋하지 마세요 (`.gitignore`에 포함됨).
