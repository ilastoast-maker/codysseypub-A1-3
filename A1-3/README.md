# Novel Radar

**Novel Radar**는 한국의 편/회차 단위 웹소설 결제 환경에서, 사용자가 국내외 작품을 결제하기 전에 작품의 특징과 품질을 빠르게 파악할 수 있도록 돕는 AI 기반 웹소설 분석 서비스입니다.

해외 작품은 한국어 번역 제목을 몰라도 영어·중국어·일본어 등 **원어 제목 그대로 입력**할 수 있으며, 공개 작품 정보와 독자 리뷰를 검색·분석해 **한국어 결과와 핵심 태그**로 제공합니다. 장르/분위기뿐 아니라 공개 근거가 존재하는 경우 한국어 번역·현지화 품질도 함께 평가합니다.

## 배포 URL

- Production: https://novel-rader.vercel.app/
- Health Check: https://novel-rader.vercel.app/api/health

## 핵심 기능

- 한국어·영어·중국어·일본어 등 작품명/원제 입력 지원
- 해외 작품도 최종 분석 결과는 한국어로 제공
- 장르/분위기/전개/번역 특성을 태그로 요약
- 스토리 전개, 매력 포인트, 주의/지뢰 요소 정리
- 공개 자료를 기반으로 번역/현지화 품질 평가
- Google Search Grounding을 이용한 검색 근거/출처 제공
- 근거가 부족한 정보는 추측하지 않고 `#확인불가` 또는 오류로 처리

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
- 기본 모델: `gemini-2.5-flash`

### Deployment / Collaboration
- Vercel
- GitHub

## 핵심 구조

```text
사용자 작품명
  → POST /api/analyze
  → 1차 Gemini + Google Search Grounding
       · 작품 식별
       · 공식/서지 정보
       · 독자 리뷰
       · 번역/현지화 공개 근거
       · grounding sources / search queries 확보
  → 출처가 없으면 재검색 → 그래도 없으면 422 근거 부족
  → 2차 Gemini 구조화 분석
       · Pydantic structured JSON 변환
       · JSON 생성 오류 시 1회 자동 재시도
  → 출처 URL은 서버가 grounding metadata에서 직접 추가
  → 프론트에서 태그 + 분석 + 출처 표시
```

Google Search 단계와 JSON 단계는 분리되어 있습니다. 검색 도구 사용과 구조화 출력이 서로 간섭하는 문제를 줄이고, 최종 출처 URL은 생성 모델이 임의로 작성하지 못하도록 grounding metadata에서 직접 가져옵니다.

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
```

선택적으로 모델을 변경할 수 있습니다.

```text
GEMINI_MODEL=gemini-2.5-flash
```

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
3. Environment Variables에 `GEMINI_API_KEY`를 등록합니다.
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
- 분석 신뢰도
- 장르 태그
- 분위기/전개 태그
- 번역/현지화 태그
- 스토리 전개
- 매력 포인트
- 주의/지뢰 및 번역 이슈
- 검색 출처 / 검색어

### 실패 처리
- 빈 입력 → 프론트에서 필수값 안내
- 검색 근거 확보 실패 → HTTP 422
- API 키/패키지 문제 → HTTP 500
- AI API 또는 구조화 분석 실패 → HTTP 502
- AI JSON이 불완전하게 생성된 경우 → 구조화 분석 1회 자동 재시도
- 브라우저 요청이 55초를 초과하면 → 타임아웃 안내

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

기존 테스트는 실제 Gemini 과금을 발생시키지 않고 입력 검증, Search Grounding metadata 처리, 리뷰 메모→태그 합성 연결, 출처 중복 제거, 태그 정규화, HTTP 상태 코드 및 프론트 오류 처리를 검증합니다.

## 설계상 안전장치

- Google Search의 `grounding_chunks`가 없으면 분석을 성공으로 반환하지 않습니다.
- 번역 품질 근거가 없으면 `#확인불가`로 처리하도록 프롬프트에서 강제합니다.
- 출처 URL은 2차 생성 모델이 작성하지 않고 Google grounding metadata에서만 가져옵니다.
- 동명 작품/근거 충돌 시 `confidence`와 `evidence_note`에 불확실성을 표시합니다.
- 구조화 JSON이 불완전한 경우 자동으로 한 번 더 생성합니다.
- 프론트는 필수 JSON 필드를 검증하고 타임아웃을 처리합니다.

## 제출 문서

- 기능 요구 사항 체크: `check_list.md`
- 서비스 기획서: `SERVICE_PLAN.md`
- 테스트 기록: `TEST_REPORT.md`

제출 시 별도로 데스크톱/모바일/AI 기능 동작 화면 스크린샷과 AI 코딩 도구 사용 과정 증빙을 첨부합니다.
