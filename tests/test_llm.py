import json

import httpx

from src.extract import extract_fields
from src.llm import judge_resume
from src.models import ParsedResume, ProjectJudgement
from src.scoring import score_candidate

TEXT = ("Jane Doe\njane@x.com\nSKILLS\nPython\nPROJECTS\n"
        "- Built a LangGraph support agent with retrieval and tool calling over 2,000 documents\n")


def resume() -> ParsedResume:
    return extract_fields(ParsedResume(file_name="x.pdf", text=TEXT))


def reply(score=30, quote="LangGraph support agent with retrieval", thin=False) -> dict:
    body = {"ai_depth_score": score, "is_thin_wrapper": thin, "reason": "Real agent workflow.",
            "evidence_quote": quote}
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(body)}]}}]}


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_no_key_skips_cleanly():
    j, status = judge_resume(resume(), client(lambda r: httpx.Response(500)), "", "")
    assert j is None and status.startswith("skipped")


def test_success_and_no_personal_data_sent():
    seen = {}
    def handler(request):
        seen["body"] = request.content.decode()
        seen["key"] = request.headers["x-goog-api-key"]
        return httpx.Response(200, json=reply())
    j, status = judge_resume(resume(), client(handler), "KEY", "some-model")
    assert status == "used" and j.ai_depth_score == 30
    assert seen["key"] == "KEY"
    assert "responseJsonSchema" in seen["body"]
    assert "jane@x.com" not in seen["body"] and "Jane Doe" not in seen["body"]


def test_bad_json_falls_back():
    bad = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    j, status = judge_resume(resume(), client(lambda r: httpx.Response(200, json=bad)), "K", "m")
    assert j is None and status.startswith("failed")


def test_http_error_falls_back():
    j, status = judge_resume(resume(), client(lambda r: httpx.Response(500)), "K", "m", retry_delay=0)
    assert j is None and status.startswith("failed")


def test_hallucinated_quote_is_rejected():
    j, status = judge_resume(resume(), client(lambda r: httpx.Response(200, json=reply(quote="built a kubernetes operator"))),
                             "K", "m")
    assert j is None and status.startswith("rejected")


def test_one_retry_after_rate_limit():
    calls = []
    def handler(request):
        calls.append(1)
        return httpx.Response(429) if len(calls) == 1 else httpx.Response(200, json=reply())
    j, status = judge_resume(resume(), client(handler), "K", "m", retry_delay=0)
    assert status == "used" and len(calls) == 2


def test_llm_can_only_nudge_the_rule_score():
    rule = score_candidate(resume()).breakdown.ai_project_depth
    high = ProjectJudgement(ai_depth_score=40, is_thin_wrapper=False, reason="r", evidence_quote="q")
    low = ProjectJudgement(ai_depth_score=0, is_thin_wrapper=True, reason="r", evidence_quote="q")
    up = score_candidate(resume(), judgement=high).breakdown.ai_project_depth
    down = score_candidate(resume(), judgement=low).breakdown.ai_project_depth
    assert up <= min(40, rule + 8)
    assert down >= max(0, rule - 8)


def test_llm_cannot_lift_classical_ml_past_its_cap():
    r = extract_fields(ParsedResume(file_name="x.pdf",
                       text="Jane Doe\nSKILLS\nPython\nPROJECTS\n- Trained a CNN image classifier in Python"))
    high = ProjectJudgement(ai_depth_score=40, is_thin_wrapper=False, reason="r", evidence_quote="q")
    assert score_candidate(r, judgement=high).breakdown.ai_project_depth <= 14