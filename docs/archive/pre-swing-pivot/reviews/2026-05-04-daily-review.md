# Daily Review — 2026-05-04 (hétfő)

**BC23 Day 16 / W19 Day 1**
**Paper Trading Day 56/63**
**M_contradiction LIVE első nap**

**Adat-frissesség:** state/.last_sync = 2026-05-04T20:13:55Z (hétfő 22:13 CEST, post-EOD)

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$154.70 |
| Napi P&L net | **-$190.72** (commission $36.02) |
| Kumulatív P&L | **-$1,141.38 (-1.14%)** |
| Pozíciók (új) | 5 ticker (VTR, OII, NOV, BG, AGNC) — **13 trade** (split-ek) |
| Win rate ticker szinten | 3/5 (BG, NOV, OII nyertek; AGNC, VTR vesztettek) |
| TP1 hit rate | 0/5 (0%) |
| TP2 hit rate | 0/5 (0%) |
| Exit mix | **6× LOSS_EXIT** (mind AGNC), 7× MOC, 0× SL, 0× trail, 0× TP |
| Avg slippage | +0.10% (BG +0.27% legrosszabb, AGNC -0.09% kedvező) |
| Commission | $36.02 ← **magasabb** mint W18 átlag ($23-28), 13 trade miatt |
| SPY return | -0.37% |
| Portfolio return | -0.15% |
| **Excess vs SPY** | **+0.21%** ⭐ outperform negatív SPY napon |
| VIX close | **18.30** (Δ=+9.65%, vissza 18 fölé!) |

## ⭐ A hét első napja — outperform a piaccal szemben

**Annak ellenére**, hogy az AGNC -$380.31 single-ticker veszteséget termelt (-22% AGNC P&L a portfolio-ban), a **3 nyertes ticker (BG, NOV, OII) +$316.41 net hozott**, és a VTR -$90.80-cal kis vesztes maradt.

**A piaci kontextus:** SPY -0.37%, VIX +9.65%-ra emelkedett (vissza 18 fölé). Ez **egyértelműen risk-off** nap volt, és **mi marginálisan jobban teljesítettünk a piacnál**.

## Pozíciók részletei

### Nyertesek (3)

**BG (Bunge, agriculture, score 91.5):** 2-split, entry $126.17 (slippage **+0.27%** rossz), MOC $127.62/$127.64 = **+$178.81 össz** (145 + 33.81). +1.15% intraday — **a nap legnagyobb % nyerő**. **Breakeven Lock 17:00:19 CEST** aktivált — SL $123.46 → $125.83 (entry). Az ár sosem esett vissza, MOC-on profit.

**NOV (NOV Inc., oilfield services, score 92.0):** 2-split, entry $19.80 (slippage **0.0% perfekt**), MOC $19.94 = **+$88.20 össz** (70 + 18.20). +0.71% intraday. Trail aktivált 18:40 CEST, **csak +0.51%-ra**, nem érte el a Breakeven Lock window-ot.

**OII (Oceaneering, marine services, score 93.0):** Entry $37.04 (slippage +0.16%), MOC $37.30 = **+$49.40**. +0.70% intraday. Trail 18:15 CEST aktivált, **a 19:00 window előtt**, így **NEM** kapott Breakeven Lock floor-t. Folyamatosan emelkedett a trail SL ($34.29 → $34.42), de irrelevánssá vált.

### Vesztesek (2)

**VTR (Ventas, healthcare REIT, score 93.5 — legmagasabb!):** 2-split, entry $88.23 (slippage +0.17%), MOC $87.83 = **-$90.80 össz** (-40 - 50.80). -0.45% intraday. **Csendes underperformer** egész nap, nem trail, nem LOSS_EXIT. **A legmagasabb score-ú ticker** kis vesztest hozott — érdekes adatpont a score korreláció kérdéséhez.

**AGNC (American Capital Agency, mortgage REIT, score 91.0 — legalacsonyabb):** 6-split (!), entry $10.87 (slippage **-0.09% kedvező**), **LOSS_EXIT @ $10.66** 18:25 CEST (-2.02%). **6 különálló split** összes -$380.31 (21+21+21+24.99+45.99+246.33).

### Az AGNC eset részletes idővonala

