import re
from functools import lru_cache

from src.config import IGNORED_SECTIONS
from src.models import ParsedResume

Line = tuple[str, str]


@lru_cache(maxsize=None)
def _pattern(term: str) -> re.Pattern:
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(term)}s?(?![A-Za-z0-9])",
        re.IGNORECASE,
    )


def find_terms(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if _pattern(t).search(text)]


def resume_lines(resume: ParsedResume) -> list[Line]:
    sections = resume.sections or {"other": resume.text}
    lines: list[Line] = []

    for section, body in sections.items():
        if section in IGNORED_SECTIONS:
            continue

        for line in body.split("\n"):
            if line.strip():
                lines.append((section, line.strip()))

    return lines


def context_text(
    lines: list[Line],
    indexes: list[int],
    before: int = 2,
    after: int = 2,
) -> str:
    keep: set[int] = set()

    for i in indexes:
        section = lines[i][0]

        for j in range(
            max(0, i - before),
            min(len(lines), i + after + 1),
        ):
            if lines[j][0] == section:
                keep.add(j)

    return " ".join(lines[j][1] for j in sorted(keep))