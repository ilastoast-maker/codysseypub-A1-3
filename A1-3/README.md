# Novel Radar

**Novel Radar**는 한국의 편/회차 단위 웹소설 결제 환경에서, 사용자가 국내외 작품을 결제하기 전에 작품의 특징과 품질을 빠르게 파악할 수 있도록 돕는 AI 기반 웹소설 분석 서비스입니다.

해외 작품은 한국어 번역 제목을 몰라도 영어·중국어·일본어 등 **원어 제목 그대로 입력**할 수 있으며, 공개 작품 정보와 독자 리뷰를 검색·분석해 **한국어 결과와 핵심 키워드**로 제공합니다.

서비스의 목표는 두 가지입니다.

1. **소개:** 도입부와 매력 포인트로 좋은 해외 작품을 한국 독자에게 알립니다. 중반 이후 전개는 다루지 않습니다.
2. **사고 방지:** 연재 중단, 슬픈 결말·주인공 사망, 억지 전개·자기복제처럼 끝까지 따라가야만 알 수 있는 위험을 결제 전에 알려줍니다. 결말 관련 항목은 눌러야 보입니다.

## 배포 URL

- Production: https://novel-rader.vercel.app/
- Health Check: https://novel-rader.vercel.app/api/health

## 핵심 기능

- 한국어·영어·중국어·일본어 등 작품명/원제 입력 지원
- 해외 작품도 최종 분석 결과는 한국어로 제공
- 요약 키워드: 메인 장르, 원작 완결/연재중, 국내 정식 연재 플랫폼, 로맨스·주인공·묘사 수위의 대표 호불호 요소 1개씩
- 정보 바: 원작 분량, 번역본 진행 상황, 초반 진입 구간 독자 평
- 도입부와 초반 전개, 매력 포인트, 비슷한 작품
- 호불호 요소 체크리스트(펼치기): 관계·로맨스 / 주인공 / 전개·결말 / 묘사 수위 / 혐오 표현
  - 상태는 `언급됨` / `언급없음`(없다는 단정이 아님) / `확인불가` 3단계
  - 새드엔딩·열린 결말·주인공 사망·주요 인물 사망·남주 교체는 🔒 눌러야 결과 공개
  - 혐오 표현은 인종/국가 여부만 표시하고 대상은 명시하지 않음
- 근거가 부족한 정보는 추측하지 않고 `확인불가`로 처리

입력 예시:

```text
诡秘之主
Lord of the Mysteries
```

두 예시는 동일한 작품을 원제와 영문명으로 입력하는 예입니다.

## 페이지 / 섹션 구성

1. **홈 (`#home`)**
   - 서비스의 목적과 핵심 가치 안내
2. **소개 (`#about`)**
   - 원제 그대로 검색, 태그 요약, 한국어 분석의 장점 설명
3. **분석하기 (`#analyze`)**
   - 작품명을 입력하고 AI 분석 결과 확인

상단 네비게이션의 `홈 / 소개 / 분석하기` 메뉴로 각 섹션으로 이동할 수 있습니다.

## 기술 스택

### Frontend
- HTML5
- Tailwind CSS (CDN)
- Vanilla JavaScript

### Backend
- Python 3.12
- FastAPI
- Pydantic

### AI / Search
- Google Gemini API (`google-genai`)
- Google Search Grounding
- 검색·조사 모델: `gemini-3.5-flash-lite` (Google Search grounding)
- JSON 정리 모델: NVIDIA API `meta/llama-3.3-70b-instruct` (키가 없거나 실패하면 Gemini로 대체)

### Deployment / Collaboration
- Vercel
- GitHub

## 핵심 구조

```text
사용자 작품명
  → POST /api/analyze
  → 1차 Gemini + Google Search Grounding
       · 모델: gemini-3.5-flash-lite
       · 작품 식별
       · 공식/서지 정보
       · 독자 리뷰
       · 연재 상태·분량·국내 정식 번역본
       · 초반 진입장벽, 호불호 요소 26개 항목 조사
       · grounding sources 확보 (내부 검증용, 응답에는 미포함)
  → 출처가 없으면 재검색 → 그래도 없으면 422 근거 부족
  → 2차 구조화 분석 (Gemini 호출 절약)
       · NVIDIA API(OpenAI 호환) + JSON Schema 프롬프트 → Pydantic 검증, 실패 시 1회 재요청
       · nvidia_key가 없거나 NVIDIA가 실패하면 Gemini structured output으로 대체
       · JSON 생성 오류 시 1회 자동 재시도
  → 서버가 체크리스트를 전체 카탈로그로 확장 (누락 항목은 확인불가)
  → 프론트에서 요약 키워드 + 초반 소개 + 체크리스트 표시
```

Google Search 단계와 JSON 단계는 분리되어 있습니다. 검색 도구 사용과 구조화 출력이 서로 간섭하는 문제를 줄이기 위함입니다. 출처 목록과 검색어는 화면에 표시하지 않고, Google Search 그라운딩 이용 시 표시가 요구되는 검색 칩만 결과 하단에 둡니다.

## 프로젝트 구조

```text
codysseypub-A1-3/
└── A1-3/
    ├── index.html              # 프론트엔드 HTML/CSS/JS
    ├── app.py                  # Vercel/FastAPI 진입점 + 프론트 제공
    ├── api/
    │   └── index.py            # AI 분석 API
    ├── tests/
    │   ├── test_api.py
    │   └── test_frontend.js
    ├── requirements.txt
    ├── pyproject.toml
    ├── pytest.ini
    ├── vercel.json
    ├── README.md
    ├── SERVICE_PLAN.md
    ├── check_list.md
    └── TEST_REPORT.md
```

