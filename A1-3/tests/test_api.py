import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("radar_api", ROOT / "api" / "index.py")
api = importlib.util.module_from_spec(SPEC)
sys.modules["radar_api"] = api
SPEC.loader.exec_module(api)
client = TestClient(api.app)


def analysis_obj(**overrides):
    data = {
        "identified_title": "Lord of the Mysteries",
        "original_title": "诡秘之主",
        "author": "Cuttlefish That Loves Diving",
        "origin": "중국 웹소설",
        "confidence": "높음",
        "genre_tags": ["#판타지", "#미스터리"],
        "serial_status": "완결",
        "original_length": "1,394화",
        "korean_releases": [{"platform": "카카오페이지", "note": "완결"}],
        "entry_point": "초반이 느리다는 평이 많음",
        "story_opening": "미스터리와 성장 중심의 도입부",
        "charm_points": "독자 리뷰에서 세계관과 복선이 장점으로 반복 언급됨",
        "similar_works": [{"title": "비교작", "reason": "세계관 중심이라는 평"}],
        "checklist": [
            {"key": "harem", "status": "언급없음", "note": ""},
            {"key": "sad_ending", "status": "언급됨", "note": "결말 호불호 언급"},
        ],
    }
    data.update(overrides)
    return api.NovelAnalysis(**data)


def grounded_response(memo="독자 리뷰에서 초반 전개가 느리지만 세계관이 강점이라는 평가가 반복된다.", *, uri="https://example.com/review", title="Reader review", queries=None):
    metadata = SimpleNamespace(
        web_search_queries=queries or ["Lord of the Mysteries review", "诡秘之主 评价"],
        grounding_chunks=[SimpleNamespace(web=SimpleNamespace(uri=uri, title=title))],
        search_entry_point=SimpleNamespace(rendered_content="<div>Google Search</div>"),
    )
    return SimpleNamespace(
        text=memo,
        candidates=[SimpleNamespace(grounding_metadata=metadata)],
    )


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model"] == api.MODEL_NAME


def test_blank_title_is_422():
    response = client.post("/api/analyze", json={"title": "   "})
    assert response.status_code == 422


def test_missing_title_is_422():
    response = client.post("/api/analyze", json={})
    assert response.status_code == 422


def test_title_over_max_length_is_422():
    response = client.post("/api/analyze", json={"title": "가" * (api.MAX_TITLE_LENGTH + 1)})
    assert response.status_code == 422


def test_title_is_normalized():
    req = api.AnalyzeRequest(title="  Lord   of   the Mysteries  ")
    assert req.title == "Lord of the Mysteries"


def test_research_prompt_targets_reader_decision_info():
    prompt = api._research_prompt("작품명")
    assert "독자 리뷰" in prompt
    assert "커뮤니티" in prompt
    assert "연재 중단" in prompt
    assert "한국어 정식 번역본" in prompt
    assert "진입장벽" in prompt
    assert "만들어내지 마세요" in prompt
    # 체크리스트 전 항목이 조사 대상에 포함된다
    for key in api.CHECKLIST_INDEX:
        assert f"({key})" in prompt


def test_synthesis_prompt_limits_story_to_opening_and_hides_sources():
    research = api.ResearchResult(
        memo="독자 리뷰: 초반이 느리지만 이후 사이다 전개라는 평가.",
        sources=[{"title": "review", "url": "https://example.com/review"}],
        search_queries=["작품 리뷰"],
        search_entry_point=None,
    )
    prompt = api._synthesis_prompt("작품", research)
    assert "초반이 느리지만" in prompt
    assert "중반 이후 사건, 반전, 결말, 인물 사망은 절대 쓰지 마세요" in prompt
    assert "조사 메모에 없는 사실은 새로 만들어내지 마세요" in prompt
    assert "https://example.com/review" not in prompt


def test_checklist_is_expanded_to_full_catalog_with_unknown_default():
    obj = analysis_obj(checklist=[
        {"key": "sad_ending", "status": "언급됨", "note": "근거"},
        {"key": "sad_ending", "status": "언급없음", "note": "중복"},
        {"key": "harem", "status": "언급없음", "note": "무시될 메모"},
    ])
    items = api.build_checklist(obj.checklist)
    assert len(items) == len(api.CHECKLIST_INDEX)
    by_key = {i.key: i for i in items}
    assert by_key["sad_ending"].status == "언급됨"
    assert by_key["sad_ending"].note == "근거"
    assert by_key["sad_ending"].spoiler is True
    assert by_key["sad_ending"].category == "전개·결말"
    assert by_key["harem"].note == ""
    assert by_key["gore"].status == "확인불가"
    assert {i.key for i in items if i.category == "혐오 표현"} == {"hate_race", "hate_nation"}


