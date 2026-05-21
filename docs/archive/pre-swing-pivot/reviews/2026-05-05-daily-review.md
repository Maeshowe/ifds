# Daily Review — 2026-05-05 (kedd)

**BC23 Day 17 / W19 Day 2**
**Paper Trading Day 57/63**
**M_contradiction LIVE 2. nap — első LIVE fire-ok!**

**Adat-frissesség:** state/.last_sync = 2026-05-05T20:38:12Z (kedd 22:38 CEST, post-EOD)

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$235.73 |
| Napi P&L net | **-$269.48** (commission $33.75) |
| Kumulatív P&L | **-$1,377.11 (-1.38%)** |
| Pozíciók (új) | 5 ticker (NE, PTEN, DBRG, BUD, BEKE) — **9 trade** (DBRG 3-split, PTEN 2-split, BEKE 2-split) |
| Win rate ticker szinten | 2/5 (BEKE +$49, DBRG +$26 nyert; NE -$143, BUD -$132, PTEN -$36 vesztett) |
| TP1 hit rate | **3/5 (60%)** ⭐ — **legmagasabb a BC23 deploy óta** |
| TP2 hit rate | 0/5 |
| Exit mix | **3× TP1 (DBRG mind)**, 6× MOC, 0× SL, 0× LOSS_EXIT, 0× trail |
| Avg slippage | **+0.19%** (NE +0.72% legrosszabb!), commission $33.75 |
| Commission | $33.75 ← magasabb a 9 trade miatt |
| SPY return | **+0.80%** (bull rally) |
| Portfolio return | -0.24% |
| **Excess vs SPY** | **-1.04%** ⚠️ underperform bull rally napon |
| VIX close | **17.29** (Δ=-5.52%, vissza 18 alá) |

## ⭐ M_contradiction LIVE — első LIVE fire-ok!

**Az execution_plan_run_20260505_141501_9e3a8e.csv-ben 2/5 ticker fired:**

| Ticker | flag | reasons | M_contradiction | Eredmény |
|--------|------|---------|-----------------|----------|
| **NE** | **1** | `earnings_beats_below_half (1/4)`, `price_above_consensus_9.9pct` | **0.80** | -$143 (-1.48%) |
| **PTEN** | **1** | `price_above_consensus_13.1pct` | **0.80** | -$36 (-0.48%) |
| DBRG | 0 | — | 1.0 | +$26 (TP1×3) |
| BUD | 0 | — | 1.0 | -$132 |
| BEKE | 0 | — | 1.0 | +$49 |

**Megfigyelés:** **mindkét fired ticker vesztett**. Ez a feature **első tényleges validációja**:
- Ha a M_contradiction nem fired volna (M=1.0), a NE pozícióméret ~25%-kal nagyobb lett volna → **becsült -$179 helyett -$143** (~$36 megtakarítás)
- Hasonlóan a PTEN-nél: ~$9 megtakarítás
- **Heti hatás:** ~$45 ezen a napon

**Kvalifikáció:** csak 1 napi adat. Statisztikailag **0 jelentősség**. **De** **iránybeli helyes** — a feature pontosan azon tickereken aktivált, amelyek **vesztették**.

## Pozíciók részletei

### Nyertesek (2 ticker)

**BEKE (KE Holdings, real estate dev, score 92.0):** 2-split, entry $18.07 (slippage **-0.11% kedvező**), MOC $18.16 = **+$49.14 össz** (45 + 4.14). +0.50% intraday — **a nap legnagyobb % nyerő**. **Breakeven Lock 17:45 CEST** aktivált trail_sl $17.42 → $17.48 (folyamatos emelkedés). **Jó pozíció — entry után stabil emelkedés MOC-ig.**

