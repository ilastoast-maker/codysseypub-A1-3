# 웹소설 선발대 레이더 — Google Search Grounded MVP

작품 제목을 입력하면 Gemini가 **Google Search Grounding으로 작품과 공개 리뷰 근거를 먼저 조사**하고, 그 조사 결과만 바탕으로 구조화된 한국어 분석을 만드는 Vercel용 프로젝트입니다.

> 저장소: `ilastoast-maker/codysseypub-A1-3`  
> 기본 브랜치: `main`  
> Vercel Root Directory: `A1-3`

## 핵심 구조

```text
사용자 작품명
  → POST /api/analyze
  → 1차 Gemini: Google Search Grounding
       · 작품 식별
       · 공식/서지 정보
       · 독자 리뷰
       · 번역/현지화 공개 근거
       · grounding sources / search queries 확보
  → 출처가 없으면 재검색 → 그래도 없으면 422 근거 부족
  → 2차 Gemini: 검색 조사 메모만 입력
       · Pydantic structured JSON 변환
  → 출처 URL은 서버가 grounding metadata에서 직접 추가
  → 프론트에서 분석 + 출처 표시
```

Google Search 단계와 JSON 단계는 분리했습니다. 이렇게 하면 검색 도구 사용과 구조화 출력이 서로 간섭하는 문제를 줄이고, 두 번째 모델이 URL을 만들어내지 못하게 할 수 있습니다.

## 프로젝트 구조

```text
codysseypub-A1-3/
└── A1-3/
    ├── index.html
    ├── api/
    │   └── index.py
    ├── tests/
    │   ├── test_api.py
    │   └── test_frontend.js
    ├── requirements.txt
    ├── pyproject.toml
    ├── vercel.json
    ├── TEST_REPORT.md
    ├── .gitignore
    └── README.md
```

## Vercel 배포 설정

Vercel에서 GitHub 저장소 `ilastoast-maker/codysseypub-A1-3`를 Import한 뒤 **Root Directory를 `A1-3`로 지정**합니다. 그 다음 Project Settings → Environment Variables에 아래 값을 설정합니다.

```text
GEMINI_API_KEY=실제 Gemini API 키
```

선택적으로 모델을 바꾸려면:

```text
GEMINI_MODEL=gemini-2.5-flash
```

API 키를 HTML 또는 Git 저장소에 넣지 마세요.

## 저장소 받기

```bash
git clone https://github.com/ilastoast-maker/codysseypub-A1-3.git
cd codysseypub-A1-3/A1-3
```

## 로컬 실행

가장 배포 환경과 가까운 방법:

```bash
npm i -g vercel
vercel dev
```

브라우저에서 보통 `http://localhost:3000`을 엽니다.

API 상태 확인:

```bash
curl http://localhost:3000/api/health
```

분석 호출:

```bash
curl -X POST http://localhost:3000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"title":"Lord of the Mysteries"}'
```

## 테스트

```bash
pip install -r requirements.txt
python -m pytest -q
node tests/test_frontend.js
```

백엔드 테스트는 실제 Gemini 과금을 발생시키지 않고 입력 검증, Google Search grounding metadata, 리뷰 메모→태그 합성 연결, 출처 중복 제거, 태그 정규화, HTTP 상태 코드를 검증합니다. 프론트 테스트는 빈 입력, 정상 태그/출처 렌더링, API 오류, 잘못된 응답 스키마를 모의 실행합니다.

현재 검증 결과:

```text
backend: 21 / 21 PASS
frontend: 5 / 5 PASS
Python syntax: PASS
JavaScript syntax: PASS
```

## 실제 API 동작 검증

배포 후 다음을 순서대로 확인하세요.

1. `/api/health` → HTTP 200
2. 빈 작품명 → HTTP 422
3. 잘 알려진 작품명 → HTTP 200 + `grounded: true` + `sources` 1개 이상
4. 모호한 작품명 → 근거 확보 실패 시 HTTP 422
5. `sources` 링크가 브라우저에서 열리는지 확인
6. Vercel Function Logs에서 Gemini 오류가 없는지 확인

## 응답 예시 구조

```json
{
  "identified_title": "Lord of the Mysteries",
  "original_title": "诡秘之主",
  "author": "...",
  "origin": "중국 웹소설",
  "confidence": "높음",
  "genre_tags": ["#판타지"],
  "atmosphere_tags": ["#미스터리"],
  "translation_tags": ["#확인불가"],
  "story_arc_map": "...",
  "charm_points": "...",
  "warning_elements": "...",
  "evidence_note": "...",
  "sources": [{"title": "...", "url": "https://..."}],
  "search_queries": ["..."],
  "grounded": true,
  "google_search_entry_point": "..."
}
```

## 설계상 중요한 안전장치

- Google Search의 `grounding_chunks`가 없으면 분석을 성공으로 반환하지 않습니다.
- 번역 품질 근거가 없으면 `#확인불가`로 처리하도록 프롬프트에서 강제합니다.
- 출처 URL은 2차 생성 모델이 작성하지 않고 Google grounding metadata에서만 가져옵니다.
- 동명 작품/근거 충돌 시 `confidence`와 `evidence_note`에 불확실성을 표시합니다.
- 프론트는 필수 JSON 필드를 검증하고 55초 timeout을 둡니다.
- 백엔드는 400/422/500/502 계열 상태를 구분합니다.

## 참고

Google Search Grounding은 검색어, grounding chunks, search entry point 같은 메타데이터를 제공합니다. 서비스에서 출처 링크와 Google Search entry point를 노출하도록 구현했습니다.
