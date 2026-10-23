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
| **Tesztek** | **2515 passing**, 0 fail (5 időzónában) |
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

> 🔄 **2026-10-19 — a fal újramérve** (commit `808e8fe`). A régi `2 × medián(|terv→fill|)`
> becslő feltételezte, hogy a kilépés a belépéssel egyenértékű, és a szimmetrikus
> elsodródás fél-szélességét költségként terhelte. A valódi súrlódás, oldalanként mérve:
> belépés **+40,3 / +52,2 bp** (n=89), kilépés **+23,2 / +32,5 bp** (n=108) →
> round trip **63,5 / 84,7 bp** → **fal 0,1059 / 0,1412** (a régi 0,2783 helyett).
> **A verdikteken ez nem változtat**: a mért `|IC| < 0,009` az új, kötő faltól is
> **~16×** van. MOO belépővel a fal **0,0387** lenne (D-C4, production-javítás, nyitva).
> Riport: `docs/review/2026-10-19-cost-estimator-implementation.md`.

A *korábbi* (2026-10-04-i) számítás **83,5 bp/oldal**-lal dolgozott → a HYP-005 h=5
IC-jéhez (+0,0130) **≤ 7,7 bp/oldal** kellett volna. Az új becslővel a küszöb enyhébb,
de a nagyságrendi következtetés változatlan.

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
| **A** — új jelcsalád | Az FRL-sáv kész és bejáratott (23 attempt, pre-reg fegyelem, BH-FDR, (e) gazdasági kapu). Új hipotézis = új pre-reg. **Az UW kivezetve**, tehát a forrás Polygon + FMP + FRED. ⚠️ **Power-korlát:** a D-U3 szabály miatt új attempt csak a 3. univerzum-rezsimen (2026-10-20-tól) futhat → T_eff≥6 mellett **h=5 csak 2026-12-08-tól**, h=10 2027-01-29-től értékelhető. Lásd lent. |
| **B** — végrehajtás-vezérelt újraindítás | A SIM-EXEC +$2 442-je valós, de **költség-csökkentő, nem alfa-forrás**. Jel nélkül csak lassítja a vérzést. **Önmagában nem stratégia.** |
| **C** — a jelcsalád lezárása | Az infrastruktúra (pipeline, FRL, sim-harness, bar-tár, pre-reg fegyelem) **vagyon**, és egy másik jelcsaládot is kiszolgál. **A score leállítása nem a projekt leállítása.** |

**A mért bizonyíték jelenleg C felé mutat.** Élesítés egyik úton sem következik
automatikusan — bármely élő periódus **új élő pre-regisztrációt** kíván
(a 2026-07-25-i protokoll **nem** újrahasznosítható).

### Az (A) út egyetlen ismert megkerülése a power-korláton — döntési bemenet

> 🔴 **2026-10-23 — ÚJ SCORING-ÉRA HATÁR.** Négy néma adathiba javítva (lásd CHANGELOG);
> ebből három **elmozdítja a `Total_Score`-t**, tehát a panel a D-U3 univerzum-határ MELLETT
> egy mérési határt is kapott: `SCORING_ERAS` / `CURRENT_SCORING_ERA` a `frl_config`-ban, és
> a batch a két határ későbbikénél kezd. **Ára 4 kereskedési nap** (10-20…10-23), és minden
> adekvációs dátum 4 nappal csúszik: **h=5 → 2026-12-14**, **h=10 → 2027-02-04** (h=1 11-03,
> h=3 11-23, h=7 2027-01-05, h=20 2027-05-17). A törés most volt a legolcsóbb: a 3. rezsim
> négy napos volt, amikor a javítás landolt.
>
> ⚠️ **A határ (2026-10-26) DEPLOY-dátum.** A 10-23-i Phase 4-6 már lefutott 14:30-kor a
> régi kóddal, tehát az a nap a RÉGI érához tartozik. A határ csak akkor igaz, ha a Mini
> **hétfő 14:30 előtt pullol** — ha a deploy csúszik, a `frl_config` konstansa is csúszik.
>
> ⚠️ **A HYP-007 (Funda, KILL ×5) a 6-ból 2 bemeneten mérődött** — a javítás újradefiniálja
> a faktort, tehát új pre-reg kell, nem újrafuttatás. Nyitott kérdés: `04-risks` §6.7.
>
> ⚠️ **A Cross-Asset Regime réteg életre kelt** (6,5 hónapig minden futáson eldobódott).
> Élő smoke 2026-10-23: mindhárom arány 22 sessionnel, mai rezsim **CAUTIOUS** (1 szavazat,
> VIX 19,77) → `vix_penalty_start` −1. Ma nincs hatása (a kereskedés áll), de ez
> **viselkedés-változás a trade-plan úton** → restart-checklist.

> **Tamás-döntés (2026-10-21):** a bar-tár terve ennek a döntésnek a **BEMENETE**, nem a
> következménye — de **nem indul el a döntés előtt**, mert új jelcsaládot (GC) épít.
> 2026-10-23-án taskból **tervdokumentummá** alakítva, mert senki nem hajthatja végre,
> amíg a döntés nyitva: `docs/planning/2026-08-24-ohlcv-store-design.md`.

