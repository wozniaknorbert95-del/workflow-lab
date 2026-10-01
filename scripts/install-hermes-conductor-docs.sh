#!/usr/bin/env bash
# Copy Nous conductor templates onto the host. No Docker, no systemctl, no secrets.
# Deploy / start Nous = Commander GO (Zasada 11).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-/var/lib/hermes-conductor}"
SRC="$ROOT/docs/ops/hermes-conductor"
if [[ ! -f "$SRC/SOUL.md" ]]; then
  echo "BLAD: brak szablonów w $SRC" >&2
  exit 1
fi
mkdir -p "$HERMES_HOME"
cp "$SRC/SOUL.md" "$SRC/CONDUCTOR.md" "$SRC/TOOLSET.md" "$HERMES_HOME/"
chmod 644 "$HERMES_HOME"/*.md
echo "OK: szablony → $HERMES_HOME"
echo "Ustaw HERMES_CONDUCTOR_STATUS i HERMES_CONDUCTOR_HANDOFF (obok ops-status.json)."
echo "CURSOR_API_KEY tylko w env hosta. Nie startuję Nous."
