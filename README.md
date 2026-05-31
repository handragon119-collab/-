# 📸 인스타그램 AI 자동 업로드 (카드뉴스)

주제(topic) 하나만 입력하면 **AI가 카드뉴스 내용을 기획 → 여러 장 슬라이드로 자동 디자인 → 인스타그램 캐러셀로 자동 업로드**합니다.

```
주제 입력  →  AI 카드뉴스 기획  →  카드 디자인 렌더링  →  캐러셀 자동 업로드
```

## ✨ 특징

- **두 가지 모드**
  - `cardnews` (기본): 정보형 **카드뉴스 캐러셀**. 표지 + 본문 N장 + 마무리(CTA)
  - `photo`: 단일 **AI 사진** 게시물
- **카드 디자인**: 글자를 직접 렌더링하므로 **한글이 깨지지 않고** 디자인이 일관됨. 4가지 테마(navy/mint/coral/cream), 페이지 번호·브랜드 핸들·CTA 버튼 자동
- **내용 생성**: Claude 또는 **Gemini(무료 등급)** 가 후킹 표지·본문·캡션·해시태그 작성
- **업로드**: **비즈니스 Graph API**(캐러셀 지원). 카드를 **imgbb**에 자동 호스팅 후 게시
- **카드뉴스는 이미지 생성 API 비용이 0원** (카드는 코드로 그림). 캡션만 무료 Gemini로 하면 **완전 무료**
- **일괄 처리** + **플러그인 구조**(제공자/업로드/테마를 환경변수로 교체)

## 💸 무료로 쓰기 ($0 구성)

돈이 드는 건 캡션(LLM)과 이미지 생성뿐이고, 둘 다 무료 대체가 가능합니다.

| 단계 | 무료 서비스 | 비고 |
|------|------------|------|
| 캡션 생성 | **Gemini 2.5 Flash 무료 등급** | Google AI Studio 무료 키. 분당/일일 한도 있음 |
| 이미지 생성 | **Pollinations.ai** | 무료. `auth.pollinations.ai`에서 무료 토큰 받으면 안정적(워터마크 제거) |
| 이미지 호스팅 | imgbb | 무료 |
| 업로드 | Graph API | 무료 |

`.env`에서 무료 구성 `[A]` 블록의 주석을 해제하면 됩니다.

```bash
CAPTION_PROVIDER=gemini
IMAGE_PROVIDER=pollinations
POLLINATIONS_TOKEN=     # auth.pollinations.ai 에서 무료 발급 (권장)
```

> ⚠️ 무료 등급은 **속도·일일 한도 제한**이 있고, Pollinations는 익명 호출 시 403이 날 수 있어 **무료 토큰 발급을 권장**합니다. 완전히 안정적인 무제한 무료 이미지 API는 없으므로, 대량 운영 시엔 로컬 Stable Diffusion 또는 유료 API가 더 적합합니다.

## 🤖 다중 에이전트 고급 엔진 (`--agentic`)

품질을 높이기 위해 생성을 7개 역할로 분리한 파이프라인을 제공합니다.

| 에이전트 | 역할 |
|----------|------|
| 리서치 | 상위 노출 글 패턴 분석 + 차별화 포인트 (웹 검색 가능 시) |
| 전략 | 저장·조회 극대화 콘텐츠 구조 설계 |
| 팩트검증 | 공신력 기관 출처만 인정, 변동 수치는 '기관 확인' 표시 |
| 카피 | 인스타 말투 + 구텐베르크(블록) 형식 본문 |
| SEO 편집 | 제목·해시태그·캡션 검색 최적화 |
| 리스크 | 민감 주제·저품질·노출저하 요인 감지 및 수정 |
| 디자인/트렌드 | 최신 말투·밈·디자인 트렌드 반영 |

```bash
python -m instagram_auto "ISA 절세 활용법" --agentic --theme luxe
# 또는 .env 에서  CONTENT_ENGINE=agentic
```

> 리서치·팩트검증·트렌드 에이전트의 **실시간 웹 검색**은 검색 가능한 LLM(Anthropic `web_search` / Gemini `google_search`)이 연결돼 있을 때 자동 수행됩니다. 없으면 모델 내장 지식으로 동작하고, 생성 결과의 `agent_report`에 '웹검색 미사용'으로 표시됩니다. 주 2~3회 자동 업데이트하려면 스케줄러(예: cron)로 이 명령을 반복 실행하세요.

