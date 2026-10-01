from src.eligibility import check_eligibility
from src.extract import extract_fields
from src.models import ParsedResume


def make(text: str) -> ParsedResume:
    return extract_fields(ParsedResume(file_name="x.pdf", text=text))


def test_java_react_only_is_rejected():
    r = check_eligibility(make("Jane Doe\nSKILLS\nJava, JavaScript, React, Spring Boot\n"
                               "PROJECTS\nBuilt a shop with React and Spring Boot"))
    assert not r.eligible
    assert any("Python" in x for x in r.rejection_reasons)
    assert "Java" in r.matched_skills and "React" in r.matched_skills


def test_java_does_not_match_javascript():
    r = check_eligibility(make("Jane Doe\nSKILLS\nJavaScript, TypeScript"))
    assert "Java" not in r.matched_skills


def test_python_plus_rag_project_is_eligible():
    r = check_eligibility(make(
        "Jane Doe\nSKILLS\nPython, FastAPI\nPROJECTS\n"
        "DocBot\n- Built a RAG pipeline with LangChain and FAISS for document search"))
    assert r.eligible
    assert r.evidence


def test_vague_ai_claim_is_rejected():
    r = check_eligibility(make(
        "Jane Doe\nSKILLS\nPython\nPROJECTS\n- Built an AI-powered study app with React"))
    assert not r.eligible
    assert any("vague" in x for x in r.rejection_reasons)


def test_copilot_only_is_rejected():
    r = check_eligibility(make(
        "Jane Doe\nSKILLS\nPython\nEXPERIENCE\n- Used GitHub Copilot and LLM tools to ship faster"))
    assert not r.eligible
    assert any("coding tool" in x for x in r.rejection_reasons)


def test_ai_keyword_only_in_skills_list_is_rejected():
    r = check_eligibility(make("Jane Doe\nSKILLS\nPython, LangChain, RAG\n"
                               "PROJECTS\n- Built a to-do website"))
    assert not r.eligible
    assert any("skills/summary list" in x for x in r.rejection_reasons)


def test_python_only_in_education_does_not_count():
    r = check_eligibility(make("Jane Doe\nEDUCATION\nCoursework: Python, Algorithms\n"
                               "PROJECTS\n- Built a RAG app with LangChain in Java"))
    assert not r.eligible
    assert any("Python" in x for x in r.rejection_reasons)


def test_classical_ml_project_is_eligible():
    r = check_eligibility(make(
        "Jane Doe\nSKILLS\nPython\nPROJECTS\n- Trained a CNN image classifier in Python"))
    assert r.eligible


def test_llm_plus_framework_on_copilot_line_still_counts():
    r = check_eligibility(make(
        "Jane Doe\nSKILLS\nPython\nPROJECTS\n- Built a LangGraph agent, coded with Copilot help"))
    assert r.eligible