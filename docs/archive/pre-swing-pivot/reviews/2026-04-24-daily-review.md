# Daily Review — 2026-04-24 (péntek)

**BC23 Day 10 / W17 Day 5**  
**Paper Trading Day 50/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | **+$652.33** |
| Napi P&L net | **+$639.54** (commission $12.79) |
| Kumulatív P&L | **-$19.03 (-0.02%)** ← **gyakorlatilag nulla** |
| Pozíciók (új) | 3 ticker (NVDA, CSCO, ARMK) — state-split miatt 7 trade |
| Win rate | 2/3 ticker (NVDA, CSCO nyert; ARMK vesztett) |
| **TP1 hit rate** | **1/3 (33%)** ← **első TP1 hit POWI kedd óta** |
| TP2 hit rate | 0/3 (0%) |
| Exit mix | 6× MOC, 1× TP1 (NVDA), 0× SL, 0× LOSS_EXIT |
| Avg slippage | +0.13% (minden ticker negatívan csúszott) |
| Commission | $12.79 |
| SPY return | **+0.78%** (TV data +0.77%) |
| Portfolio return | +0.65% |
| **Excess vs SPY** | **-0.13%** (enyhe underperform, de bull napon pozitív) |
| VIX close | 18.72 (-3.01%) |

## Piaci kontextus

- **VIX -3.01%** — a stressz teljesen feloldódott a héten (19.49 → 18.72)
- **SPY +0.78%** — harmadik pozitív nap 5-ből, risk-on continuation
- **MID regime:** STAGFLATION Day 7 (folyamatos, nincs regime change)
- **MID events:** `/api/admin/events/recent` továbbra is csendes — az event detector konzervatív beállítása igazolódik

## Pozíciók

| Ticker | Score | Sector | Entry | Exit | P&L | Exit Type | Contradiction? |
|--------|-------|--------|-------|------|-----|-----------|----------------|
| NVDA A bracket | 93.5 | Tech/Semi | $202.65 | $208.34 | **+$278.57** | **TP1 +2.81%** | ❌ |
| NVDA B bracket | 93.5 | Tech/Semi | $202.65 | $208.22 | **+$272.69** | MOC +2.75% | ❌ |
| CSCO | 92.5 | Tech | $88.31 | $88.96 | **+$146.90** | MOC +0.74% | ❌ |
| ARMK (4 split) | 88.0 | Cons. Cyclical | $46.44 | $46.33-34 | **-$45.83** | MOC -0.22% | (nem flagged) |

**NVDA total: +$551.26**, CSCO +$146.90, ARMK -$45.83. **Két ticker fedezte a napot**, ARMK enyhén húzta le.

## A nap nagy története — NVDA TP1 chain

**Az első TP1 hit POWI (ápr 21) óta.** Nézzük az eseményeket:

```
14:18 UTC  Entry: $202.65 (planned $202.43, slippage +0.11%)
           SL $195.33, TP1 $208.34 (+2.81%), TP2 $211.88 (+4.55%)
           Bracket split: 49A + 49B

15:00 UTC  TP1 HIT @ $208.34 (csak 42 perc múlva!)
           ↓ A bracket zárva (+$278.57)
           ↓ Trail A activated @ $202.43 (breakeven)

15:15      Trail SL $202.56 (price $209.66)
15:45      Trail SL $202.61 (price $209.71)
16:25      Trail SL $202.70 (price $209.80)
16:35      Trail SL $203.21 (price $210.31) ← peak period
16:40      Trail SL $203.72 (price $210.82) ← napi max

...majd nem mozdul...

19:40 UTC  MOC submit (trail nem triggerelt)
20:00 UTC  MOC fill @ $208.22 (B bracket +$272.69)
```

**Megfigyelések:**

1. **42 perc** a belépéstől a TP1 hitig — extrém gyors. A piaci nyitás utáni első rally elvitt minket a targetre. A POWI kedden **4 óra alatt** érte el TP1-et (14:18 → 18:15), ehhez képest ez **6× gyorsabb**.

2. **A napi max $210.82 volt**, TP2 $211.88. **Csak $1.06-ra voltunk** a TP2-től, azaz +0.5%. Ha a rally folytatódott volna, mindkét bracket profitálhatott volna. De **~16:40 után konszolidálódott**, és a MOC close $208.22-n ment — **2.75%**, pontosan a TP1 szintjén.