def test_ending_items_are_spoiler_locked():
    spoilers = {key for key, (_, item) in api.CHECKLIST_INDEX.items() if item.get("spoiler")}
    assert {"sad_ending", "open_ending", "mc_death", "major_death"} <= spoilers
    assert "hiatus_dropped" not in spoilers


def test_unknown_checklist_key_is_rejected():
    try:
        api.ChecklistFinding(key="not_a_key", status="언급됨", note="")
    except Exception:
        return
    raise AssertionError("unknown checklist key should be rejected")


def test_extract_grounding_deduplicates_sources_and_filters_bad_urls():
    chunks = [
        SimpleNamespace(web=SimpleNamespace(uri="https://example.com/a", title="A")),
        SimpleNamespace(web=SimpleNamespace(uri="https://example.com/a", title="A duplicate")),
        SimpleNamespace(web=SimpleNamespace(uri="javascript:alert(1)", title="bad")),
        SimpleNamespace(web=SimpleNamespace(uri="https://example.com/b", title="B")),
    ]
    metadata = SimpleNamespace(
        web_search_queries=["query 1", "query 1", "query 2"],
        grounding_chunks=chunks,
        search_entry_point=SimpleNamespace(rendered_content="<div>Google</div>"),
    )
    response = SimpleNamespace(candidates=[SimpleNamespace(grounding_metadata=metadata)])
    sources, queries, html = api._extract_grounding(response)
    assert sources == [
        {"title": "A", "url": "https://example.com/a"},
        {"title": "B", "url": "https://example.com/b"},
    ]
    assert queries == ["query 1", "query 2"]
    assert html == "<div>Google</div>"


def test_extract_grounding_caps_sources_and_queries_at_12():
    chunks = [SimpleNamespace(web=SimpleNamespace(uri=f"https://example.com/{i}", title=str(i))) for i in range(20)]
    metadata = SimpleNamespace(
        web_search_queries=[f"q{i}" for i in range(20)],
        grounding_chunks=chunks,
        search_entry_point=None,
    )
    response = SimpleNamespace(candidates=[SimpleNamespace(grounding_metadata=metadata)])
    sources, queries, _ = api._extract_grounding(response)
    assert len(sources) == 12
    assert len(queries) == 12


def test_analysis_fields_are_normalized():
    obj = analysis_obj(
        genre_tags=["판타지", "#판타지", "", "회귀", "무협", "헌터", "여섯"],
        korean_releases=[{"platform": " 카카오페이지 ", "note": " 완결 "}, {"platform": "카카오페이지", "note": "중복"}],
        similar_works=[{"title": f"작품{i}", "reason": "r"} for i in range(5)],
    )
    assert obj.genre_tags == ["#판타지", "#회귀", "#무협", "#헌터"]
    assert [r.platform for r in obj.korean_releases] == ["카카오페이지"]
    assert obj.korean_releases[0].note == "완결"
    assert len(obj.similar_works) == 3


