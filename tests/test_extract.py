from src.extract import (
    extract_email, extract_github_username, extract_name, split_sections,
)
from src.models import ParsedResume


def resume(text="", links=None):
    return ParsedResume(file_name="x.pdf", text=text, links=links or [])


def test_email_prefers_mailto_link():
    r = resume("Agam # wrong@junk.com", ["mailto:jainagam4@gmail.com"])
    assert extract_email(r) == "jainagam4@gmail.com"


def test_email_from_text_and_missing():
    assert extract_email(resume("Email: a.b@x.com |")) == "a.b@x.com"
    assert extract_email(resume("no contact here")) is None


def test_github_repo_link_gives_profile_username():
    links = ["https://github.com/AgamJain05/QuickRevise", "https://github.com/AgamJain05"]
    assert extract_github_username(resume(links=links)) == "AgamJain05"


def test_github_lookalikes_are_ignored():
    assert extract_github_username(resume("agamjain.github.io/portfolio")) is None
    assert extract_github_username(resume("github.com/features/copilot")) is None
    assert extract_github_username(resume("notgithub.com/foo")) is None


def test_name_is_first_name_like_line():
    assert extract_name("SHIVAM RAJ\nAssociate Software Engineer | React.js") == "SHIVAM RAJ"
    assert extract_name("Curriculum Vitae\nJane Doe\njane@x.com") == "Jane Doe"
    assert extract_name("12345\n@@@") is None


def test_sections_split_on_headings():
    text = "Jane Doe\nSKILLS\nPython, FastAPI\nProjects:\nBuilt RAG bot\nEXPERIENCE\nIntern at X"
    s = split_sections(text)
    assert s["header"] == "Jane Doe"
    assert s["skills"] == "Python, FastAPI"
    assert s["projects"] == "Built RAG bot"
    assert s["experience"] == "Intern at X"


def test_email_typo_in_link_is_ignored():
    r = resume("kartikay.sinha17@gmail.com", ["mailto:kartikay.sinhal7@gmail.com"])
    assert extract_email(r) == "kartikay.sinha17@gmail.com"