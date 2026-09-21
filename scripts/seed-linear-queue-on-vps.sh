#!/usr/bin/env bash
# Seed linear-queue.json + refresh ops-status from file (works before new tick deploy).
set -euo pipefail
QUEUE="${1:-/opt/workflow-lab/data/linear-queue.json}"
STATUS="${2:-/opt/akademia/data/ops-status.json}"
mkdir -p /opt/workflow-lab/data /opt/akademia/data
chmod 644 "$QUEUE" 2>/dev/null || true
python3 - "$QUEUE" "$STATUS" <<'PY'
import json, sys, time
from pathlib import Path

queue_path, status_path = Path(sys.argv[1]), Path(sys.argv[2])
q = json.loads(queue_path.read_text(encoding="utf-8"))
issues = q.get("issues") if isinstance(q, dict) else q
lanes = {"autopilot": [], "manual": [], "local": []}
for it in issues or []:
    labels = {str(x).lower() for x in (it.get("labels") or [])}
    row = {
        "id": it.get("id"),
        "title": it.get("title") or "",
        "repo": it.get("repo") or "",
        "url": it.get("url") or "",
        "labels": sorted(labels),
        "status": it.get("status") or "",
    }
    if "hitl:approval-required" in labels or "blocked" in labels or "agent" not in labels:
        lanes["local"].append(row)
    else:
        lanes["manual"].append(row)
next_i = (lanes["manual"] or lanes["autopilot"] or [None])[0]
payload = {
    "ok": True,
    "mode": "MANUAL",
    "engine": "PAUSED",
    "worker": "cursor",
    "status": "PAUSED",
    "lanes": lanes,
    "next": next_i,
    "live": None,
    "active_agents": [],
    "approval": [
        {
            "kind": "hitl_local",
            "id": x.get("id"),
            "title": x.get("title") or "",
            "url": x.get("url") or "",
            "message": "Zostaw na laptopie — brak agent / hitl:approval-required",
            "actions": ["pause", "stop", "open_linear"],
        }
        for x in lanes["local"]
    ],
    "today": {
        "runs": 0,
        "merged": 0,
        "failed": 0,
        "waiting": len(lanes["local"]),
        "tokens": None,
        "cost": None,
    },
    "run_all_enabled": False,
    "reason": "queue_file",
    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            "ok": True,
            "issues": len(issues or []),
            "manual": len(lanes["manual"]),
            "local": len(lanes["local"]),
            "next": (next_i or {}).get("id"),
        },
        ensure_ascii=False,
    )
)
PY
# If new tick is already on VPS, prefer it (queue_file source) — ignore failures.
TICK=""
for c in /opt/workflow-lab/scripts/hermes-ops-tick.py /opt/workflow-lab/current/scripts/hermes-ops-tick.py; do
  if [ -f "$c" ]; then TICK="$c"; break; fi
done
if [ -n "$TICK" ]; then
  export LINEAR_OPS_QUEUE_FILE="$QUEUE"
  export HERMES_OPS_STATUS="$STATUS"
  export ACADEMY_DATA_DIR=/opt/akademia/data
  cd "$(dirname "$TICK")/.."
  if python3 "$TICK" --help 2>&1 | grep -q -- '--no-push'; then
    python3 "$TICK" --no-push --status-out "$STATUS" || true
  fi
fi
python3 - "$STATUS" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
lanes = d.get("lanes") or {}
print(
    "kanarek",
    d.get("status"),
    d.get("reason"),
    "auto",
    len(lanes.get("autopilot") or []),
    "manual",
    len(lanes.get("manual") or []),
    "local",
    len(lanes.get("local") or []),
    "next",
    (d.get("next") or {}).get("id"),
)
PY
