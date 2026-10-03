"""Cursor Cloud Agents API client. Injectable transport for tests."""
from __future__ import annotations

import base64
import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://api.cursor.com/v1/agents"

Fetch = Callable[[str, str, dict[str, Any] | None], dict[str, Any]]


def _auth_header(key: str) -> str:
    token = base64.b64encode(f"{key}:".encode("ascii")).decode("ascii")
    return f"Basic {token}"


def _parse_body(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    if text[:1] in "{[":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"events": parsed}
    events: list[Any] = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if not chunk or chunk == "[DONE]":
            continue
        try:
            item = json.loads(chunk)
        except json.JSONDecodeError:
            item = {"cmd": "sse", "excerpt": chunk[:400], "verdict": "UNKNOWN"}
        events.append(item)
    return {"events": events}


def default_fetch(
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    key: str,
    *,
    timeout: int = 60,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", _auth_header(key))
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "code": int(resp.status), "body": _parse_body(raw)}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        body = _parse_body(raw)
        if not body:
            body = {"error": raw[:200]}
        return {"ok": False, "code": int(exc.code), "body": body}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "code": 0, "body": {"error": str(exc)[:120]}}


class CloudClient:
    def __init__(self, key: str, fetch: Fetch | None = None):
        self.key = key
        self._fetch = fetch

    def call(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: int = 60,
    ) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{API}{path}"
        if self._fetch is not None:
            return self._fetch(method, url, payload)
        return default_fetch(method, url, payload, self.key, timeout=timeout)

    def create(self, prompt: str, repo: str, *, auto_pr: bool, name: str) -> dict[str, Any]:
        return self.call(
            "POST",
            "",
            {
                "prompt": {"text": prompt[:20000]},
                "name": name[:100],
                "repos": [{"url": repo, "startingRef": "main"}],
                "autoCreatePR": bool(auto_pr),
            },
        )

    def followup(self, agent_id: str, prompt: str) -> dict[str, Any]:
        return self.call("POST", f"/{agent_id}/followup", {"prompt": {"text": prompt[:20000]}})

    def followup_run(self, agent_id: str, prompt: str) -> dict[str, Any]:
        return self.call("POST", f"/{agent_id}/runs", {"prompt": {"text": prompt[:20000]}})

    def stream(self, agent_id: str, run_id: str) -> dict[str, Any]:
        if not agent_id or not run_id:
            return {"ok": True, "code": 200, "body": {"events": []}}
        return self.call("GET", f"/{agent_id}/runs/{run_id}/stream", None, timeout=15)

    def cancel(self, agent_id: str, run_id: str) -> dict[str, Any]:
        return self.call("POST", f"/{agent_id}/runs/{run_id}/cancel", {})

    def archive(self, agent_id: str) -> dict[str, Any]:
        return self.call("POST", f"/{agent_id}/archive", {})

    def unarchive(self, agent_id: str) -> dict[str, Any]:
        return self.call("POST", f"/{agent_id}/unarchive", {})


def busy_or_error(resp: dict[str, Any]) -> str:
    if resp.get("ok"):
        return ""
    code = int(resp.get("code") or 0)
    body = resp.get("body") if isinstance(resp.get("body"), dict) else {}
    err = str(body.get("error") or body.get("message") or "").lower()
    if code == 409 or "agent_busy" in err:
        return "cursor_api_busy"
    if code in (401, 403) and "key" in err:
        return "missing_CURSOR_API_KEY"
    return "conductor_timeout"


def extract_ids(resp: dict[str, Any]) -> tuple[str, str, str]:
    body = resp.get("body") if isinstance(resp.get("body"), dict) else {}
    agent = body.get("agent") if isinstance(body.get("agent"), dict) else body
    run = body.get("run") if isinstance(body.get("run"), dict) else {}
    agent_id = str(agent.get("id") or body.get("id") or "")[:80]
    run_id = str(run.get("id") or body.get("run_id") or agent.get("latestRunId") or "")[:80]
    url = str(agent.get("url") or body.get("url") or "")[:500]
    if agent_id and not url:
        url = f"https://cursor.com/agents/{agent_id}"
    return agent_id, run_id, url


def tests_from_stream(resp: dict[str, Any]) -> list[dict[str, str]]:
    body = resp.get("body")
    events: list[Any] = []
    if isinstance(body, dict):
        events = body.get("events") or body.get("items") or []
        if not events and body.get("cmd"):
            events = [body]
    if isinstance(body, list):
        events = body
    out: list[dict[str, str]] = []
    for item in events[:40]:
        if not isinstance(item, dict):
            continue
        event = str(item.get("type") or item.get("event") or "")
        payload = item.get("data") if isinstance(item.get("data"), dict) else item
        cmd = str(payload.get("cmd") or payload.get("command") or payload.get("name") or event)[:200]
        excerpt = str(payload.get("excerpt") or payload.get("output") or payload.get("text") or "")[:400]
        verdict = str(payload.get("verdict") or payload.get("status") or "UNKNOWN").upper()
        if verdict not in ("PASS", "FAIL", "UNKNOWN"):
            verdict = "UNKNOWN"
        if cmd or excerpt:
            out.append({"cmd": cmd or "tool_call", "excerpt": excerpt, "verdict": verdict})
    return out