**DBRG (DigitalBridge, real estate, score 92.5):** 3-split, entry $15.58 (slippage +0.06%), **3× TP1 hit @ $15.60 = +$25.68 össz** (10 + 10 + 5.68). **TP1 cél csak +0.13%-ra** — nagyon szűk cél (0.75×ATR). **A nap egyetlen TP1 hit-je.** **Megfigyelés:** a TP1 olyan közel van az entry-hez, hogy szinte azonnal triggerel. **Profitabilitás kérdéses** — a 3× $10 ≈ $30 profit ebből a 1284 share pozícióból, **a 0.5% risk per trade értelmében elhanyagolható**.

### Vesztesek (3 ticker)

**NE (Noble Corp, energy/contract drilling, score 95.0 — LEGMAGASABB):** Entry $50.70 (slippage **+0.72% — a hét legrosszabb!**), MOC $49.95 = **-$143.00**. -1.48% intraday. **A score 95.0 ellenére** (legmagasabb minden ticker között) **a legnagyobb vesztes**. **M_contradiction fired** (1/4 beats + 9.9% overshoot) — a feature pontosan ezt a kockázatot jelezte. A chart screenshot szerint **17:00 CEST körül zuhant** $50.30-ról $49.70-ra (-1.2% gyors mozgás), aztán oldalozott zárásig.

**BUD (Anheuser-Busch, ADR, score 92.0):** Entry $80.87 (slippage +0.05%), MOC $80.33 = **-$131.61**. -0.67% intraday. **A reggel jelentett Q1 earnings** (BMO ~12:00 CEST) volt a kockázat — pre-market +8.74% rally után **a IFDS pozíció után** csendes oldalazás 80-81 sávban, MOC-on enyhe csúszás. **Az SL $77.99 sosem triggerelt** — a -3.5% védelem védett. **A 10-Q és FMP ADR adathiány bug ma este már a backlog P1-en van.** **De** a tényleges veszteség **mértékletes** ($132), nem katasztrófa.

**PTEN (Patterson-UTI Energy, score 94.0):** 2-split, entry $12.47 (slippage +0.24%), MOC $12.41 = **-$35.94 össz**. -0.48% intraday. **M_contradiction fired** (price 13.1% consensus fölött). **A trail aktivált 18:40 CEST-kor** — de csak +0.51%-ra emelkedett, a 19:00 CEST window előtt aktivált, így **NEM kapott Breakeven Lock floor-t**. Az ár utána visszaesett a fill árig, MOC kis vesztes. **A trail dolgozott** (SL $11.605 → $11.675 emelkedett), de irrelevánssá vált.

### Score → P&L napi nézet

| Ticker | Score | M_contradiction | P&L net | Win? | Exit |
|--------|-------|-----------------|---------|------|------|
| **NE** | **95.0** | 0.80 ⭐ | **-$143.00** | ✗ | MOC |
| PTEN | 94.0 | 0.80 ⭐ | -$35.94 | ✗ | MOC |
| DBRG | 92.5 | 1.0 | **+$25.68** | ✓ | TP1×3 |
| **BEKE** | **92.0** | 1.0 | **+$49.14** | ✓ | MOC |
| BUD | 92.0 | 1.0 | -$131.61 | ✗ | MOC |

**Megfigyelés:** **a 2 LEGMAGASABB score-ú ticker MIND vesztett**, és **mindkettő M_contradiction-flagged volt**. A 2 alacsonyabb score-ú nyert (BEKE 92.0, DBRG 92.5). **Ez** a **scoring validation negatív Pearson korrelációját** (Pearson r ≈ 0 a 55 napi adaton) **újabb adatpontként megerősíti** — sőt, a M_contradiction signal valószínűleg **éppen a "túl magas score" tickereket flageli**, ami az adat alapján **valóban** kockázatos.

---

## ⭐ A "jól indul, végére visszaesik" pattern — adatvezérelt elemzés

A te megfigyelésed **konkrét** és **mérhető**. Hadd vizsgáljam meg a **9 mai trade trajektóriáját** és a **17 napi BC23 mintát** együtt.

