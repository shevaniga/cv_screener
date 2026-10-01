from dataclasses import dataclass, field
from pathlib import Path

from src.config import (
    AI_CLASSICAL_TERMS, AI_GENERIC_TERMS, AI_STRONG_TERMS, AI_TOOL_TERMS,
    AI_VAGUE_TERMS, ALLOW_CLASSICAL_ML_ELIGIBLE, PYTHON_FRAMEWORKS,
    PYTHON_TERMS, SKILL_VOCAB, WEAK_SECTIONS,
)
from src.matching import Line, find_terms, resume_lines
from src.models import EligibilityResult, ParsedResume


@dataclass
class AIEvidence:
    strong_idx: list[int] = field(default_factory=list)
    classical_idx: list[int] = field(default_factory=list)
    strong_terms: set[str] = field(default_factory=set)
    classical_terms: set[str] = field(default_factory=set)
    weak_only_terms: set[str] = field(default_factory=set)
    vague_terms: set[str] = field(default_factory=set)
    tool_seen: bool = False


def classify_ai(lines: list[Line]) -> AIEvidence:
    ev = AIEvidence()
    for i, (section, text) in enumerate(lines):
        strong = find_terms(text, AI_STRONG_TERMS)
        classical = find_terms(text, AI_CLASSICAL_TERMS)
        ev.vague_terms.update(find_terms(text, AI_VAGUE_TERMS))
        if find_terms(text, AI_TOOL_TERMS):
            ev.tool_seen = True
            strong = [t for t in strong if t not in AI_GENERIC_TERMS]
            classical = []
        if section in WEAK_SECTIONS:
            ev.weak_only_terms.update(strong + classical)
            continue
        if strong:
            ev.strong_idx.append(i)
            ev.strong_terms.update(strong)
        if classical:
            ev.classical_idx.append(i)
            ev.classical_terms.update(classical)
    return ev


def _snippet(line: Line) -> str:
    return f"[{line[0]}] {line[1][:160]}"


def _ai_rejection_reason(ev: AIEvidence) -> str:
    if ev.weak_only_terms:
        terms = ", ".join(sorted(ev.weak_only_terms))
        return (
            f"AI terms ({terms}) appear only in a skills/summary list, "
            "with no project or work evidence"
        )
    if ev.vague_terms:
        terms = ", ".join(sorted(ev.vague_terms))
        return (
            f"AI claims are vague ('{terms}'): no LLM, RAG, agent or ML "
            "framework is named"
        )
    if ev.tool_seen:
        return "AI appears only as a coding tool (e.g. Copilot), not as a project"
    return "No AI/agentic project evidence"


def check_eligibility(resume: ParsedResume) -> EligibilityResult:
    lines = resume_lines(resume)
    name = resume.name or Path(resume.file_name).stem
    python_idx = [
        i
        for i, (_, t) in enumerate(lines)
        if find_terms(t, PYTHON_TERMS + PYTHON_FRAMEWORKS)
    ]
    ai = classify_ai(lines)
    has_ai = bool(ai.strong_idx) or (
        ALLOW_CLASSICAL_ML_ELIGIBLE and bool(ai.classical_idx)
    )

    reasons: list[str] = []
    if not python_idx:
        reasons.append(
            "No evidence of Python (as a skill, project or work technology)"
        )
    if not has_ai:
        reasons.append(_ai_rejection_reason(ai))

    all_text = "\n".join(t for _, t in lines)
    skills = find_terms(all_text, SKILL_VOCAB)
    skills += sorted(
        ai.strong_terms | ai.classical_terms | ai.weak_only_terms
    )

    evidence: list[str] = []
    if not reasons:
        evidence.append(_snippet(lines[python_idx[0]]))
        ai_idx = ai.strong_idx or ai.classical_idx
        evidence += [_snippet(lines[i]) for i in ai_idx[:2]]

    return EligibilityResult(
        candidate=name,
        eligible=not reasons,
        rejection_reasons=reasons,
        matched_skills=list(dict.fromkeys(skills)),
        evidence=evidence,
    )