A D-U3 korlát azért köt, mert a mai FRL-panel a `full_scan_matrix` CSV-kből épül
(`scripts/research/frl_loader.py`), azaz **a pipeline által pontozott univerzumból** —
ezért rezsim-függő. Egy bar-alapú, fogyasztói oldalon szűrt panel (a task §5.4-e) a
likviditási szűrőt **minden napra újraszámolhatja** a lezárt napi bar-okból, tehát
pont-az-időben tiszta és **rezsim-független** lehet, és a meglévő folytonos bar-tárral
(2026-02-11 → 2026-10-02, 162 session; backfillel 348) azonnal van mintája.

⚠️ **A korlát, ami megmarad:** a **tagság visszamenőleg nem rekonstruálható** — a
Russell-1000 forrás a **mai** lista. Egy ilyen panel univerzuma ezért **nem lehet**
„index-tagság ∩ floor", hanem csak egy tisztán bar-ból számolt szűrő (pl. napi top-N
medián dollárvolumen). Ez **önálló döntés, nem következtetés**, és a **pre-reg elé**
tartozik — az adat megnézése előtt rögzítendő, különben garden-of-forking-paths.

Állapot: **0/8 lépés kész.** A task lezárt mérései (§5.1 mult=√2, §5.2 hlc3, §5.3
korrekciós évjárat 0,65% ticker/hó) és a §6 önhordó referencia-fixture érvényesek.

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

**2672 passing**, 0 fail (2026-10-23) — Budapest / UTC / Tokyo / UTC+14 / UTC−11. Baseline csak nőhet.

---

## Nyitott taskok

```bash
grep -lE "^Status:[[:space:]]*(OPEN|WIP)" docs/tasks/*.md
```

> A lekérdezést 2026-10-21 óta **guard-teszt** tartja érvényben
> (`tests/test_task_header_hygiene.py`): a félkövér `**Status**:` és a hiányzó header
> is **elrejti** a fájlt a grep elől — ez 2026-10-04-én 12, 2026-10-21-én további 5
> fájlon fordult elő. A teszt a formátumot ott kényszeríti ki, ahol a lekérdezés
> támaszkodik rá.

| Task | Státusz |
|---|---|
| — | **Nincs nyitott task** (2026-10-23). |


**Nem a lekérdezésben, de a gyökérben:**

| Fájl | Státusz |
|---|---|
| `2026-10-19-preclose-tp-auction-exit.md` | BLOCKED — a panel 12 blokkolója |
| `future-2026-04-17-bc-ifds-phase3-from-mid.md` | BLOCKED — külső függőség (MID Phase B) |
| `2026-05-25-operator-emergency-procedure.md` | élő operátori runbook, nem task (a guard allowlistjében) |

**2026-10-21-én lezárva:** `2026-07-17-automated-daily-review-mini.md` → **REJECTED**
(a premisszája a Day 63 kapu volt, ami 2026-10-03-án lezárult; a funkciót a
`/daily-review` command + `generate_review{,_data}.py` fedi; a build-fázisból 0 történt
meg). Archiválva: +7 fájl a `docs/tasks/archive/`-ba.

---

## Az API-költség-leminősítések állapota (2026-10-23)

A $516/hó számlából **$269** szabadult fel vagy vált feltétel-mentessé. Tamás intézi a
billinget; a kódoldali feltételek állapota:

| Lépés | Megtakarítás | Kódoldali feltétel |
|---|---:|---|
| **Options Developer → Starter** | −$50 | ✅ kész — a leminősítés utáni első futáskor `scripts/analysis/options_coverage_diff.py`, **törölt opciós cache** mellett |
| **Indices Starter → lemondás** | −$49 | ✅ kész — a VIX FMP ^VIX-ről jön, óra-guarddal. ⚠️ `pt_monitor.py:497` még Polygon I:VIX-et hív (trading-guarded, dormant) → restart-checklist |
| **Stocks Advanced → Starter** | −$170 | 🟡 a két guard kész; a **Mini cron-tolás** még hátra, és az első informatív teszt **2026-11-02** (a 10-26…10-30 hét DST-ráhagyása használhatatlanná teszi) |
| Currencies Starter | −$49 | ⛔ nem IFDS-kérdés: a `signum` ugyanazon a Massive-kulcson fut |

**✅ ELVÉGEZVE (2026-10-23):** a `vix_close` 113 production napból 18-on (15,9%) egyezett a
hivatalos CBOE zárással — az ok a 16:10 ET-s futási idő, öt perccel az elszámolás előtt. A
backfill **97 fájlt javított**, az egyezés most **113/113 = 100,0%**, max. hiba 0,00.
Backupok: `state/state_backups/vix_backfill_20261023/` (111 fájl).

**✅ ELVÉGEZVE (2026-10-23):** a Mini 22:xx cron-lánca +30 perccel tolva (22:30 / 22:40 /
22:41 / 22:45 / 22:50 / 23:15); a telepített crontab és a `crontab.md` bájtra egyezik.
A 22:05 (`signum`) és a 23:30 (`aetherveil`) nem ütközik. ⚠️ Első **informatív** teszt-nap:
**2026-11-02** — a 10-26…10-30 hét DST-ráhagyása használhatatlanná teszi.

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
