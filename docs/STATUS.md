# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up). Ez az EGYETLEN dinamikus állapotfájl — a session-start hook betölti. -->
<!-- Utolsó frissítés: 2026-10-04 (vasárnap), CC -->

> ⚠️ **2026-10-04: teljes újraírás.** A korábbi törzs 2026-05-16-i volt (swing-pivot
> roadmap, Day 126 milestone, 1582 teszt, májusi blokkolók) — **4,5 hónapig elavultan
> élt**, pontosan abba a hibába esve, amit a CLAUDE.md fejléce tilt. A régi tartalom
> a git history-ban megvan; ami még releváns, az alább.

---

## 🔴 EGY MONDATBAN

**A kereskedés leállt (adatgyűjtési mód), a kapu lefutott, és az IFDS score-család
mind a négy horizonton, mind a három komponensén megerősített keresztmetszeti null.
Nyitott stratégiai döntés: új jelcsalád vagy a projekt lezárása.**

---

## Hol tartunk (2026-10-04)

| | |
|---|---|
| **Kereskedés** | ⛔ **LEÁLLT** — adatgyűjtési mód (`state/trading_enabled.json: enabled=false`, D8, 10-03) |
| **A könyv** | **ÜRES 2026-09-30 óta** — 0 pozíció, 0 élő order (bróker-verifikált) |
| **Pipeline** | ✅ **FUT** — Phase 1-6 minden nap, csak az IBKR-hez kapcsolódó jobok állnak |
| **Kapu (2026-09-22-i pre-reg dátum)** | ✅ **LEFUTOTT 2026-10-03-án**, 8 kereskedési nap dokumentált késéssel |
| **Tesztek** | **2377 passing**, 0 fail |
| **Kumulatív P&L (befagyva)** | **−$6 460,95** / 88 kereskedési nap |

---

## A négy mérés, ami ide vezetett

| # | Mérés | Eredmény |
|---|---|---|
| 1 | **Kapu-futás** (10-03) | ÉLESÍTÉS ❌ · **LEÁLLÍTÁS kritérium teljesül** (`cum_30d` −5,22% vs −3,0%). Attribúció (leíró): L2 ρ = **+0,073**, CI [−0,150, +0,289] |
| 2 | **SIM-1** — §11.20 exit-geometria | a javítás **≈$0** (−$8, CI [−707, +649]) → a geometria **nem** okozta a veszteséget |
| 3 | **SIM-2** — exit-architektúra sweep | **0/15 cella pozitív**, 0/14 szignifikáns; 25 bejárt konfigurációból a legjobb is −$3 582 |
| 4 | **SIM-EXEC** — belépési végrehajtás | **mind a 4 LMT-variáns veri a MKT-t**, V1 **+$2 442** — de a könyv így is veszteséges (−$2 915) |

**Veszteség-dekompozíció** (n=78 minta, realizált −$7 657,43):
belépési slippage **−$1 958 (26%)** · commission −$215 (3%) · geometria **≈$0** ·
exit-architektúra **≈$0** · **reziduális = a belépők maguk ≈ −$5 500 (72%)**.

---

## 🔴 A jelcsalád: mind KILL, adekvát erővel, megerősítve

| Hipotézis | Mi | Súly | Attemptek | Šidák p | Verdikt |
|---|---|---:|---|---:|---|
| HYP-005 | aggregált S_j | — | A-0005..A-0010 | 0,6411 | **KILL ×4** ✅ |
| HYP-006 | Flow blokk | **0,60** | A-0011..A-0014 | 0,9455 | **KILL ×4** ✅ |
| HYP-008 | Tech blokk | **0,30** | A-0015..A-0018 | 0,9699 | **KILL ×4** ✅ |
| HYP-007 | Funda blokk | 0,10 | A-0019..A-0023 | 0,9993 | **KILL ×5** ✅ |

*(✅ = `human_confirmed: true`. Korábban: HYP-004 sector-reversal KILL ×4.)*

