# Chat Handoff — IFDS Strategic Review folytatása

**Készült:** 2026-05-08 (péntek reggel)
**Készítő:** előző chat (Strategic Review chat)
**Cél:** a következő chat azonnali folytatása ezen az állapoton

---

## TL;DR (30 másodperces áttekintés)

- **Day 59/63**, 4 nap a Day 63 értékelésig (csüt máj 14)
- **Kumulatív paper P&L: -$1 616** (papír aggregát) → **~-$1 460 valós** (SQM SHORT zárás után)
- **2 P0 task fut CC-nél**: Snapshot regresszió fix + dp_pct scoring rekalibráció
- **2 stratégiai dokumentum kész**: 5 oldalas exec summary + 25 oldalas teljes anyag
- **Master Reference Card terve jóváhagyva**, hétvégén kell megírni (Chat-feladat)
- **UW marad** — Tamás döntés, "használjuk rendesen"

---

## A 4 szereplő modell (változatlan, kiegészítve)

| Szereplő | Szerep | Eszköz |
|----------|--------|--------|
| Tamás (PO) | discretionary judgment, manuális műveletek (nuke.py), stratégiai döntések | Mac Mini terminal |
| **Chat (Claude)** | **orchestrator + dokumentum-karbantartás** | claude.ai (ez a projekt) |
| **Claude Code (CC)** | **implementáció + Code QA (külön command)** | VSCode (MacBook) |
| ~~Code QA~~ | ~~read-only audit~~ → **CC-be integrálva** | CC külön command |

A korábbi 4-szereplő modellben a Code QA külön volt; most CC-be integrálva.

---

## 1. Folyamatban lévő munkák (CC-nél)

### Task 1: Snapshot regresszió fix (P0, ~1-3 óra)

**Fájl:** `docs/tasks/2026-05-08-snapshot-regression-fix.md`

**Probléma:** ápr 10 körül a `state/phase4_snapshots/` fájlok mérete drasztikusan csökkent (470+ ticker → 1 ticker, csak AAPL probe). **Minden post-Apr 10 snapshot ténylegesen üres.**

**Stratégiai jelentősége:** a `flow-decomposition.md` (232 ügylet) a régi (Feb-Apr 1) mintán futott; a BC23 utáni scoring teljesítmény **statisztikailag nem mérhető** snapshot nélkül.

**Hipotézisek:**
- A: Phase 1-3 context nem töltődik be a 16:15 cron-ban
- B: `phase4.passed` lista szűrési bug
- C: Snapshot mentési logika regresszió
- D: Pipeline-split (`c90e634`, ápr 3) regresszió

**Várt kimenet:** root cause azonosítás + fix + post-deploy validáció (egy intraday futás 470+ ticker snapshot-ot mentsen).

### Task 2: dp_pct scoring rekalibráció (P0, ~1-1,5 óra)

**Kontextus:** a Tamás 2026-05-08-i döntése: **UW marad ($150/mo), de használjuk rendesen.**

**Mit kell csinálni (3 lépés):**

1. **Production removal AZONNAL** — a hibás pozitív bonus eltávolítása:
   ```
   defaults.py — TUNING
   "dp_pct_bonus": 0,        # volt: +10
   "dp_pct_high_bonus": 0,   # volt: +15
   ```
   **Indok:** a 60-trade audit megerősítette az **inverz** signalt (Pearson r = -0,265, p=0,041 per-share), de a sign-flip (-15 inverz penalty) overfitting kockázat a kis n-en.

2. **Shadow log indítása** — a `dp_pct` raw érték mentése a Phase 4 snapshot-ba (a scoring-tól függetlenül). A snapshot regresszió fix **után** működik.

3. **Day 90-i újraértékelés** (kb. 2026-06-05) — ha a shadow log megerősíti az inverz signalt, **kalibrált** módon vezetjük vissza a scoring-ba (-5 vagy -10 pont penalty a magas dp_pct-re, realisztikus küszöbökkel: 8%/12%, NEM 40%/60%).

**Indok a 3 hónap shadow-ra:** $150/mo × 3 hó = $450 — olcsó vásárolt opció a Day 90-i adat-vezérelt döntéshez. A 60-trade alapú azonnali sign-flip prematúr.

---

