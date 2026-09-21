#Requires -Version 5.1
<#
.SYNOPSIS
  Dopisz LINEAR_OPS_READ + GITHUB_OPS_WRITE do hermes-engineer.env na VPS (chmod 600).
  Nie loguje wartości. Nie kasuje GITHUB_ENGINEER_TOKEN.
.EXAMPLE
  $lin = Read-Host -AsSecureString "LINEAR_OPS_READ"
  $gh  = Read-Host -AsSecureString "GITHUB_OPS_WRITE"
  .\scripts\push-ops-tokens-to-vps.ps1 -SecureLinear $lin -SecureGithub $gh
#>
param(
  [SecureString]$SecureLinear,
  [SecureString]$SecureGithub,
  [string]$VpsHost = "root@185.243.54.115",
  [string]$EnvPath = "/etc/workflow-lab/hermes-engineer.env"
)

$ErrorActionPreference = "Stop"

function ConvertFrom-Secure([SecureString]$s) {
  if (-not $s) { return "" }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

$lin = ConvertFrom-Secure $SecureLinear
$gh = ConvertFrom-Secure $SecureGithub
if (-not $lin) { $lin = $env:LINEAR_OPS_READ }
if (-not $gh) { $gh = $env:GITHUB_OPS_WRITE }
if (-not $lin -or -not $gh) {
  throw "Podaj -SecureLinear i -SecureGithub (albo LINEAR_OPS_READ / GITHUB_OPS_WRITE w env)."
}

# Payload: two lines, base64 — remote python merges into existing env file.
$payload = "LINEAR_OPS_READ=$lin`nGITHUB_OPS_WRITE=$gh"
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload))
$py = @'
import base64, os, pathlib, subprocess
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
env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
os.chmod(env_path, 0o600)
subprocess.run(["systemctl", "start", "hermes-ops.service"], check=False)
print("OK: ops tokens merged; lengths", {k: len(v) for k, v in incoming.items()})
'@
$pyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
$remote = "export ENV_PATH='$EnvPath' B64='$b64'; echo $pyB64 | base64 -d > /tmp/merge-ops-env.py && python3 /tmp/merge-ops-env.py; rm -f /tmp/merge-ops-env.py; python3 -c `"import json;d=json.load(open('/opt/akademia/data/ops-status.json',encoding='utf-8'));print('kanarek',d.get('status'),d.get('reason'))`""
ssh -o BatchMode=yes $VpsHost $remote
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OK: tokeny na VPS. /ops nie powinien pokazywać missing_LINEAR_OPS_READ."
