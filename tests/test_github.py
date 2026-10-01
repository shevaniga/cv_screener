from datetime import datetime, timedelta, timezone

import httpx

from src.github import fetch_github


def iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.github.com")


def active_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/events/public"):
        return httpx.Response(200, json=[{"created_at": iso(2)} for _ in range(6)])
    repos = [
        {"name": "rag-bot", "fork": False, "pushed_at": iso(10), "language": "Python", "description": None, "topics": []},
        {"name": "site", "fork": False, "pushed_at": iso(40), "language": "JavaScript", "description": "portfolio", "topics": []},
        {"name": "api", "fork": False, "pushed_at": iso(100), "language": "Python", "description": None, "topics": []},
        {"name": "forked", "fork": True, "pushed_at": iso(1), "language": "Python", "description": None, "topics": []},
    ]
    return httpx.Response(200, json=repos)


def test_active_user_gets_full_score():
    r = fetch_github("asha", make_client(active_handler), {})
    assert r.status == "ok"
    assert r.activity_score == 5
    assert r.repo_score == 5   
    assert "6 public events" in r.summary


def test_stale_user_scores_zero_but_is_ok():
    def handler(request):
        if request.url.path.endswith("/events/public"):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{"name": "old", "fork": False, "pushed_at": iso(900),
                                          "language": "Python", "description": None, "topics": []}])
    r = fetch_github("old", make_client(handler), {})
    assert r.status == "ok" and r.activity_score == 0 and r.repo_score == 0


def test_user_not_found_is_recorded_not_raised():
    r = fetch_github("nobody", make_client(lambda req: httpx.Response(404, json={})), {})
    assert r.status == "failed" and "not found" in r.error


def test_rate_limit_is_recorded_not_raised():
    r = fetch_github("x", make_client(lambda req: httpx.Response(403, json={})), {})
    assert r.status == "failed" and "rate-limited" in r.error


def test_network_error_is_recorded_not_raised():
    def handler(request):
        raise httpx.ConnectError("boom")
    r = fetch_github("x", make_client(handler), {})
    assert r.status == "failed"


def test_cache_avoids_repeat_calls():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return active_handler(request)
    client, cache = make_client(handler), {}
    fetch_github("Asha", client, cache)
    n = len(calls)
    fetch_github("asha", client, cache)   
    assert len(calls) == n