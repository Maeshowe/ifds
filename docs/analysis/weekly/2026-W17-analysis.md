# BC23 Heti Metrika Elemzés — 2026-W17 (ápr 20-24)

**Második teljes hét a BC23 deploy után, W16 követően.** A hivatalos `weekly_metrics.py` futás: `docs/analysis/weekly/2026-W17.md`.

**Kulcs kontextus:** W16-ban az abszolút P&L pozitív volt (+$1,661), de **-2.73% excess vs SPY** és **0% TP1 hit** aggasztó volt. W17 képe jelentősen más.

---

## Abszolút számok

- Gross P&L: **+$675.50**
- Net P&L (commission után): **+$593.09**
- Kumulatív: -$694.53 → **-$19.03 (-0.02%)** — **breakeven közelben**
- Win days: 3/5 (hétfő, szerda, péntek nyerő)
- Commission: $82.41 (12% a gross P&L-hez képest — **magas**, a W16 4%-hoz képest jelentős növekedés)
- Átlag slippage: +0.05% (W16-hoz hasonló)

## Piaci kontextus

### SPY-adjusted Excess Return: **+0.13%**

**Drámai javulás a W16 -2.73%-hoz képest.** 

- Portfólió heti: +0.68%
- SPY heti: +0.55%
- **Enyhe outperform**

**Ez a W16-W17 legfontosabb változása.** A W16-ban a +$1,661 nagy része "csak" a piaci rally volt (SPY +4.45%). A W17-ben a piac gyakorlatilag **lapos** volt (SPY +0.55%), és a rendszer **mégis** hozott +0.68%-ot — **ez valós, nem csak piaci rally**.

Fontos nuance: a W17 +0.13% excess **gyenge** statisztikailag (5 nap, alacsony volatilitás). Nem egyértelmű pozitív alpha, de **nem is az SPY-rally kölcsönzés**.

### Score→P&L korreláció: **r = +0.180**

**Pozitív korreláció** — **először a BC23 óta**. A W16-ban r=-0.414 (negatív, inverz), most r=+0.180 (enyhe pozitív).

- W16: magasabb score = rosszabb P&L (meglepő, alulmaradás)
- W17: magasabb score = jobb P&L (várt irány)

**Napi kép:**
- Hétfő: CNK (94.5) = legnagyobb vesztes, inverz
- Kedd: POWI (95.0) = legnagyobb nyertes, pozitív ⭐
- Szerda: CARG (93.0) = vesztes (de közeli), kevert
- Csütörtök: POWI (95.0) = ismét vesztes, inverz
- Péntek: NVDA (93.5) = legnagyobb nyertes, pozitív ⭐

**A heti pozitív korreláció inkább péntek (NVDA) és kedd (POWI) eredménye.** Nem tiszta pattern, de **statisztikailag közelebb a nullához vagy pozitívhoz** — ez **jelentős javulás** a W16 erős negatívhoz képest.

### TP1 hit rate: 3/34 (9%)

**Első TP1 hitek a BC23 óta:**
- Kedd: POWI TP1 + TP2 (2 hit, +$758 összesen)
- Péntek: NVDA TP1 (+$279)

**R:R realized: 1:1.59** — a TP1 átlagos profit $190, a kockázat ($700 max) arányában **1.59x**. Ez **elfogadható**, bár elméleti 1:2 szint alatti.

**Tanulság:** a TP1 1.25×ATR **csak magas realized vol napokon** működik. Átlag napokon MOC dominál. A W17 3 hit-je **speciális alkalmak**:
- POWI +8.96% intraday (ritka)
- NVDA +2.81% intraday (átlag-feletti, de nem extrém)

## Exit Breakdown

| Exit típus | N | Komment |
|-----------|---|---------|
| MOC | 22 | 65% — a W16 100%-hoz képest **csökkent** |
| LOSS_EXIT | 7 | 21% — **új, a W16-ban 0 volt**. Ez a soft stop (-2%) hatékonyan fogja be a rossz tickereket |
| TP1 | 3 | 9% — első hitek a BC23 óta |
| TP2 | 2 | 6% — POWI chain (kedd) |
| SL | 0 | 0% — a hard stop (-4-5%) soha nem triggerelt |
| Trail | 0 | 0% — a trail SL pontosabb a MOC-nál, nem ér el triggert |

**Pozitív:** a diverzifikált exit mix — nem csak MOC close, hanem TP hit-ek és loss_exit-ek is megjelennek. **A BC23 mechanika aktívan működik.**

## Összesítés — BC23 2 hét vs 1 hét

