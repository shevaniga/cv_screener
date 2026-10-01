
from datetime import datetime, timedelta, timezone

import httpx

from src.config import (
    AI_CLASSICAL_TERMS, AI_STRONG_TERMS, GITHUB_MAINTAINED_DAYS,
    GITHUB_RECENT_DAYS, GITHUB_WINDOW_DAYS,
)
from src.matching import find_terms
from src.models import GitHubResult


class GitHubError(Exception):
    pass


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _get(client: httpx.Client, path: str, params: dict) -> list:
    response = client.get(path, params=params)
    if response.status_code == 404:
        raise GitHubError("GitHub user not found (wrong or private profile)")
    if response.status_code in (403, 429):
        raise GitHubError("GitHub API rate-limited or forbidden (set GITHUB_TOKEN to raise the limit)")
    if response.status_code >= 400:
        raise GitHubError(f"GitHub API returned HTTP {response.status_code}")
    return response.json()


def activity_score(events: list[dict], now: datetime) -> tuple[int, int]:
    """0-5 from public events. Returns (score, events_in_last_30_days)."""
    times = [_parse_time(e["created_at"]) for e in events if e.get("created_at")]
    recent = sum(1 for t in times if now - t <= timedelta(days=GITHUB_RECENT_DAYS))
    in_window = sum(1 for t in times if now - t <= timedelta(days=GITHUB_WINDOW_DAYS))
    if recent >= 5:
        return 5, recent
    if recent >= 1:
        return 4, recent
    if in_window >= 1:
        return 2, recent
    return 0, recent


def _is_relevant(repo: dict) -> bool:
    text = " ".join([repo.get("name") or "", repo.get("description") or "", *(repo.get("topics") or [])])
    return repo.get("language") == "Python" or bool(find_terms(text, AI_STRONG_TERMS + AI_CLASSICAL_TERMS))


def repo_score(repos: list[dict], now: datetime) -> tuple[int, int, int]:
    """0-5: up to 3 for maintained non-fork repos, up to 2 for Python/AI-relevant ones."""
    own = [r for r in repos if not r.get("fork")]
    maintained = [
        r for r in own
        if r.get("pushed_at") and now - _parse_time(r["pushed_at"]) <= timedelta(days=GITHUB_MAINTAINED_DAYS)
    ]
    relevant = [r for r in maintained if _is_relevant(r)]
    return min(len(maintained), 3) + min(len(relevant), 2), len(maintained), len(relevant)


def _fetch(username: str, client: httpx.Client) -> GitHubResult:
    now = datetime.now(timezone.utc)
    events = _get(client, f"/users/{username}/events/public", {"per_page": 100})
    repos = _get(client, f"/users/{username}/repos", {"per_page": 100, "sort": "pushed"})
    a_score, recent = activity_score(events, now)
    r_score, maintained, relevant = repo_score(repos, now)
    summary = (f"{recent} public events in the last {GITHUB_RECENT_DAYS} days; "
               f"{maintained} maintained non-fork repos, {relevant} Python/AI-relevant")
    return GitHubResult(status="ok", summary=summary, activity_score=a_score, repo_score=r_score)


def fetch_github(username: str, client: httpx.Client, cache: dict[str, GitHubResult]) -> GitHubResult:
    """Cached per run. Any failure becomes status='failed' instead of an exception."""
    key = username.lower()
    if key in cache:
        return cache[key]
    try:
        result = _fetch(username, client)
    except Exception as exc:  # deliberate: enrichment must never stop the batch
        message = str(exc) if isinstance(exc, GitHubError) else f"{type(exc).__name__}: {exc}"
        result = GitHubResult(status="failed", error=message,
                              summary="GitHub enrichment failed; screening continued without it")
    cache[key] = result
    return result