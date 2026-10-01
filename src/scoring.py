import re

from src.config import (
    AI_DEPTH_MARKERS,
    AI_WRAPPER_ONLY_TERMS,
    BACKEND_TERMS,
    CLASSICAL_ML_AI_CAP,
    CLOUD_TERMS,
    ENGINEERING_DEPTH_TERMS,
    FULLSTACK_SUPPORT_TERMS,
    LLM_MAX_ADJUST,
    NO_STRONG_AI_TOTAL_CAP,
    PYTHON_FRAMEWORKS,
    PYTHON_TERMS,
    THIN_WRAPPER_PENALTY,
    TUTORIAL_HINTS,
    TUTORIAL_PENALTY,
    WEAK_SECTIONS,
    WEIGHTS,
)
from src.eligibility import AIEvidence, classify_ai
from src.matching import Line, context_text, find_terms, resume_lines
from src.models import ParsedResume, ProjectJudgement, ScoreBreakdown, ScoringResult

METRIC_RE = re.compile(
    r"\d[\d,.]*\s*(?:%|ms\b|fps\b|x\b|\+|k\b|users|records|requests|queries|documents|files)",
    re.IGNORECASE,
)


def _snippet(section: str, text: str) -> str:
    return f"[{section}] {text[:160]}"


def _term_evidence(
    lines: list[Line],
    terms: list[str],
) -> dict[str, tuple[str, bool]]:
    found: dict[str, tuple[str, bool]] = {}

    for section, text in lines:
        weak = section in WEAK_SECTIONS

        for term in find_terms(text, terms):
            if term not in found or (found[term][1] and not weak):
                found[term] = (_snippet(section, text), weak)

    return found


def _points(
    found: dict,
    strong_pts: int,
    weak_pts: int,
    cap: int,
) -> int:
    return min(
        sum(
            strong_pts if not weak else weak_pts
            for _, weak in found.values()
        ),
        cap,
    )


def _score_ai(
    lines: list[Line],
    ai: AIEvidence,
) -> tuple[int, list[str], list[str]]:
    concerns: list[str] = []

    if ai.strong_idx:
        context = context_text(lines, ai.strong_idx)
        markers = find_terms(context, AI_DEPTH_MARKERS)

        wrapper_terms = [
            term
            for term in ai.strong_terms
            if term in AI_WRAPPER_ONLY_TERMS
        ]

        if wrapper_terms and not markers:
            concerns.append(
                f"-{THIN_WRAPPER_PENALTY}: AI project looks like a thin LLM/API wrapper "
                "(no retrieval, state, workflow or evaluation described)"
            )

            evidence = [
                _snippet(*lines[i])
                for i in ai.strong_idx[:3]
            ]

            return 0, evidence, concerns

        pts = min(len(ai.strong_terms), 4) * 5
        pts += min(len(markers), 4) * 4

        if METRIC_RE.search(context):
            pts += 4

        if find_terms(context, TUTORIAL_HINTS) or (
            len(context.split()) < 15
            and not METRIC_RE.search(context)
        ):
            pts -= TUTORIAL_PENALTY
            concerns.append(
                f"-{TUTORIAL_PENALTY}: AI project is listed with little implementation detail"
            )

        evidence = [
            _snippet(*lines[i])
            for i in ai.strong_idx[:3]
        ]

        return (
            max(
                0,
                min(
                    pts,
                    WEIGHTS["ai_project_depth"],
                ),
            ),
            evidence,
            concerns,
        )

    if ai.classical_idx:
        pts = min(
            CLASSICAL_ML_AI_CAP,
            5 + 3 * len(ai.classical_terms),
        )

        concerns.append(
            f"AI depth capped at {CLASSICAL_ML_AI_CAP}/40: "
            "classical ML only, no LLM/RAG/agent work"
        )

        return (
            pts,
            [
                _snippet(*lines[i])
                for i in ai.classical_idx[:3]
            ],
            concerns,
        )

    return 0, [], concerns


