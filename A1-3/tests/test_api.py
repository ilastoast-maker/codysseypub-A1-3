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
        "genre_tags": ["#판타지", "#미스턬리"],
        "atmosphere_tags": ["#느린초반", "#세계관중심"],
        "translation_tags": ["#확인불가"],
        "story_arc_map": "미스터리와 성장 중심 전개",
        "charm_points": "독자 리뷰에서 세계관과 복선이 장점으로 반복 언급됨",
        "warning_elements": "초반 정보량과 전개 속도에 호불호가 있다는 리뷰가 있음",
        "evidence_note": "공식 정보와 독자 리뷰를 함께 참고",
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


def test_research_prompt_explicitly_requests_reader_reviews_and_translation_evidence():
    prompt = api._research_prompt("작품명")
    assert "독자 리뷰" in prompt
    assert "커뮤니티" in prompt
    assert "번역/현지화" in prompt
    assert "만들어내지 마세요" in prompt


def test_synthesis_prompt_passes_review_memo_to_tag_generation_stage():
    research = api.ResearchResult(
        memo="독자 리뷰: 초반이 느리지만 후반 사이다 전개라는 평가. 한국 번역은 자연스럽다는 평가가 일부 있음.",
        sources=[{"title": "review", "url": "https://example.com/review"}],
        search_queries=["작품 리뷰"],
        search_entry_point=None,
    )
    prompt = api._synthesis_prompt("작품", research)
    assert "초반이 느리지만 후반 사이다" in prompt
    assert "한국 번역은 자연스럽다" in prompt
    assert "https://example.com/review" in prompt
    assert "translation_tags" in prompt
    assert "조사 메모에 없는 사실은 새로 만들어내지 마세요" in prompt


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


def test_analysis_tags_are_normalized_and_deduplicated():
    obj = analysis_obj(
        genre_tags=["판타지", "#판타지", ""],
        atmosphere_tags=["성장"],
        translation_tags=["확인불가"],
    )
    assert obj.genre_tags == ["#판타지"]
    assert obj.atmosphere_tags == ["#성장"]
    assert obj.translation_tags == ["#확인불가"]


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
    parsed = analysis_obj(
        atmosphere_tags=["#느린초반", "#후반가속"],
        translation_tags=["#번역평가혼재"],
    )

    class Models:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(parsed=parsed, text="")

    fake_client = SimpleNamespace(models=Models())
    fake_types = SimpleNamespace(GenerateContentConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    research = api.ResearchResult(
        memo="독자 리뷰에서 초반이 느리다는 의견과 후반 가속이 장점이라는 의견이 반복됨. 번역 평가는 혼재.",
        sources=[{"title": "R", "url": "https://example.com/r"}],
        search_queries=["review"],
        search_entry_point=None,
    )
    with patch.object(api, "_client", return_value=fake_client), patch.object(api, "_google_sdk", return_value=(None, fake_types)):
        result = api._synthesize("작품", research)

    assert "초반이 느리다" in captured["contents"]
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].response_schema is api.NovelAnalysis
    assert result.atmosphere_tags == ["#느린초반", "#후반가속"]
    assert result.translation_tags == ["#번역평가혼재"]


def test_analyze_title_combines_review_based_tags_with_grounding_sources():
    research = api.ResearchResult(
        memo="리뷰 메모",
        sources=[{"title": "Reader review", "url": "https://example.com/review"}],
        search_queries=["novel review"],
        search_entry_point="<div>Search</div>",
    )
    synthesis = analysis_obj(atmosphere_tags=["#사이다", "#다크"], translation_tags=["#확인불가"])
    with patch.object(api, "_research_work", return_value=research), patch.object(api, "_synthesize", return_value=synthesis):
        result = api.analyze_title("Lord of the Mysteries")
    assert result.grounded is True
    assert result.atmosphere_tags == ["#사이다", "#다크"]
    assert result.sources[0].url == "https://example.com/review"
    assert result.search_queries == ["novel review"]


def test_successful_api_response_contains_tags_and_sources():
    result = api.AnalyzeResponse(
        **analysis_obj().model_dump(),
        sources=[api.Source(title="Source", url="https://example.com")],
        search_queries=["Lord of the Mysteries review"],
        grounded=True,
        google_search_entry_point=None,
    )
    with patch.object(api, "analyze_title", return_value=result):
        response = client.post("/api/analyze", json={"title": "Lord of the Mysteries"})
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["genre_tags"]
    assert body["atmosphere_tags"]
    assert body["translation_tags"]
    assert body["sources"][0]["url"] == "https://example.com"


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


def test_frontend_contains_response_validation_sources_and_timeout():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "requireAnalysisShape(data)" in html
    assert "data.genre_tags.forEach" in html
    assert "data.atmosphere_tags.forEach" in html
    assert "data.translation_tags.forEach" in html
    assert "data.sources.forEach" in html
    assert "fetch('/api/analyze'" in html
    assert "setTimeout(() => controller.abort(), 55000)" in html
    assert "noopener noreferrer" in html


def test_vercel_and_dependencies_are_present():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    vercel = (ROOT / "vercel.json").read_text(encoding="utf-8")
    assert "fastapi" in requirements
    assert "google-genai" in requirements
    assert "pydantic" in requirements
    assert '"api/index.py"' in vercel
    assert '"maxDuration": 60' in vercel


def test_full_pipeline_fake_google_search_to_review_tags_and_sources():
    research_response = grounded_response(
        memo="독자 리뷰에서 초반은 느리지만 세계관과 복선 회수가 강점이라는 평가가 반복된다. 번역 평가는 자료가 부족하다.",
        uri="https://example.com/readers-review",
        title="Readers review",
        queries=["Lord of the Mysteries reader review"],
    )
    synthesis_response = SimpleNamespace(
        parsed=analysis_obj(
            atmosphere_tags=["#느린초반", "#복선회수"],
            translation_tags=["#확인불가"],
            charm_points="독자 리뷰에서 세계관과 복선 회수가 반복적으로 호평됨",
        ),
        text="",
    )

    class Models:
        def __init__(self):
            self.count = 0
            self.calls = []
        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
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
    assert result.grounded is True
    assert result.atmosphere_tags == ["#느린초반", "#복선회수"]
    assert result.translation_tags == ["#확인불가"]
    assert "독자 리뷰" in result.charm_points
    assert result.sources[0].url == "https://example.com/readers-review"
    assert result.search_queries == ["Lord of the Mysteries reader review"]
