#Requires -Version 5.1
<#
.SYNOPSIS
  Wgraj tokeny z pliku poza repo (nie z czatu), potem USUN plik.
  Plik: %USERPROFILE%\.config\workflow-lab\ops-tokens.env
  Format (dwie linie):
    LINEAR_OPS_READ=lin_api_...
    GITHUB_OPS_WRITE=github_pat_...
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
  @"
# Wklej tokeny PONIZEJ (bez cudzyslowow). Zapisz. Uruchom ponownie ten skrypt.
# Plik zostanie USUNIETY po udanym pushu na VPS.
LINEAR_OPS_READ=
GITHUB_OPS_WRITE=
"@ | Set-Content -LiteralPath $EnvFile -Encoding UTF8
  Write-Host "Utworzono szablon: $EnvFile"
  Write-Host "1) Uzupelnij LINEAR_OPS_READ i GITHUB_OPS_WRITE"
  Write-Host "2) Zapisz plik"
  Write-Host "3) Uruchom ponownie: .\scripts\push-ops-tokens-from-file.ps1"
  notepad $EnvFile
  exit 2
}

$lin = ""; $gh = ""
Get-Content -LiteralPath $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#")) { return }
  if ($line -match '^LINEAR_OPS_READ=(.*)$') { $lin = $Matches[1].Trim() }
  if ($line -match '^GITHUB_OPS_WRITE=(.*)$') { $gh = $Matches[1].Trim() }
}
if (-not $lin -and -not $gh) {
  throw "Plik $EnvFile nie zawiera wypelnionych tokenow."
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
# Wipe plain from memory as best-effort
$lin = $null; $gh = $null

& (Join-Path $Root "scripts\push-ops-tokens-to-vps.ps1") -SecureLinear $secLin -SecureGithub $secGh
$code = $LASTEXITCODE

# Always shred local file after attempt if push ok
if ($code -eq 0) {
  Remove-Item -LiteralPath $EnvFile -Force
  Write-Host "OK: lokalny plik tokenow USUNIETY: $EnvFile"
} else {
  Write-Host "Push nieudany — plik $EnvFile ZOSTAJE (popraw i sprobuj ponownie)." -ForegroundColor Yellow
}
exit $code
