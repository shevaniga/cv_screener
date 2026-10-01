
import re
from collections import Counter

from src.config import GITHUB_RESERVED_PATHS, NON_NAME_WORDS, SECTION_ALIASES
from src.models import ParsedResume

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GITHUB_RE = re.compile(
    r"(?<![\w.-])(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})",
    re.IGNORECASE,
)
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z.'-]*(?: [A-Za-z][A-Za-z.'-]*){1,3}$")

HEADING_TO_SECTION = {
    alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases
}

def extract_email(resume: ParsedResume) -> str | None:
    for link in resume.links:
        if link.lower().startswith("mailto:"):
            found = EMAIL_RE.search(link[len("mailto:"):])
            if found:
                return found.group(0).lower()
    found = EMAIL_RE.search(resume.text)
    return found.group(0).lower() if found else None

def extract_github_username(resume: ParsedResume) -> str | None:
    for haystack in (" ".join(resume.links), resume.text):
        names = [
            m.group(1)
            for m in GITHUB_RE.finditer(haystack)
            if m.group(1).lower() not in GITHUB_RESERVED_PATHS
        ]
        if names:
            return Counter(names).most_common(1)[0][0]  
    return None

def extract_name(text: str) -> str | None:
    lines = [line.strip() for line in text.split("\n") if line.strip()][:6]
    for line in lines:
        words = line.lower().split()
        if (
            NAME_RE.match(line)
            and not NON_NAME_WORDS.intersection(words)
            and line.lower() not in HEADING_TO_SECTION
        ):
            return line
    return None

def _normalize(line: str) -> str:
    return line.strip().rstrip(":").strip().lower()


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.split("\n"):
        key = HEADING_TO_SECTION.get(_normalize(line))
        if key:
            current = key
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "".join(v).strip()}

def extract_fields(resume: ParsedResume) -> ParsedResume:
    if resume.parse_error:  
        return resume
    resume.email = extract_email(resume)
    resume.github_username = extract_github_username(resume)
    resume.name = extract_name(resume.text)
    resume.sections = split_sections(resume.text)
    return resume