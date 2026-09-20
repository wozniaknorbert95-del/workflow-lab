#!/usr/bin/env bash
# Idempotent install: /opt/workflow-lab + env + systemd timer (run as root on VPS).
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/wozniaknorbert95-del/workflow-lab.git}"
TARGET="${TARGET:-/opt/workflow-lab}"
ENV_DIR="${ENV_DIR:-/etc/workflow-lab}"
ENV_FILE="${ENV_DIR}/hermes-engineer.env"
BRANCH="${BRANCH:-main}"

mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR"

if [[ ! -d "$TARGET/.git" ]]; then
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TARGET"
else
  git -C "$TARGET" fetch origin "$BRANCH" --depth 1
  git -C "$TARGET" checkout "$BRANCH"
  git -C "$TARGET" reset --hard "origin/$BRANCH"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cat >"$ENV_FILE" <<'EOF'
# Hermes Engineer — fine-grained PAT (Contents/PR/Checks/Actions: READ, 90 dni)
# Uzupełnij GITHUB_ENGINEER_TOKEN= i uruchom: scripts/verify-engineer-pat.sh
GITHUB_ENGINEER_TOKEN=
EOF
  chmod 600 "$ENV_FILE"
  echo "UWAGA: utworzono szablon $ENV_FILE — wklej read-only PAT"
fi

install -m 644 "$TARGET/docs/ops/hermes-phone-loop.service.example" /etc/systemd/system/hermes-phone-loop.service
install -m 644 "$TARGET/docs/ops/hermes-phone-loop.timer.example" /etc/systemd/system/hermes-phone-loop.timer
sed -i "s|/opt/workflow-lab|$TARGET|g" /etc/systemd/system/hermes-phone-loop.service
systemctl daemon-reload
systemctl enable hermes-phone-loop.timer
systemctl restart hermes-phone-loop.timer || true

echo "OK: workflow-lab @ $TARGET, timer hermes-phone-loop.timer"
