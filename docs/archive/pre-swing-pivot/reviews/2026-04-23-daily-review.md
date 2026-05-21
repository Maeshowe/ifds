# Daily Review — 2026-04-23 (csütörtök)

**BC23 Day 9 / W17 Day 4**  
**Paper Trading Day 49/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$201.44 |
| Napi P&L net | **-$226.59** (commission $25.15) |
| Kumulatív P&L | **-$671.36 (-0.67%)** |
| Pozíciók (új) | 5 ticker (POWI, ADI, WMT, ET, POST) — state-split miatt 7 trade |
| Win rate | 2/5 ticker (WMT, ET nyert; POWI, ADI, POST vesztett) |
| TP1 hit rate | 0/5 (0%) |
| TP2 hit rate | 0/5 (0%) |
| Exit mix | 6× MOC, 1× LOSS_EXIT (POWI), 0× SL, 0× TP |
| Avg slippage | **+0.07%** (minden ticker negatívan csúszott) |
| Commission | $25.15 ← **napi maximum eddig** |
| SPY return | -0.39% |
| Portfolio return | -0.20% |
| **Excess vs SPY** | **+0.19%** ← enyhe outperform, de negatív nap |
| VIX (Phase 0 intraday) | 19.13 (normal) |

## Piaci kontextus

- **SPY -0.39%** — tegnapi bull nap után enyhe lefordulás
- **VIX 19.13 intraday** — szintén csökkent a szerdai 18.85-ről (trend: eső vol)
- **MID regime:** STAGFLATION Day 6 (stabil)
- **Tendencia:** a szerdai risk-on bounce megingott, de nincs pánik

## Pozíciók

| Ticker | Score | Sector | Entry (avg fill) | Exit | P&L | Exit Type | Contradiction? |
|--------|-------|--------|------------------|------|-----|-----------|----------------|
| POWI | **95.0** | Tech/Semi | $74.00 | $72.29 | **-$253** | **LOSS_EXIT -2.31%** | ❌ Nincs |
| ADI | 93.5 | Tech/Semi | $404.63 | $403.99 | -$27 | MOC -0.16% | ✅ ár 7.9% consensus fölött |
| WMT | 91.5 | Cons. Defensive | $131.57 | $132.07 | **+$76** | MOC +0.38% | ❌ Nincs |
| ET | 91.5 | Energy | $19.11 | $19.14 | +$31 (3 split) | MOC +0.16% | ✅ 3 earnings miss |
| POST | 91.5 | Cons. Defensive | $104.90 | $104.64 | -$29 | MOC -0.25% | ❌ Nincs |

## ⚡ A nap nagy története — POWI paradoxon

**POWI, score 95.0, a tegnapi napi nyertes (+$758), MA legnagyobb vesztes (-$253).**

Ugyanaz a ticker, ugyanaz a score, **egymást követő nap**. A pipeline **nem tudja**, hogy tegnap POWI-ban voltunk; a flow/funda/tech scoring megint 95-öt adott, és a rendszer **újra vett** — pont azon a napon, amikor a ticker természetesen **korrigált** a tegnapi +8.96% után.

**Időzítés:**
```
14:18 UTC  Entry $74.00 (pozitív slippage, planned $73.91 → fill $74.00 = +0.12%)
           SL $69.19, TP1 $77.84, TP2 $80.20
17:15 UTC  LOSS_EXIT @ $72.29 (-2.31%)
           ~3 óra a belépéstől a bevágásig
```

**A POWI 2 napos P&L összesen:**
- Kedd: +$758 net (TP1 + TP2 chain)
- Csütörtök: -$253 net (LOSS_EXIT)
- **Összesen: +$505 net** — **mean reversion trap-be estünk**, de **nettóban** még mindig **pozitív**

**Tanulság:** ez a **mean reversion nap** klasszikus mintája. Egy +9%-os nap után a ticker **statisztikailag is várhatóan** korrigál a következő napon. A BC23 scoring **nem veszi ezt figyelembe** — a "ticker már volt portfolio-ban tegnap" állapot nem csökkenti a score-t. **Ez egy W18+ megfontolás:**

**Javaslat a backlog-ideas-be:** **"Recent Winner Penalty"** — ha ticker az elmúlt 3 napban ±5%-nál nagyobb napot csinált, `M_recency` multiplier × 0.80. Célja: elkerülni a mean reversion trap-et ismétlődő magas-momentum tickereken. **Ez NEM most**, csak feljegyzés.

## A contradiction pattern FINOMODIK — első kivétel!

**Nagyon érdekes fordulat.** Ma **2 flagged + 3 nem-flagged** ticker volt:

