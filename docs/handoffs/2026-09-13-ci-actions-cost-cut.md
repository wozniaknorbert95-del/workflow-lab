# Handoff — CI Actions cost + email noise cut (Phase 1 + 2)

**Data:** 2026-09-13  
**Sesja:** dokończenie audytu Copilota; merge do `main`; Faza 2 quietforge + platform  
**Dowódca:** Norbert Wozniak

---

## Co zrobione

### workflow-lab — Faza 1 ✅ MERGED

| Element | Status |
|---------|--------|
| PR | [#54](https://github.com/wozniaknorbert95-del/workflow-lab/pull/54) merged → `main` |
| `daily-digest.yml` | Pn/Śr/Pt 07:30 (zamiast codziennie) |
| `weekly-security-sweep.yml` | tylko `workflow_dispatch` |
| `ci.yml` | path filters — CI tylko przy `src/`, `scripts/`, `package.json`, `ci.yml` |
| Dokumentacja | `docs/AUDIT-PHASE-1.md` |

### dsaas-quietforge — Faza 2 ✅ MERGED

| Element | Status |
|---------|--------|
| PR | [#6](https://github.com/wozniaknorbert95-del/dsaas-quietforge/pull/6) merged → `main` |
| `deploy.yml` | tylko `workflow_dispatch` (zgodne z `brain.md` — deploy ręczny) |
| `lighthouse.yml` | tylko `workflow_dispatch` (koniec auto-run na każdy PR) |
| Dokumentacja | `docs/operations/AUDIT-PHASE-2.md` |

### dsaas-platform-main — Faza 2 ⏳ OTWARTY PR

| Element | Status |
|---------|--------|
| PR | [#37](https://github.com/wozniaknorbert95-del/dsaas-platform-main/pull/37) **OPEN** — branch `audit/phase-2-optimize-ci` |
| `policy-gates.yml` | `paths-ignore`: docs, `*.md`, `.gitlab/**` |
| `security.yml` | j.w. |
| `gitleaks.yml` | `paths-ignore`: docs, `*.md` |
| `db-rls.yml` | `paths`: tenancy/db/alembic/requirements-db |
| Dokumentacja | `docs/ops/AUDIT-PHASE-2-CI-PATH-FILTERS.md` |
| CI na PR #37 | `gates` ✅ `gitleaks` ✅ `postgres-rls` ✅ `negative-security` ✅ |
| CI na PR #37 | `coverage` ❌ `container-scan` ❌ (**pre-existing na main**, nie regresja path filters) |

---

## Co live (efekt po merge)

| Repo | Efekt od razu po merge |
|------|------------------------|
| workflow-lab | Mniej cronów + mniej CI na docs-only PR |
| dsaas-quietforge | Push do `main` **nie** odpala deploy ani Lighthouse |
| dsaas-platform-main | Path filters **dopiero po merge PR #37** |

**Deploy produkcyjny QuietForge:** Actions → *Deploy to Vercel* → Run workflow (Commander).

**Digest workflow-lab:** Pn/Śr/Pt; ręcznie: Actions → *daily-digest*.

---

## Blockery

1. **PR #37 platform** — merge zablokowany przez czerwone checki **niezwiązane ze zmianą YAML**:
   - `coverage`: `tests/test_mc_bff.py::LedgersEndpointTests::test_real_repo_ledgers_readable` — brak evidence w ledgerze
   - `container-scan`: CVE w base image (`util-linux` w MCP Docker image)
   - **Właściciel fixu:** osobna sesja platform / Dowódca decyduje: naprawić testy+image **albo** merge z override (path filters same w sobie przeszły `gates`)

2. **GitHub Notifications** — nadal można ściąć w Settings → Notifications (Actions / failed only).

---

## Następny krok (jeden ▶ TERAZ)

**Merge PR #37** po decyzji Dowódcy:
- **Opcja A (szybka):** merge z admin override — path filters są niskiego ryzyka; czerwone checki istniały przed audytem
- **Opcja B (czysta):** naprawić `test_mc_bff` + pin/ignore Trivy na MCP image, potem merge

Komenda merge (gdy zielone lub override):
```bash
gh pr merge 37 --repo wozniaknorbert95-del/dsaas-platform-main --merge --delete-branch
```

---

## Komendy weryfikacji (copy-paste)

```bash
# workflow-lab — main ma optymalizację
gh pr view 54 --repo wozniaknorbert95-del/workflow-lab --json state,mergedAt

# quietforge — brak auto-deploy po push
git -C dsaas-quietforge show origin/main:.github/workflows/deploy.yml | head -8

# platform — status PR
gh pr checks 37 --repo wozniaknorbert95-del/dsaas-platform-main

# lokalny parity workflow-lab
cd workflow-lab && npm run lint && npm test && npm run build
```

---

## Pliki dotknięte (po merge / na branchu)

**workflow-lab (main):**
- `.github/workflows/ci.yml`
- `.github/workflows/daily-digest.yml`
- `.github/workflows/weekly-security-sweep.yml`
- `docs/AUDIT-PHASE-1.md`

**dsaas-quietforge (main):**
- `.github/workflows/deploy.yml`
- `.github/workflows/lighthouse.yml`
- `docs/operations/AUDIT-PHASE-2.md`

**dsaas-platform-main (branch `audit/phase-2-optimize-ci`, PR #37):**
- `.github/workflows/policy-gates.yml`
- `.github/workflows/security.yml`
- `.github/workflows/db-rls.yml`
- `.github/workflows/gitleaks.yml`
- `docs/ops/AUDIT-PHASE-2-CI-PATH-FILTERS.md`

---

## Szacunek oszczędności (miesięcznie, orientacyjnie)

| Źródło | Oszczędność |
|--------|-------------|
| workflow-lab digest | ~17 runów |
| workflow-lab security sweep | ~4 runy |
| quietforge auto-deploy | N × push (3–5 min każdy) |
| quietforge Lighthouse/PR | M × PR (5–8 min) |
| platform docs-only PR | do dziesiątek minut na PR (po merge #37) |

---

## Kontekst sesji

- Copilot GitHub zaczął Fazę 1, nie dokończył push — dokończone lokalnie + merge PR #54
- Dowódca prosił o redukcję kosztów Actions i maili — **nie stać na ciągłe testy**
- Repo platform przywrócone na gałąź `chore/qui-18-done-ev337` (stash odtworzony)

**Jutro zdanie startowe:** „Path filters platform czekają na merge PR #37; quietforge deploy tylko ręcznie z Actions.”
