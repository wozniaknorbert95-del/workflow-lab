"""Linear read path — queue only. Issue description is OFF (injection)."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

LINEAR_API = os.environ.get("LINEAR_API", "https://api.linear.app/graphql")
READ_TOKEN = os.environ.get("LINEAR_OPS_READ", "")
PROJECT_NAMES = ("workflow-lab", "dsaas-platform-main")
PROJECT_REPO = {
    "workflow-lab": "workflow-lab",
    "dsaas-platform-main": "dsaas-platform-main",
}
GITHUB_PULL_RX = re.compile(r"github\.com/[^/]+/([^/]+)/pull/(\d+)", re.I)

QUEUE_QUERY = """
query OpsQueue($first: Int!, $names: [String!]!) {
  issues(
    first: $first
    filter: {
      project: { name: { in: $names } }
      state: { type: { nin: ["completed", "canceled"] } }
    }
  ) {
    nodes {
      id
      identifier
      title
      url
      state { name }
      labels { nodes { name } }
      project { name }
      attachments { nodes { url } }
    }
  }
}
"""


def _repo_from_project(name: str) -> str:
    return PROJECT_REPO.get((name or "").strip(), "")


def _github_from_attachments(node: dict[str, Any]) -> tuple[str, int]:
    attachments = node.get("attachments") or {}
    nodes = attachments.get("nodes") if isinstance(attachments, dict) else attachments
    for item in nodes or []:
        url = ""
        if isinstance(item, dict):
            url = str(item.get("url") or "")
        elif isinstance(item, str):
            url = item
        match = GITHUB_PULL_RX.search(url)
        if match:
            return match.group(1), int(match.group(2))
    return "", 0


def normalize_issue(node: dict[str, Any]) -> dict[str, Any]:
    labels = []
    lab = node.get("labels") or {}
    for item in lab.get("nodes") or node.get("labelList") or []:
        if isinstance(item, dict) and item.get("name"):
            labels.append(item["name"])
        elif isinstance(item, str):
            labels.append(item)
    state = node.get("state") or {}
    project = node.get("project") or {}
    project_name = project.get("name") if isinstance(project, dict) else str(project or "")
    repo, number = _github_from_attachments(node)
    if not repo:
        repo = node.get("repo") or _repo_from_project(project_name)
    if not number:
        number = int(node.get("github_number") or 0)
    return {
        "id": node.get("identifier") or node.get("id"),
        "title": node.get("title") or "",
        "url": node.get("url") or "",
        "status": state.get("name") if isinstance(state, dict) else str(state or ""),
        "labels": labels,
        "repo": repo,
        "github_number": number,
        "project": project_name,
    }


class LinearOps:
    def __init__(self, token: str | None = None, fetch: Callable | None = None) -> None:
        self.token = (token if token is not None else READ_TOKEN).strip()
        self.fetch = fetch
        self.last_error: str | None = None

    def list_queue(self, issues: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        self.last_error = None
        if issues is not None:
            return [normalize_issue(i) if "identifier" in i or "labels" in i else i for i in issues]
        if self.fetch:
            raw = self.fetch()
            return [normalize_issue(n) for n in raw]
        if not self.token:
            self.last_error = "missing_LINEAR_OPS_READ"
            return []
        payload = json.dumps(
            {"query": QUEUE_QUERY, "variables": {"first": 50, "names": list(PROJECT_NAMES)}}
        ).encode("utf-8")
        req = urllib.request.Request(
            LINEAR_API,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": self.token,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self.last_error = f"linear_http_{exc.code}"
            return []
        except Exception:
            self.last_error = "linear_unreachable"
            return []
        if body.get("errors"):
            self.last_error = "linear_graphql_error"
            return []
        nodes = (((body.get("data") or {}).get("issues") or {}).get("nodes")) or []
        return [normalize_issue(n) for n in nodes]
