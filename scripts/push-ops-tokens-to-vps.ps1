#Requires -Version 5.1
<#
.SYNOPSIS
  Dopisz LINEAR_OPS_READ i/lub GITHUB_OPS_WRITE do hermes-engineer.env na VPS (chmod 600).
  Nie loguje wartości. Nie kasuje GITHUB_ENGINEER_TOKEN. Odrzuca gho_ (OAuth laptop).
.EXAMPLE
  $lin = Read-Host -AsSecureString "LINEAR_OPS_READ"
  $gh  = Read-Host -AsSecureString "GITHUB_OPS_WRITE"
  .\scripts\push-ops-tokens-to-vps.ps1 -SecureLinear $lin -SecureGithub $gh
.EXAMPLE
  # tylko Linear (GitHub już na VPS):
  .\scripts\push-ops-tokens-to-vps.ps1 -SecureLinear $lin
#>
param(
  [SecureString]$SecureLinear,
  [SecureString]$SecureGithub,
  [string]$VpsHost = "root@185.243.54.115",
  [string]$EnvPath = "/etc/workflow-lab/hermes-engineer.env"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function ConvertFrom-Secure([SecureString]$s) {
  if (-not $s) { return "" }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Test-TokenShape([string]$Kind, [string]$Token) {
  $py = Join-Path $Root "scripts\hermes_ops\ops_token_validate.py"
  $code = @"
import sys
sys.path.insert(0, r'$($Root -replace '\\','/')/scripts')
from hermes_ops.ops_token_validate import validate_linear_ops_read, validate_github_ops_write
t = sys.argv[1]
kind = sys.argv[2]
ok, reason = (validate_linear_ops_read(t) if kind == 'linear' else validate_github_ops_write(t))
print(reason)
sys.exit(0 if ok else 2)
"@
  $tmpPy = Join-Path $env:TEMP "ops-token-shape-check.py"
  [IO.File]::WriteAllText($tmpPy, $code, (New-Object Text.UTF8Encoding $false))
  $out = & python $tmpPy $Token $Kind 2>&1
  $codeExit = $LASTEXITCODE
  if ($codeExit -ne 0) {
    throw "Odrzucono $Kind (powod: $out). Nie uzywaj gho_ z 'gh auth token'."
  }
}

$lin = ConvertFrom-Secure $SecureLinear
$gh = ConvertFrom-Secure $SecureGithub
if (-not $lin) { $lin = $env:LINEAR_OPS_READ }
if (-not $gh) { $gh = $env:GITHUB_OPS_WRITE }

$incoming = @{}
if ($lin) {
  Test-TokenShape "linear" $lin
  $incoming["LINEAR_OPS_READ"] = $lin
}
if ($gh) {
  Test-TokenShape "github" $gh
  $incoming["GITHUB_OPS_WRITE"] = $gh
}
if ($incoming.Count -eq 0) {
  throw "Podaj -SecureLinear i/lub -SecureGithub (albo LINEAR_OPS_READ / GITHUB_OPS_WRITE w env)."
}

$lines = foreach ($k in $incoming.Keys) { "$k=$($incoming[$k])" }
$payload = ($lines -join "`n")
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload))
$py = @'
import base64, os, pathlib, subprocess, json
env_path = pathlib.Path(os.environ["ENV_PATH"])
raw = base64.b64decode(os.environ["B64"]).decode("utf-8")
incoming = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
env_path.parent.mkdir(parents=True, exist_ok=True)
lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
out, seen = [], set()
for line in lines:
    if "=" not in line or line.strip().startswith("#"):
        out.append(line)
        continue
    k, _, _ = line.partition("=")
    if k in incoming:
        out.append(f"{k}={incoming[k]}")
        seen.add(k)
    else:
        out.append(line)
for k, v in incoming.items():
    if k not in seen:
        out.append(f"{k}={v}")
# Ensure queue file path for bootstrap fallback
if not any(l.startswith("LINEAR_OPS_QUEUE_FILE=") for l in out):
    out.append("LINEAR_OPS_QUEUE_FILE=/opt/workflow-lab/data/linear-queue.json")
env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
os.chmod(env_path, 0o600)
subprocess.run(["systemctl", "start", "hermes-ops.service"], check=False)
# lengths only
lens = {k: len(v) for k, v in incoming.items()}
# read back lengths of all three identities (never values)
vals = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    if "=" not in line or line.strip().startswith("#"):
        continue
    k, _, v = line.partition("=")
    vals[k.strip()] = len(v.strip())
print("OK: ops tokens merged;", json.dumps({"pushed": lens, "on_vps": {
    "LINEAR_OPS_READ": vals.get("LINEAR_OPS_READ", 0),
    "GITHUB_OPS_WRITE": vals.get("GITHUB_OPS_WRITE", 0),
    "GITHUB_ENGINEER_TOKEN": vals.get("GITHUB_ENGINEER_TOKEN", 0),
}}))
subprocess.run(
    ["bash", "/opt/workflow-lab/scripts/verify-ops-tokens.sh"],
    check=False,
)
try:
    d = json.loads(pathlib.Path("/opt/akademia/data/ops-status.json").read_text(encoding="utf-8"))
    print("kanarek", d.get("status"), d.get("reason"), (d.get("next") or {}).get("id"))
except Exception as exc:
    print("kanarek_err", type(exc).__name__)
'@
$pyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
$remote = "export ENV_PATH='$EnvPath' B64='$b64'; echo $pyB64 | base64 -d > /tmp/merge-ops-env.py && python3 /tmp/merge-ops-env.py; rm -f /tmp/merge-ops-env.py"
ssh -o BatchMode=yes $VpsHost $remote
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OK: tokeny na VPS (tylko len w logu). Odswiez /ops — oczekuj reason=vps_timer gdy Linear zywy."