```
14:18 CEST  Submit @ $10.88 limit (slippage -0.09% → fill $10.87)
            6 különálló bracket-szegmens: 219 + 100 + 1173 + 100 + 119 + 100 = 1811 share
            (a CC-féle implicit split-et a bracket méret korlát triggerelte: MAX_ORDER_SIZE=500)

~17:21 CEST 10-Q SEC filing publikálva (TradingView headline 15:21 EDT):
            "AGNC Investment Corp. 1Q 2026: Net income $(148)M, EPS $(0.17) — 10-Q Summary"

18:25 CEST  AGNC ár -2.02%-ra zuhan ($10.66) → LOSS_EXIT trigger mind a 6 bracket-en
            Exit aggregát: 1811 share @ $10.66
            P&L: -$380.31 net

18:30 CEST  phantom_filtered AGNC (helyes viselkedés, monitor felismeri)
```

**Strukturális gap, amit ma azonosítottunk:**

A Phase 2 `earnings_exclusion_days = 7` szabály **NEM zárta ki** az AGNC-t, mert:
- Q1 2026 earnings release **ápr 21-én** volt (13 nappal korábban, kívül az ablakon)
- Következő earnings: **jún 17** (>7 nap a jövőben)
- **DE** a 10-Q SEC filing **MA jelent meg** (~17:21 CEST), és érdemi piaci hatást termelt

**Backlog idea ma rögzítve:** `docs/planning/backlog-ideas.md` — "10-Q / 10-K SEC Filing Exclusion" (W19+ scope, P2, ~2-3h CC).

## ⭐ M_contradiction LIVE első nap — viselkedési mérleg

A CC `f6c4d9e` deploy szombat délután. **Hétfő reggel volt a feature első éles napja.**

| Ticker | Score | Contradiction flag | M_contradiction multiplier |
|--------|-------|---------------------|----------------------------|
| VTR | 93.5 | **No** (Telegram) | 1.0 (default) |
| OII | 93.0 | **No** | 1.0 |
| NOV | 92.0 | **No** | 1.0 |
| BG | 91.5 | **No** | 1.0 |
| AGNC | 91.0 | **No** | 1.0 |

**0/5 fire — egyetlen ticker sem kapott multiplier-t.** Az audit log-ban semmilyen `[M_CONTRADICTION]` entry nem szerepel.

**Ez NEM hiba** — a feature pontosan úgy működik, ahogy a spec rögzítette. A 4 OR-feltétel egyike sem teljesült mind az 5 tickerre.

### Az AGNC kritikus elemzése

Az AGNC esete **a feature működésének limitációját** illusztrálja:

1. **Earnings beats:** Q1 2026 BEAT (adjusted EPS) — FMP `/stable/earnings` valószínűleg 2-3/4 beat-et ad → **NEM fire** (`< 0.5` strict)
2. **Price vs consensus:** $10.88 vs $11.13 = **-2.2% alatt** → NEM fire
3. **Price vs analyst high:** $10.88 vs ~$13 → NEM fire
4. **Recent downgrades:** UBS Neutral maintain, JPM Overweight maintain → NEM fire

**A 10-Q közzétételét** (a tényleges piaci trigger) **a feature nem érzékeli**. A `< 0.5` strict küszöb + REIT-specifikus adjusted vs GAAP különbség + 10-Q event hiánya **együttesen** azt jelenti: az AGNC -$380 elkerülhetetlen volt a jelen feature-rel.

### Kvalifikáció — a smoke teszt megerősítve

A CC szombati smoke teszt 5 historikus eset alapján **csak CARG fired-olt** (1/5). **Hétfő LIVE 5 esetből 0 fired** — összhangban a smoke eredménnyel. **A feature ritka outlier protection**, nem regular signal.

**Realisztikus W19 várakozás:** ~1-3 fire / hét — ez most még **adat-gyűjtés fázisban** van, és a tényleges hatás (megtakarított $) csak W19 vége után mérhető.

## Score → P&L napi nézet

| Ticker | Score | P&L net | Win? | Exit |
|--------|-------|---------|------|------|
| **VTR** | **93.5** | -$90.80 | ✗ | MOC |
| OII | 93.0 | +$49.40 | ✓ | MOC |
| NOV | 92.0 | +$88.20 | ✓ | MOC |
| BG | 91.5 | +$178.81 | ✓ | MOC |
| **AGNC** | **91.0** | -$380.31 | ✗ | LOSS_EXIT (6-split) |

**Score korreláció ma vegyes:** a legmagasabb score (VTR 93.5) vesztett, a legalacsonyabb (AGNC 91.0) **nagyon** vesztett. **De** a két középső score (OII 93, NOV 92, BG 91.5) **mind nyert**. **Spearman r ≈ 0** napon belül.