3. **Trail B NEM aktiválódott** (csak A). Ez azért van, mert a B bracket trail trigger magasabb szinten van (~+3-4% körül), és a $210.82 max + $202.65 entry = **+4.03%** volt. **A TP2 $211.88 = +4.55%** — ennyire **NEM** ment fel az ár, így B trail SL activation sem volt.

**Összehasonlítás POWI kedd:** POWI-nál **mindkét bracket** kijátszott (TP1 → trail A → új SL → TP2). NVDA-nál **A bracket TP1 + B bracket MOC**. Kisebb mozgás, de **konzervatívabb végkimenet**: +$551 NVDA vs +$758 POWI.

## CSCO — csendes nyertes

CSCO +0.74% MOC. Trail B **aktiválódott 17:00-kor** @ $89.50, aztán fokozatosan emelkedett ($86.53 → $86.75), de **soha nem triggerelt** — az ár $89.50-90.00 sávban maradt, a trail SL alatta. MOC $88.96-on zárt.

**A trail B "passive protection"** szerepében jó — ha a rally visszaesett volna, levágta volna a pozíciót $86.75-ön (még mindig kicsi profit). **Nem aggresszív exit**, hanem **downside védelem**.

## ARMK — a nap "mainstream" vesztese

4 split, mind MOC, mind ~-$11. Összesen -$45.83 kár. **Nem drámai, de konzekvens.** 

ARMK (Aramark) egy cons. cyclical, food services, score **csak 88.0** — a nap legalacsonyabb score-ja, és **a nap egyetlen vesztese**. Ez **pozitív score korreláció egy napon belül**:

- NVDA 93.5 → +$551 (legmagasabb score, legnagyobb nyerés)
- CSCO 92.5 → +$147 (közepes)
- ARMK 88.0 → -$46 (legalacsonyabb score, egyetlen vesztes)

**Tökéletes rank korreláció ma!** Egy napos minta, de **érdekes**. A W16 inverz korrelációhoz (r=-0.414) képest ma **pozitív** — ha így folytatódik a W18-ban, az a BC23 scoring **mégis működik** hipotézist támogatja.

## 7 trade, 3 ticker — state-split újra

A hét során állandó probléma:
- Hétfő 5 ticker → ~6 trade
- Kedd 3 ticker → 9 trade (POWI 4-split + ET 3-split)
- Szerda 3 ticker → 4 trade
- Csütörtök 5 ticker → 7 trade (ET 3-split)
- **Péntek 3 ticker → 7 trade (NVDA 2-split + ARMK 4-split)**

Az ARMK 428 shares → 4 × 100+ split — IBKR paper account ~100-150 shares limit? Érdemes ellenőrizni, miért bontódik ennyire. Ez **nem új probléma**, csak ma kiugróan látványos (4 ticker és a 4-split miatt 7 trade).

## A teljes hét első ránézésre

| Nap | Net P&L | Excess vs SPY | TP1 hits |
|-----|---------|---------------|----------|
| Hétfő | -$433 | -0.21% | 0/5 |
| Kedd | **+$553** | **+1.22%** | 2/5 (POWI) |
| Szerda | +$60 | -0.94% | 0/3 |
| Csütörtök | -$227 | +0.19% | 0/5 |
| **Péntek** | **+$640** | **-0.13%** | **1/3 (NVDA)** |
| **Σ W17** | **+$593 net** | **+0.03% átlag** | **3/21 (14%)** |

**Péntek megmentette a hetet.** -$47 kumulatív W17 1-4 nap → **+$593 W17 összes**. A rendszer **utolsó nap behúzta**.

**Kumulatív állapot: -$19.03 (-0.02%)** — **gyakorlatilag breakeven**. A BC23 (ápr 13 óta) hamarosan **zéró-pont átléphet**.

## Kulcsmegfigyelések

### 1. A W17 heti mérlege: "neutrális, kicsit pozitív"

- **Net +$593** — szerény nyereség
- **Excess +0.03%** — gyakorlatilag SPY-hoz igazodik
- **TP1 hit 3/21 (14%)** — alacsony, de **nem 0**: POWI (2) + NVDA (1)
- **Win rate 3/5 nap** (kedd, szerda, péntek)

