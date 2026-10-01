import json
from pathlib import Path

from reportlab.pdfgen import canvas

from src.pipeline import run_pipeline, write_results


def make_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path))
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 16
    c.save()


AGENT = ["Asha Rao", "asha@example.com", "SKILLS", "Python, FastAPI, PostgreSQL", "PROJECTS",
         "Support Agent | Python, LangGraph, FastAPI, Redis, Docker",
         "- Built a stateful multi-agent workflow with retrieval over 2,000 documents and tool calling",
         "- Added pytest evaluation suite, Redis caching and retry logic; deployed on GCP with Docker"]
CNN = ["Ben Ito", "ben@example.com", "SKILLS", "Python, Flask", "PROJECTS",
       "- Trained a CNN image classifier in Python and deployed it with Flask for a class project"]
JAVA = ["Carl Java", "carl@example.com", "SKILLS", "Java, JavaScript, React, Spring Boot", "PROJECTS",
        "- Built an online shop with React and Spring Boot for 500+ users"]


def test_full_batch_with_good_bad_corrupt_and_duplicate(tmp_path):
    make_pdf(tmp_path / "a_agent.pdf", AGENT)
    (tmp_path / "b_agent_copy.pdf").write_bytes((tmp_path / "a_agent.pdf").read_bytes())
    make_pdf(tmp_path / "c_cnn.pdf", CNN)
    make_pdf(tmp_path / "d_java.pdf", JAVA)
    (tmp_path / "e_corrupt.pdf").write_bytes(b"not a pdf")

    results = run_pipeline(tmp_path, use_github=False, use_llm=False)
    s = results["batch_summary"]
    assert s == {"total_resumes": 5, "duplicates_skipped": 1, "successfully_parsed": 3,
                 "eligible": 2, "rejected": 1, "failed_or_unreadable": 1}

    ranked = results["ranked_candidates"]
    assert [c["candidate_name"] for c in ranked] == ["Asha Rao", "Ben Ito"]
    assert [c["rank"] for c in ranked] == [1, 2]
    assert ranked[0]["total_score"] > ranked[1]["total_score"]
    assert ranked[0]["evidence"]["ai_project_depth"]

    assert results["rejected_candidates"][0]["candidate_name"] == "Carl Java"
    assert any("Python" in r for r in results["rejected_candidates"][0]["rejection_reasons"])
    assert results["failed_resumes"][0]["file_name"] == "e_corrupt.pdf"


def test_results_json_is_written_and_valid(tmp_path):
    make_pdf(tmp_path / "a.pdf", AGENT)
    out = tmp_path / "out" / "results.json"
    write_results(run_pipeline(tmp_path, use_github=False, use_llm=False), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data) == {"batch_summary", "ranked_candidates", "rejected_candidates",
                         "failed_resumes", "duplicates_skipped"}
    assert data["ranked_candidates"][0]["score_breakdown"]["github"] == 0