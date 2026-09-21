# Otwiera formularz fine-grained PAT (write) dla Hermes Ops na VPS.
# Dowódca w UI MUSI dodać repo: workflow-lab + dsaas-platform-main.
$q = @(
  "name=Hermes-Ops-Write-VPS"
  "description=Ops+comment+cursor+squash-merge+after+CI+no+Actions+write"
  "target_name=wozniaknorbert95-del"
  "expires_in=90"
  "contents=read"
  "pull_requests=write"
  "issues=write"
  "checks=read"
) -join "&"
$url = "https://github.com/settings/personal-access-tokens/new?$q"
Write-Host "URL (sudo GitHub moze wymagac kodu z maila):"
Write-Host $url
Write-Host ""
Write-Host "W formularzu: Repository access = Only select repositories"
Write-Host "  - workflow-lab"
Write-Host "  - dsaas-platform-main"
Write-Host "Potem: Generate token -> SecureString -> push-ops-tokens-to-vps.ps1 -SecureGithub"
Start-Process $url
