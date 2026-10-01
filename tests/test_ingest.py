from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from src.ingest import load_resumes

GOOD = "Jane Doe Python developer building LangChain RAG agents with FastAPI"


def make_pdf(path: Path, text: str) -> None:
    c = canvas.Canvas(str(path))
    c.drawString(72, 750, text)
    c.save()


def test_corrupt_pdf_does_not_crash(tmp_path):
    (tmp_path / "bad.pdf").write_bytes(b"this is not a pdf")
    resumes, _ = load_resumes(tmp_path)
    assert len(resumes) == 1
    assert resumes[0].parse_error is not None


def test_good_file_survives_next_to_bad_one(tmp_path):
    (tmp_path / "a_bad.pdf").write_bytes(b"garbage")
    make_pdf(tmp_path / "b_good.pdf", GOOD)
    resumes, _ = load_resumes(tmp_path)
    good = [r for r in resumes if r.file_name == "b_good.pdf"][0]
    assert good.parse_error is None
    assert "Python" in good.text


def test_duplicate_is_skipped(tmp_path):
    make_pdf(tmp_path / "a.pdf", GOOD)
    (tmp_path / "b.pdf").write_bytes((tmp_path / "a.pdf").read_bytes())
    resumes, skipped = load_resumes(tmp_path)
    assert len(resumes) == 1
    assert len(skipped) == 1


def test_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_resumes(tmp_path / "nope")