## 2. Elkészült stratégiai dokumentumok

**Helye:** `docs/strategic-review/`

| Fájl | Hossz | Cél |
|------|-------|-----|
| `2026-05-08-strategic-review-summary.md` | ~5 oldal | Portfolio menedzser/befektetési bizottság gyors áttekintés |
| `2026-05-08-strategic-review-full.md` | ~25 oldal | Teljes elemzés, 9 fejezet, függelékekkel |

**Kulcs finding-ok a dokumentumokban:**

1. **A 2026 áprilisi 13 pontos terv 8/13 implementálva**, 5 nem (a leglényegesebb a "dinamikus pozíciószám" — még mindig fix 5).
2. **Pearson r ≈ 0** a kompozit pontszám és a P&L között (60 napi mintán) — a kompozit nem prediktív.
3. **Flow al-komponens dekompozíció finding-ja:**
   - **PCR**: +0,203\*\* — erős pozitív prediktor
   - **RVOL**: +0,147\* — pozitív
   - **OTM call**: -0,194\*\* — **NEGATÍV szignifikáns** (a hipotézis cáfolata)
   - **dark pool, block trade, buy pressure**: nem prediktív / inaktív
4. **A "magas pontszám paradoxon" strukturális** — Q5 -$677, Q3 -$1 341, Q2 +$880.
5. **Az "időtáv-paradoxon" a leghosszabb távú stratégiai finding** — a 6 órás holding strukturálisan kitett (earnings event, slippage, afternoon retracement).
6. **Három stratégiai irány**: A — Inkremeális finomítás, B — Multi-day swing redesign, C — Hibrid kísérletek. **Javasolt**: A + C kombináció + B párhuzamos R&D.

**FONTOS KORREKCIÓ:** a 25 oldalas dokumentum 2.4 fejezetében az API költség **$354/hó hibás**. A pontos érték (az `API_STACK.md` 2026-03-01-i frissítendő szerint): **$665/hó** (Polygon $376 + FMP $139 + UW $150 + FRED $0). Ezt a következő dokumentum-frissítéskor korrigálni kell.

---

## 3. Jóváhagyásra vár — Master Reference Card

**Tamás jóváhagyta a tervet** a chat zárása előtt; **a hétvégi megírásra kész**.

**Struktúra (5 fájl, hibrid):**

```
docs/master-reference/
├── INDEX.md                       ~1-2 oldal — kezdőlap, "mi a helyzet most?"
├── 01-parameters.md               ~2 oldal  — aktuális paraméter-snapshot
├── 02-scoring-and-exit.md         ~2-3 oldal — scoring + exit logika vizuálisan
├── 03-day63-and-performance.md    ~2 oldal  — Day 63 keret + aktuális teljesítmény
└── 04-risks-and-open-questions.md ~1-2 oldal — kockázatok, P1 backlog, nyitott kérdések
```

**Tartalom-elvek:**
- Pénzügyi terminológia, NEM kód-szintű
- Táblázatok és vizuális ábrák, kevés bullet
- Linkek a részletes forrásokra (defaults.py, scoring-validation.md, strategic-review/)
- Magyarul írva
- Az INDEX.md a belépési pont, 30 másodperc alatt áttekinthető

**Frissítési protokoll:**
- Eseményalapú (azonnal): minden CC commit, paraméter-tuning, debug-eredmény után
- Heti review (péntek 22:00 weekly metric után): konzisztencia-check
- **Felelős**: Chat (Claude), heti rendszerességgel

**Részletes terv:** az előző chat utolsó válaszában szerepel (a `Master Reference Card — Terv` szakasz). A következő chat azt **kvázi-direktívaként** tekintheti.

---

## 4. P1 Backlog (most 9 tétel)

A `docs/planning/backlog-ideas.md`-ben részletezve:

