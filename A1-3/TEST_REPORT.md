# TEST REPORT

검증 대상: Tavily Search + NVIDIA DeepSeek 기반 웹소설 선발대 레이더 (Novel Radar v2.0)

## 결론

- 백엔드 자동 테스트: **28 / 28 PASS** (pytest 실행 성공)
- 프론트 JavaScript 시나리오: **7 / 7 PASS**
- Python 문법 및 타입 린트: **PASS**
- NDJSON 스트리밍 무결성: **PASS**
- 전체 상태: **READY (제출 및 배포 준비 완료)**

---

## 파이프라인 및 기능 검증

파이프라인은 독자의 유료 결제 전 판단 및 지뢰 회피를 지원하기 위해 다음과 같이 작동합니다.

1. **Tavily 5개 쿼리 병렬 검색 (0~35% 진행률):**
   - 작품 정보(작가, 원제, 줄거리)
   - 해외 독자 리뷰(NovelUpdates, Reddit, Goodreads 등)
   - 국내 정식 서비스 플랫폼(카카오페이지, 시리즈, 리디, 문피아)
   - 국내 독자 후기(결말, 하차, 호불호)
   - 연재 이력 및 결말 상태(연재중단, 완결, 휴재 여부)
   - URL 중복 제거 및 유효 스니펫 정제
2. **NVIDIA API (DeepSeek V4.1 Flash) 스트리밍 분석 (40~90% 진행률):**
   - 검색 결과만을 엄격한 근거로 채택하여 환각을 원천 차단
   - 중반 이후 핵심 반전/결말은 도입부 소개에서 배제하고 스포일러 최소화
   - 26종 카탈로그 항목 판정 (언급됨/언급없음/확인불가)
   - JSON 스키마 검증 실패 시 오류 내용을 피드백하여 1회 자동 재요청
3. **백엔드 카탈로그 전수 확장 (95~100% 진행률):**
   - 모델이 누락한 항목을 `확인불가`로 자동 보정하여 누락이 '없음'으로 왜곡되지 않도록 보장
   - 새드엔딩, 열린 결말, 주인공 사망, 주요 인물 사망, 남주 교체 등 결말 항목은 `spoiler=True` 처리
4. **프론트엔드 실시간 렌더링:**
   - NDJSON 스트림 수신으로 원형 게이지(Progress Ring) 및 단계별 안내 실시간 표시
   - 상단 요약 배지(장르, 대표 호불호, 완결 상태, 국내 플랫폼) 및 정보 바 노출
   - 스포일러 항목은 🔒 블라인드 처리되어 사용자가 직접 클릭해야만 공개
   - 원클릭 추천 키워드 입력 및 요약 복사 기능 지원

---

## 백엔드 자동 테스트 28개 상세