**Minden mért \|IC\| < 0,009**, T_eff 6,2–62,0 (mind a 6,0-os floor fölött).
**A kioltás-hipotézis nem támogatott** — nincs mit kioltani.

### A költségoldal, ami a képet lezárja

A `breakeven_ic` lineáris a forgásban, a forgás `252/half_life` — tehát:

| Blokk | t½ (nap) | breakeven IC (h=5) |
|---|---:|---:|
| Flow (0,60) | **0,4** | **3,79** ⛔ *matematikailag lehetetlen* |
| Tech (0,30) | **2,8** | **0,4975** ⛔ |
| Funda (0,10) | **799,8** | **0,0017** 🟢 |
| aggregát | 9,9 | 0,1403 |

A mért végrehajtási költség **83,5 bp/oldal** → a HYP-005 h=5 IC-jéhez (+0,0130)
**≤ 7,7 bp/oldal** kellene, nulla marzzsal. Még **ingyenes belépéssel** is a
kilépési oldal egymaga a bruttó **5,4-szerese**.

### Egyetlen fenntartás

A **Funda** a saját időskáláján (t½ 800 nap) **még nincs megmérve**: h ∈ {20, 60}
regisztrálva (AMENDMENT-1), de **erő-kapuzva** (T_eff 3,10 és 0,52 < floor 6,0).
Esedékesség a jelenlegi adatütemen: **h=20 ≈ +12 hét, h=60 ≈ +60 hét**.
A h-görbe viszont **nem emelkedik, sőt előjelet vált** — ez a „kibontakozó lassú jel"
ellen szól.

---

## 🔑 A nyitott stratégiai döntés

A mechanikai magyarázatok elfogytak, és a jelcsalád 100%-a null. Három út:

| | |
|---|---|
| **A** — új jelcsalád | Az FRL-sáv kész és bejáratott (23 attempt, pre-reg fegyelem, BH-FDR, (e) gazdasági kapu). Új hipotézis = új pre-reg. **Az UW kivezetve**, tehát a forrás Polygon + FMP + FRED. |
| **B** — végrehajtás-vezérelt újraindítás | A SIM-EXEC +$2 442-je valós, de **költség-csökkentő, nem alfa-forrás**. Jel nélkül csak lassítja a vérzést. **Önmagában nem stratégia.** |
| **C** — a jelcsalád lezárása | Az infrastruktúra (pipeline, FRL, sim-harness, bar-tár, pre-reg fegyelem) **vagyon**, és egy másik jelcsaládot is kiszolgál. **A score leállítása nem a projekt leállítása.** |

**A mért bizonyíték jelenleg C felé mutat.** Élesítés egyik úton sem következik
automatikusan — bármely élő periódus **új élő pre-regisztrációt** kíván
(a 2026-07-25-i protokoll **nem** újrahasznosítható).

---

## Operatív állapot

### Ami fut
- **Pipeline** Phase 1-6 (cron, Mac Mini) — a scan matrix, a Phase 4 snapshot és a
  `daily_metrics` **naponta keletkezik** → az FRL mintája ~5 nap/héttel nő.