| | Flagged | Nem-flagged |
|---|---------|-------------|
| Nyerés | **ET: +$31** ⭐ ELSŐ KIVÉTEL | WMT: +$76 |
| Vesztés | ADI: -$27 | POST: -$29, **POWI: -$253** |

**ET +$15 (3 split, összesen +$31) nyert, pedig a Company Intel explicit CONTRADICTION flag-elt** ("Serial earnings misses over three quarters contradict the 91.5 IFDS score"). **Ez az első eset W17 alatt, amikor egy flagged ticker nyer.**

**Frissített contradiction statisztika:**

| | Flag + veszít | Flag + nyer | Nem-flag + veszít | Nem-flag + nyer |
|---|---|---|---|---|
| **W17 1-3 nap** | 4 (CNK, GFS, SKM, CARG) | **0** | 1 (GME) | 5 |
| **W17 Day 4 (+ma)** | +1 (ADI) | **+1 (ET)** | +2 (POST, POWI) | +1 (WMT) |
| **Σ eddig** | **5** | **1** | **3** | **6** |

**Korábbi hipotézis:** "flag = vesztes, 100% pattern"
**Valóság most:** **5/6 flagged vesztes** (83%), de **nem 100%**.

**Ez gyengíti** az M_contradiction multiplier javaslatot, de **nem semmisíti meg**. 5/6 = 83% tippelési arány **még mindig erős** signal. De: **nem abszolút**. Az M_contradiction-t így **konzervatívabban** kellene bevezetni: **×0.8** (enyhe penalty), **nem ×0.5 vagy ×0.7**.

Ráadásul **a flagged tickerek átlagos P&L-je még így is negatív**: 
- Flag összesített P&L: -$354 + -$27 + +$31 = **-$350 (6 ticker)**
- Non-flag összesített P&L: +$121 - $36 - $149 (napi csúcsok) = komplex számolás...

Egyszerűbben: **a flagged tickerek kumulatív P&L-je** W17 4 napon: **-$633** (CNK+GFS+SKM+CARG+ADI+ET). **Ez egy portfolio, ami flag-mentes lenne, -$633-kal lenne jobb**. Vagyis **ha nem kereskedtük volna ezt a 6 tickert, a W17 eddig +$586 lenne -$47 helyett**.

## Slippage — ma mindenki ellenünk

**Átlag +0.07%**, ami **negatív slippage** (rosszabb fill mint tervezett):

| Ticker | Planned | Fill | Slippage | $ hatás |
|--------|---------|------|----------|---------|
| POWI | $73.91 | $74.00 | **+0.12%** | ~-$13 (148×$0.09) |
| ADI | $403.85 | $404.63 | **+0.19%** | ~-$33 (42×$0.78) |
| WMT | $131.57 | $131.57 | 0.0% | $0 |
| ET | $19.11 | $19.11 | 0.0% | $0 |
| POST | $104.88 | $104.90 | +0.02% | ~-$2 |

**POWI + ADI együtt ~$46 extra kár** csak a fill minőség miatt. A POWI napi -$253-ból ez ~5%, az ADI -$27-ből ~100%+. **ADI teljes vesztesége a slippage-ből jön** — ha a fill a tervezett $403.85-en ment volna, a MOC close $403.99 → **+$5.88 nyereség** lett volna.

Ez **5 ticker slippage-e nem volt véletlen**: mind a 3 fill-elt ticker (POWI, ADI, POST) **felfelé** csúszott, 2 (WMT, ET) flat maradt, **egy sem csúszott lefelé**. Ma a piac nem nekünk kedvezett.

## Commission napi csúcs

**$25.15 commission**, eddigi W17 legmagasabb:
- Hétfő: $18.46 (5 ticker)
- Kedd: $12.99 (3 ticker, de POWI 4 split)
- Szerda: $13.02 (3 ticker)
- **Csütörtök: $25.15 (5 ticker, 10 bracket order + 7 close = 17+ tranzakció)**

A `scripts/paper_trading/logs/pt_eod.log` szerint **7 trade closed** (POWI split 2, ET split 3, WMT 1, POST 1, ADI 1). Ez ~$12 IBKR kommisszió fixkormatikus + a bracket order submit, monitoring fee. **Nem magas**, de **napi összegben** látszik a sok szétaprózott pozíció hatása.

## W17 4 napos trend

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív |
|-----|-----|-----------|--------|---------|-----------|
| Hétfő | -0.20% | -0.41% | -0.21% | -$433 | -$1,109 |
| Kedd | -0.65% | +0.57% | **+1.22%** | +$553 | -$543 |
| Szerda | +1.01% | +0.07% | -0.94% | +$60 | -$470 |
| **Csütörtök** | **-0.39%** | **-0.20%** | **+0.19%** | **-$227** | **-$671** |
| **Σ 4 nap** | **-0.23%** | **+0.03%** | **átlag +0.07%** | **-$47** | — |