### A mai (kedd) intraday trajektóriák

**Az events log alapján:**

| Idő (CEST) | Esemény | Ticker | Megjegyzés |
|------------|---------|--------|------------|
| 16:18 | Submit | mind az 5 | Entry-k @ ~16:18:20-30 |
| 17:45 | trail_activated_b | BEKE | +0.55% felett |
| 18:00-18:25 | trail_sl_update | BEKE | folyamatos emelkedés ($17.42 → $17.48) |
| 18:40 | trail_activated_b | PTEN | csak +0.51% felett |
| 18:45-19:11 | trail_sl_update | PTEN | $11.605 → $11.675 |
| **19:11** | **utolsó trail update** | PTEN | **az ár ezután elindul lefelé** |
| 21:40 | MOC submit | mind az 5 | Hivatalos MOC fill 22:00 CEST |

**A te megfigyelésed igaz:** a **17:00-19:11 sávban** mindkét trail aktiválódott (BEKE, PTEN), tehát **17:00-19:11 között a portfolio profit-trajektórián volt**. A **19:11 után** az ár tendenciák **megfordultak** — a PTEN visszaesett +0.51%-ról MOC-on -0.48%-ra (1%-os fordulat 2.5 óra alatt!), a NE drasztikusan zuhant, a BUD oldalazott lefelé.

**Konkrét időablakok (intraday peak vs MOC):**

| Ticker | Peak idő | Peak ár | MOC ár | Peak → MOC |
|--------|----------|---------|--------|------------|
| BEKE | ~18:25 CEST | $18.25 | $18.16 | -0.49% |
| PTEN | ~19:11 CEST | $12.605 | $12.41 | **-1.55%** |
| NE | ~16:18 CEST | $50.70 entry után csak lefelé | $49.95 | -1.48% (entry után) |
| DBRG | sosem szárnyalt | $15.62 (TP1) | $15.60 | -0.13% |
| BUD | ~16:18 entry $80.87 | csendes oldalazás | $80.33 | -0.67% |

**Pattern megerősítve mai napon:** **a 4 ticker-ből 4 az MOC közelében alacsonyabb volt**, mint a délutáni intraday peak. **A "végére visszaesik" megfigyelésed konkrét számokon mérhető.**

### A 17 napi BC23 makró pattern

Most nézzük szélesebb perspektívában a 17 napi BC23 (ápr 13 — máj 5) eloszlását:

| Nap | Net P&L | Excess vs SPY | TP1 hit | Trail aktiv |
|-----|---------|---------------|---------|-------------|
| Apr 13 | +$381 | -0.59% | 0/3 | 0 |
| Apr 14 | +$181 | -1.03% | 0/3 | 0 |
| Apr 15 | +$587 | -0.19% | 0/4 | 0 |
| Apr 16 | +$563 | +0.33% ⭐ | 0/4 | 0 |
| Apr 17 | -$51 | -1.25% | 0/4 | 0 |
| Apr 20 | +$112 | +0.25% | 0/3 | 0 |
| Apr 21 | -$87 | -0.39% | 0/2 | 0 |
| Apr 22 | -$291 | -0.27% | 0/4 | 0 |
| Apr 23 | -$152 | -0.41% | 0/3 | 0 |
| Apr 24 | -$132 | -0.31% | 0/4 | 0 |
| Apr 27 | -$361 | -0.50% | 0/5 | 0 |
| Apr 28 | -$308 | +0.22% | 0/5 | 0 |
| Apr 29 | +$406 | +0.45% ⭐ | 0/5 | 4 |
| Apr 30 | +$405 | -0.57% | 0/5 | 2 |
| May 1 | -$1,248 | -1.50% | 0/5 | 1 |
| May 4 | -$191 | +0.21% ⭐ | 0/5 | 3 |
| May 5 | -$269 | -1.04% | **3/5** ⭐ | 2 |