### 금융 시리즈 예시 생성

```bash
python scripts/make_finance_series.py
# → 금융 10편(번호 01~10, luxe 명조 테마) 카드 + 표지 몽타주 + 카피 인덱스 PDF
```

## 🖥️ 웹 UI (자동발행 스튜디오)

브라우저에서 주제 입력 → 카드 미리보기 → 캡션 편집 → **버튼 한 번으로 발행**.

```bash
pip install -r requirements.txt
python -m web.server          # http://localhost:8000 접속
```

- **콘텐츠 생성·발행 탭**: 주제/형식/테마/카드수 입력 → 생성 → 미리보기 → [지금 발행]
- **계정 연결·설정 탭**: 인스타 비즈니스 계정(Graph API 토큰·ID) + Gemini/imgbb 키 입력 → [연결 테스트] → 상단에 `@계정 연결됨` 표시
- 자격증명은 로컬 `web_settings.json`에 저장됩니다(.gitignore 처리).

> ⚠️ **로컬 전용입니다.** API 키·토큰을 다루므로 인증 없이 공개 인터넷(외부 도메인)에 그대로 띄우지 마세요. 외부 배포 시 로그인/HTTPS를 반드시 추가하세요.

## 🚀 빠른 시작 (CLI)

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
# 카드뉴스 (기본 모드)
python -m instagram_auto "직장인 점심 스트레칭 5가지"

# 본문 카드 수·테마 지정
python -m instagram_auto "돈 모으는 습관 7가지" --cards 7 --theme cream

# 업로드 없이 카드만 생성해서 미리보기
python -m instagram_auto "초보 등산 꿀팁" --dry-run

# 단일 AI 사진 모드
python -m instagram_auto "가을 캠핑 감성" --mode photo

# 여러 주제 일괄 처리 (topics.txt: 한 줄에 하나)
python -m instagram_auto --topics-file topics.txt
```

옵션: `--mode {cardnews,photo}`, `--theme {navy,mint,coral,cream}`, `--cards N`, `--tone "..."`, `--dry-run`

생성 결과는 `output/` 폴더에 카드 이미지들(`*_01_cover.jpg`, `*_NN_card.jpg`, ...)과 메타데이터(`.json`)로 저장됩니다.

> 💡 **카드뉴스 모드는 한글 폰트(나눔고딕)를 처음 실행 시 자동 다운로드**해 `~/.cache/instagram_auto/fonts`에 캐싱합니다. 인터넷이 안 되는 환경이면 `FONT_DIR`에 폰트 폴더를 직접 지정하세요.

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
├── llm.py         # LLM 호출 공통 (anthropic / gemini)
├── content.py     # 카드뉴스 내용 생성 (표지·본문·마무리·캡션)
├── card_render.py # 카드 슬라이드 디자인 렌더링 (PIL, 4가지 테마)
├── fonts.py       # 한글 폰트 자동 다운로드·로드
├── caption.py     # 단일 사진 모드용 캡션 생성
├── image_gen.py   # 이미지 생성 (pollinations / gemini / openai / placeholder)
├── image_host.py  # 공개 URL 호스팅 (imgbb / cloudinary / base_url)
├── publisher.py   # 업로드 (graph / instagrapi / none, 캐러셀 지원)
├── pipeline.py    # 전체 오케스트레이션
└── cli.py         # 커맨드라인 인터페이스
```

## ⚠️ 주의사항

- 공식 Graph API는 하루 게시 횟수에 **계정당 25회/24시간** 제한이 있습니다.
- 게시되는 이미지는 imgbb의 공개 URL을 거칩니다. 민감한 이미지는 비공개 호스팅(Cloudinary/S3)을 고려하세요.
- 인스타그램 [콘텐츠 게시 정책](https://developers.facebook.com/docs/instagram-platform/content-publishing)을 준수하세요.
- Gemini 생성 이미지에는 **SynthID 워터마크**가 포함됩니다.
- API 키·토큰이 담긴 `.env` 파일은 절대 커밋하지 마세요 (`.gitignore`에 포함됨).