**Heti kép (még 1 nappal a végéig):**
- A portfolio **gyakorlatilag neutrális** a SPY-hoz képest (+0.07% átlagos excess)
- Az abszolút P&L **-$47 net** — essentially flat
- **TP1 hit rate 2/18 trades** (11%, csak POWI tegnap) — továbbra is alacsony
- **Loss_exit 2 nap** (SKM hétfő -$298, POWI ma -$253) — ~-$551 loss_exit P&L

**Mit mond ez a péntek heti metrika szempontjából:** a rendszer **nem veszít, nem is nyer**. **Kockázat-kontrollált, de alpha-szegény.** Ha péntek valami drámait nem hoz, a W17 heti riport **"unalmas" de nem rossz**.

## Kulcsmegfigyelések

### 1. A POWI paradoxon — mean reversion egy egyedi tickeren

Egymást követő napokon magas score ugyanazon tickeren **figyelmeztetés**: a rendszer nem **frissíti** a ticker-kockázatot a tegnapi mozgás alapján. **Szóban:** "tegnap +8.96%, ma várhatóan korrigál" — **számszerűen:** a scoring-ban nincs ilyen feature.

**Két lehetséges W18+ megoldás:**
- (A) **Recent winner penalty** az egyedi tickerre (backlog-idea fent)
- (B) **Position dedup** — "ha a ticker az elmúlt 3 napban szerepelt a portfolio-ban és már zárt, skip today" (egyszerűbb, konzervatívabb)

Az (A) elegánsabb (scoring-alapú), a (B) biztosabb (hard filter). **Nem most kell dönteni.**

### 2. A contradiction pattern tompult, de erős

5/6 (83%) flagged ticker vesztett W17 4 napon. Az ET-kivétel **értékes adat** — a CONTRADICTION flag **nem 100% prediktor**, csak **erős statisztikai jel**. Az M_contradiction multiplier bevezetése **igazolható**, de **konzervatív** értékkel:

**Régi javaslat:** ×0.5 vagy ×0.7
**Új javaslat:** ×0.80 (20% penalty) — még ha néha téved is, **az átlagos hatás** pozitív

**Megfontolandó:** W18 elején **két heti metrika együtt** (W16 + W17) ad jobb képet, mint egy hét. Esetleg érdemes a W18-at **még egy hét BC23 változatlanul** futtatni (10 napos adat), aztán W19 elején dönteni. **3 hetes BC23 adat > 2 hetes**.

### 3. A TP1 és TP2 0/18 a W17 óta (kivéve POWI kedd)

**Egész W17 alatt TP1 hit: 2 (mindkettő POWI tegnap)**. 17 egyéb trade, TP1 hit = 0. A POWI egyetlen +8.96% napot hozott, **ami elérte a TP1 + TP2 targeteket**. Minden más napon a TP1 ATR-alapú távolsága (1.25×ATR = ~3-6%) **túl nagy** az intraday mozgáshoz.

**Megerősített finding:** a TP1 1.25×ATR **csak speciális napokon** működik. Az átlag napok **MOC-al zárulnak**, a trail ritkán triggerel, a loss_exit időnként megvág.

**BC24+ megoldás** a TP1 skálázásra (GARCH-alapú realizált vol) már szerepel a backlog-ideas-ben. Ma **megerősödött** ez a javaslat.

### 4. Leftover-ek: CRGY, AAPL — mindennap

4 napja egymás után megjelennek. **Hétvégi nuke** muszáj lesz. Már várja Tamás.

## Anomáliák

- **Nincs új anomália ma.** A daily_metrics időben megérkezett (a tegnapi ~1 órás késés nem ismétlődött).
- **Telegram regresszió** továbbra is él — "4/6 breakdown" hiányzik.
- **CRGY + AAPL leftover** — 4 nap óta folyamatosan, **hétvégi Tamás-feladat**.

## Teendők

- **Ma este:** nincs
- **Holnap (péntek ápr 24):** 
  - Normál pipeline, 5. W17 nap
  - **Este 22:00 CEST:** W17 heti metrika futtatás — BC23 2 hetes kiértékelés
  - Péntek utáni Telegram összesítés vs a hét többi napja
- **Hétvégén:**
  - Tamás: CRGY + AAPL leftover nuke
  - Chat: MID vs IFDS sector összehasonlítás (CAS heatmap-alapú, informális)

## Kapcsolódó

- `state/phase4_snapshots/2026-04-23.json.gz`
- `logs/pt_events_2026-04-23.jsonl`
- `logs/pt_eod_2026-04-23.log`
- `logs/cron_intraday_20260423_161500.log`
- `state/daily_metrics/2026-04-23.json`