| # | Tétel | Effort | Forrás |
|---|-------|--------|--------|
| 1 | LOSS_EXIT bracket SL cancellation | ~30-45 min | DTE 2026-05-01 + SQM 2026-05-07 (2 alkalom 6 nap alatt) |
| 2 | 10-Q SEC filing exclusion | ~2-3 óra | AGNC 2026-05-04 |
| 3 | ADR earnings adatforrás fix | ~3-4 óra | BUD 2026-05-05 (FMP /stable/earnings ADR-eken hiányos) |
| 4 | **Snapshot regresszió fix** | ~1-3 óra | **CC most dolgozik rajta** |
| 5 | **dp_pct scoring rekalibráció** | ~1-1,5 óra | **CC most dolgozik rajta** |
| 6 | Breakeven Lock profit-küszöb csökkentés | ~10-15 min | UEC 2026-05-06 felfedezés (profit-trigger live) |
| 7 | TP1 cél revízió | ~30 min | DBRG 2026-05-05 (TP1 cél túl szűk) |
| 8 | Phase 4 snapshot enrichment | ~30-45 min | W18 elemzésből |
| 9 | High-score liquidity check | ~1 óra | NE 2026-05-05 (+0,72% slippage) |

---

## 5. Day 63 keret aktuális állása

| Mutató | Érték | Status |
|--------|-------|--------|
| Day | 59/63 — **4 nap van** | |
| Kumulatív paper | -$1 616 (-1,62%) | papír aggregát |
| Kumulatív tényleges | ~-$1 460 (-1,46%) | becsült (SQM SHORT zárás után) |
| 9 napi excess vs SPY | -0,54%/nap | ~1% buffer a leállítási küszöbtől |
| VIX | 17,13 stabil | leállítási feltétel inaktív |
| **Várt kimenet** | **PAPER FOLYTATÁS** | default, 4 nap egymás után megerősítve |

**A 25 oldalas dokumentum javasol egy revíziós élesítési kritériumot Day 90-re:**
- Régi (Day 63): kumulatív > +$3 000 (~+30% éves cél, túl ambíciózus)
- Új javaslat (Day 90): kumulatív > +$2 500 (~+10% éves) ÉS excess vs SPY > +1% ÉS 20+ napi nem-Stagflation regime

---

## 6. W19 napi mérleg (4 nap kész + 1 hátra)

| Nap | Net P&L | Excess | Megjegyzés |
|-----|---------|--------|-----------|
| Hé máj 4 | -$191 | +0,21% ⭐ | AGNC -$380 (10-Q SEC filing event) |
| Ke máj 5 | -$269 | -1,04% | NE -$143 (slippage), BUD -$132 (ADR earnings gap), 3× TP1 (DBRG) |
| Sze máj 6 | +$234 ⭐ | -1,14% | UEC +$161 (Breakeven Lock profit-trigger LIVE first sighting) |
| Csü máj 7 | -$501 (paper) | -0,18% ✓ | QCOM TP1+TP2 +$556 (a hét legjobbja!), SQM duplikált zárás bug |
| **Pé máj 8** | **?** | ? | ma reggel: SQM SHORT 91 zárása (nuke.py), W19 utolsó nap |

**Pénteki teendők:**
- 22:00 CEST EOD report
- 22:00 CEST W19 weekly metric (`weekly_metrics.py`)

---

## 7. Friss döntések / finding-ok (a chatben rögzítve)

1. **UW marad** — Tamás 2026-05-08-i döntés, "használjuk rendesen"
2. **Per-ticker UW dark pool**: VALÓDI prediktív erővel rendelkezik, de **inverz** (Pearson r = -0,265, p=0,041 per-share). A jelenlegi pozitív bonus **kétszeresen rossz**: szembemegy a signallal + irreális küszöbök (40%/60% vs valós 7-15%).
3. **Snapshot regresszió** felfedezve — több downstream elemzés érvénytelen (post-Apr 10 minta).
4. **API_STACK.md frissítendő** — 2026-03-01-i, az addigi BC23 átalakítás, M_contradiction, flow decomposition finding-jai nem benne.
5. **A "discretionary judgment a fejlesztési iterációkban" elv** — Linda Raschke-féle filozófia, Tamás simplicity-orientált megközelítése.

---

## 8. Következő lépések (sorrendben)

### Most → péntek 22:00

1. **CC**: a 2 task befejezése (snapshot regresszió fix + dp_pct scoring rekalibráció)
2. **Tamás**: a CC commit-ok review-ja
3. **22:00**: EOD + W19 weekly metric

### Hétvégén

1. **Chat**: Master Reference Card első verzió megírása (~3-4 fejlesztői óra)
2. **Frissítés a stratégiai dokumentumokban** (a $354/hó → $665/hó korrekció + új API-stratégia szakasz, ha a CC eredménye indokolja)