A rendszer **nem veszít, de nem is bőven nyer**. Ez **paper trading Day 63-ra** (~máj 14) is hasonló várható, ha a W18-ban nincs változás.

### 2. A TP1 pattern: érzékeny a napi volatilitásra

- TP1 hit napok: **kedd (POWI +8.96%)** és **péntek (NVDA +2.81%)**
- TP1 miss napok: **hétfő, szerda, csütörtök** — mind alacsony realized vol

**Péntek érdekes:** a NVDA +2.81% **nem kiugró**, csak **átlagos-jó** napi mozgás, és az mégis **elérte** a TP1-et (1.25×ATR). Ez azt jelenti, hogy a **1.25×ATR kalibráció néha helyes**, ha a ticker-szintű ATR reálisan tükrözi a várható mozgást.

**Összesen W17 3 TP1 hit** (POWI kedd + POWI kedd TP2 + NVDA péntek TP1). Ez a **hiba-tolerancia határán** — ha egy hét alatt csak **1** TP hit van, a partial exit nem értékes. Ha **2-3**, az **működik**.

### 3. A score-P&L korreláció — napi nézet inkonzisztens

- **Hétfő (r<0):** CNK 94.5 legnagyobb vesztes
- **Kedd (r>0):** POWI 95.0 legnagyobb nyertes
- **Szerda (kevert):** CARG 93.0 vesztett
- **Csütörtök (kevert):** POWI 95.0 legnagyobb vesztes
- **Péntek (r>0):** NVDA 93.5 legnagyobb nyertes

**Egyik napon inverz, másikon pozitív.** Heti átlagban a weekly_metrics.py fog nekünk számolni. **A W16 r=-0.414 a bázisunk** — ha a W17-ben ez **enyhébb** (pl. r=-0.2 vagy semleges), akkor a scoring-problema **javult** vagy eltűnt.

### 4. A contradiction pattern W17 végső állapota

**Összesített:**
- Flagged tickerek W17-ben: CNK, GFS, SKM, CARG, ADI, ET = **6 ticker**
- Flagged vesztes: CNK (-$122), GFS (-$83), SKM (-$149), CARG (-$172), ADI (-$27) = 5 ticker, -$553
- Flagged nyertes: **ET +$31** — 1 ticker
- **Statisztika: 5/6 (83%) vesztes, 1/6 nyertes**

**A pattern nem 100%, de erős.** Az **M_contradiction multiplier ×0.80** konzervatív paraméterrel továbbra is indokolt.

### 5. Leftover-ek — 5 napja egyaránt

CRGY + AAPL minden nap. **Hétvégi Tamás-teendő** továbbra is.

### 6. MID webhook/events — csendes hét

**0 event egész héten.** A STAGFLATION regime **stabil** maradt 5 napig (Day 3 → Day 7). Ez **jól kalibrált érzékenység** — a detector nem zajt generál, csak valódi regime-váltásra reagál.

## Anomáliák

- **daily_metrics időben megérkezett**, nincs probléma
- **ARMK 4-split újra** — érdekes lenne holnapután (hétfő) megnézni, hogy az 428 shares miért bontódik 100+100+100+128-ra, nem 250+178-ra
- **Telegram regresszió** változatlanul él
- **CRGY + AAPL** leftover-ek

## Teendők

- **Ma este:** nincs
- **Hétvégén:**
  - Tamás: CRGY + AAPL leftover nuke
  - Chat: W17 heti metrika teljes elemzése (külön dokumentum)
  - Chat: MID vs IFDS sector rotation informális összehasonlítás (CAS heatmap alapú)
- **Hétfő (ápr 27):**
  - W18 ápr 27-én CC megkapja a `2026-04-21-mid-bundle-integration-shadow.md` task-ot
  - Normál pipeline BC23 folytatódik

## Kapcsolódó

- `state/phase4_snapshots/2026-04-24.json.gz`
- `logs/pt_events_2026-04-24.jsonl`
- `logs/pt_eod_2026-04-24.log`
- `logs/cron_intraday_20260424_161500.log`
- `state/daily_metrics/2026-04-24.json`
- **W17 heti metrika** — a scripthúzó Telegram küldte, de `docs/analysis/weekly/2026-W17.md` még nem látszik a mappában (generálás folyamatban, vagy más útvonalra ment)