1. `test_health_reports_providers_without_exposing_keys`: `/api/health`가 키 값 자체를 노출하지 않고 검색/모델 제공자 및 키 설정 여부를 올바르게 반환하는지 확인
2. `test_blank_title_is_422`: 공백 작품명 입력 시 422 반환
3. `test_missing_title_is_422`: 작품명 필드 누락 시 422 반환
4. `test_title_over_max_length_is_422`: 200자 초과 작품명 입력 시 422 반환
5. `test_title_is_normalized`: 작품명 내부 중복 공백 정규화 확인
6. `test_no_gemini_dependency_left`: Gemini 관련 레거시 의존성이 코드베이스에서 완전히 제거되었는지 확인
7. `test_keys_read_user_env_names`: `travily_key`, `tavily_key`, `nvidia_key` 등 다양한 환경변수 이름을 유연하게 인식하는지 확인
8. `test_missing_keys_produce_clear_error`: 환경변수 키 누락 시 명확한 500 오류 반환
9. `test_queries_cover_reviews_platforms_and_ending_history`: Tavily 5개 쿼리가 리뷰, 플랫폼, 결말 이력을 고르게 포괄하는지 확인
10. `test_tavily_request_shape_and_snippet_cleanup`: Tavily API 페이로드 규격 및 스니펫 정리 로직 확인
11. `test_searches_report_progress_and_dedupe_urls`: 검색 단계별 진행률 통지 및 중복 URL 제거 확인
12. `test_one_failed_search_does_not_stop_analysis`: 5개 병렬 검색 중 일부가 실패해도 나머지 결과로 정상 분석 진행
13. `test_no_search_results_is_422_and_quota_is_429`: 검색 결과가 전혀 없을 때 422, 사용량 초과 시 429 반환
14. `test_prompt_limits_story_to_opening_and_marks_search_as_data`: 프롬프트가 스포일러를 방지하고 검색 결과를 지시가 아닌 데이터로 취급하는지 확인
15. `test_extract_json_handles_think_fences_and_prose`: DeepSeek의 `<think>` 태그, 마크다운 코드블록, 주변 텍스트에서 순수 JSON만 안전하게 추출하는지 확인
16. `test_nvidia_stream_request_and_progress`: NVIDIA 스트리밍 요청 규격 및 진행률(40~90%) 계산 확인
17. `test_invalid_json_is_retried_with_validation_error`: JSON 스키마 검증 실패 시 오류 내용을 피드백하여 1회 자동 재요청하는지 확인
18. `test_nvidia_http_errors_map_to_user_messages`: NVIDIA HTTP 오류(401, 404, 429 등)가 사용자 친화적 메시지로 매핑되는지 확인
19. `test_no_time_left_fails_fast`: 예산 시간이 부족할 때 지체 없이 빠르게 실패 처리되는지 확인
20. `test_fields_are_normalized`: 장르 태그 `#` 자동 부여 및 플랫폼 중복 제거 검증
21. `test_checklist_is_expanded_to_full_catalog_with_unknown_default`: 26종 체크리스트 카탈로그 확장 및 누락 항목 `확인불가` 기본값 처리 확인
22. `test_ending_items_are_spoiler_locked`: 결말 관련 민감 항목(새드엔딩, 주인공 사망 등)이 `spoiler=True`로 잠금 처리되는지 확인
23. `test_unknown_checklist_key_is_rejected`: 카탈로그에 없는 임의의 체크리스트 키가 스키마에서 거부되는지 확인
24. `test_full_stream_progress_then_result`: 전체 분석 파이프라인에서 단조 증가하는 진행률 이벤트 이후 최종 결과 이벤트가 정상 발행되는지 확인
25. `test_stream_reports_errors_as_events`: 스트림 처리 중 발생한 예외가 `type: error` 이벤트로 정상 발행되는지 확인
26. `test_analyze_endpoint_streams_ndjson`: `/api/analyze` 엔드포인트가 `application/x-ndjson` 헤더와 함께 스트리밍되는지 확인
27. `test_frontend_has_progress_ring_and_stream_reader`: `index.html`에 원형 진행률 SVG 요소와 NDJSON 스트림 리더 함수가 구비되어 있는지 확인
28. `test_vercel_allows_two_minutes`: `vercel.json`의 maxDuration(120초) 및 서버 시간 예산(110초) 정합성 확인

---

## 프론트엔드 시나리오 7개 상세

1. **빈 입력 검증:** 작품명이 공백일 때 API 호출 없이 필수값 입력 경고 표시 및 포커스 이동
2. **정상 스트리밍 및 결과 렌더링:**
   - 실시간 진행률 수신에 따른 원형 게이지 업데이트
   - 대표 요약 칩(#장르, 대표호불호, 완결상태, 국내플랫폼) 렌더링
   - 정보 바(원작 화수, 진입장벽 독자평) 표시
   - 호불호 체크리스트의 스포일러 제외 건수 표시
   - 결말 스포일러 항목(🔒)의 블라인드 잠금 유지 확인 및 클릭 시에만 내용 공개 검증
   - 유사 추천작 섹션 정상 노출
   - 완료 후 진행률 100% 처리 및 로딩 상태 해제
3. **스트림 내부 error 이벤트 수신:** 백엔드에서 전송된 오류 이벤트(예: 429 사용량 한도)를 사용자 경고창에 정확히 표시
4. **스트림 중간 단절 예외:** result 없이 스트림이 조기 종료되었을 때 적절한 재시도 안내 메시지 표시
5. **서버 422 오류 렌더링:** 검색 결과 미확보 시 서버 detail 메시지 표시
6. **비정상 JSON 스키마 거부:** 필수 필드가 누락된 비정상 데이터 수신 시 형식 오류 처리
7. **HTML/비JSON 응답 거부:** 게이트웨이 타임아웃 등 비정상 텍스트 수신 시 안전하게 오류 처리

---

## 라이브 API 검증 조건 (Vercel 배포)

Vercel 환경변수에 `travily_key`와 `nvidia_key`를 등록한 후 라이브 검증 시 성공 기준:

- HTTP 200 (`Content-Type: application/x-ndjson`)
- 실시간 `progress` 이벤트(0% ~ 97%) 순차 수신
- 최종 `result` 이벤트 내 26개 `checklist` 항목 전수 포함
- 원형 프로그레스 링이 100% 완료로 이동한 후 분석 결과 카드로 전환
- 스포일러 항목(새드엔딩, 주인공 사망 등) 클릭 시 정상적으로 판정 내용 공개
