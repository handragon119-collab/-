# 📸 인스타그램 AI 자동 업로드

주제(topic) 하나만 입력하면 **AI가 캡션 + 해시태그 + 이미지를 만들고 인스타그램에 자동 업로드**합니다.

```
주제 입력  →  Claude 캡션·해시태그  →  AI 이미지 생성  →  인스타그램 업로드
```

## ✨ 특징

- **캡션 생성**: Claude(Anthropic)가 감성적인 한국어 캡션과 해시태그를 작성
- **이미지 생성**: **Gemini 2.5 Flash Image(Nano Banana)** 기본 사용, 1:1 정사각형 자동. (OpenAI / 오프라인 placeholder도 지원)
- **업로드**: **비즈니스 계정 공식 Graph API** 기본. 생성한 이미지를 **imgbb**에 자동 호스팅해 공개 URL을 만든 뒤 게시
- **일괄 처리**: 주제 목록 파일로 여러 게시물 한 번에 생성
- **플러그인 구조**: 제공자/업로드/호스팅 방식을 환경변수만 바꿔 교체

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

## ⚙️ 설정 (.env) — 기본: Gemini + 비즈니스(Graph) + imgbb

| 변수 | 설명 | 값 |
|------|------|----|
| `ANTHROPIC_API_KEY` | 캡션 생성용 Claude 키 | 필수 |
| `CAPTION_MODEL` | 캡션 모델 | `claude-sonnet-4-6` |
| `IMAGE_PROVIDER` | 이미지 제공자 | `gemini` |
| `GEMINI_API_KEY` | Gemini 키 | 필수 |
| `GEMINI_IMAGE_MODEL` | 이미지 모델 | `gemini-2.5-flash-image` |
| `IMAGE_ASPECT_RATIO` | 이미지 비율 | `1:1`(피드) / `4:5` / `9:16` |
| `PUBLISHER` | 업로드 방식 | `graph` |
| `IG_GRAPH_ACCESS_TOKEN` | Graph API 액세스 토큰 | 필수 |
| `IG_GRAPH_USER_ID` | 인스타그램 비즈니스 계정 ID | 필수 |
| `IMAGE_HOST` | 공개 URL 호스팅 | `imgbb` |
| `IMGBB_API_KEY` | imgbb 키 (무료) | 필수 |

### 🔑 비즈니스(Graph API) 준비물

공식 Graph API로 게시하려면 아래가 필요합니다:

1. **인스타그램 비즈니스/크리에이터 계정** (개인 계정이면 앱에서 전환)
2. 그 계정과 연결된 **Facebook 페이지**
3. **Meta(Facebook) 개발자 앱** 생성 → `instagram_basic`, `instagram_content_publish`, `pages_read_engagement` 권한
4. **장기 액세스 토큰**(`IG_GRAPH_ACCESS_TOKEN`)과 **인스타그램 비즈니스 계정 ID**(`IG_GRAPH_USER_ID`)
5. **imgbb API 키** — https://api.imgbb.com/ 에서 무료 발급 (`IMGBB_API_KEY`)

> 토큰은 60일 후 만료됩니다. 장기 운영 시 토큰 자동 갱신 로직을 추가하는 것을 권장합니다(원하면 추가해 드립니다).

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
├── image_gen.py   # 이미지 생성 (gemini / openai / placeholder)
├── image_host.py  # 공개 URL 호스팅 (imgbb / cloudinary / base_url)
├── publisher.py   # 업로드 (graph / instagrapi / none)
├── pipeline.py    # 전체 오케스트레이션
└── cli.py         # 커맨드라인 인터페이스
```

## ⚠️ 주의사항

- 공식 Graph API는 하루 게시 횟수에 **계정당 25회/24시간** 제한이 있습니다.
- 게시되는 이미지는 imgbb의 공개 URL을 거칩니다. 민감한 이미지는 비공개 호스팅(Cloudinary/S3)을 고려하세요.
- 인스타그램 [콘텐츠 게시 정책](https://developers.facebook.com/docs/instagram-platform/content-publishing)을 준수하세요.
- Gemini 생성 이미지에는 **SynthID 워터마크**가 포함됩니다.
- API 키·토큰이 담긴 `.env` 파일은 절대 커밋하지 마세요 (`.gitignore`에 포함됨).
