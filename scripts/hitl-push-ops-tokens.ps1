#Requires -Version 5.1
<#
.SYNOPSIS
  HITL: zbierz LINEAR_OPS_READ + GITHUB_OPS_WRITE (SecureString) i wgraj na VPS.
  Nie loguje wartości. Uruchom w widocznym oknie PowerShell (nie w czacie).
#>
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host ""
Write-Host "=== Hermes Ops tokens (HITL) ===" -ForegroundColor Cyan
Write-Host "1) Linear: https://linear.app/settings/account/security -> Create key Hermes-Ops-Read-VPS"
Write-Host "2) GitHub: uruchom scripts\open-ops-write-pat-prefill.ps1 (oba repo)"
Write-Host "Nie wklejaj tokenow do czatu Cursor."
Write-Host ""

$lin = Read-Host -AsSecureString "LINEAR_OPS_READ (lin_api_...)"
$gh  = Read-Host -AsSecureString "GITHUB_OPS_WRITE (github_pat_...)"

& "$PSScriptRoot\push-ops-tokens-to-vps.ps1" -SecureLinear $lin -SecureGithub $gh
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Kanarek lokalny /ops/status (przez SSH)..." -ForegroundColor Cyan
ssh -o BatchMode=yes root@185.243.54.115 "systemctl start hermes-ops.service; sleep 2; bash /opt/workflow-lab/scripts/verify-ops-tokens.sh; python3 -c `"import json;d=json.load(open('/opt/akademia/data/ops-status.json',encoding='utf-8'));print('status',d.get('status'),'reason',d.get('reason'),'next',(d.get('next') or {}).get('id'))`""
Write-Host ""
Write-Host "DONE. Mozesz zamknac to okno." -ForegroundColor Green
pause