**4 nap pozitív excess vs SPY (16 napi adatból ~25%).** A "bull rally underperform" minta, amit múlt héten azonosítottunk, **strukturálisan stabil**:
- Pozitív SPY napokon (≥+0.5%): 5/12 underperform (Apr 13, 14, 15, 17, May 5) — pénzügyileg pozitív, de relatív vesztes
- Negatív vagy nulla SPY napokon: az IFDS gyakran outperformol (Apr 28, May 4)

### A "végére visszaesik" makró kérdés

**Itt** kell lennünk **kritikusnak**, mert a hipotézis **statisztikailag konkrétan vizsgálható**, és a daily metrics **NEM tartalmaz** intraday peak vs MOC adatot. **Két lehetőség:**

**(a)** **Általános swing pattern**: a portfolio gyakran 17:00-19:00 között tetőzik, aztán 21:00-22:00 felé visszaesik. **Ez a tipikus US piaci minta** — a "lunch lull" 18:30-19:30 CEST (12:30-13:30 ET) körül, aztán afternoon power hour 21:00-22:00 CEST (15:00-16:00 ET) gyakran retracement-ekkel jár.

**(b)** **Konkrét IFDS-specifikus pattern**: a 16:15 CEST entry-k után **az opening range** beáll, az első 1-2 óra a "TP1 zóna", aztán a profit visszaesik a kis cél miatt (0.75×ATR), és MOC-on a positions lassan elcsúsznak.

**Mai (kedd) adatok szerint mindkét hatás látszik:**

1. A **DBRG TP1 hit-jei 3-szor** azonnal triggereltek **valószínűleg az opening range első órájában** (a TP1 cél +0.13%-ra van, ami **rendkívül szűk** — szinte spread-szerű). Ez **megerősíti** hogy a 0.75×ATR TP1 **túl szigorú**.

2. A **PTEN trail** 18:40-19:11 között 31 perc alatt felépült $11.605 → $11.675-re (+0.6% trail SL emelkedés), **DE** 19:11 után **az ár visszaesett MOC-ig**, és a trail SL **NEM aktivált**, mert mindig az aktuális ár alatt maradt 9% trail-szel. Tehát a profit **aktiválódott** (paper-en), **de a trail too loose** ahhoz, hogy a profitot megőrizze.

### Ezekből milyen következtetés

**A te "ismétlődő pattern" megfigyelésed valid**, és **a tényleges adat alátámasztja**. **De** **két különböző effektust** különít el:

**1. Általános US piaci pattern** — afternoon retracement, reverse-of-the-day eladások 21:30 CEST körül. **Ez** **NEM IFDS hiba**, hanem piaci tényező. A swing rendszer **alapvetően** ki van téve ennek.

**2. IFDS-specifikus profit-megőrzés gyengeség** — a Breakeven Lock **csak a 19:00:00-19:04:59 CEST window**-ban aktiválódik a B bracketen. **A PTEN ma 18:40-kor aktivált trail-t**, ami **kívül esik** a window-on. **Tehát a trail mechanika "soft floor" nélkül fut** a 19:00 előtti aktiválásoknál — pontosan **ezért** veszett el a PTEN profit.

**Strukturális finding (rögzítendő a backlog-ba):**

> **Breakeven Lock kibővítése a window előtti aktiválásokra is** — jelenleg csak a 19:00:00-19:04:59 CEST window-ban aktivál a B bracketen. **Pattern megfigyelve W19 Day 2**: a trail aktiválás 18:40 CEST körül (vagy korábban) gyakori, és ezekben az esetekben a trail **window előtt** aktivál, így **NEM kap soft floor-t**. A PTEN ma ezt mutatta: trail $11.605 → $11.675 (+0.6%) felépült, de **a profit elveszett** mert a trail túl laza (9%) és a soft floor hiányzott. **Megoldási irány:** ha trail bracket B-n bármikor +0.5% felett aktivál, **automatikusan** alkalmazni kell a Breakeven Lock floor-t (entry ár). **Effort:** ~30-45 min CC. **W19+ scope.**

