#Requires -Version 5.1
<#
.SYNOPSIS
  Wgraj read-only fine-grained PAT na VPS i uruchom kanarek verify-engineer-pat.sh.
  Token NIE jest logowany — podaj przez SecureString albo zmienną GITHUB_ENGINEER_TOKEN.
.EXAMPLE
  $sec = Read-Host -AsSecureString "Fine-grained PAT (github_pat_...)"
  .\scripts\push-engineer-pat-to-vps.ps1 -SecureToken $sec
#>
param(
  [SecureString]$SecureToken,
  [string]$VpsHost = "root@185.243.54.115",
  [string]$EnvPath = "/etc/workflow-lab/hermes-engineer.env"
)

$ErrorActionPreference = "Stop"

function Get-PlainToken {
  if ($SecureToken) {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  }
  if ($env:GITHUB_ENGINEER_TOKEN) { return $env:GITHUB_ENGINEER_TOKEN.Trim() }
  throw "Brak tokenu: użyj -SecureToken lub ustaw GITHUB_ENGINEER_TOKEN (fine-grained read-only)."
}

$token = Get-PlainToken
if ($token -notmatch '^github_pat_|^ghp_') {
  Write-Warning "Token nie wygląda jak fine-grained (github_pat_) — upewnij się, że to read-only PAT, nie gh auth token."
}

$content = "GITHUB_ENGINEER_TOKEN=$token"
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($content))
$remote = "echo $b64 | base64 -d > $EnvPath && chmod 600 $EnvPath && bash /opt/workflow-lab/scripts/verify-engineer-pat.sh; echo VERIFY_EXIT=$?"
ssh -o BatchMode=yes $VpsHost $remote
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Kanarek lokalny (bez wypisywania tokenu)
$merge = curl.exe -sS -o NUL -w "%{http_code}" -X PUT `
  -H "Authorization: Bearer $token" `
  -H "Accept: application/vnd.github+json" `
  "https://api.github.com/repos/wozniaknorbert95-del/workflow-lab/pulls/34/merge" `
  -d "{`"merge_method`":`"squash`"}"
Write-Host "Lokalny kanarek merge HTTP: $merge (oczekiwane 403/404/405/422)"
if ($merge -in @("200","201","204")) {
  Write-Error "Token ma WRITE — nie zostawiaj go na VPS."
  exit 1
}
Write-Host "OK: PAT na VPS + verify (patrz VERIFY_EXIT powyżej)."
