#!/usr/bin/env bash
# Build + enable Nous conductor container. Never writes secret values.
set -euo pipefail
TARGET="${TARGET:-/opt/workflow-lab}"
ENV_FILE="${ENV_FILE:-/etc/workflow-lab/hermes-engineer.env}"
AKADEMIA_DATA="${AKADEMIA_DATA:-/opt/akademia/data}"
HERMES_HOME="${HERMES_HOME:-/var/lib/hermes-conductor}"

mkdir -p "$AKADEMIA_DATA" "$HERMES_HOME"
if [[ ! -f "$TARGET/docs/ops/Dockerfile.hermes-conductor" ]]; then
  echo "BLAD: brak Dockerfile.hermes-conductor w $TARGET" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "BLAD: brak $ENV_FILE — najpierw install-hermes-ops-vps.sh" >&2
  exit 1
fi
grep -q '^CURSOR_API_KEY=' "$ENV_FILE" || printf '\nCURSOR_API_KEY=\n' >>"$ENV_FILE"
# Host paths stay in the systemd -e flags (/data/...). Do not put them in env-file.
chmod 600 "$ENV_FILE"
bash "$TARGET/scripts/install-hermes-conductor-docs.sh"
docker build -t hermes-conductor:local -f "$TARGET/docs/ops/Dockerfile.hermes-conductor" "$TARGET"
install -m 644 "$TARGET/docs/ops/hermes-conductor.service.example" /etc/systemd/system/hermes-conductor.service
systemctl daemon-reload
systemctl enable hermes-conductor.service
systemctl restart hermes-conductor.service
echo "OK: hermes-conductor.service"
awk -F= '/^CURSOR_API_KEY=/{print $1"="(length($2)>0?"SET":"EMPTY")}' "$ENV_FILE"