def test_research_work_retries_when_first_call_has_no_grounding():
    no_ground = SimpleNamespace(text="모델 기억 응답", candidates=[SimpleNamespace(grounding_metadata=None)])
    with_ground = grounded_response()

    class Models:
        def __init__(self):
            self.calls = []
        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            return no_ground if len(self.calls) == 1 else with_ground

    fake_client = SimpleNamespace(models=Models())
    fake_types = SimpleNamespace(
        Tool=lambda **kwargs: SimpleNamespace(**kwargs),
        GoogleSearch=lambda: SimpleNamespace(),
        GenerateContentConfig=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    with patch.object(api, "_client", return_value=fake_client), patch.object(api, "_google_sdk", return_value=(None, fake_types)):
        result = api._research_work("Lord of the Mysteries")

    assert len(fake_client.models.calls) == 2
    assert "반드시 Google Search를 실제로 사용" in fake_client.models.calls[1]["contents"]
    assert result.sources[0]["url"] == "https://example.com/review"
    assert "독자 리뷰" in result.memo


def test_research_work_raises_if_both_calls_have_no_sources():
    no_ground = SimpleNamespace(text="응답", candidates=[SimpleNamespace(grounding_metadata=None)])
    fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: no_ground))
    fake_types = SimpleNamespace(
        Tool=lambda **kwargs: SimpleNamespace(**kwargs),
        GoogleSearch=lambda: SimpleNamespace(),
        GenerateContentConfig=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    with patch.object(api, "_client", return_value=fake_client), patch.object(api, "_google_sdk", return_value=(None, fake_types)):
        try:
            api._research_work("unknown")
        except RuntimeError as exc:
            assert "Google Search 근거" in str(exc)
        else:
            raise AssertionError("grounding failure should raise RuntimeError")


def test_synthesize_uses_structured_json_schema_and_review_memo():
    captured = {}
    parsed = analysis_obj()

    class Models:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(parsed=parsed, text="")

    fake_client = SimpleNamespace(models=Models())
    fake_types = SimpleNamespace(GenerateContentConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    research = api.ResearchResult(
        memo="독자 리뷰에서 초반이 느리다는 의견이 반복됨.",
        sources=[{"title": "R", "url": "https://example.com/r"}],
        search_queries=["review"],
        search_entry_point=None,
    )
    with patch.object(api, "_client", return_value=fake_client), patch.object(api, "_google_sdk", return_value=(None, fake_types)):
        result = api._synthesize("작품", research)

    assert "초반이 느리다" in captured["contents"]
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].response_schema is api.NovelAnalysis
    assert result.serial_status == "완결"


def test_analyze_title_returns_no_source_list_but_keeps_search_chip():
    research = api.ResearchResult(
        memo="리뷰 메모",
        sources=[{"title": "Reader review", "url": "https://example.com/review"}],
        search_queries=["novel review"],
        search_entry_point="<div>Search</div>",
    )
    with patch.object(api, "_research_work", return_value=research), patch.object(api, "_synthesize", return_value=analysis_obj()):
        result = api.analyze_title("Lord of the Mysteries")
    body = result.model_dump()
    assert "sources" not in body
    assert "search_queries" not in body
    assert "evidence_note" not in body
    assert body["google_search_entry_point"] == "<div>Search</div>"
    assert len(body["checklist"]) == len(api.CHECKLIST_INDEX)


def test_successful_api_response_contains_reader_fields():
    result = api.AnalyzeResponse(
        **analysis_obj().model_dump(exclude={"checklist"}),
        checklist=api.build_checklist(analysis_obj().checklist),
        google_search_entry_point=None,
    )
    with patch.object(api, "analyze_title", return_value=result):
        response = client.post("/api/analyze", json={"title": "Lord of the Mysteries"})
    assert response.status_code == 200
    body = response.json()
    assert body["genre_tags"]
    assert body["serial_status"] == "완결"
    assert body["korean_releases"][0]["platform"] == "카카오페이지"
    assert body["checklist"]


def test_no_grounding_returns_422():
    with patch.object(api, "analyze_title", side_effect=RuntimeError("Google Search 근거를 확보하지 못했습니다.")):
        response = client.post("/api/analyze", json={"title": "unknown"})
    assert response.status_code == 422
    assert "Google Search" in response.json()["detail"]


def test_missing_api_key_returns_500():
    with patch.object(api, "analyze_title", side_effect=RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")):
        response = client.post("/api/analyze", json={"title": "test"})
    assert response.status_code == 500


def test_upstream_failure_returns_502():
    with patch.object(api, "analyze_title", side_effect=RuntimeError("upstream timeout")):
        response = client.post("/api/analyze", json={"title": "test"})
    assert response.status_code == 502


def test_frontend_contains_validation_spoiler_lock_and_timeout():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "requireAnalysisShape(data)" in html
    assert "renderChecklist(data)" in html
    assert "item.spoiler" in html
    assert "fetch('/api/analyze'" in html
    assert "setTimeout(() => controller.abort(), 58000)" in html
    assert "sourcesContainer" not in html


def test_vercel_and_dependencies_are_present():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    vercel = (ROOT / "vercel.json").read_text(encoding="utf-8")
    assert "fastapi" in requirements
    assert "google-genai" in requirements
    assert "pydantic" in requirements
    assert '"api/index.py"' in vercel
    assert '"maxDuration": 60' in vercel


def test_full_pipeline_fake_google_search_to_reader_analysis():
    research_response = grounded_response(
        memo="독자 리뷰에서 초반은 느리지만 세계관이 강점이라는 평가가 반복된다.",
        uri="https://example.com/readers-review",
        title="Readers review",
        queries=["Lord of the Mysteries reader review"],
    )
    synthesis_response = SimpleNamespace(parsed=analysis_obj(), text="")

    class Models:
        def __init__(self):
            self.count = 0
        def generate_content(self, **kwargs):
            self.count += 1
            return research_response if self.count == 1 else synthesis_response

    fake_client = SimpleNamespace(models=Models())
    fake_types = SimpleNamespace(
        Tool=lambda **kwargs: SimpleNamespace(**kwargs),
        GoogleSearch=lambda: SimpleNamespace(),
        GenerateContentConfig=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    with patch.object(api, "_client", return_value=fake_client), patch.object(api, "_google_sdk", return_value=(None, fake_types)):
        result = api.analyze_title("Lord of the Mysteries")

    assert fake_client.models.count == 2
    assert result.genre_tags == ["#판타지", "#미스터리"]
    assert result.google_search_entry_point == "<div>Google Search</div>"
    assert len(result.checklist) == len(api.CHECKLIST_INDEX)
