
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from src.config import (
    GITHUB_API, GITHUB_TIMEOUT, GITHUB_TOKEN, GITHUB_WORKERS, LLM_API_KEY,
    LLM_MODEL, LLM_TIMEOUT, LLM_WORKERS,
)
from src.eligibility import check_eligibility
from src.extract import extract_fields
from src.github import fetch_github
from src.ingest import load_resumes
from src.llm import judge_resume
from src.models import CandidateResult, EligibilityResult, GitHubResult, ParsedResume
from src.scoring import score_candidate


def _github_url(resume: ParsedResume) -> str | None:
    return f"https://github.com/{resume.github_username}" if resume.github_username else None


def _rejected(resume: ParsedResume, elig: EligibilityResult) -> CandidateResult:
    return CandidateResult(
        candidate_name=elig.candidate, file_name=resume.file_name, email=resume.email,
        github_url=_github_url(resume), eligible=False,
        matched_skills=elig.matched_skills, rejection_reasons=elig.rejection_reasons,
    )


def _github_for_all(resumes: list[ParsedResume], enabled: bool) -> list[GitHubResult]:
    if not enabled:
        return [GitHubResult(status="skipped", summary="GitHub enrichment disabled") for _ in resumes]
    cache: dict[str, GitHubResult] = {}
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    with httpx.Client(base_url=GITHUB_API, headers=headers, timeout=GITHUB_TIMEOUT) as client:
        def task(r: ParsedResume) -> GitHubResult:
            if not r.github_username:
                return GitHubResult(status="no_profile", summary="No GitHub profile found on resume")
            return fetch_github(r.github_username, client, cache)
        with ThreadPoolExecutor(max_workers=GITHUB_WORKERS) as pool:
            return list(pool.map(task, resumes))


def _llm_for_all(resumes: list[ParsedResume], enabled: bool):
    if not enabled:
        return [(None, "skipped: disabled") for _ in resumes]
    with httpx.Client(timeout=LLM_TIMEOUT) as client:
        with ThreadPoolExecutor(max_workers=LLM_WORKERS) as pool:
            return list(pool.map(lambda r: judge_resume(r, client, LLM_API_KEY, LLM_MODEL), resumes))


def run_pipeline(input_dir: Path, use_github: bool = True, use_llm: bool = True) -> dict:
    resumes, duplicates = load_resumes(input_dir)
    failed: list[dict] = []
    rejected: list[CandidateResult] = []
    eligible: list[tuple[ParsedResume, EligibilityResult]] = []

    for resume in resumes:
        if resume.parse_error:
            failed.append({"file_name": resume.file_name, "error": resume.parse_error})
            continue
        try:  # one unexpected bug on one resume must not stop the batch
            extract_fields(resume)
            elig = check_eligibility(resume)
        except Exception as exc:
            failed.append({"file_name": resume.file_name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if elig.eligible:
            eligible.append((resume, elig))
        else:
            rejected.append(_rejected(resume, elig))

    people = [r for r, _ in eligible]
    github_results = _github_for_all(people, use_github)
    llm_results = _llm_for_all(people, use_llm)

    ranked: list[CandidateResult] = []
    for (resume, elig), gh, (judgement, llm_status) in zip(eligible, github_results, llm_results):
        try:
            scoring = score_candidate(resume, gh.activity_score + gh.repo_score, judgement)
        except Exception as exc:
            failed.append({"file_name": resume.file_name, "error": f"Scoring failed: {type(exc).__name__}: {exc}"})
            continue
        ranked.append(CandidateResult(
            candidate_name=elig.candidate, file_name=resume.file_name, email=resume.email,
            github_url=_github_url(resume), eligible=True, total_score=scoring.total_score,
            score_breakdown=scoring.breakdown, matched_skills=elig.matched_skills,
            project_summary=scoring.project_summary,
            github_summary=gh.summary if gh.status != "failed" else f"{gh.summary} ({gh.error})",
            github_status=gh.status, llm_status=llm_status,
            strengths=scoring.strengths, concerns=scoring.concerns,
            evidence={"eligibility": elig.evidence, **scoring.evidence},
        ))

    ranked.sort(key=lambda c: (-c.total_score, -c.score_breakdown.ai_project_depth, c.candidate_name.lower()))
    for position, candidate in enumerate(ranked, start=1):
        candidate.rank = position

    parse_failures = sum(1 for r in resumes if r.parse_error)
    return {
        "batch_summary": {
            "total_resumes": len(resumes) + len(duplicates),
            "duplicates_skipped": len(duplicates),
            "successfully_parsed": len(resumes) - parse_failures,
            "eligible": len(ranked),
            "rejected": len(rejected),
            "failed_or_unreadable": len(failed),
        },
        "ranked_candidates": [c.model_dump() for c in ranked],
        "rejected_candidates": [c.model_dump() for c in rejected],
        "failed_resumes": failed,
        "duplicates_skipped": duplicates,
    }


def write_results(results: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")