**Ez NEM nagy meglepetés** — az 55 napi scoring validation Pearson r ≈ 0 finding-ját **megerősíti** a hétfő-i nap. A score önmagában nem prediktív; **a flow score (komponens) az egyetlen statisztikailag jelentős prediktor**.

## Breakeven Lock napi mérleg

| Ticker | trail aktiváció | Breakeven Lock alkalmazás | Eredmény |
|--------|-----------------|---------------------------|----------|
| BG | ✓ 17:00:17 (window-ban) | ✓ 17:00:19 ($123.46→$125.83) | MOC nyertes (+$178.81) |
| OII | ✓ 18:15 CEST (window előtt) | ✗ NEM alkalmazódott | MOC nyertes (+$49.40) |
| NOV | ✓ 18:40 CEST (window előtt) | ✗ NEM alkalmazódott | MOC nyertes (+$88.20) |
| VTR | ✗ nem aktivált | ✗ | MOC vesztes (-$90.80) |
| AGNC | ✗ nem aktivált (LOSS_EXIT 18:25-kor) | ✗ | LOSS_EXIT (-$380.31) |

**1/5 BG-n a Breakeven Lock alkalmazódott**, és a feature pontosan úgy működött ahogy tervezve: SL emelve entry-re, az ár sosem esett vissza, MOC-on profit.

## A 10-Q event mint új strukturális finding

Az AGNC eset megmutatta, hogy **az earnings exclusion (7 nap) nem fed le minden binary event-et**. A 10-Q SEC filing, ami **2-3 héttel** az earnings release után közzéteszik, **érdemi piaci hatást termelhet** — különösen REIT-eknél, ahol az adjusted vs GAAP különbség jelentős.

**Backlog idea rögzítve** a `docs/planning/backlog-ideas.md`-ben:
- **10-Q / 10-K SEC Filing Exclusion** — Phase 2 bővítés
- **Adatforrás:** SEC EDGAR API (ingyenes)
- **Effort:** ~2-3h CC
- **Priority:** P2, **W19+ scope**
- Ha W19-W20 alatt **még** ilyen 10-Q-driven veszteség jelentkezik, **P1-re emelhető**

## VIX visszament 18 fölé — Day 63 keret implikáció

**A VIX 16.69 → 18.30** (+9.65% napi). Ez **fontos váltás**:

**Az utóbbi 6 napi VIX:**
- W18 hét: 18.20, 18.04, 18.51, 16.99, 16.69 (átlag 17.69)
- **W19 Day 1: 18.30** ← visszatértünk a 18 fölé

**Mit jelent:** ha a VIX **stabilan** 18 felett marad a következő napokban, akkor a **leállítási feltétel** ("20+ napon át VIX > 18 mellett kumulatív excess vs SPY < -1.5%") **aktiválódhat** újra.

**Jelenlegi excess vs SPY 5 napi átlag:** -0.99% (W18 -1.90% + ma +0.21%, 6 nap = -0.28% → de hosszú távban a W18 dominál).

**A leállítási feltétel távolsága:** kumulatív excess a -1.5%-tól **távol** (-0.28% jelenleg), tehát **nincs panik-pillanat**. **De** a VIX-feltétel mostantól **aktív monitoring** alá kerül.

## A W18 → W19 átmenet adatai

| Metrika | W18 hét összesítő | W19 Day 1 |
|---------|-------------------|-----------|
| Net P&L | -$1,106 | -$190.72 |
| Excess vs SPY | -1.90% | **+0.21%** ⭐ |
| Win rate (ticker) | 11/38 (29%) | 3/5 (60%) |
| LOSS_EXIT | 7 (W18 hét) | 6 (mind AGNC, ma) |
| TP1 hits | 0 | 0 |
| Avg score | 91.1 | 92.2 |

**A W19 Day 1 erősebb start mint a W18 átlag** — ticker win rate 60% vs 29%, excess +0.21% vs -1.90% átlag. **De** egy nap nem trend.

## Day 63 keret — hétfő esti állapot

| Metrika | Érték | Status a kerethez képest |
|---------|-------|--------------------------|
| Day | 56/63 | **7 nap van hátra** |
| Kumulatív P&L | -$1,141 (-1.14%) | **biztonságos sávban** (paper folytatás default) |
| ÉLESÍTÉS távolság | +$4,141 a +$3,000-hoz | **7 nap × +$591/nap → NEM realisztikus** |
| LEÁLLÍTÁS távolság | excess -0.28% távol a -1.5%-tól | **biztonságos sávban** |
| 6 napi excess vs SPY átlag | -0.28% | 5 nap W18 + 1 nap W19 |
| VIX W19 átlag (Day 1) | 18.30 | **18 fölött, monitor aktív** |

