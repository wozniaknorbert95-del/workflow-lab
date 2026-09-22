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

    def create_issue(self, repo: str, title: str, body: str, labels: list[str] | None = None) -> dict[str, Any]:
        if repo not in ALLOWED_REPOS:
            return {"ok": False, "code": 403, "error": "repo_not_in_policy"}
        payload: dict[str, Any] = {"title": title[:240], "body": body[:6000]}
        if labels:
            payload["labels"] = labels[:10]
        return self._post(f"/repos/{OWNER}/{repo}/issues", payload)

    def find_open_issue_by_marker(self, repo: str, marker: str) -> dict[str, Any]:
        """Find open issue whose title contains Linear id (e.g. QUI-70)."""
        if repo not in ALLOWED_REPOS or not marker:
            return {"ok": False, "code": 400, "error": "bad_args"}
        q = f'repo:{OWNER}/{repo} is:issue is:open in:title "{marker}"'
        from urllib.parse import quote

        return self._get(f"/search/issues?q={quote(q)}&per_page=5")

    def ensure_cursor_trigger(self, repo: str, issue: dict[str, Any]) -> dict[str, Any]:
        """E4: guarantee a GitHub issue exists, then comment @cursor (B8 automation path).

        Linear queue often has github_number=0 (no PR attachment yet). Without this,
        run_next skipped @cursor forever — root cause of QUI-70 'agent never started'.
        """
        if repo not in ALLOWED_REPOS:
            return {"ok": False, "code": 403, "error": "repo_not_in_policy"}
        if not self.token and not self.fetch:
            return {"ok": False, "code": 401, "error": "missing GITHUB_OPS_WRITE"}
        linear_id = str(issue.get("id") or issue.get("identifier") or "").strip()
        title = str(issue.get("title") or linear_id or "Hermes Ops task").strip()
        number = int(issue.get("github_number") or 0)
        created = False
        if number <= 0 and linear_id:
            found = self.find_open_issue_by_marker(repo, linear_id)
            items = ((found.get("body") or {}).get("items") if found.get("ok") else None) or []
            if items:
                number = int(items[0].get("number") or 0)
        if number <= 0:
            body = (
                f"Hermes Ops (Linear-first)\n\n"
                f"- Linear: {linear_id or '?'}\n"
                f"- URL: {issue.get('url') or ''}\n"
                f"- Repo: {repo}\n\n"
                f"Automation: label `agent` + this comment starts Cloud Agent.\n"
                f"Do not deploy. Merge after green CI.\n"
            )
            gh_title = f"[{linear_id}] {title}" if linear_id else title
            created_res = self.create_issue(repo, gh_title, body, labels=["agent"])
            if not created_res.get("ok"):
                return {
                    "ok": False,
                    "code": created_res.get("code") or 599,
                    "error": created_res.get("error") or "create_issue_failed",
                }
            number = int(((created_res.get("body") or {}).get("number")) or 0)
            created = True
            if number <= 0:
                return {"ok": False, "code": 599, "error": "create_issue_no_number"}
        comment_body = f"@cursor\n\nLinear `{linear_id}` — Hermes Ops Start/Run next."
        commented = self.comment_cursor(repo, number, comment_body)
        if not commented.get("ok"):
            return {
                "ok": False,
                "code": commented.get("code") or 599,
                "error": commented.get("error") or "comment_failed",
                "issue_number": number,
                "created": created,
            }
        return {
            "ok": True,
            "issue_number": number,
            "created": created,
            "commented": True,
            "html_url": ((commented.get("body") or {}).get("html_url") or ""),
        }

    def merge_pull(self, repo: str, pull_number: int, checks_green: bool, issue: dict | None = None) -> dict[str, Any]:
        ok, code, reason = allow_merge(repo, checks_green, issue)
        if not ok:
            return {"ok": False, "code": code, "error": reason}
        payload = {"merge_method": "squash"}
        return self._put(f"/repos/{OWNER}/{repo}/pulls/{pull_number}/merge", payload)

    def workflow_dispatch(self, *_a: Any, **_k: Any) -> dict[str, Any]:
        ok, code, reason = allow_deploy("workflow_dispatch")
        return {"ok": ok, "code": code, "error": reason, "exists": has_workflow_dispatch_deploy()}

    def _get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path, None)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, payload)

    def _put(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", path, payload)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        if self.fetch:
            return self.fetch(method, path, payload or {})
        if not self.token:
            return {"ok": False, "code": 401, "error": "missing GITHUB_OPS_WRITE"}
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {**self._headers()}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            GITHUB_API + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw) if raw else {}
                return {"ok": True, "code": resp.status, "body": body}
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8")[:200]
            except Exception:
                pass
            return {"ok": False, "code": exc.code, "error": f"http_{exc.code}", "detail": err_body}
        except Exception as exc:
            return {"ok": False, "code": 599, "error": type(exc).__name__}