### Hétfő reggel

1. **Tamás + Chat**: a Master Reference Card együttes átnézése (30 perc)
2. **Korrigálás**: mit hagyunk ki, mit detalizálunk
3. **Konszolidált verzió** rögzítése

### Csüt máj 14 (Day 63)

1. Reggel: Day 63 felülvizsgálat
2. Várt kimenet: PAPER FOLYTATÁS (default)
3. Új doc: `docs/decisions/2026-05-14-day63-decision-outcome.md`
4. **A revíziós élesítési kritérium** rögzítése Day 90-re

---

## 9. Kapcsolódó dokumentumok (gyors elérés)

**Aktív állapot:**
- `docs/STATUS.md` — heti állapot
- `docs/planning/backlog-ideas.md` — 9 P1 backlog tétel
- `docs/decisions/2026-04-28-day63-decision-framework.md` — Day 63 keret formálva

**Frissesti elemzések:**
- `docs/analysis/scoring-validation.md` — 378 ügylet, Pearson r = -0,000
- `docs/analysis/flow-decomposition.md` — 232 ügylet, PCR +0,203\*\*, OTM -0,194\*\*
- `docs/analysis/loss-exit-whipsaw-analysis.md` — net whipsaw cost +$87,98

**Stratégiai elemzések (most kész):**
- `docs/strategic-review/2026-05-08-strategic-review-summary.md` — 5 oldal
- `docs/strategic-review/2026-05-08-strategic-review-full.md` — 25 oldal

**Folyamatban lévő task-ok:**
- `docs/tasks/2026-05-08-snapshot-regression-fix.md`
- `docs/tasks/2026-05-08-dark-pool-debug.md` (lezárt — diagnosztika eredménye CC-től)
- `docs/tasks/2026-05-08-dp-pct-scoring-recalibration.md` (CC most írja)

**Friss daily review-k:**
- `docs/review/2026-05-04-daily-review.md` (W19 D1)
- `docs/review/2026-05-05-daily-review.md` (W19 D2)
- `docs/review/2026-05-06-daily-review.md` (W19 D3)
- `docs/review/2026-05-07-daily-review.md` (W19 D4)

**Backlog hivatkozások:**
- `docs/API_STACK.md` — 2026-03-01-i, frissítendő
- `docs/planning/roadmap-2026-consolidated.md` — BC definíciók

---

## 10. Egy fontos önreflexiós pont — Tamás üzenete a chat zárása előtt

> "Úgy érzem, hogy most értem el annak a határára, hogy teljesen átlássam a fejlesztést és minden paraméter, beállítás, értékkel tudjak számolni. Simplicity alatt azt értem, hogy számomra is átlátható legyen minden, ezért kell egy részletes dokumentáció egy source of truth, hogy te is cc is, a csapatom is, és én is ehhez tudjunk fordulni, ugyanazzal dolgozzunk. Nem félek bevallana, önmagam korlátait."

**Ez a Master Reference Card megrendelési indoka.** A következő chat-nek tudni kell, hogy **a Master Reference Card NEM "újabb dokumentum a sorban"**, hanem **egy strukturált karbantartási rendszer**, amely Tamás (és a csapat) számára **navigálható kontextust** ad. **Az átláthatóság szervezeti igény, nem egyéni intelligencia-kérdés**.

A frissítés felelőse Chat (Claude) — heti rendszerességgel + minden lényeges deploy után. **Tamás szerepe**: heti 5-10 perc átfutás + jelzés, ha valami nem stimmel vagy nem érthető.

---

## A handoff vége

A következő chat azonnal folytathatja a Master Reference Card megírását, vagy a CC eredmények review-ját, vagy a péntek esti EOD-t — bármelyiket a sorrend szerint.

**Köszönöm Tamásnak az eddigi munkát**: a 60 napi paper trading **strukturált tanulságokat** termelt, **a stratégiai dokumentumok kész** vannak a csapat-megosztásra, és **a következő lépések tisztán vannak**. **A simplicity-filozófia és a discretionary judgment a fejlesztési iterációkban** egy **szakmailag erős keret** — a következő chat ezt **folytatni** fogja.
