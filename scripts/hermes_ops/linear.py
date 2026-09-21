"""Linear read path — queue only. Issue description is OFF (injection)."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

LINEAR_API = os.environ.get("LINEAR_API", "https://api.linear.app/graphql")
READ_TOKEN = os.environ.get("LINEAR_OPS_READ", "")
# Fallback when LINEAR_OPS_READ is empty: file pushed from laptop/MCP (no secrets).
QUEUE_FILE = Path(
    os.environ.get(
        "LINEAR_OPS_QUEUE_FILE",
        str(Path(__file__).resolve().parents[2] / "data" / "linear-queue.json"),
    )
)
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
    if isinstance(lab, list):
        raw_labels = lab
    elif isinstance(lab, dict):
        raw_labels = lab.get("nodes") or node.get("labelList") or []
    else:
        raw_labels = node.get("labelList") or []
    for item in raw_labels:
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
        "status": state.get("name") if isinstance(state, dict) else str(state or node.get("status") or ""),
        "labels": labels,
        "repo": repo,
        "github_number": number,
        "project": project_name,
    }


def _load_queue_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(raw, dict):
        items = raw.get("issues") or []
    else:
        items = raw
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(normalize_issue(item) if ("identifier" in item or "labels" in item or "state" in item) else item)
    return out


class LinearOps:
    def __init__(
        self,
        token: str | None = None,
        fetch: Callable | None = None,
        queue_file: Path | None = None,
    ) -> None:
        self.token = (token if token is not None else READ_TOKEN).strip()
        self.fetch = fetch
        self.queue_file = queue_file if queue_file is not None else QUEUE_FILE
        self.last_error: str | None = None
        self.source: str = "none"

    def list_queue(self, issues: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        self.last_error = None
        self.source = "none"
        if issues is not None:
            self.source = "arg"
            return [normalize_issue(i) if "identifier" in i or "labels" in i else i for i in issues]
        if self.fetch:
            self.source = "fetch"
            raw = self.fetch()
            return [normalize_issue(n) for n in raw]
        if self.token:
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
            self.source = "linear_api"
            return [normalize_issue(n) for n in nodes]
        # No API token: durable file bootstrap (MCP / laptop push). Not UNKNOWN if file has issues.
        file_issues = _load_queue_file(self.queue_file)
        if file_issues:
            self.source = "queue_file"
            return file_issues
        self.last_error = "missing_LINEAR_OPS_READ"
        return []
