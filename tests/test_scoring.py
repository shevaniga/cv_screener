from src.extract import extract_fields
from src.models import ParsedResume
from src.scoring import score_candidate

AGENT = (
    "Jane Doe\nSKILLS\nPython, FastAPI, PostgreSQL\nPROJECTS\n"
    "Support Agent | Python, LangGraph, FastAPI, Redis, Docker\n"
    "- Built a stateful multi-agent workflow with retrieval over 2,000 documents and tool calling\n"
    "- Added pytest evaluation suite, Redis caching and retry logic; deployed on GCP with Docker\n")
WRAPPER = ("Jane Doe\nSKILLS\nPython\nPROJECTS\n"
           "ChatBot\n- Chatbot that calls the OpenAI API to answer questions\n")
CLASSICAL = ("Jane Doe\nSKILLS\nPython, FastAPI, PostgreSQL, Redis, Docker, AWS\nEXPERIENCE\n"
             "- Built FastAPI async services on PostgreSQL with Redis caching, deployed with Docker on AWS\n"
             "- Wrote pytest tests, logging and retry handling\nPROJECTS\n"
             "- Trained a CNN classifier in Python\n")


def make(text):
    return extract_fields(ParsedResume(file_name="x.pdf", text=text))


def test_agent_project_scores_high_with_evidence():
    s = score_candidate(make(AGENT))
    assert s.breakdown.ai_project_depth >= 30
    assert s.total_score >= 60
    assert s.evidence["ai_project_depth"]


def test_thin_wrapper_is_penalised():
    s = score_candidate(make(WRAPPER))
    assert s.breakdown.ai_project_depth == 0
    assert any("thin LLM/API wrapper" in c for c in s.concerns)


def test_classical_ml_is_capped_and_cannot_rank_near_top():
    s = score_candidate(make(CLASSICAL))
    assert s.breakdown.ai_project_depth <= 14
    assert s.total_score <= 50
    assert s.total_score < score_candidate(make(AGENT)).total_score


def test_every_category_stays_within_its_weight():
    b = score_candidate(make(AGENT)).breakdown
    assert b.python_backend <= 30 and b.cloud_fullstack <= 15 and b.engineering_depth <= 5


def test_python_only_in_skills_list_scores_lower_and_is_flagged():
    work = score_candidate(make("Jane Doe\nSKILLS\nPython\nPROJECTS\n- Built Python tools"))
    listed = score_candidate(make("Jane Doe\nSKILLS\nPython\nPROJECTS\n- Built web tools"))
    assert listed.breakdown.python_backend < work.breakdown.python_backend
    assert any("only in a skills list" in c for c in listed.concerns)