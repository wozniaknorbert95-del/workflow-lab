"""Linear read path — queue only. Issue description is OFF (injection)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

LINEAR_API = os.environ.get("LINEAR_API", "https://api.linear.app/graphql")
READ_TOKEN = os.environ.get("LINEAR_OPS_READ", "")

QUEUE_QUERY = """
query OpsQueue($first: Int!) {
  issues(first: $first, filter: { project: { id: { in: ["workflow-lab", "dsaas-platform-main"] } } }) {
    nodes { id identifier title url state { name } labels { nodes { name } } }
  }
}
"""


def normalize_issue(node: dict[str, Any]) -> dict[str, Any]:
    labels = []
    lab = node.get("labels") or {}
    for item in lab.get("nodes") or node.get("labelList") or []:
        if isinstance(item, dict) and item.get("name"):
            labels.append(item["name"])
        elif isinstance(item, str):
            labels.append(item)
    state = node.get("state") or {}
    return {
        "id": node.get("identifier") or node.get("id"),
        "title": node.get("title") or "",
        "url": node.get("url") or "",
        "status": state.get("name") if isinstance(state, dict) else str(state or ""),
        "labels": labels,
        "repo": node.get("repo") or "",
        "github_attachment": node.get("github_attachment") or node.get("attachment"),
    }


class LinearOps:
    def __init__(self, token: str | None = None, fetch: Callable | None = None) -> None:
        self.token = (token if token is not None else READ_TOKEN).strip()
        self.fetch = fetch

    def list_queue(self, issues: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if issues is not None:
            return [normalize_issue(i) if "identifier" in i or "labels" in i else i for i in issues]
        if self.fetch:
            raw = self.fetch()
            return [normalize_issue(n) for n in raw]
        if not self.token:
            return []
        payload = json.dumps({"query": QUEUE_QUERY, "variables": {"first": 50}}).encode("utf-8")
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
        except (urllib.error.HTTPError, Exception):
            return []
        nodes = (((body.get("data") or {}).get("issues") or {}).get("nodes")) or []
        return [normalize_issue(n) for n in nodes]
