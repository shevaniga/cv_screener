import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from src.config import MIN_TEXT_CHARS
from src.models import ParsedResume

SUPPORTED_EXTENSIONS = {".pdf"}


def find_resume_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Input folder not found: {folder}")

    files = [
        p
        for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
        and not p.name.startswith((".", "~$"))
    ]

    return sorted(files)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_text(raw: str) -> str:
    text = raw.replace("\x00", "")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_pdf(path: Path) -> tuple[str, list[str]]:
    reader = PdfReader(path)

    pages_text: list[str] = []
    links: list[str] = []

    for page in reader.pages:
        pages_text.append(page.extract_text() or "")

        for annot in page.get("/Annots") or []:
            action = annot.get_object().get("/A")

            if action is not None:
                uri = action.get_object().get("/URI")

                if uri:
                    links.append(str(uri))

    return "\n".join(pages_text), list(dict.fromkeys(links))


def parse_resume(path: Path) -> ParsedResume:
    result = ParsedResume(file_name=path.name)

    try:
        result.file_hash = file_hash(path)

        raw, links = extract_pdf(path)

        result.text = clean_text(raw)
        result.links = links

        if len(result.text) < MIN_TEXT_CHARS:
            result.parse_error = (
                f"Extracted text too short: {len(result.text)} "
                f"characters; minimum is {MIN_TEXT_CHARS}"
            )

    except Exception as exc:
        result.parse_error = f"{type(exc).__name__}: {exc}"

    return result


def load_resumes(folder: Path) -> tuple[list[ParsedResume], list[str]]:
    resumes: list[ParsedResume] = []
    skipped: list[str] = []
    seen: dict[str, str] = {}

    for path in find_resume_files(folder):
        parsed = parse_resume(path)

        if parsed.file_hash and parsed.file_hash in seen:
            skipped.append(
                f"{path.name} skipped: duplicate of {seen[parsed.file_hash]}"
            )
            continue

        if parsed.file_hash:
            seen[parsed.file_hash] = path.name

        resumes.append(parsed)

    return resumes, skipped