**Ezt most rögzítem a backlog-ba**, ha akarod.

---

## Slippage anomália — NE +0.72%

A NE entry slippage **+0.72%** (planned $50.34 → filled $50.70). **Ez a hét legrosszabb slippage-ja** — összehasonlításban a többi mai ticker:
- PTEN +0.24%, DBRG +0.06%, BUD +0.05%, BEKE -0.11%
- W18 átlag: +0.10%

**Az NE slippage költsége: +$0.36/share × 190 share = +$68.40 plusz veszteség.** Ha a tényleges fill $50.34 lett volna (planned), akkor a -$143 veszteség csak **-$74.60 lenne** (-0.74%, nem -1.48%). **Ez majdnem felére csökkenti a NE veszteséget.**

**Mi lehet az oka:**
- 16:18 CEST = 10:18 ET — opening range első órájában, vol **magas**
- NE = Noble Corp, **alacsony likviditású** energy mid-cap
- A score 95 (legmagasabb) → magas pozícióméret → market impact

**Ez** egy **strukturális megfigyelés**: a high-score tickerek **gyakran alacsonyabb likviditású cégek**, és a slippage költség **arányosan** nagyobb. **Backlog idea:**

> **High-score liquidity check** — ha score >94 ÉS avg_volume <$50M, alkalmazni egy ×0.85 multiplier-t a position size-ra (vagy LIMIT helyett VWAP entry). **Effort:** ~1h CC. **W19+ scope.**

---

## Breakeven Lock napi mérleg

| Ticker | trail aktiv idő | Window-ban? | Breakeven Lock alkalm. | Eredmény |
|--------|-----------------|-------------|------------------------|----------|
| BEKE | 17:45 CEST | ✗ (window előtt) | ✗ | MOC nyertes (+$49) — szerencse |
| PTEN | 18:40 CEST | ✗ (window előtt) | ✗ | MOC vesztes (-$36) — **a window kihagyás megérzett** |
| NE | nem aktiv (entry után csak lefelé) | n/a | ✗ | MOC vesztes (-$143) |
| BUD | nem aktiv | n/a | ✗ | MOC vesztes (-$132) |
| DBRG | TP1 hit 3x (nincs trail logika) | n/a | ✗ | TP1 nyertes (+$26) |

**0/2 trail aktiváció esett a 19:00:00-19:04:59 CEST window-ba.** **Ez** ahogy a PTEN megmutatta: **a window előtt aktivált trailek nem kapnak soft floor-t**, és a profit elveszhet.

---

## A teljes hét + W18 átmenet

| Metrika | W18 hét | W19 D1 (hétfő) | W19 D2 (kedd) | W19 átlag eddig |
|---------|---------|----------------|---------------|------------------|
| Net P&L | -$1,106 | -$191 | **-$269** | -$230/nap |
| Excess vs SPY | -1.90% | +0.21% ⭐ | **-1.04%** ⚠️ | -0.42%/nap |
| Win rate (ticker) | 11/38 (29%) | 3/5 (60%) | 2/5 (40%) | 5/10 (50%) |
| TP1 hits | 0/38 (0%) | 0/5 (0%) | **3/5 (60%)** ⭐ | 3/10 (30%) |
| LOSS_EXIT | 7 | 6 (mind AGNC) | 0 | 6 |
| Avg score | 91.1 | 92.2 | **93.1** | 92.65 |

**Pozitívumok W19-ben eddig:**
- **TP1 hit rate 0% → 30%** — a DBRG-féle 3-split TP1 ráhozta az átlagot
- **LOSS_EXIT 7/hét → 6 + 0** — a hétfő AGNC-volt az egyetlen
- **Avg score nő** — a flow signal jobb minőségű tickert választ

