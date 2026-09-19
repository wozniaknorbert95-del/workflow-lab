#!/usr/bin/env bash
# Execute every notebook in notebooks/ headlessly (nbconvert --execute).
# Usage: run-notebooks.sh [kernel_name] [timeout_seconds]
#   kernel_name     — jupyter kernel to run (CI passes "ci-kernel"); default "python3"
#   timeout_seconds — per-cell nbconvert timeout; default 600
set -euo pipefail

KERNEL="${1:-python3}"
TIMEOUT="${2:-600}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mapfile -t NOTEBOOKS < <(find notebooks -name '*.ipynb' -not -path '*/.ipynb_checkpoints/*' | sort)

if [ "${#NOTEBOOKS[@]}" -eq 0 ]; then
  echo "no notebooks found — nothing to execute"
  exit 0
fi

failed=0
for nb in "${NOTEBOOKS[@]}"; do
  name="$(basename "$nb" .ipynb)"
  echo "=== execute $nb ==="
  if ! jupyter nbconvert \
        --to notebook \
        --execute "$nb" \
        --ExecutePreprocessor.kernel_name="$KERNEL" \
        --ExecutePreprocessor.timeout="$TIMEOUT" \
        --output "${name}.executed" \
        --output-dir /tmp; then
    echo "FAILED: $nb"
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  echo "one or more notebooks failed"
  exit 1
fi

echo "all notebooks executed OK"
