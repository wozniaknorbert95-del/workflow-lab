# Otwiera formularz fine-grained PAT z prefillem (read-only, 90 dni).
$q = @(
  "name=Hermes-Engineer-VPS"
  "description=Read-only+S1-S6+phone+loop+VPS"
  "target_name=wozniaknorbert95-del"
  "expires_in=90"
  "contents=read"
  "pull_requests=read"
  "checks=read"
  "actions=read"
) -join "&"
$url = "https://github.com/settings/personal-access-tokens/new?$q"
Write-Host "URL (sudo GitHub może wymagać kodu z maila):"
Write-Host $url
Start-Process $url