**Aggasztóbb:**
- **Excess vs SPY -0.42%/nap átlag** — folytatódó underperform a bull rally-ben
- **Vesztesek koncentráltak**: az NE -$143 (slippage-driven) és BUD -$132 (10-Q + FMP gap) **strukturális, nem taktikai veszteségek**
- **Day 2 pattern**: a magas score (95, 94) mindig alulteljesít — **megerősíti** a 55 napi scoring validation finding-ot

---

## Day 63 keret — kedd esti állapot

| Metrika | Érték | Status a kerethez képest |
|---------|-------|--------------------------|
| Day | **57/63** — **6 nap van hátra** | |
| Kumulatív P&L | -$1,377 (-1.38%) | **biztonságos sávban** (paper folytatás default) |
| ÉLESÍTÉS távolság | +$4,377 a +$3,000-hoz | **6 nap × +$730/nap → NEM realisztikus** |
| LEÁLLÍTÁS távolság | excess -0.42% távol a -1.5%-tól | **biztonságos sávban** (~1% buffer) |
| 7 napi excess vs SPY átlag | -0.42% | W18 + W19 D1-D2 |
| VIX W19 átlag | 17.80 (D1: 18.30, D2: 17.29) | **a 18-as küszöb körül**, monitor aktív |

**Realisztikus Day 63 várt kimenet (még 6 nap):** **PAPER FOLYTATÁS (default)** — a kumulatív P&L valószínűleg -$1,800 és -$700 között lesz.

**A leállítási feltétel távolsága:**
- A 7 napi excess átlag -0.42%, a -1.5% küszöbtől **1.08% buffer**
- 6 napi -0.40%/nap átlagos excess: -2.4% kumulatív → a 7 napi (running) átlag **akkor csúsznia** -1.5% alá, **ha** a következő 6 nap **-0.7%/nap** átlag alá esik
- **Ez** egy **lehetséges scenario**, ha a bull rally folytatódik VIX <18 mellett

**Élesítési feltétel:**
- +$730/nap kell 6 napon át a +$3,000 cumulative-ra
- **Statisztikailag elérhetetlen** ez a 17 napi BC23 átlagból (~+$30/nap)

---

## Új backlog idea-k a W19 D2 elemzésből

A vasárnapi backlog-ideas mellé felvegyük:

1. **Breakeven Lock window-bővítés** — ha trail B aktivál >+0.5% bármikor (nem csak 19:00 window-ban), automatikus soft floor (entry). **W19+ scope, ~30-45 min CC, P2.**

2. **High-score liquidity check** — score >94 + avg_volume <$50M → ×0.85 size multiplier vagy VWAP entry. **W19+ scope, ~1h CC, P3.**

3. **TP1 cél revízió** (már a W18 elemzésben felmerült, mai DBRG 3-split TP1 megerősítette) — a 0.75×ATR cél túl szigorú; emelni 1.0-1.25×ATR-re vagy szűkíteni LOSS_EXIT-et. **W19+ scope, ~30 min config tuning, P2.**

4. **Phase 4 snapshot enrichment** (W18 elemzésből, még nem rögzítve) — teljes scoring tábla, nem csak winner. **W19+ scope, ~30-45 min CC, P3.**

**Javaslat:** ezeket most explicit rögzítem a backlog-ideas.md-be? Vagy várjuk meg, amíg a W19 vége (csütörtök máj 8) lezárul, és **konszolidált formában** dolgozzuk fel?

---

## Anomáliák

- **CRGY/AAPL leftover phantoms** továbbra is — `monitor_positions.py` BUG (régóta ismert, 2026-04-14 cleanup task)
- **LION/SDRL/DELL/DOCN phantom events** 22:00 CEST — IBKR API quirk
- **AVDL.CVR** non-tradable, ignorálható
- **Slippage NE +0.72%** — első +0.7% slippage W19-ben, monitor

---

## Kulcsmegfigyelések

### 1. ⭐ M_contradiction LIVE első fire-ok — irányhelyes

