#Requires -Version 5.1
<#
.SYNOPSIS
  Wgraj linear-queue.json na VPS i odśwież ops-status (bootstrap bez LINEAR_OPS_READ).
.EXAMPLE
  .\scripts\push-linear-queue-to-vps.ps1
#>
param(
  [string]$VpsHost = "root@185.243.54.115",
  [string]$Fixture = "",
  [string]$RemoteQueue = "/opt/workflow-lab/data/linear-queue.json",
  [string]$RemoteStatus = "/opt/akademia/data/ops-status.json"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Fixture) {
  $Fixture = Join-Path $Root "scripts\fixtures\hermes-ops\linear-queue-open.json"
}
if (-not (Test-Path -LiteralPath $Fixture)) {
  throw "Brak fixture: $Fixture"
}
$SeedSh = Join-Path $Root "scripts\seed-linear-queue-on-vps.sh"
if (-not (Test-Path -LiteralPath $SeedSh)) {
  throw "Brak $SeedSh"
}

Write-Host "SCP queue + seed script"
scp -o BatchMode=yes $Fixture "${VpsHost}:/tmp/linear-queue.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# Force LF on remote: copy via stdin python to avoid CRLF from Windows scp of .sh
$bytes = [IO.File]::ReadAllBytes($SeedSh)
$text = [Text.Encoding]::UTF8.GetString($bytes) -replace "`r`n", "`n" -replace "`r", "`n"
$tmpLocal = Join-Path $env:TEMP "seed-linear-queue-on-vps.sh"
[IO.File]::WriteAllText($tmpLocal, $text, (New-Object Text.UTF8Encoding $false))
scp -o BatchMode=yes $tmpLocal "${VpsHost}:/tmp/seed-linear-queue-on-vps.sh"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

ssh -o BatchMode=yes $VpsHost "mkdir -p /opt/workflow-lab/data /opt/akademia/data && mv /tmp/linear-queue.json $RemoteQueue && chmod 644 $RemoteQueue && bash /tmp/seed-linear-queue-on-vps.sh $RemoteQueue $RemoteStatus"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OK: kolejka na VPS. /ops/status reason=queue_file."