- **FileVault MEGOLDVA** (Tamás kikapcsolta, 10-04) — a 4 FileVault-osztályú outage
  (07-15/16, 07-22, 08-07, 08-21) gyökéroka lezárva. A §11.16 tanulság
  (*„az SSH-elérhetőség NEM egészség-jelzés a cron-láncra"*) **változatlanul áll**.

### Ami áll
- **Minden IBKR-hez kapcsolódó job** — `check_trading_enabled()` guard, tiszta
  `sys.exit(0)`. 8 PT-script guardolva; a `daily_metrics.py` **szándékosan nem**
  (ő írja a kutatási adatfolyamot), ott a fetch rövidre zár.
- A kereskedési review-stack (napi/heti) — nincs mit reviewolni.

### Nyitott operatív tételek
`docs/tasks/2026-10-04-operational-backlog.md` — §2 (3 elhalasztott, production
kereskedési kódút, **egyik sem sürgős**) és §3 (2 Tamás-akció: UW `.env` kulcs
rotáció, UW dormant kód ~10 modul).

---

## Tesztek

**2377 passing**, 0 fail (2026-10-04). Baseline csak nőhet.

---

## Nyitott taskok

```bash
grep -lE "^Status:[[:space:]]*(OPEN|WIP)" docs/tasks/*.md
```

| Task | Státusz |
|---|---|
| `2026-07-17-automated-daily-review-mini.md` | OPEN — a review-stack áll, nem sürgős |
| `2026-08-24-ohlcv-store-backfill.md` | OPEN — az 1. lépés adat-előfeltétele teljesült (folytonos bar-tár 02-11 → 10-02) |
| `2026-10-04-operational-backlog.md` | OPEN — lásd fent |

---

## Kapcsolódó docs

| Mi | Hol |
|---|---|
| **Kapu-kimenet** (a fő döntési dokumentum) | `docs/decisions/2026-10-03-gate-run-outcome.md` |
| **Gate-protokoll / pre-reg** (a kánon) | `docs/planning/2026-07-25-gate-protocol-preregistration.md` |
| **(e) gazdasági kapu pre-reg** | `docs/planning/2026-10-04-economic-gate-preregistration.md` |
| **Komponens-dekompozíció pre-reg + AMENDMENT-1** | `docs/planning/2026-10-04-component-decomposition-preregistration.md` |
| **Kockázatok / nyitott kérdések** | `docs/master-reference/04-risks-and-open-questions.md` (§11.20–§11.27) |
| **Riportok** | `docs/review/2026-10-03-sim1-*`, `2026-10-03-sim2-*`, `2026-10-04-sim-exec-*`, `2026-10-04-hyp005-retest.md`, `2026-10-04-component-decomposition.md` |
| **FRL spec** | `docs/design/2026-07-21-factor-research-loop-spec.md` |
| **Hipotézis-registry** | `docs/design/frl/hypotheses/` · ledger: `research/attempt_ledger.jsonl` |
| **Házszabályok** | `.claude/rules/ifds-rules.md` |
| **UW kivezetés** | `docs/decisions/2026-08-18-uw-decommission.md` |

---

## Utolsó commitok

```
9adb88e feat(research): AMENDMENT-1 + HYP-007 — a súlyozás 100%-a megerősített null
50eddb5 feat(research): komponens-dekompozíció — a súlyozás 90%-a megerősített null
2dabfee docs(rules): kutatási futás előtt a derivált cache FRISSESSÉGÉT verifikálni
a42ee0e chore: operatív backlog — a 3 zéró-kockázatú tétel elvégezve
e885ce3 feat(research): HYP-005 újrateszt — az S_j aggregát keresztmetszeti nullja lezárult
3c5f255 docs(research): komponens-dekompozíció pre-reg (HYP-006/007/008)
17ba2ba feat(research): (e) gazdasági szignifikancia-kapu az FRL PROMOTE-kritériumokhoz
2cf4893 feat(analysis): SIM-EXEC — a belépési végrehajtás ellenpróbája + (e) kapu pre-reg
0429c73 feat(analysis): SIM-2 — exit-architektúra sweep a fix belépőkön
ae5e668 feat(analysis): SIM-1 — a §11.20 exit-geometria ellenpróbája a valós filleken
```

---

## Blokkolók

**Nincs aktív P0.** A korábbi P0-k (realized P&L tracking gap, days_held calendar-bug,
cumulative drift, a kapu-futás elmaradása) **mind lezárva** — lásd `04-risks` §11.

A `state/circuit_breaker.json` **elavult Day 1-es fájl** (`active: false`) —
⚠️ a 10-02-án tüzelt breaker **submit-időben számolt** ellenőrzés
(`submit_orders.py:161-169`), **nem ez a fájl**. Nehogy valaki „resetelje".
