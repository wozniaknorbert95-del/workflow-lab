"""GitHub evidence for phone-loop-status (stdlib, read-only)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_REPO = "wozniaknorbert95-del/workflow-lab"


def api_get(path: str, token: str = "") -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "workflow-lab-phone-loop/1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def token_from_env_file(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("GITHUB_ENGINEER_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def build_live_payload(
    *,
    repo: str = DEFAULT_REPO,
    issue_number: int | None = None,
    pr_number: int | None = None,
    token: str = "",
) -> dict[str, Any]:
    owner, name = repo.split("/", 1)
    linear: dict[str, Any] = {
        "issue_id": str(issue_number or pr_number or "?"),
        "six_fields": bool(issue_number or pr_number),
        "agent_label": True,
    }
    github: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    review: dict[str, Any] = {}
    merge: dict[str, Any] = {}

    try:
        if not pr_number and issue_number:
            issue = api_get(f"/repos/{owner}/{name}/issues/{issue_number}", token)
            labels = [x.get("name", "") for x in issue.get("labels") or []]
            linear["agent_label"] = any("agent" in (lb or "").lower() for lb in labels)
            pulls = api_get(
                f"/repos/{owner}/{name}/issues/{issue_number}/events?per_page=30", token
            )
            for ev in pulls:
                if ev.get("event") == "cross-referenced":
                    pass
            pr_number = pr_number or issue_number

        if pr_number:
            pr = api_get(f"/repos/{owner}/{name}/pulls/{pr_number}", token)
            github["pr_url"] = pr.get("html_url") or ""
            github["head_ref"] = (pr.get("head") or {}).get("ref") or ""
            github["draft"] = bool(pr.get("draft"))
            comments = api_get(f"/repos/{owner}/{name}/issues/{pr['number']}/comments", token)
            github["cursor_comment"] = any(
                "@cursor" in (c.get("body") or "").lower() for c in comments
            )
            # E5: scrape real agent run URL from comments (fail-closed — never invent).
            agent = {"provider": "", "run_url": "", "model": "", "run_id": ""}
            recent = []
            for c in comments[-15:]:
                body = c.get("body") or ""
                recent.append(
                    {
                        "at": c.get("created_at") or "",
                        "text": (body[:120] + ("…" if len(body) > 120 else "")),
                    }
                )
                for token_url in body.replace(")", " ").replace("(", " ").split():
                    low = token_url.lower()
                    if "cursor.com" in low and ("/agents" in low or "/agent" in low):
                        if low.startswith("http"):
                            agent["run_url"] = token_url.strip(".,;")
                            agent["provider"] = "cursor-cloud"
                            if "/agents/" in low:
                                agent["run_id"] = token_url.rstrip("/").split("/")[-1][:80]
            github["agent"] = agent
            github["recent"] = recent[-8:]
            sha = (pr.get("head") or {}).get("sha") or ""
            if sha:
                cr = api_get(
                    f"/repos/{owner}/{name}/commits/{sha}/check-runs?per_page=100", token
                )
                runs = cr.get("check_runs") or []
                names = {r.get("name"): r.get("conclusion") for r in runs}
                checks["validate"] = names.get("validate") or "skipped"
                checks["execute"] = (
                    names.get("execute")
                    or names.get("phone-loop-guard")
                    or ("success" if names.get("validate") == "success" else "skipped")
                )
                checks["jobs_ran_steps"] = any(
                    r.get("conclusion") == "success" and r.get("name")
                    for r in runs
                )
                for r in runs:
                    html = r.get("html_url") or ""
                    if html and r.get("name") == "validate":
                        github["ci_url"] = html
                        break
                if not github.get("ci_url"):
                    for r in runs:
                        if r.get("html_url"):
                            github["ci_url"] = r.get("html_url")
                            break
            try:
                files = api_get(f"/repos/{owner}/{name}/pulls/{pr['number']}/files?per_page=100", token)
                if isinstance(files, list):
                    github["diff"] = {
                        "files": len(files),
                        "summary": ", ".join(
                            (f.get("filename") or "")[:40] for f in files[:5]
                        ),
                    }
            except Exception:
                pass
            review["approved"] = bool(pr.get("merged") or pr.get("merge_commit_sha"))
            merge["squash_on_main"] = bool(pr.get("merged"))
            merge["draft"] = bool(pr.get("draft"))
            merge["sha"] = (pr.get("merge_commit_sha") or "")[:40]
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            github["missing_token"] = True
            checks["missing_token"] = True
            merge["missing_token"] = True
        else:
            raise

    return {
        "linear": linear,
        "github": github,
        "checks": checks,
        "review": review,
        "merge": merge,
        "ttl_minutes": 15,
    }
