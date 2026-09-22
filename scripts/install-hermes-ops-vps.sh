#!/usr/bin/env bash
# Install Hermes Ops timer on the VPS (Linear queue → status cache for /ops).
# Never writes secrets. Never deploys dsaas-platform-main.
set -euo pipefail
TARGET="${TARGET:-/opt/workflow-lab}"
ENV_DIR="${ENV_DIR:-/etc/workflow-lab}"
ENV_FILE="${ENV_DIR}/hermes-engineer.env"
AKADEMIA_DATA="${AKADEMIA_DATA:-/opt/akademia/data}"
BRANCH="${BRANCH:-main}"
# phone-loop stays as optional watchdog log; S1–S6 now live inside hermes-ops cache.
KEEP_PHONE_LOOP="${KEEP_PHONE_LOOP:-1}"

mkdir -p "$ENV_DIR" "$TARGET/data" "$AKADEMIA_DATA"
chmod 700 "$ENV_DIR"
chmod 755 "$TARGET/data" "$AKADEMIA_DATA"

if [[ ! -d "$TARGET/.git" ]]; then
  echo "BLAD: $TARGET nie jest klonem workflow-lab. Najpierw: scripts/install-hermes-engineer-vps.sh" >&2
  exit 1
fi
git -C "$TARGET" fetch origin "$BRANCH" --depth 1
git -C "$TARGET" checkout "$BRANCH"
git -C "$TARGET" reset --hard "origin/$BRANCH"

if [[ ! -f "$ENV_FILE" ]]; then
  cat >"$ENV_FILE" <<'EOF'
GITHUB_ENGINEER_TOKEN=
LINEAR_OPS_READ=
GITHUB_OPS_WRITE=
GITHUB_OPS_COMMENT=
OPS_MODE=MANUAL
OPS_MAX_CONCURRENT=1
OPS_MAX_RUNS_PER_DAY=8
OPS_RUN_ALL=0
EOF
  chmod 600 "$ENV_FILE"
  echo "UWAGA: utworzono $ENV_FILE — wklej LINEAR_OPS_READ i GITHUB_OPS_WRITE"
else
  grep -q '^LINEAR_OPS_READ=' "$ENV_FILE" || printf '\nLINEAR_OPS_READ=\n' >>"$ENV_FILE"
  grep -q '^GITHUB_OPS_WRITE=' "$ENV_FILE" || printf '\nGITHUB_OPS_WRITE=\n' >>"$ENV_FILE"
  grep -q '^GITHUB_OPS_COMMENT=' "$ENV_FILE" || printf '\nGITHUB_OPS_COMMENT=\n' >>"$ENV_FILE"
  grep -q '^OPS_MODE=' "$ENV_FILE" || printf '\nOPS_MODE=MANUAL\n' >>"$ENV_FILE"
  grep -q '^OPS_RUN_ALL=' "$ENV_FILE" || printf '\nOPS_RUN_ALL=0\n' >>"$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

install -m 644 "$TARGET/docs/ops/hermes-ops.service.example" /etc/systemd/system/hermes-ops.service
install -m 644 "$TARGET/docs/ops/hermes-ops.timer.example" /etc/systemd/system/hermes-ops.timer
install -m 644 "$TARGET/docs/ops/hermes-ops-cmd.path.example" /etc/systemd/system/hermes-ops-cmd.path
sed -i "s|/opt/workflow-lab|$TARGET|g" /etc/systemd/system/hermes-ops.service
# Phone POST /ops/run writes ops-cmd.json (bind-mount). Path unit kicks tick immediately
# — vault runs in Docker and cannot systemctl the host.
touch "$AKADEMIA_DATA/ops-cmd.json" 2>/dev/null || true
chmod 664 "$AKADEMIA_DATA/ops-cmd.json" 2>/dev/null || true
systemctl daemon-reload
systemctl enable hermes-ops.timer hermes-ops-cmd.path
systemctl restart hermes-ops.timer
systemctl restart hermes-ops-cmd.path
systemctl start hermes-ops.service || true

if [[ "$KEEP_PHONE_LOOP" == "1" ]]; then
  echo "INFO: hermes-phone-loop.timer zostaje jako watchdog logu (S1–S6 i tak w ops-status.json)."
else
  systemctl disable --now hermes-phone-loop.timer 2>/dev/null || true
  echo "INFO: hermes-phone-loop.timer wyłączony (KEEP_PHONE_LOOP=0)."
fi

echo "OK: hermes-ops.timer + hermes-ops-cmd.path → $AKADEMIA_DATA/ops-status.json"
grep -q '^LINEAR_OPS_QUEUE_FILE=' "$ENV_FILE" || printf '\nLINEAR_OPS_QUEUE_FILE=%s/linear-queue.json\n' "$TARGET/data" >>"$ENV_FILE"
chmod 600 "$ENV_FILE"
if ! grep -q '^LINEAR_OPS_READ=.\+' "$ENV_FILE"; then
  echo "UWAGA: LINEAR_OPS_READ pusty — użyj queue file ($TARGET/data/linear-queue.json) albo wklej token."
  echo "  Bootstrap: scripts/push-linear-queue-to-vps.ps1"
fi
if ! grep -q '^GITHUB_OPS_WRITE=.\+' "$ENV_FILE"; then
  echo "UWAGA: GITHUB_OPS_WRITE pusty — Run next / merge nie ruszy. Status i kolejka Linear i tak mogą żyć."
fi
