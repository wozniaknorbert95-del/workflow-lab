# Linear API key — Hermes Ops (`LINEAR_OPS_READ`)

**Cel:** kolejka QuietForge na VPS bez opisu issue (zero injection do LLM).

1. Otwórz [Linear → Settings → Account → Security & access → Personal API keys](https://linear.app/settings/account/security).
2. **Create key** → nazwa `Hermes-Ops-Read-VPS` → skopiuj `lin_api_…` (jednorazowo).
3. **Nie** wklejaj do czatu / gita / handoffu.
4. Na laptopie:

```powershell
cd workflow-lab
$lin = Read-Host -AsSecureString "LINEAR_OPS_READ (lin_api_...)"
.\scripts\push-ops-tokens-to-vps.ps1 -SecureLinear $lin
```

5. Kanarek VPS: `bash /opt/workflow-lab/scripts/verify-ops-tokens.sh` → Linear viewer HTTP 200.  
   `/ops/status` → `reason=vps_timer` (nie `missing_LINEAR_OPS_READ`).

Rotacja: 90 dni. Awaryjnie bez klucza: `scripts/push-linear-queue-to-vps.ps1` (plik kolejki).