def score_candidate(
    resume: ParsedResume,
    github_points: int = 0,
    judgement: ProjectJudgement | None = None,
) -> ScoringResult:
    lines = resume_lines(resume)
    ai = classify_ai(lines)

    evidence: dict[str, list[str]] = {}
    strengths: list[str] = []
    concerns: list[str] = []

    ai_pts, ai_ev, ai_concerns = _score_ai(lines, ai)

    concerns += ai_concerns

    if judgement and (ai.strong_idx or ai.classical_idx):
        ceiling = (
            WEIGHTS["ai_project_depth"]
            if ai.strong_idx
            else CLASSICAL_ML_AI_CAP
        )

        delta = max(
            -LLM_MAX_ADJUST,
            min(
                LLM_MAX_ADJUST,
                judgement.ai_depth_score - ai_pts,
            ),
        )

        ai_pts = max(
            0,
            min(
                ceiling,
                ai_pts + delta,
            ),
        )

        evidence["llm_review"] = [
            f"{judgement.reason} | quote: {judgement.evidence_quote}"
        ]

        if judgement.is_thin_wrapper:
            concerns.append(
                "LLM review: AI project looks like a thin wrapper"
            )

    evidence["ai_project_depth"] = ai_ev

    if ai.strong_idx:
        strengths.append(
            "LLM/agentic work in projects or experience: "
            + ", ".join(sorted(ai.strong_terms))
        )

    py = _term_evidence(
        lines,
        PYTHON_TERMS + PYTHON_FRAMEWORKS,
    )

    py_in_work = any(
        not weak
        for _, weak in py.values()
    )

    py_pts = (
        12
        if py_in_work
        else (4 if py else 0)
    )

    backend = _term_evidence(
        lines,
        BACKEND_TERMS,
    )

    py_pts += _points(
        backend,
        3,
        1,
        18,
    )

    evidence["python_backend"] = list(
        dict.fromkeys(
            e
            for e, _ in list(py.values()) + list(backend.values())
        )
    )[:4]

    if py_in_work:
        strengths.append(
            "Python used in projects/work, not just listed as a skill"
        )
    elif py:
        concerns.append(
            "Python appears only in a skills list, not in any project or job"
        )

    work_backend = sorted(
        t
        for t, (_, weak) in backend.items()
        if not weak
    )

    if work_backend:
        strengths.append(
            "Backend tools used: "
            + ", ".join(work_backend)
        )
    else:
        concerns.append(
            "No backend tools (FastAPI, async, PostgreSQL, Redis) shown in projects/work"
        )

    cloud = _term_evidence(
        lines,
        CLOUD_TERMS,
    )

    fullstack = _term_evidence(
        lines,
        FULLSTACK_SUPPORT_TERMS,
    )

    cloud_pts = _points(
        cloud,
        3,
        1,
        12,
    )

    if any(
        not weak
        for _, weak in fullstack.values()
    ):
        cloud_pts += 3

    cloud_pts = min(
        cloud_pts,
        WEIGHTS["cloud_fullstack"],
    )

    evidence["cloud_fullstack"] = list(
        dict.fromkeys(
            e
            for e, _ in list(cloud.values()) + list(fullstack.values())
        )
    )[:4]

    if cloud_pts == 0:
        concerns.append(
            "No cloud/deployment evidence"
        )

    depth = _term_evidence(
        lines,
        ENGINEERING_DEPTH_TERMS,
    )

    depth_pts = min(
        sum(
            1
            for _, weak in depth.values()
            if not weak
        ),
        WEIGHTS["engineering_depth"],
    )

    evidence["engineering_depth"] = [
        e
        for e, _ in depth.values()
    ][:4]

    breakdown = ScoreBreakdown(
        ai_project_depth=ai_pts,
        python_backend=min(
            py_pts,
            WEIGHTS["python_backend"],
        ),
        cloud_fullstack=cloud_pts,
        github=github_points,
        engineering_depth=depth_pts,
    )

    total = breakdown.total()

    if not ai.strong_idx and total > NO_STRONG_AI_TOTAL_CAP:
        total = NO_STRONG_AI_TOTAL_CAP

        concerns.append(
            f"Total capped at {NO_STRONG_AI_TOTAL_CAP}: "
            "no LLM/RAG/agentic project evidence"
        )

    summary = (
        ai_ev[0]
        if ai_ev
        else "No AI project evidence found"
    )

    return ScoringResult(
        breakdown=breakdown,
        total_score=total,
        evidence=evidence,
        strengths=strengths,
        concerns=concerns,
        project_summary=summary,
    )