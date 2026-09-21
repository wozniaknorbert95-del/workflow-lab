"""GitHub write path: comment @cursor + squash merge. No Actions dispatch."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

from .policy import ALLOWED_REPOS, allow_deploy, allow_merge, has_workflow_dispatch_deploy

GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")
WRITE_TOKEN = os.environ.get("GITHUB_OPS_WRITE", "")
OWNER = os.environ.get("GITHUB_OPS_OWNER", "wozniaknorbert95-del")


class GitHubOps:
    def __init__(self, token: str | None = None, fetch: Callable | None = None) -> None:
        self.token = (token if token is not None else WRITE_TOKEN).strip()
        self.fetch = fetch

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def comment_cursor(self, repo: str, issue_number: int, body: str = "@cursor") -> dict[str, Any]:
        if repo not in ALLOWED_REPOS:
            return {"ok": False, "code": 403, "error": "repo_not_in_policy"}
        if "@cursor" not in body:
            body = "@cursor\n" + body
        return self._post(f"/repos/{OWNER}/{repo}/issues/{issue_number}/comments", {"body": body})

    def merge_pull(self, repo: str, pull_number: int, checks_green: bool, issue: dict | None = None) -> dict[str, Any]:
        ok, code, reason = allow_merge(repo, checks_green, issue)
        if not ok:
            return {"ok": False, "code": code, "error": reason}
        payload = {"merge_method": "squash"}
        return self._put(f"/repos/{OWNER}/{repo}/pulls/{pull_number}/merge", payload)

    def workflow_dispatch(self, *_a: Any, **_k: Any) -> dict[str, Any]:
        ok, code, reason = allow_deploy("workflow_dispatch")
        return {"ok": ok, "code": code, "error": reason, "exists": has_workflow_dispatch_deploy()}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, payload)

    def _put(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", path, payload)

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.fetch:
            return self.fetch(method, path, payload)
        if not self.token:
            return {"ok": False, "code": 401, "error": "missing GITHUB_OPS_WRITE"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GITHUB_API + path,
            data=data,
            headers={**self._headers(), "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw) if raw else {}
                return {"ok": True, "code": resp.status, "body": body}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "code": exc.code, "error": f"http_{exc.code}"}
        except Exception as exc:
            return {"ok": False, "code": 599, "error": type(exc).__name__}
