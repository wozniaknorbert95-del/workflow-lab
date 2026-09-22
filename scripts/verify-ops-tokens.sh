#!/usr/bin/env bash
# Kanarek Hermes Ops: LINEAR_OPS_READ + GITHUB_OPS_WRITE na VPS.
# Nigdy nie drukuje wartości sekretów. Nie merguje losowego PR.
set -euo pipefail
ENV_FILE="${1:-/etc/workflow-lab/hermes-engineer.env}"
OWNER="${GITHUB_OPS_OWNER:-wozniaknorbert95-del}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: brak $ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

fail=0

len_lin=${#LINEAR_OPS_READ}
len_write=${#GITHUB_OPS_WRITE}
len_eng=${#GITHUB_ENGINEER_TOKEN}
echo "lens LINEAR_OPS_READ=$len_lin GITHUB_OPS_WRITE=$len_write GITHUB_ENGINEER_TOKEN=$len_eng"

# --- Linear ---
if [[ -z "${LINEAR_OPS_READ:-}" ]]; then
  echo "WARN: LINEAR_OPS_READ pusty — kolejka moze byc queue_file / UNKNOWN"
else
  code=$(curl -sS -o /tmp/linear-viewer.json -w '%{http_code}' \
    -X POST "https://api.linear.app/graphql" \
    -H "Content-Type: application/json" \
    -H "Authorization: ${LINEAR_OPS_READ}" \
    -d '{"query":"{ viewer { id } }"}')
  if [[ "$code" != "200" ]]; then
    echo "FAIL: Linear viewer HTTP $code" >&2
    fail=1
  else
    if grep -q '"errors"' /tmp/linear-viewer.json 2>/dev/null && ! grep -q '"viewer"' /tmp/linear-viewer.json; then
      echo "FAIL: Linear GraphQL errors" >&2
      fail=1
    else
      echo "PASS: Linear viewer HTTP 200"
    fi
  fi
fi

# --- GitHub WRITE ---
if [[ -z "${GITHUB_OPS_WRITE:-}" ]]; then
  echo "WARN: GITHUB_OPS_WRITE pusty — Run next / merge nie ruszy"
else
  case "${GITHUB_OPS_WRITE}" in
    gho_*)
      echo "FAIL: GITHUB_OPS_WRITE wygląda na gho_ (OAuth laptop) — odrzuć" >&2
      fail=1
      ;;
  esac
  code=$(curl -sS -o /tmp/gh-ops-me.json -w '%{http_code}' \
    -H "Authorization: Bearer ${GITHUB_OPS_WRITE}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    https://api.github.com/user)
  if [[ "$code" != "200" ]]; then
    echo "FAIL: GitHub WRITE /user HTTP $code" >&2
    fail=1
  else
    echo "PASS: GitHub WRITE /user HTTP 200"
  fi
  for repo in workflow-lab dsaas-platform-main; do
    code=$(curl -sS -o /tmp/gh-ops-repo.json -w '%{http_code}' \
      -H "Authorization: Bearer ${GITHUB_OPS_WRITE}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${OWNER}/${repo}")
    if [[ "$code" != "200" ]]; then
      echo "FAIL: GET ${repo} HTTP $code" >&2
      fail=1
    else
      echo "PASS: GET ${repo} HTTP 200"
    fi
    code=$(curl -sS -o /tmp/gh-ops-pulls.json -w '%{http_code}' \
      -H "Authorization: Bearer ${GITHUB_OPS_WRITE}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${OWNER}/${repo}/pulls?per_page=1&state=all")
    if [[ "$code" != "200" ]]; then
      echo "FAIL: LIST pulls ${repo} HTTP $code (potrzeba PR read)" >&2
      fail=1
    else
      echo "PASS: LIST pulls ${repo} HTTP 200"
    fi
  done
  # Dry write probe: GITHUB_OPS_COMMENT (or WRITE fallback) on non-existent issue
  comment_tok="${GITHUB_OPS_COMMENT:-}"
  comment_name="GITHUB_OPS_COMMENT"
  if [[ -z "$comment_tok" ]]; then
    echo "FAIL: GITHUB_OPS_COMMENT pusty — Start nie obudzi Cursor Cloud" >&2
    fail=1
  else
    echo "lens GITHUB_OPS_COMMENT=${#comment_tok}"
    code=$(curl -sS -o /tmp/gh-ops-comment-tok.json -w '%{http_code}' -X POST \
      -H "Authorization: Bearer ${comment_tok}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      -H "Content-Type: application/json" \
      "https://api.github.com/repos/${OWNER}/workflow-lab/issues/999999999/comments" \
      -d '{"body":"@cursor ops-comment-canary-dry"}')
    case "$code" in
      404|410|422)
        echo "PASS: ${comment_name} comment dry HTTP $code (Issues write OK; issue nie istnieje)"
        ;;
      401|403)
        echo "FAIL: ${comment_name} comment dry HTTP $code — brak Issues write" >&2
        fail=1
        ;;
      201|200)
        echo "WARN: ${comment_name} dry niespodziewanie utworzył komentarz HTTP $code"
        ;;
      *)
        echo "WARN: ${comment_name} dry HTTP $code"
        ;;
    esac
  fi
fi

# --- ENGINEER drift alarm (nie blokuje ops write) ---
if [[ -n "${GITHUB_ENGINEER_TOKEN:-}" ]] && [[ -f "$(dirname "$0")/verify-engineer-pat.sh" ]]; then
  if bash "$(dirname "$0")/verify-engineer-pat.sh" "$ENV_FILE" >/tmp/eng-verify.out 2>&1; then
    echo "PASS: ENGINEER read-only ($(head -1 /tmp/eng-verify.out))"
  else
    echo "ALARM: ENGINEER verify FAIL — mozliwy write drift (osobny ticket). Szczegoly:"
    head -5 /tmp/eng-verify.out || true
  fi
fi

if [[ "$fail" -ne 0 ]]; then
  echo "FAIL: verify-ops-tokens" >&2
  exit 1
fi
if [[ -z "${LINEAR_OPS_READ:-}" ]] || [[ -z "${GITHUB_OPS_WRITE:-}" ]]; then
  echo "PARTIAL: verify OK dla obecnych kluczy, ale brakuje co najmniej jednego ops sekretu"
  exit 0
fi
echo "PASS: verify-ops-tokens (Linear + GitHub WRITE)"
exit 0