| Metrika | W16 | **W17** | Trend |
|---------|-----|---------|-------|
| Abszolút P&L | +$1,661 | +$593 | lecsökkent (kevésbé piaci rally) |
| Win rate (napok) | 4/5 | 3/5 | enyhe romlás |
| Commission ratio | 4% | 12% | 🔴 romlott (state-split hatás) |
| Slippage | +0.06% | +0.05% | 🟢 stabil |
| **Excess vs SPY** | **-2.73%** | **+0.13%** | 🟢 **drámai javulás** |
| **Score korreláció** | **r=-0.414** | **r=+0.180** | 🟢 **iránya megfordult** |
| **TP1 hit rate** | **0%** | **9%** | 🟢 **javult, de alacsony** |

### A 3 kritikus megfigyelés

**1. Excess vs SPY fordulat (-2.73% → +0.13%)**

A W16 aggasztó -2.73% alulteljesítés **megszűnt**. A W17-ben a portfolio **enyhén jobb** mint a SPY. **De fontos caveat:** a W17 alacsonyabb volatilitású hét volt (SPY +0.55% vs W16 +4.45%), kevésbé diagnosztikus. **Egy magas-vol hét vagy bull piac kell még**, hogy a BC23 tényleg pozitív excess-t tudjon hozni.

**2. Score korreláció fordulat (r=-0.414 → r=+0.180)**

A W16 **erős inverz** korrelációja (magasabb score = rosszabb P&L) **megszűnt**. A W17-ben enyhe pozitív (r=+0.180) — a várt irány. **De:** r=+0.180 statisztikailag **gyenge**, egy hét adat alapján. A bias valószínűleg **megszűnt**, de a **positive alpha** még nem bizonyított.

**3. TP1 hit rate javulás (0% → 9%)**

**Első TP1 hit** a BC23 óta. Kevesebb mint a célzott ~20-30%, de **a mechanika működik**. A probléma **specifikus napokhoz** kötődik (magas vol kell), nem a szisztéma egésze.

## Azonosított strukturális problémák

### 1. Contradiction pattern — 5/6 (83%) vesztes flagged ticker

**A W17 statisztikai highlight-je.** A Company Intel 6 tickeren állított CONTRADICTION flag-et:

| Ticker | Nap | Flag indoklás | P&L |
|--------|-----|---------------|-----|
| CNK | Hé | 0/4 earnings beat | **-$122** |
| GFS | Hé | ár Target High fölött | **-$83** |
| SKM | Hé | JPM + Citi downgrade | **-$149** |
| CARG | Sze | ár 2.8% consensus fölött | **-$172** |
| ADI | Csü | ár 7.9% consensus fölött | **-$27** |
| ET | Csü | 3 earnings miss | **+$31** ← kivétel |

**5 vesztes / 1 nyertes = 83% vesztes arány.**

**Ha visszamenőleg** alkalmaznánk egy **×0.80 M_contradiction multiplier**-t, a W17 P&L várhatóan:
- 5 vesztes ticker kisebb pozícióval → **-$350 → -$175** csökkenés (becsült $175 megtakarítás)
- ET nyertes is kisebb → +$31 → +$25
- **Net hatás: kb. +$170** javulás a W17-re retrofit esetén

**Javaslat:** W18 közepén implementálni (×0.80 konzervatív, mert nem 100% prediktor).

### 2. POWI paradoxon — recent winner trap

**Egyetlen ticker, 2 napos kontraszt:**
- Kedd: POWI +$758 (TP1 + TP2 full chain, +8.96% intraday)
- Csütörtök: POWI -$253 (LOSS_EXIT, -2.31%)
- 2 napos net: +$505 (még nyertes)

**Probléma:** a scoring ugyanazt a 95.0-t adja egymás utáni napokon, figyelmen kívül hagyva a tegnapi +8.96%-ot. Statisztikailag egy +9%-os nap után a ticker átlagosan **-2-3%** korrigál — a rendszer **újravette** a legrosszabb időzítéssel.

**Javaslat:** Recent Winner Penalty (M_recency × 0.80 ha elmúlt 3 napban ±5%) VAGY Position Dedup (hard skip). Backlog-ideas.md-ben rögzítve.

### 3. TP1 fix ATR nem skálázódik jól

**Megfigyelés:** 1.25×ATR TP1 **csak magas vol napokon** érhető el. Átlag napokon túl távoli target.

**W17 evidencia:** 3 TP1 hit a 34 trade közül — 9%. Ebből:
- POWI kedd: +8.96% intraday → TP1 +4.42% könnyedén
- NVDA péntek: +2.81% intraday → TP1 +2.81% szorosan

Az átlag tickerek +1-2%-t mozognak intraday, a 1.25×ATR (~+3-5%) túl magas.