프론트엔드는 소규모 단일 페이지 서비스이므로 별도의 `css/`, `js/` 폴더 대신 `index.html` 내부에 스타일과 JavaScript를 함께 구성했습니다. 백엔드는 `api/`로 분리되어 있습니다.

## 환경 변수

Vercel Project Settings → Environment Variables에 다음 값을 설정합니다.

```text
GEMINI_API_KEY=실제 Gemini API 키
nvidia_key=NVIDIA API 키 (선택, NVIDIA_API_KEY도 인식)
```

선택적으로 모델을 변경할 수 있습니다.

```text
GEMINI_MODEL=gemini-3.5-flash-lite
NVIDIA_MODEL=meta/llama-3.3-70b-instruct
NVIDIA_BUDGET_SECONDS=30
```

`/api/health`의 `synthesis` 값으로 2단계가 NVIDIA와 Gemini 중 무엇을 쓰는지 확인할 수 있습니다.

API 키는 HTML이나 GitHub 저장소에 직접 저장하지 않습니다.

## 저장소 받기

```bash
git clone https://github.com/ilastoast-maker/codysseypub-A1-3.git
cd codysseypub-A1-3/A1-3
```

## 로컬 실행

의존성을 설치합니다.

```bash
pip install -r requirements.txt
```

Vercel 개발 환경으로 실행하려면:

```bash
npm i -g vercel
vercel dev
```

브라우저에서 보통 아래 주소를 엽니다.

```text
http://localhost:3000
```

API 상태 확인:

```bash
curl http://localhost:3000/api/health
```

분석 호출 예시:

```bash
curl -X POST http://localhost:3000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"title":"Lord of the Mysteries"}'
```

## Vercel 배포 방법

1. GitHub 저장소 `ilastoast-maker/codysseypub-A1-3`를 Vercel에 Import합니다.
2. Root Directory를 `A1-3`로 지정합니다.
3. Environment Variables에 `GEMINI_API_KEY`와 `nvidia_key`를 등록합니다.
4. `main` 브랜치를 Production 배포와 연결합니다.
5. 배포 후 `/`, `/api/health`, 실제 작품 분석을 순서대로 확인합니다.

현재 Production URL:

```text
https://novel-rader.vercel.app/
```

## AI 기능의 입력 / 출력 / 실패 처리

### 입력
- 웹소설 제목 또는 원제
- 최대 200자
- 빈 문자열은 허용하지 않음

### 출력
- 식별된 작품명 / 원제 / 작가 / 원작 국가·언어 정보
- 작품 식별 신뢰도
- 메인 장르 태그, 원작 연재 상태·분량, 국내 정식 연재 플랫폼
- 초반 진입 구간 독자 평
- 도입부와 초반 전개, 매력 포인트, 비슷한 작품
- 호불호 요소 체크리스트 (스포일러 항목 잠금)

### 실패 처리
- 빈 입력 → 프론트에서 필수값 안내
- 검색 근거 확보 실패 → HTTP 422
- API 키/패키지 문제 → HTTP 500
- Gemini 무료 사용량 한도 초과 → HTTP 429 + 사용자용 안내 메시지
- AI API 또는 구조화 분석 실패 → HTTP 502
- AI JSON이 불완전하게 생성된 경우 → 구조화 분석 1회 자동 재시도
- 브라우저 요청이 58초를 초과하면 → 타임아웃 안내

## 반응형

Tailwind의 반응형 클래스를 사용합니다.

- 입력 폼: 모바일 `flex-col` → `sm:flex-row`
- 소개 카드: 모바일 1열 → `md:grid-cols-3`
- 분석 결과 카드: 모바일 1열 → 데스크톱 2열
- `viewport` 메타 태그 적용

데스크톱과 실제 휴대폰 화면에서 배포 서비스 동작을 확인했습니다.

## 테스트

```bash
python -m pytest -q
node tests/test_frontend.js
```

테스트는 실제 Gemini 과금을 발생시키지 않고 입력 검증, Search Grounding metadata 처리, 체크리스트 카탈로그 확장, 스포일러 잠금, 출처 비노출, 필드 정규화, HTTP 상태 코드 및 프론트 오류 처리를 검증합니다.

## 설계상 안전장치

- Google Search의 `grounding_chunks`가 없으면 분석을 성공으로 반환하지 않습니다.
- 체크리스트 key는 카탈로그에 정의된 값만 허용하고, 모델이 빠뜨린 항목은 `확인불가`로 채웁니다. AI가 근거 없이 "없음"을 단정하지 못하게 하기 위함입니다.
- 스토리 소개는 초반 전개까지만 작성하도록 프롬프트에서 강제합니다.
- 동명 작품/근거 충돌 시 `confidence`를 낮춥니다.
- 구조화 JSON이 불완전한 경우 자동으로 한 번 더 생성합니다.
- 무료 사용량이 소진된 경우 긴 SDK 내부 오류 대신 사용자용 429 안내를 표시합니다.
- 프론트는 필수 JSON 필드를 검증하고 타임아웃을 처리합니다.

## 제출 문서

- 기능 요구 사항 체크: `check_list.md`
- 서비스 기획서: `SERVICE_PLAN.md`
- 테스트 기록: `TEST_REPORT.md`

제출 시 별도로 데스크톱/모바일/AI 기능 동작 화면 스크린샷과 AI 코딩 도구 사용 과정 증빙을 첨부합니다. AI 기능 동작 결과 스크린샷은 무료 API 할당량이 사용 가능한 시점에 추가할 수 있습니다.