**Realisztikus Day 63 várt kimenet:** **PAPER FOLYTATÁS (default)** — a kumulatív P&L valószínűleg -$1,500 és -$500 között lesz, ami **távol** mind az élesítési, mind a leállítási küszöbtől.

**6 nap maradt** Day 63-ig. Az átlagos napi alpha cél (paper folytatáshoz) **~+$50-100 / nap**. A mai +$0 (technikailag -$191) ezt nem érte el, **de** az excess vs SPY pozitív volt — ami a **fontosabb metrika**.

## Anomáliák

- **20:00 CEST IBKR API quirk events** továbbra is — LION/SDRL/DELL/DOCN phantom (a 2026-04-14 cleanup task Bug 3, régóta ismert)
- **CRGY/AAPL leftover phantoms** — `monitor_positions.py` 20:00 CEST után újra "leftover_found" → már szombat reggel megerősítettük, hogy ez phantom (`monitor_positions.py` BUG, nem valódi pozíció)
- **AGNC bracket-split mechanika érdekes:** 1811 share **6 különálló bracket-szegmenssé** alakult (219 + 100 + 1173 + 100 + 119 + 100 = 1811). A `MAX_ORDER_SIZE = 5000` (config) nem indokolja — a tényleges IBKR fill mechanika split-elt. Megfigyelendő.

## Kulcsmegfigyelések

### 1. Outperform negatív SPY napon — első W19 adatpont

A SPY -0.37%, VIX +9.65% napon **+0.21% excess**. Ez **a swing trading rendszer természetes ereje** — risk-off napokon a stock-pickking jobban teljesít a passzív long-only-nál.

### 2. AGNC eset = 10-Q event gap megerősítése

A 7 napos earnings exclusion **nem védett** a 10-Q SEC filing ellen. Backlog idea rögzítve, W19+ implementálható ha még egy ilyen veszteség jelentkezik.

### 3. M_contradiction LIVE — adat-gyűjtés fázis

0/5 fire ma. **Konzisztens** a smoke teszt eredményével (1/5 fire CARG-on). A feature **outlier protection**, nem regular signal. **Ne pánikolj** ha a következő héten is 0-2 fire jön — **ez a tervezett viselkedés**.

### 4. Score korreláció — egyértelmű napi szóródás

Pearson r ≈ 0 a hétfői nap (VTR 93.5 vesztett, AGNC 91.0 vesztett, középső score-ok nyertek). **Megerősíti** az 55 napi validation finding-ot.

### 5. Breakeven Lock pontos időablak

A 19:00:00-19:04:59 CEST window továbbra is **konzisztens** — ma BG az egyetlen ticker, amelyik a window-on belül aktivált. OII (18:15) és NOV (18:40) **a window előtt** — a feature design szándékosan szigorú a délutáni stabilitás-ablakra.

## Holnap (kedd máj 5) várnivalók

- **Reggeli ellenőrzés:** sync, MID snapshot (Stagflation Day 16/28?)
- **CC:** semmi új feladat — a M_contradiction LIVE viselkedés mérése zajlik
- **Pipeline:** normál ritmus, BC23 W19 Day 2

## Hétközi (W19) teendők (Tamás)

- **Csütörtök máj 7:** kis backlog átnézés ha CC-nek szabad kapacitása van (TP1 cél revízió, Phase 4 snapshot enrichment)
- **Csütörtök máj 8 22:00:** **W19 weekly metrika** futtatás
- **Csütörtök máj 14 09:00:** **Day 63 KIÉRTÉKELÉS** (Reminder)

## Kapcsolódó

- `state/phase4_snapshots/2026-05-04.json.gz`
- `logs/pt_events_2026-05-04.jsonl` ← **AGNC LOSS_EXIT 6-split** + 1× breakeven_lock_applied (BG)
- `logs/pt_eod_2026-05-04.log`
- `state/daily_metrics/2026-05-04.json` ← **vix_close = 18.30**, kumulatív -$1,141
- `docs/planning/backlog-ideas.md` ← **10-Q SEC filing exclusion** rögzítve (új)
- **State:** BC23 + Breakeven Lock + MID Bundle + vix-close + LOSS_EXIT whipsaw audit + **M_contradiction LIVE**
- **Aktív CC tasks:** nincs (M_contradiction deployed, sync improvement deployed)
- **W19+ backlog:** TP1 cél revízió, Phase 4 snapshot enrichment, 10-Q SEC filing exclusion
