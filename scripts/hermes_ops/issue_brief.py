"""Sanitize Linear DoR excerpts for conductor handoff. Description OFF on queue path.

At Start we optionally fetch one issue (LINEAR_OPS_READ) and extract 6-field
sections + AC checkboxes. Never dump raw description into Cloud prompt.

QUI-153: ISSUE-JSON v1 = the issue metadata the platform preflight needs
(`session-preflight.py <id> --issue-json tmp/issue-<id>.json`). Its
`description` is a sanitized DoR digest (metadata block + AC + Rollback),
not the raw Linear description.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

SIX_FIELDS = (
    "cel",
    "kontekst",
    "wymagania",
    "ograniczenia",
    "kryteria akceptacji",
    "weryfikacja",
)
# Default smoke ids keep T1c / QUI-13x on lab_probe brief.
_DEFAULT_LAB_PROBE = ("QUI-129", "QUI-130", "QUI-131")
IDENT_RE = re.compile(r"^([A-Z]+)-(\d+)$", re.I)
LINEAR_GQL = os.environ.get("LINEAR_API", "https://api.linear.app/graphql")
_MAX_SECTION = 600
_MAX_AC = 12
ISSUE_JSON_VERSION = 1
_MAX_DOR_DIGEST = 2500
_MAX_META_LINES = 20
_HEADING_RE = re.compile(r"^\s*#{1,6}\s*(?:\d+[.)]?\s*)?(.+?)\s*$")


def lab_probe_issue_ids() -> set[str]:
    raw = str(os.environ.get("CONDUCTOR_LAB_PROBE_ISSUES") or "").strip()
    if raw:
        return {x.strip().upper() for x in raw.split(",") if x.strip()}
    return set(_DEFAULT_LAB_PROBE)


def resolve_brief_kind(issue: dict[str, Any]) -> str:
    explicit = str(issue.get("brief_kind") or "").strip().lower()
    if explicit in ("lab_probe", "real"):
        return explicit
    if str(os.environ.get("OPS_CONDUCTOR_LAB_PROBE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return "lab_probe"
    labels = [str(x).lower() for x in (issue.get("labels") or [])]
    if "lab-smoke" in labels or "lab_smoke" in labels:
        return "lab_probe"
    issue_id = str(issue.get("id") or issue.get("identifier") or "").strip().upper()
    if issue_id in lab_probe_issue_ids():
        return "lab_probe"
    return "real"


def _strip_inject(text: str) -> str:
    out = str(text or "")
    out = re.sub(r"(?i)(token|api[_-]?key|authorization|password)\s*[:=]\s*\S+", "[redacted]", out)
    out = re.sub(r"https?://[^\s)]+", "[url]", out)
    out = re.sub(r"`{3}[\s\S]*?`{3}", "[code]", out)
    return out.strip()


def extract_dor_excerpts(description: str) -> dict[str, str]:
    """Pull SIX_FIELDS sections from markdown/plain Linear description."""
    text = str(description or "").replace("\r\n", "\n")
    if not text.strip():
        return {}
    lines = text.split("\n")
    current = ""
    buckets: dict[str, list[str]] = {k: [] for k in SIX_FIELDS}
    heading_re = re.compile(r"^(#{1,4}\s*|\*\*|__)?\s*([^*\n#:]+?)\s*(\*\*|__)?\s*:?\s*$")

    def match_field(label: str) -> str:
        low = label.strip().lower().rstrip(":")
        for field in SIX_FIELDS:
            if field in low or low in field:
                return field
        if "acceptance" in low or low.startswith("ac"):
            return "kryteria akceptacji"
        return ""

    for line in lines:
        hm = heading_re.match(line.strip())
        if hm:
            field = match_field(hm.group(2) or "")
            if field:
                current = field
                continue
        if current and line.strip():
            buckets[current].append(line.rstrip())

    out: dict[str, str] = {}
    for field, parts in buckets.items():
        if not parts:
            continue
        blob = _strip_inject("\n".join(parts))[:_MAX_SECTION]
        if blob:
            out[field] = blob
    return out


def extract_ac_list(description: str, excerpts: dict[str, str] | None = None) -> list[str]:
    """Checkbox / numbered AC lines → short ids for handoff.ac."""
    src = ""
    if excerpts and excerpts.get("kryteria akceptacji"):
        src = excerpts["kryteria akceptacji"]
    else:
        src = str(description or "")
    items: list[str] = []
    for line in src.splitlines():
        s = line.strip()
        m = re.match(r"^(?:[-*]\s*\[.\]\s*|\d+[.)]\s*|AC-\d+\s*[:.)-]?\s*)(.+)$", s, re.I)
        if not m:
            continue
        body = _strip_inject(m.group(1))[:120]
        if not body:
            continue
        items.append(body)
        if len(items) >= _MAX_AC:
            break
    if not items and excerpts and excerpts.get("kryteria akceptacji"):
        # Single block without checkboxes — one AC line.
        one = excerpts["kryteria akceptacji"].split("\n")[0].strip()[:120]
        if one:
            items.append(one)
    return items


def fetch_linear_issue(issue_id: str) -> dict[str, Any] | None:
    token = str(os.environ.get("LINEAR_OPS_READ") or "").strip()
    if not token or token == "test-linear-fixture":
        return None
    ident = (issue_id or "").strip().upper()
    parsed = IDENT_RE.match(ident)
    if not parsed:
        return None
    team, num = parsed.group(1).upper(), int(parsed.group(2))
    payload = {
        "query": (
            "query($team: String!, $num: Float!) { issues(filter: { team: { key: { eq: $team } }, "
            "number: { eq: $num } }, first: 1) { nodes { identifier title description url "
            "estimate state { name } project { name } labels { nodes { name } } } } }"
        ),
        "variables": {"team": team, "num": float(num)},
    }
    req = urllib.request.Request(
        LINEAR_GQL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    nodes = (((body.get("data") or {}).get("issues") or {}).get("nodes")) or []
    node = nodes[0] if nodes and isinstance(nodes[0], dict) else None
    if not node:
        return None
    labels = [
        n.get("name")
        for n in ((node.get("labels") or {}).get("nodes") or [])
        if isinstance(n, dict) and n.get("name")
    ]
    project = ((node.get("project") or {}) or {}).get("name") or ""
    state = node.get("state") if isinstance(node.get("state"), dict) else {}
    return {
        "id": str(node.get("identifier") or ident),
        "title": node.get("title") or "",
        "description": node.get("description") or "",
        "url": node.get("url") or "",
        "labels": labels,
        "project": project,
        "estimate": node.get("estimate"),
        "status": str(state.get("name") or ""),
    }


def _section(lines: list[str], wanted: tuple[str, ...]) -> list[str]:
    """Body lines of the first markdown heading whose label contains a wanted word."""
    out: list[str] = []
    inside = False
    for line in lines:
        hm = _HEADING_RE.match(line) if line.lstrip().startswith("#") else None
        if hm:
            if inside:
                break
            label = hm.group(1).strip().lower()
            inside = any(w in label for w in wanted)
            continue
        if inside and line.strip():
            out.append(line.rstrip())
    return out


def dor_digest(description: str) -> str:
    """Sanitized DoR text for the platform preflight (no raw description).

    Keeps: leading metadata blockquote (Severity/NC/Fala/Owner/Zakres środowiska),
    the acceptance-criteria section and the rollback section. Each line goes
    through `_strip_inject` (URLs, code blocks, credentials-looking pairs).
    """
    text = str(description or "").replace("\r\n", "\n")
    if not text.strip():
        return ""
    lines = text.split("\n")
    meta: list[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith("#"):
            break
        if s.startswith(">"):
            body = s.lstrip(">").strip()
            if body:
                meta.append(body)
            if len(meta) >= _MAX_META_LINES:
                break
    ac = _section(lines, ("kryteria akceptacji", "acceptance"))
    rollback = _section(lines, ("rollback",))
    parts: list[str] = []
    if meta:
        parts.append("\n".join(meta))
    if ac:
        parts.append("## Kryteria akceptacji\n" + "\n".join(ac[: _MAX_AC + 4]))
    if rollback:
        parts.append("## Rollback\n" + "\n".join(rollback[:8]))
    clean = [_strip_inject(p) for p in parts]
    blob = "\n\n".join(p for p in clean if p)
    # Never cut inside the rollback section silently: trim AC/meta first.
    if len(blob) > _MAX_DOR_DIGEST and rollback:
        tail = "\n\n" + _strip_inject("## Rollback\n" + "\n".join(rollback[:8]))[:600]
        blob = blob[: _MAX_DOR_DIGEST - len(tail)].rstrip() + tail
    return blob[:_MAX_DOR_DIGEST]


def _estimate(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        return _estimate(value.get("value"))
    try:
        num = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return int(num) if num.is_integer() else num


def build_issue_json(issue: dict[str, Any], description: str = "") -> dict[str, Any]:
    """ISSUE-JSON v1 for `session-preflight.py --issue-json` (platform contract).

    Missing data stays missing (estimate None, empty description) so the
    preflight answers STOP-LINEAR instead of a fake PASS (fail-closed, B6a).
    """
    labels = [str(x)[:60] for x in (issue.get("labels") or []) if str(x).strip()][:30]
    return {
        "v": ISSUE_JSON_VERSION,
        "id": str(issue.get("id") or issue.get("identifier") or "").strip().upper()[:40],
        "title": _strip_inject(str(issue.get("title") or ""))[:200],
        "status": str(issue.get("status") or "").strip()[:60],
        "labels": labels,
        "estimate": _estimate(issue.get("estimate")),
        "project": str(issue.get("project") or "")[:80],
        "repo": str(issue.get("repo") or "")[:80],
        "description": dor_digest(description),
    }


def issue_json_block(issue_json: dict[str, Any]) -> str:
    """Prompt block: the JSON + exact preflight steps. STOP wins over AC."""
    iid = str(issue_json.get("id") or "").strip() or "?"
    payload = json.dumps(issue_json, ensure_ascii=False, indent=2)
    path = f"tmp/issue-{iid}.json"
    return (
        "ISSUE-JSON v1 (dane zadania z Linear, przekazane przez Hermesa):\n"
        f"```json\n{payload}\n```\n"
        f"KROK 1 (zawsze, przed jakąkolwiek zmianą): zapisz powyższy JSON bez zmian do `{path}` "
        "(`tmp/` jest w .gitignore, nie commituj go).\n"
        f"KROK 2: `python scripts/session-preflight.py {iid} --issue-json {path}`.\n"
        "KROK 3: LANE=HERMES i exit 0 → `/start` (przejęcie pracy: najpierw przeczytaj "
        "`### Stan sesji` z opisu otwartego PR tego zadania), potem AC.\n"
        "LANE=UNKNOWN / LOCAL / BLOCKED albo STOP → zakończ w tej turze raportem STOP-LINEAR "
        "z wyjściem preflightu i listą brakujących pól. Zero zmian w plikach, zero PR. "
        "STOP ma pierwszeństwo przed AC."
    )


def enrich_issue(issue: dict[str, Any], *, fetch_linear: bool = True) -> dict[str, Any]:
    """Return a copy with brief_kind, url, dor_excerpts, ac (string list)."""
    out = dict(issue or {})
    issue_id = str(out.get("id") or out.get("identifier") or "").strip().upper()
    if issue_id:
        out["id"] = issue_id
    desc = str(out.get("description") or out.get("body") or "")
    if fetch_linear and issue_id and not desc:
        remote = fetch_linear_issue(issue_id)
        if remote:
            desc = str(remote.get("description") or "")
            if out.get("estimate") in (None, "") and remote.get("estimate") not in (None, ""):
                out["estimate"] = remote["estimate"]
            if not out.get("status") and remote.get("status"):
                out["status"] = remote["status"]
            if not out.get("project") and remote.get("project"):
                out["project"] = remote["project"]
            if not out.get("url") and remote.get("url"):
                out["url"] = remote["url"]
            if not out.get("title") and remote.get("title"):
                out["title"] = remote["title"]
            if remote.get("labels") and not out.get("labels"):
                out["labels"] = remote["labels"]
            # Prefer project→repo only when issue had no repo.
            proj = str(remote.get("project") or "")
            if not out.get("repo") and "dsaas-platform" in proj.lower():
                out["repo"] = "dsaas-platform-main"
            elif not out.get("repo") and "workflow-lab" in proj.lower():
                out["repo"] = "workflow-lab"
    if not out.get("url") and issue_id:
        out["url"] = f"https://linear.app/quietforge/issue/{issue_id}"
    excerpts = extract_dor_excerpts(desc)
    ac_bodies = extract_ac_list(desc, excerpts)
    out["dor_excerpts"] = excerpts
    out["ac"] = [f"AC-{i + 1}: {body}" for i, body in enumerate(ac_bodies)]
    out["brief_kind"] = resolve_brief_kind(out)
    out["issue_json"] = build_issue_json(out, desc)
    # Never persist raw description into handoff file.
    out.pop("description", None)
    out.pop("body", None)
    return out