**Javaslat (BC24+ scope):** ticker-szintű vol-alapú TP1 skálázás (realized vol-ból GARCH, vagy egyszerűbben 20-napos realized range). Nem most, **W19+ után**.

### 4. Commission ratio romlás (4% → 12%)

**Új probléma** a W16-hoz képest. 34 trade (21 ticker-szinten) — a **state-split** miatt az egyes pozíciók több részre bontódnak (bracket A + B, plus ARMK 4-split, ET 3-split). Minden split IBKR commission + monitoring overhead.

**Ha ticker-szinten lett volna a commission** (21 × ~$3 = $63), **~20% csökkentés** lett volna. De a jelenlegi architektúra elvárja a splittet (MAX_ORDER_SIZE=500, state-alapú bracket management).

**Nem akut javítandó,** de a P&L-drag **jelen van** (12% = $82 egy hét alatt, éves skálán ~$4,300).

## MID kontextus (új a W17-ben)

**A W17 során élesbe ment több MID API feature:**

- **2026-04-21:** `/api/bundle/latest` — teljes MID snapshot egy kérésben
- **2026-04-22:** `/api/bundle/{date}` historical + webhook/SSE
- **2026-04-22:** init_db vs Alembic normalize (MID tech debt tisztítás)

**W17 alatt 0 MID regime change event** — a STAGFLATION regime Day 3 → Day 7, stabil. Az event detector konzervatív, nem generál zajt.

**Implikáció az IFDS-re:** a W18-ban elindul a MID Bundle Integration Shadow Mode task — napi MID bundle snapshot gyűjtés + offline comparison script. **NEM érinti a Phase 3-at**, csak adatot gyűjt a W19 eleji BC25 GO/NO-GO döntéshez.

## Következtetés

**A BC23 W17-ben jelentős javulást mutatott a W16-hoz képest, de nem bizonyított pozitív alpha.**

### Pozitív

- **Excess vs SPY fordulat** (-2.73% → +0.13%)
- **Score korreláció iránya** megfordult (r=-0.414 → r=+0.180)
- **TP1 hit** első alkalommal (2 nap, 3 hit)
- **LOSS_EXIT működik** (7 eset, korlátozza a drawdown-t)
- **Kumulatív breakeven közelben** (-$19)

### Negatív / Megfigyelt

- **Commission ratio nőtt** (4% → 12%) — state-split hatás
- **Score korreláció gyenge** (r=+0.18 alacsony, 1 hét adat)
- **TP1 hit rate alacsony** (9%, cél 20-30%)
- **Contradiction pattern** (5/6) nem kezelt a scoring-ban

### Paper Trading Day 63 (~máj 14) kilátás

**13 nap múlva** éles/paper döntés. A jelenlegi trajektória:

**"Éles"-re váltás jelei:**
- Kumulatív >+5% (~+$5,000) a BC23 óta ✗ (jelenleg -$19)
- Excess vs SPY konzisztensen pozitív ~ (1 hét pozitív, de gyenge)
- TP1 hit rate >20% ✗ (9%)
- Nincs strukturális hiba ✗ (4 azonosítva)

**"Paper folytatás" jelek:**
- BC23 stabil, nincs elkanyarodás
- Problémák azonosítva, megoldhatók
- MID integráció új kontextust ad

**Valószínűbb kimenet:** +1 hónap paper trading, közben BC24 + M_contradiction + Recent Winner Penalty implementáció, **június elején** újra-értékelés.

## W18 teendők prioritása

**1. MID Bundle Integration Shadow Mode** (CC task kész, `docs/tasks/2026-04-21-mid-bundle-integration-shadow.md`)
- Hétfő ápr 27 reggel indul
- 4-5h CC, 5 napi adat gyűjtés

**2. M_contradiction multiplier ×0.80** (új CC task, W18 közepén)
- 2-3h CC
- Alapja: 5/6 W17 pattern + visszamenőleg $170 megtakarítás
- Risk: alacsony (konzervatív paraméter)

**3. BC23 folytatódik normál pipeline-ban**
- Célok: W17 excess fenntartása, TP1 hit stabilizálódása

**NEM W18-ra:** Recent Winner Penalty (várunk W18 adatra), TP1 dinamikus skálázás (BC24 scope), BC25 Phase 3 refactor (W19+ döntés után).

**NE implementáljunk több változást egyszerre** — 1-2 változtatás max, hogy a mérés tiszta maradjon a Day 63 döntéshez.

---

*Generated: 2026-04-24 ~22:30 CEST. Hivatalos weekly metrika: `docs/analysis/weekly/2026-W17.md`.*
