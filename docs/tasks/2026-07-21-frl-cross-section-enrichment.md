Status: OPEN
Updated: 2026-07-21
Note: **D_A MEGERŐSÍTVE (Tamás, 2026-07-21, chat)** — a v2 enrichment sink freeze alatti deploy-a jóváhagyva, az R1 két kemény előfeltételével (lásd §Deploy-előfeltételek). A build+teszt freeze-safe; a deploy a §Deploy-szekvencia szerint, sorrendben kötelező.

# FRL-5 — v2 nyers keresztmetszet forward-perzisztálás (enrichment sink)

## Probléma

A nyers scoring-al-komponensek (PCR-érték, OTM-percentilis, RVOL, EWMA-előtti
S_j-inputok) ma csak a ~3-7 winner tickerre perzisztálódnak (phase4_snapshot). A
keresztmetszeti faktor-kutatás v2 sávja (nyers komponens-szintű hipotézisek, FRL spec
§4.2) e nélkül nem tesztelhető, és a történeti pótlás Polygon options-visszaszámolással
aránytalanul drága. Forward-gyűjtéssel minden új trading nap teljes nyers keresztmetszete
megmarad — minden csúszó nap végleges adatveszteség a Day 63 utáni dev-ablakból.

## Megközelítés

- Új sink a Phase 4 futás végén: a TELJES pontozott tábla (a scan-halmaz minden olyan
  sora, ahol scoring futott — a tech-filter kiesőknél a rendelkezésre álló mezőkkel)
  írása `state/research_cross_section/YYYY-MM-DD.json.gz`-be, a phase4_snapshot
  rekord-sémájával (ticker, sector, nyers mezők, sub-score-ok, S_j és legacy kompozit
  KÜLÖN mezőben — a V1 audit szemantika-tanulságát kódolva).
- Viselkedés-invariancia: a sink KIZÁRÓLAG ír; scoring/sizing/exit útvonalat nem érint.
  Try/except-guarded (sink-hiba nem állíthatja meg a pipeline-t), a §0.11-tanulság
  mintájára logolt WARNING-gal.
- **Sink-audit fegyelem (04-risks §8.1.6-8.1.9, KÖTELEZŐ):** az új sink felvétele
  MINDKÉT e2e patch-stackbe (`test_full_pipeline_flow` +
  `TestSnapshotIsolation`) `@patch`-csel + `assert called` regressziós teszttel;
  a `runner.py` sink-grep audit-szabály frissítése.
- Méret-becslés: ~430 sor × ~40 mező ≈ 60-120 KB/nap gzip előtt → elhanyagolható.
  A `state/` sync-halmazban van → automatikusan átjön a MacBookra (az FRL loader
  a szinkronizált példányt olvassa).
## Deploy-előfeltételek (R1, KEMÉNYEK — előfeltétel, nem utólagos ellenőrzés)

A runner.py utolsó két sinkje (save_phase4_snapshot, write_shadow_snapshot) MINDKETTŐ
teszt-pollutiós bugot okozott (28 napos phase4-mock eset, test-env-hygiene szabály
kétszer). Ezért:

1. **Sink-audit regressziós tesztek zöldek ÉS teszt-pollúció-próba**: a teljes
   pytest-suite lefutása UTÁN a `state/research_cross_section/` könyvtár mtime és
   tartalma VÁLTOZATLAN (dedikált CI-lépés vagy kézi verifikáció a deploy-riportban
   dokumentálva). Deploy e nélkül TILOS.
2. **Napi ops-monitoring**: a Log Review chat ops-checklistjébe bekerül a napi sor:
   research_cross_section sor-szám ≈ scan-matrix scored sor-szám (± a tech-filter
   kezelés dokumentált különbsége). Ez a Log Review chat oldalán már vállalva.

- Deploy-lépések (a D_A megerősítés + előfeltétel-1 zöld után): CC build+teszt →
  Tamás push-jóváhagyás → Mini git pull → következő 14:30 cron élesben ír → első
  fájl verifikáció (sor-szám ≈ scan-matrix scored-sorok, mező-teljesség) → 04-risks
  §11 freeze-melléklet sor (tracking-jellegű módosításként logolva).

## Implementációs terv (fájlok)

Módosuló (MINIMÁLIS, sink-only):
- `src/ifds/pipeline/runner.py` — sink-hívás a Phase 4 után (a write_full_scan_matrix
  mintájára)
- Új: `src/ifds/output/research_cross_section.py` (writer + séma)
- `tests/test_pipeline_e2e.py` — mindkét patch-stack bővítés + regressziós assert
- Új: `tests/test_research_cross_section.py` (writer unit: séma, gzip, guarded-fail)

## Commit

`feat(output): research cross-section sink — full scored table daily persist (freeze carve-out §4.2/1, D_A approved)`

## Döntési napló

- **D_A: IGEN — Tamás, 2026-07-21** (chat). A v2 nyers keresztmetszet forward-gyűjtése
  a freeze alatt elindul, mert minden csúszó nap **végleges adatveszteség** a Day 63
  utáni v2 dev-ablakból. A carve-out jellege: **display/tracking** (§4.2/1) — a sink
  kizárólag ír, kereskedési viselkedést nem érint.
  Előfeltételek (R1, a deploy része): (1) pytest-suite utáni mtime+tartalom-invariancia
  bizonyítva a deploy-riportban; (2) napi ops-checklist sor a Log Review chatnél.

## Deploy-szekvencia (sorrendben kötelező)

| # | Lépés | Felelős | Állapot |
|---|---|---|---|
| 1 | build + teszt (sink + mindkét e2e patch-stack + regressziós assertek) | CC | — |
| 2 | **Előfeltétel-1 bizonyítás**: teljes pytest-suite után a `state/research_cross_section/` mtime **és tartalom változatlan**, a riportban dokumentálva | CC | — |
| 3 | push-jóváhagyás | **Tamás** | — |
| 4 | Mini `git pull` | Tamás | — |
| 5 | első 14:30 cron élesben ír | (automatikus) | — |
| 6 | **első-fájl verifikáció**: sor-szám ≈ scan-matrix scored; mező-teljesség; **S_j és legacy kompozit KÜLÖN mezőben** | CC | — |
| 7 | `04-risks` §11 freeze-melléklet sor (11.x formátum: mit / miért carve-out / viselkedés-hatás NEM / commit) | CC | — |

**Amit a deploy elindít:** a v2 forward-gyűjtés órája. Az első teljes nyers
keresztmetszeti nap után indul a **40-napos minimum-minta** számláló (spec §4.2) →
a HYP-001b/002b/003b legkorábban **~2026 szeptember közepén** válik tesztelhetővé,
nagyjából a Day 63 kapuval egyidőben — a v2-fordulat a kapu utáni iterációs fázisra érik be.
