#!/usr/bin/env bash
# Kanarek C2: token must read checks and must NOT merge (403/404/422, never 200 merge).
set -euo pipefail
ENV_FILE="${1:-/etc/workflow-lab/hermes-engineer.env}"
REPO="${2:-wozniaknorbert95-del/workflow-lab}"
PR="${3:-34}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: brak $ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
if [[ -z "${GITHUB_ENGINEER_TOKEN:-}" ]]; then
  echo "FAIL: GITHUB_ENGINEER_TOKEN pusty" >&2
  exit 1
fi

code_checks="$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer ${GITHUB_ENGINEER_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/commits/main/check-runs?per_page=1")"
if [[ "$code_checks" != "200" ]]; then
  echo "FAIL: GET check-runs HTTP $code_checks (oczekiwano 200)" >&2
  exit 1
fi

merge_code="$(curl -sS -o /dev/null -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer ${GITHUB_ENGINEER_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/pulls/${PR}/merge" \
  -d '{"merge_method":"squash"}')"
case "$merge_code" in
  403|404|405|422)
    echo "PASS: merge blocked HTTP $merge_code (read-only OK)"
    exit 0
    ;;
  200|201|204)
    echo "FAIL: merge dozwolony HTTP $merge_code — token ma WRITE, nie może zostać na VPS" >&2
    exit 1
    ;;
  *)
    echo "FAIL: nieoczekiwany HTTP $merge_code na merge" >&2
    exit 1
    ;;
esac
