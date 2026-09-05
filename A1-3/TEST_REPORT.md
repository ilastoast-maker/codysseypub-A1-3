# TEST REPORT

검증 대상: Google Search Grounded 웹소설 선발대 레이더 MVP

## 결론

- 백엔드 자동 테스트: **21 / 21 PASS**
- 프론트 JavaScript 시나리오: **5 / 5 PASS**
- Python 문법 검사: **PASS**
- JavaScript 문법 검사: **PASS**
- 최종 ZIP 무결성: **PASS**

## 리뷰 → 태그 기능 검증

현재 파이프라인은 다음 순서로 작동합니다.

1. Gemini + Google Search Grounding이 작품을 식별하고 공개 웹 자료를 조사합니다.
2. 조사 프롬프트에서 독자 리뷰/커뮤니티 반응과 번역·현지화 평가를 명시적으로 수집하도록 요구합니다.
3. 검색으로 그라운딩된 조사 메모와 실제 source URL만 2차 합성 단계에 전달합니다.
4. 2차 Gemini structured output이 `genre_tags`, `atmosphere_tags`, `translation_tags`를 생성합니다.
5. 번역 관련 근거가 없으면 `#확인불가`를 사용하도록 지시합니다.
6. 최종 응답에 태그와 Google Search 출처/search_queries를 함께 반환합니다.

추가 테스트에서는 리뷰 메모(`초반이 느림`, `후반 가속`, `번역 평가 혼재`)가 합성 프롬프트에 실제로 전달되고, 모의 structured output에서 `#느린초반`, `#후반가속`, `#번역평가혼재`와 같은 태그가 최종 응답으로 전달되는 것을 확인했습니다.

## 백엔드 자동 테스트 21개

1. `/api/health` 정상 응답 및 모델명 확인
2. 빈 작품명 422
3. 작품명 필드 누락 422
4. 200자 초과 작품명 422
5. 작품명 공백 정규화
6. 조사 프롬프트가 독자 리뷰/커뮤니티/번역 평가 검색을 요구하는지 확인
7. 리뷰 조사 메모가 태그 합성 프롬프트에 전달되는지 확인
8. grounding source 중복 제거 및 위험 URL 제거
9. source/search query 최대 12개 제한
10. 태그 `#` 자동 보정 및 중복 제거
11. 첫 검색에 grounding이 없을 때 강제 재검색
12. 두 번 모두 grounding이 없으면 실패 처리
13. 합성 단계가 JSON structured output/Pydantic schema를 사용하는지 확인
14. 리뷰 메모에서 생성된 분위기/번역 태그 전달 확인
15. `analyze_title()`이 태그 + sources + search_queries를 결합하는지 확인
16. 정상 `/api/analyze` 응답에 3종 태그와 출처 포함
17. grounding 근거 미확보 시 422
18. API 키 설정 오류 500
19. Gemini 상류 장애 502
20. 프론트 응답 검증/출처/timeout 코드 존재 확인
21. Vercel 설정 및 `fastapi`, `google-genai`, `pydantic` 의존성 확인

## 프론트 시나리오 5개

1. 빈 입력 → API 호출 없이 오류 표시
2. 정상 응답 → 장르/분위기/번역 태그 및 리뷰 근거/출처 표시
3. HTTP 422 → 서버 detail 오류 표시
4. 성공 HTTP지만 필드가 누락된 JSON → 응답 스키마 오류 처리
5. JSON이 아닌 서버 응답 → 오류 처리

정상 응답 시 로딩 상태가 해제되고 버튼이 다시 활성화되는 것도 확인했습니다.

## 정적/구조 검증

- `api/index.py`, `tests/test_api.py` Python compile PASS
- `index.html` JavaScript `node --check` PASS
- `/api/analyze` 연결 PASS
- Google Search grounding tool 사용 PASS
- grounding metadata의 source URL/search query 추출 PASS
- 2차 `NovelAnalysis` structured output PASS
- Google Search 결과가 없을 때 모델 기억만으로 분석하지 않고 중단하는 로직 PASS
- 실제 `GEMINI_API_KEY`는 프로젝트에 포함하지 않음

## 라이브 API 검증 범위

이 테스트는 실제 Gemini API 과금을 발생시키지 않도록 Google API 부분을 mock으로 검증했습니다. 따라서 코드 경로와 데이터 흐름은 검증했지만, 실제 검색 품질·Google Search가 특정 작품에 대해 어떤 리뷰를 찾는지는 네트워크와 검색 색인에 따라 달라집니다.

실제 배포 환경에서 `GEMINI_API_KEY`를 설정한 뒤 최종 라이브 검증 시 성공 조건은 다음입니다.

- HTTP 200
- `grounded: true`
- `sources` 1개 이상
- `genre_tags`, `atmosphere_tags`, `translation_tags` 배열 존재
- `search_queries` 존재
- UI에서 태그와 검색 출처가 함께 표시됨