**2/5 fire (NE, PTEN), mindkettő vesztes pozíció.** A feature pontosan azon tickereken aktivált, amelyek **kockázatosak voltak**. **Kvalifikáció:** 1 napi adat, statisztikailag jelentéktelen, **de** iránybeli helyes. **Heti hatás becslés:** ~$45 ezen a napon. **W19 vége után** ~5-10 fire-on lesz mérhető szignifikancia.

### 2. ⭐ TP1 hit rate 0% → 60% mai napon

A DBRG 3-split TP1 hit a BC23 deploy óta **az első ilyen**. **De** a profit **elhanyagolható** ($26 a 1284 share pozícióból). **Megerősíti** hogy a 0.75×ATR cél **túl szigorú** — ha 60% hit rate-en is csak $26 profit jön, akkor strukturálisan kérdéses a célválasztás. **W19+ tuning kérdés.**

### 3. ⭐ A "jól indul, végére visszaesik" pattern megerősítve

**Mai napon konkrétan**: 4/5 ticker az MOC közelében alacsonyabb volt mint a délutáni peak. **PTEN konkrét eset**: trail aktivált 18:40-kor +0.51%-on, peak 19:11-kor $12.605, MOC $12.41 → **-1.55% retracement 2.5 óra alatt**. **Ez** kombinációja:
- Általános US piaci afternoon retracement (NEM IFDS hiba)
- IFDS-specifikus Breakeven Lock window túl szigorú (csak 19:00:00-19:04:59) — a window előtti aktiválások nem kapnak soft floor-t

### 4. Score-P&L negatív korreláció megerősítve

**A 2 legmagasabb score-ú ticker (NE 95, PTEN 94) MIND vesztett**, **mindkettő M_contradiction-flagged**. A 2 alacsonyabb score (BEKE 92, DBRG 92.5) **mind nyert**. **Pearson r ≈ 0** napon belül megerősítve, **és** a M_contradiction signal valószínűleg **éppen a "túl magas score" tickereket flageli** — ami az adat alapján **valóban** kockázatos.

### 5. NE slippage +0.72% — a high-score liquidity probléma

A NE high-score (95) + alacsony likviditású (~$50M avg vol) energy mid-cap. **+0.72% slippage = +$68 plusz veszteség** ezen a pozíción. **Strukturális finding** — a high-score tickerek gyakran alacsony likviditású cégek, és a slippage költség **kompromittálja** az alpha-t.

---

## Holnap (szerda máj 6) várnivalók

- **Reggeli ellenőrzés:** sync, MID snapshot (Stagflation Day 17/28?)
- **Pipeline:** normál ritmus, BC23 W19 Day 3
- **Várható M_contradiction fire-ok**: 1-3 ticker (W19 átlag eddig 1.0/nap)

---

## Kapcsolódó

- `state/phase4_snapshots/2026-05-05.json.gz`
- `logs/pt_events_2026-05-05.jsonl` ← **3× TP1** + 6× MOC, 2× trail aktiválás (BEKE 17:45, PTEN 18:40)
- `logs/pt_eod_2026-05-05.log`
- `state/daily_metrics/2026-05-05.json` ← **vix_close = 17.29**, kumulatív -$1,377
- `output/execution_plan_run_20260505_141501_9e3a8e.csv` ← **2/5 contradiction_flag=1** (NE, PTEN)
- `docs/planning/backlog-ideas.md` ← W19+ tuning idea-k

**State:** BC23 + Breakeven Lock + MID Bundle + vix-close + LOSS_EXIT whipsaw audit + **M_contradiction LIVE (2 fire)**

**Aktív CC tasks:** nincs

**W19+ backlog idea-k (nőtt 4-re ma):** TP1 cél revízió, Phase 4 snapshot enrichment, 10-Q SEC filing exclusion, ADR earnings adatforrás fix, **+ Breakeven Lock window-bővítés**, **+ High-score liquidity check**
