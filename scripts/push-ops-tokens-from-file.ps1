#Requires -Version 5.1
<#
.SYNOPSIS
  Push LINEAR_OPS_READ / GITHUB_OPS_WRITE from a local file outside the repo, then delete the file.
  Default path: %USERPROFILE%\.config\workflow-lab\ops-tokens.env
#>
param(
  [string]$EnvFile = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $EnvFile) {
  $EnvFile = Join-Path $env:USERPROFILE ".config\workflow-lab\ops-tokens.env"
}
if (-not (Test-Path -LiteralPath $EnvFile)) {
  $dir = Split-Path -Parent $EnvFile
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  @(
    "# Fill tokens below (no quotes). Save. Re-run this script.",
    "# File is DELETED after a successful VPS push.",
    "LINEAR_OPS_READ=",
    "GITHUB_OPS_WRITE="
  ) | Set-Content -LiteralPath $EnvFile -Encoding UTF8
  Write-Host "Created template: $EnvFile"
  notepad $EnvFile
  exit 2
}

$lin = ""
$gh = ""
Get-Content -LiteralPath $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#")) { return }
  if ($line -match '^LINEAR_OPS_READ=(.*)$') { $lin = $Matches[1].Trim() }
  if ($line -match '^GITHUB_OPS_WRITE=(.*)$') { $gh = $Matches[1].Trim() }
}
if (-not $lin -and -not $gh) {
  throw "File has no filled tokens: $EnvFile"
}

function To-Secure([string]$plain) {
  if (-not $plain) { return $null }
  $ss = New-Object System.Security.SecureString
  foreach ($ch in $plain.ToCharArray()) { $ss.AppendChar($ch) }
  $ss.MakeReadOnly()
  return $ss
}

$secLin = To-Secure $lin
$secGh = To-Secure $gh
$lin = $null
$gh = $null

& (Join-Path $Root "scripts\push-ops-tokens-to-vps.ps1") -SecureLinear $secLin -SecureGithub $secGh
$code = $LASTEXITCODE

if ($code -eq 0) {
  Remove-Item -LiteralPath $EnvFile -Force
  Write-Host "OK: local token file deleted"
} else {
  Write-Host "Push failed; local token file kept for retry"
}
exit $code
