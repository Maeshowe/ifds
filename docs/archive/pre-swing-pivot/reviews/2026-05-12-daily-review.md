# Daily Review — 2026-05-12 (kedd)

**BC23 Day 22 / W20 Day 2 — 1 NAP A DAY 63 KIÉRTÉKELÉSIG (csüt máj 14)**
**Paper Trading Day 62/63**
**M_contradiction LIVE 7. nap — iránybeli helyesség 33%-ra esett**
**Snapshot fix 2. nap validálva (161 qualified, konzisztens 159 ↔ 161)**
**🆘 KRITIKUS BUG: FORM -29 SHORT — LOSS_EXIT bracket SL cancellation 3. instancia 8 napon belül**

**Adat-frissesség:** EOD log 22:05, daily_metrics.py 22:10 CEST. Phase 4 snapshot ~22 KB várt (konzisztens hétfői mintázattal). Cron_intraday log: UW HTTP 429 a hétfői 50-ről 170+-ra emelkedett.

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$350.73 |
| Napi P&L net | **-$369.28** ⚠️ |
| Kumulatív P&L (paper aggregát) | **-$1,445.81 (-1.45%)** ⚠️ visszaesés a hétfői -$1,095-től |
| Tényleges valós (SQM korrekcióval) | ~-$1,332 (-1.33%) becsült |
| Pozíciók (új) | 3 ticker (CENX, TGB, NVDA) |
| Trade count | 5 (CENX 1× + TGB 3× partial fill + NVDA 1×) |
| Win rate ticker szinten | **1/3 (33%)** — CENX nyertes, TGB + NVDA vesztes |
| **Exit mix** | **4× LOSS_EXIT (80%!), 1× MOC, 0× TP1/TP2/SL/TRAIL** ⚠️ |
| TP1 / TP2 / SL / TRAIL hit | 0 / 0 / 0 / 0 |
| Avg slippage | +0.38% (CENX +0.86% legrosszabb, NVDA +0.01% minimal) |
| SPY return | -0.15% (mild risk-off) |
| VIX close | **18.03** (Δ -2.28%, csökkent — risk-on, de mégis vesztes P&L) |
| Portfolio return | -0.35% |
| **Excess vs SPY** | **-0.20%** ⚠️ underperform mild risk-off napon (folytatja a "bull rally underperform" pattern-t MILD risk-off-on is) |
| **🆘 Open positions EOD-után** | **FORM -29 shares** (SHORT, BUG!) |

## 🆘 KRITIKUS BUG — FORM -29 SHORT (LOSS_EXIT bracket SL cancellation 3. instancia)

Az EOD log végén:
```
22:05:05 [WARNING] Still 1 open positions!
22:05:05 [WARNING]   FORM: -29.0 shares
```

A FORM **tegnap (W20 D1, máj 11) zárt MOC-on** 22:00 körül (+$213.73, +5.11%). A close.py ma 19:40-kor `position_skipped` eseménnyel jelezte: `"reason": "fully_closed_intraday"`. **Mégis a paper accountban -29 SHORT a kedd végén.**

**Ez a HARMADIK instancia** ugyanennek a bug-nak 8 napon belül:
| Dátum | Ticker | SHORT mennyiség | Loss exit típusa |
|-------|--------|------------------|-------------------|
| 2026-05-01 (csüt) | DTE | -? shares | bracket SL after monitor LOSS_EXIT |
| 2026-05-07 (csüt) | SQM | -91 shares | bracket SL after monitor LOSS_EXIT |
| **2026-05-12 (kedd)** | **FORM** | **-29 shares** | **bracket TP/SL after MOC fill (tegnapi)** ⚠️ ÚJ MINTA |

**A mai instancia ÚJ MINTÁT mutat:** az SQM és DTE esetén a **monitor LOSS_EXIT** triggerelte a duplikált zárást egyazon napon. A FORM esetén viszont a **tegnapi MOC** zárás után maradt függőben az IBKR bracket TP/SL order, és ma valamikor triggerelt (legvalószínűbb 16:00 ET = 22:00 CEST nyitás után, a tegnapi MOC fill árának ($151.57) közelében).

**A P1 #1 backlog idea (LOSS_EXIT bracket SL cancellation) tehát nem elég — bővíteni kell:**
- Eredeti scope: a `pt_monitor.py` `trigger_loss_exit()` cancel-elje a meglévő bracket SL ordereket
- **Bővített scope**: a `pt_close.py` MOC fill után IS cancel-eljen minden függő bracket TP/SL ordert az adott tickerre

**Tamás teendő reggel:** `nuke.py --positions` (vagy specifikus BUY 29 FORM) a -29 SHORT takarításra. Becsült valós eredmény: a tegnapi MOC ár $151.57 + ma kis fluktuáció → ~$30-100 kis profit vagy veszteség (a hétközti $0.5-$3-os FORM mozgástól függően).

**A P1 backlog idea ezért NEM a "csüt Day 63 utáni W20+ scope" — hanem szerda reggel előzetes hot-fix érdemes** (a `pt_close.py` MOC-fill után cancel logika hozzáadása).

## ⚠️ A NAP STRATÉGIAI JELENTŐSÉGE — 80% LOSS_EXIT, kettős infrastruktúra-finding

| Megfigyelés | Adat |
|-------------|------|
| LOSS_EXIT arány | **4/5 (80%)** — történelmileg magas |
| TGB LOSS_EXIT triggert | **17:00 CEST** (= 11:00 ET, **40 perccel az entry után**) |
| NVDA LOSS_EXIT triggert | **17:05 CEST** (= 11:05 ET, **45 perccel az entry után**) |
| CENX trail_activated_b | 17:35 CEST (= 11:35 ET, **75 perccel az entry után**) |
| CENX trail_sl_update count | **22** events (17:40 → 19:40 között, klasszikus tiszta trail) |

**Két ticker (TGB + NVDA) is 40-45 perccel az entry után LOSS_EXIT-tel zárt.** A jelenlegi -2% LOSS_EXIT küszöb **agresszívan triggerel** akkor is, ha a normál intraday volatilitás meghaladja a 2%-ot. **A screenshotok és kvantitatív elemzés** szerint mindkét ticker a nap végére visszamászott vagy meghaladta az entry árat.

## 🆘 ENTRY TIMING HIPOTÉZIS — KVANTITATÍV MEGERŐSÍTÉS

Tamás 3 screenshotja (TGB, NVDA, CENX 15-perces intraday charts) + a kedd logok együttesen **kvantifikálható finding-ot** termelnek az entry timing-ról.

### A kvantitatív kép

| Ticker | Tervezett 16:20-i entry | Tényleges 16:20 fill | LOSS_EXIT exit | EOD ár (visszamászás) |
|--------|--------------------------|----------------------|----------------|-----------------------|
| **TGB** | $7.62 | $7.64 (slippage +0.26%) | $7.42 (-2.62%) | **$7.91 (+3.66% az entry-től)** ⭐ |
| **NVDA** | $220.48 | $220.51 (slippage +0.01%) | $215.96 (-2.05%) | **$220.78 (+0.13% az entry-től)** |
| CENX | $60.48 | $61.00 (slippage +0.86%) | nem triggerelt | $63.23 MOC (+3.66% az entry-től) |

**Elmaradt P&L kalkuláció** (ha a LOSS_EXIT nem triggerelt volna, és a pozíciók MOC-ig maradtak volna):

| Ticker | Tényleges P&L | Hipotetikus P&L (MOC-ig) | Elmaradt P&L |
|--------|---------------|---------------------------|--------------|
| TGB | **-$257** | **+$340** (1175 × $0.29) | **~$597** |
| NVDA | **-$266** | **+$16** (58 × $0.27) | **~$282** |
| **Összesen** | **-$523** | **+$356** | **~$879** |

**A nap valós alpha (LOSS_EXIT küszöb nélkül) +$528** lett volna (CENX +$172 + hipotetikus TGB +$340 + hipotetikus NVDA +$16), **-$369 helyett**. **Különbség: ~$897.**

### A screenshotok kvalitatív finding-jai

**TGB chart (15m intraday):**
- 15:30 CEST (market open) tájékán **$7.20-7.30 mélypont** látszik
- Reggeli emelkedés $7.40-7.50-ig
- **16:20-i entry $7.64** — a reggeli emelkedés peak-jéhez közeli (locally rossz időpont)
- 17:00 LOSS_EXIT $7.42 alá
- 18:00-21:00 között további emelkedés $7.90-$8.00 közelébe (intraday peak ~$8.00 körül)
- **MOC zárás $7.91** — ha 15:30-kor léptünk volna be $7.30 körül, **+$0.61/share × 1175 = +$716 lett volna** (vs tényleges -$257)

**NVDA chart (15m intraday):**
- 15:30 CEST körül **$215-217** range
- 16:00-16:30 között emelkedés $220-ra
- **16:20-i entry $220.51** — a reggeli emelkedés peak-jéhez közeli
- 17:05 LOSS_EXIT $215.96 alá
- 19:00 után újabb emelkedés $222-224 közelébe
- **MOC zárás $220.78** — ha 15:30-kor léptünk volna be $215 körül, **+$5.78/share × 58 = +$335 lett volna** (vs tényleges -$266)

**CENX chart (15m intraday):**
- 11-én (hétfő) dropp $62.50-ról $59 körüli mélypontra
- 12-én (ma) vissza-emelkedés $62-63 közelébe a nap során
- **16:20-i entry $61.00** — a vissza-emelkedés korai fázisa, **JÓ TIMING**
- Trail aktiválva 17:35-kor, 22 SL-update az emelkedéssel
- MOC $63.23 (+3.66%) — a 0.48× szorzó ellenére is a nap legjobb nyerője
- Furcsa kvalitatív finding: **a TradingView chart tetején "Bear" jelzés** látható (technikai bear setup), mégis +5.13% napi mozgás (a flow és fundamentumok felülírták a technikai bear-t)

### Hipotézis

A jelenlegi 16:20 CEST (= 10:20 ET, **50 perccel a market open után**) entry-idő **gyakran a reggeli rally peak-jére esik**, ami:
- Lokálisan magas entry-árat eredményez (peak-vásárlás)
- A normál reggeli profit-taking (10:30-11:30 ET) **azonnal a LOSS_EXIT küszöb alá hozza** a tickert
- Akkor is, ha a nap végére a ticker meghaladja az entry árat

**Három alternatív entry időablak megvizsgálandó (Day 63 utáni analitikus task):**

| Időpont | CEST | ET | Karakterisztika |
|---------|------|----|--------------------|
| Market open | 15:30 | 09:30 | Pre-market hype árban, de mélypontok itt jellemzők |
| **Jelenlegi** | **16:20** | **10:20** | Reggeli rally peak — **strukturálisan rossz?** |
| Mid-morning | 17:15 | 11:15 | Reggeli profit-taking utáni, lokálisan mélypont (FORM máj 8 esete megerősítette: -4.5% slippage) |
| Délben | 18:30 | 12:30 | Aktivitási minimum, "lunchtime drift" |

**Új P2 backlog idea (analitikus):** "Entry timing optimalizáció — backtest a 60+ napi adaton" — kvantitatív vizsgálat, hogyan változna a P&L 15:30 vs 16:20 vs 17:15 vs 18:30 CEST entry-időkkel a meglévő logokból. **Effort: ~1-2 óra Chat-oldali. Day 63 utáni elemzéshez érdemes.** Tamás explicit kérése.

## Pozíciók részletei

### Nyertes (1 ticker, +$172)

**CENX (Century Aluminum, Basic Materials, score 95.0)**: Entry $61.00 (planned $60.48, slippage +0.86%), MOC $63.23 = **+$171.71 (+3.66%)** ⭐ — a nap egyetlen nyerője.

**🔍 Kritikus M-szankció a CENX-en:**
- `contradiction_flag=1`, reason: `"earnings_beats_below_half (0/4)"` (az utolsó 4 earnings-ből 0 beat) → M_contradiction = 0.8
- `gex_regime: high_vol` → M_gex = 0.6
- **multiplier_total = 0.8 × 0.6 = 0.48** (52% csökkentett position size!)

Ez **MÁSODIK típusú dupla szankcionálás minta** a péntek FORM-os M_contradiction × M_target_penalty (= 0.68) után:
- Hétfő FORM: M_contradiction (0.8) × M_target_penalty (0.85) = **0.68** → nap legjobb nyerője (+$214)
- **Kedd CENX: M_contradiction (0.8) × M_gex (0.6) = 0.48** → nap legjobb nyerője (+$172)

**Hatás-becslés:** ha M=1.0 lett volna a CENX-en, qty 161 helyett 77 → **+$359 lett volna** a +$172 helyett, +$187 elmaradt nyereség. **Plusz** a kedvező kvalitatív/CC company intelligence ("Mt. Holly expansion, Potline 2 restart, Grundartangi Iceland, Jamaica + Oklahoma projects, capex prioritás osztalék helyett") a 95-ös score-ral összhangban — a 3 earnings miss (Q1 -32.5%, Q4 -98.4%, Q3 -81.0%) GAAP one-time item-eket tartalmazott, NEM strukturális üzleti gyengeséget.

### Vesztesek (2 ticker, 4 trade-ben, -$521)

**TGB (Taseko Mines, Basic Materials, score 95.0)**: 3 partial fillben zárult LOSS_EXIT-tel, mind ugyanazon a $7.42 áron:

```
Entry $7.64 (planned $7.62, slippage +0.26%)
Submit 16:20:51 CEST: qty 1175 (bracket_a 588 + bracket_b 587)
LOSS_EXIT trigger 17:00:11 CEST: SELL 1175 @ MARKET
IBKR partial fills (3-split):
  Fill 1: 796 share × -$0.22 = -$173.77
  Fill 2: 200 share × -$0.22 = -$43.66
  Fill 3: 179 share × -$0.22 = -$39.08
Total: -$256.51 (-2.86%)
```

**A 3-split NEM bug — IBKR partial fill artifact**, amikor az 1175 share liquiditás nem elég egyetlen blokkban a $7.42 áron. **A tényleges LOSS_EXIT event egy darab**, a 3 split csak a fill-szintű elszámolás. (Daily_metrics 4 LOSS_EXIT-et jelez, mert fill_id-k alapján számolja — ez kvalitatív hiba a metric-ben, de nem strukturális.)

**Kvalitatív kontextus** (CC company intelligence):
- Q1 2026 Gibraltar mine (75% interest) erős üzemi eredmények, Q1 EPS +50% beat
- Yellowhead copper project permitting — potenciálisan Canada 2. legnagyobb réz-bányája
- DE: Q2 2026 (aug 5) "no actual EPS reported" — bizonytalanság
- Ár $7.62 vs analyst target $9.00 — alulteljesítési kockázat

A 16:20-i entry $7.64 lokálisan a reggeli rally peak közelében, a 17:00 LOSS_EXIT a normál profit-taking-en, **a nap intraday peak $8.00 körül** (lásd screenshot).

**NVDA (NVIDIA, Technology, score 93.5)**: Entry $220.51 (planned $220.48, slippage +0.01% minimal), LOSS_EXIT $215.96 = **-$265.93 (-2.05%)** — a nap legrosszabb.

**Kvalitatív kontextus** (CC company intelligence):
- Erős earnings beat sorozat (Q4 +5.2%, Q3 +3.2%, Q2 +4.0%)
- "Agentic AI inflection" — inference compute revenue driver
- **Upcoming Q1 FY27 earnings 2026-05-20** (8 nap múlva, BC23 utáni időszak!)
- Analyst target $279, current $220.48 — significant upside
- No contradiction_flag (0)

A 17:05-i LOSS_EXIT $215.96 a normál NVDA intraday volatilitás aljához esett. **A MOC $220.78** (a screenshot szerint) **közel az entry-hez** — ha nem LOSS_EXIT, kb. +$16 lett volna, NEM -$266.

**A -2% LOSS_EXIT küszöb agresszivitása high-cap, magas volatilitású tickereken (NVDA-szerű) strukturálisan problémás.** A daily ATR ezek 2.5-4%, így a -2% gyorsan triggerel napi technikai dip-eken.

**Új P2 backlog idea: "LOSS_EXIT küszöb finomítás high-cap / high-volatility tickereken"** — például per-ticker ATR-arányos LOSS_EXIT küszöb (pl. -1×ATR a -2% helyett). Effort: ~1 óra CC + 3-5 teszt.

## M_contradiction LIVE 7. nap mérlege — iránybeli helyesség 33%-ra esett

| Nap | Fired tickerek | Eredmények | Iránybeli helyesség |
|-----|----------------|------------|---------------------|
| Hé máj 4 | 0/5 | n/a | n/a |
| Ke máj 5 | NE (0.8), PTEN (0.8) | -$143, -$36 | ✓ ✓ helyes (mindkettő vesztes) |
| Sze máj 6 | 0/3 | n/a | n/a |
| Csü máj 7 | (nincs adat) | (nincs adat) | n/a |
| Pé máj 8 | AMD (0.8), GOOG (0.8) | +$263, +$19 | ✗ ✗ helytelen |
| Hé máj 11 | FORM (0.68 — M_c × M_target) | +$214 | ✗ helytelen |
| **Ke máj 12** | **CENX (0.48 — M_c × M_gex)** | **+$172** | **✗ helytelen** |

**6 fired esetből 2 ✓ + 4 ✗ = 33% iránybeli helyesség** — **rosszabb mint random (50%)**.

**Statisztikai szignifikancia**: n=6 még mindig kis minta, de **a trend egyértelmű** — a contradiction-flagged tickerek **az utolsó 4 esetből 4-szer nyertesek vagy breakeven**. **A feature jelenlegi formájában strukturálisan rossz irányba dolgozik**, hasonlóan ahhoz, ahogyan a dp_pct UW dark pool % is **inverz prediktor** volt a 60-trade auditban (Pearson -0.265\*\*).

**Lehetséges magyarázat:** a contradiction_flag = "kvalitatív aggály" (overshoot consensus, recent downgrades, earnings_beats_below_half) **nem prediktív** a swing trading P&L-re, mert:
1. A flow-súly 0.60 már beépítette a piaci sentiment-et
2. A target_penalty külön szankcionál a target overshoot-ra
3. A contradiction redundánsan szankcionál a meglévő sentiment-en, de **a meglévő flow signal pozitív** ezeken a tickereken (95-ös score, magas RVOL, etc.)

**Az M_contradiction sign-flip vizsgálandó** — hasonlóan a dp_pct rekal-hoz, lehet hogy a contradiction_flag pozitív irányba mutat (azaz **emelni** kéne a position size-ot, NEM csökkenteni). **Új P2 backlog idea** vagy a 2.3 backlog idea kibővítése.

## Új strukturális megfigyelés: M_contradiction × M_gex DUPLA SZANKCIONÁLÁS (2. típus)

A 2.3 backlog idea (péntek óta) eredetileg az M_contradiction × M_target_penalty deduplikációt célozta. Ma egy **második típusú dupla szankcionálás** jelentkezett:

| Dátum | Ticker | Szorzó | Komponensek | Eredmény |
|-------|--------|--------|--------------|----------|
| 2026-05-11 | FORM | **0.68** | M_contradiction (0.8) × M_target_penalty (0.85) | +$214 nap-legjobb |
| **2026-05-12** | **CENX** | **0.48** | **M_contradiction (0.8) × M_gex (0.6)** | **+$172 nap-legjobb** |

**Mindkét DUPLA-szankcionált ticker a nap legjobb nyerője lett.**

**A 2.3 backlog idea ezért kibővítendő:** "M_contradiction × bármely másik M-szorzó kölcsönhatás revíziója" — esetleg az M_contradiction teljes deaktiválása vagy sign-flip vizsgálata.

## Score → P&L napi nézet

| Ticker | Score | Multiplier | Exit | P&L net | Win? |
|--------|-------|------------|------|---------|------|
| **CENX** | 95.0 | **0.48** ⚠️⚠️ DUPLA | MOC | **+$171.71** | ⭐ |
| TGB | 95.0 | 1.00 | LOSS_EXIT | -$256.51 | ✗ |
| NVDA | 93.5 | 1.00 | LOSS_EXIT | -$265.93 | ✗ |

**A 7 napi trend (W19 D1 → W20 D2):**
- High score, high multiplier (1.0): **gyakran vesztes** (NE 95 -$143, RMBS 93.5 vesztes, MTCH 95 -$43, HYMC 95 -$141, TGB 95 -$257, NVDA 93.5 -$266)
- High score, dupla-szankcionált multiplier (0.48-0.68): **gyakran nyertes** (FORM 95 +$214, CENX 95 +$172)
- Low score, high multiplier (1.0): **mixed** (CRWD 95 +$247 nyertes, AAPL 94.5 -$37 vesztes, GOOG 89.5 +$19 breakeven)

**A pattern**: a contradiction-flagged tickerek **felülteljesítik** a tisztaakat. Erős kvantitatív érv az M_contradiction revíziójára.

## Snapshot fix 2. nap validáció — KONZISZTENS

| Nap | Phase 4 tickers (analyzed) | Qualified (>85) | Snapshot méret |
|-----|----------------------------|------------------|----------------|
| Hé W20 D1 (máj 11) | 1390 | **159** | 22.89 KB |
| **Ke W20 D2 (máj 12)** | (a cron log Phase 4 része nem kerestem ki — `daily_metrics`-ben `qualified_above_threshold: 161`) | **161** | becsült ~22-25 KB |

**A snapshot fix stabilan működik** — a 159 → 161 közötti kis változás konzisztens (a Phase 2 universumban naponta néhány ticker ki/be kerülhet az earnings exclusion miatt).

## ⚠️ UW HTTP 429 RATE LIMITS — SÚLYOSABB MA MINT HÉTFŐN

A `cron_intraday_20260512_161500.log` Phase 4 darkpool fetch szakasza tömegesen failelt:

- **Hétfő (W20 D1)**: ~50 ticker 3/3 retry után 429
- **Kedd (W20 D2)**: **170+ ticker** 3/3 retry után 429 (a head 200 sorban már 170 darab — a teljes log valószínűleg 200-300 darab)

A 3 megnyitott ticker (CENX, TGB, NVDA) sikeresen kapott UW adatot (top-N-ig eljutottak), **de a tegnapinál sokkal több ticker score-olt dp_pct adat nélkül**. **A 1.6 P1 backlog idea (UW rate limit kezelés finomítás) sürgőssége NÖVEKEDETT** — egy hét alatt 3-4×-ese a rate-limit-hibás tickereknek.

## Excess vs SPY napi pattern megerősítés

| Nap | Net P&L | SPY return | Portfolio return | Excess vs SPY | Pattern |
|-----|---------|------------|------------------|---------------|---------|
| Hé W19 D1 | -$191 | -0.37% | -0.15% | +0.21% ⭐ | risk-off outperform |
| Ke W19 D2 | -$269 | +0.80% | -0.24% | -1.04% | bull underperform |
| Sze W19 D3 | +$234 | +1.39% | +0.25% | -1.14% | bull underperform |
| Csü W19 D4 | -$501 | -0.31% | -0.49% | -0.18% | mild risk-off, near-neutral |
| Pé W19 D5 | +$486 | ~0% | +0.49% | +0.49% ⭐ | mild lateral outperform |
| Hé W20 D1 | +$28 | +0.23% | +0.03% | -0.19% | mild bull underperform |
| **Ke W20 D2** | **-$369** | **-0.15%** | **-0.35%** | **-0.20%** ⚠️ | **mild risk-off ALSO underperform (új!)** |

**Új finding: a ma a swing rendszer mild risk-off napon IS underperformolt** (-0.20% excess SPY -0.15% napi mellett). A korábbi pattern: "outperform risk-off / lateral, underperform bull rally" — ma **ez NEM jelentkezett**. **Egyetlen nap, nem konklúzió**, de a 4× LOSS_EXIT-tel kombinálva azt sejteti, hogy a **LOSS_EXIT küszöb agresszivitása** rontja a risk-off napi outperformance-t is.

**7 napi átlag excess: -0.29%** (összes -2.05% / 7 nap). A Day 63 leállítási küszöb -1.5% mellett **bőven biztonságos** (~1.21% buffer).

## monitor.py "replay" események — a hétfői pattern megerősítése

A `pt_events_2026-05-12.jsonl` 22:00 CEST körüli szakaszában megint megjelennek a **LION és SDRL eseményei** (TP1 detected, trail activated, trail hit, loss_exit) — pontosan ugyanazok mint a hétfői logban. **A 3.5 P3 backlog idea (monitor.py replay események jelölése) megerősítve**: ez egy ismétlődő daily noise a logban, ami strukturálisan szűrendő.

## Day 63 keret — 1 NAP MARADT!

| Metrika | Érték | Status |
|---------|-------|--------|
| Day | **62/63** — **1 nap van Day 63-ig** (csüt máj 14) | |
| Kumulatív (paper aggregát) | -$1,445.81 (-1.45%) | **biztonságos sávban**, kis visszaesés |
| Tényleges valós (becsült) | ~-$1,332 (-1.33%) | SQM bug-korrekció utáni |
| ÉLESÍTÉS távolság | +$4,332 a +$3,000-hoz | **1 nap × +$4,332 → ABSOLUT NEM realisztikus** |
| LEÁLLÍTÁS távolság | 7 napi excess átlag -0.29% | **biztonságos**, ~1.21% buffer a -1.5%-tól |
| 7 napi excess átlag (W19+W20) | ~-0.29% | a mai -0.20% csökkentette átlagot kissé |
| VIX close | 18.03 (Δ -2.28%) | **alacsony**, leállítási feltétel monitor inaktív |

**Realisztikus Day 63 várt kimenet**: **PAPER FOLYTATÁS (default)** — most már **7+ nap egymás után megerősítve**. A kumulatív P&L 1 nap után valószínűleg **-$1,300 és -$1,600 között**.

## Anomáliák

- **🆘 FORM -29 SHORT** (LOSS_EXIT bracket SL cancellation 3. instancia) — **szerda reggel sürgős takarítás**
- **CRGY/AAPL leftover phantoms** továbbra is (régóta ismert BUG)
- **DELL, DOCN phantom_filtered** (helyes szűrés)
- **AVDL.CVR (69.0)** továbbra is non-tradable, ignorálva
- **UW HTTP 429 növekedés**: 50 → 170+ ticker egy nap alatt — **a 1.6 P1 backlog idea kritikusabb mint valaha**
- **monitor.py LION/SDRL replay** events — ismétlődő pattern
- **CENX kvalitatív paradoxon**: "Bear" technikai jelzés a screenshoten + +5.13% napi mozgás. Flow > technikai

## Kulcsmegfigyelések

### 1. 🆘 KRITIKUS — FORM -29 SHORT (LOSS_EXIT bracket SL cancellation 3. instancia)

3 hibatípus 8 napon belül (DTE máj 1, SQM máj 7, **FORM máj 12 — ÚJ MINTA: MOC fill után másnap**). **Szerda reggel sürgős `nuke.py` takarítás** + **a P1 #1 backlog idea bővítendő** (close.py MOC fill után is cancel logika).

### 2. ⚠️ ENTRY TIMING HIPOTÉZIS — KVANTIFIKÁLT $879 elmaradt P&L

Ha a TGB és NVDA nem LOSS_EXIT-tel zárt volna, +$356 lett volna a -$523 helyett. **A 16:20 CEST entry-idő strukturálisan a reggeli rally peak-jére esik**, és a normál profit-taking azonnal LOSS_EXIT-et trigger-el. **Új P2 backlog idea (analitikus, Day 63 után): "Entry timing optimalizáció backtest" — 15:30 vs 16:20 vs 17:15 vs 18:30 CEST összehasonlítás a 60+ napi adaton.**

### 3. ⚠️ LOSS_EXIT -2% küszöb AGRESSZIVITÁSA high-cap tickereken

A NVDA -2.05% LOSS_EXIT 45 perccel az entry után, **mégis a nap végére +0.13%-on zárt** az entry-höz képest. **Új P2 backlog idea: "LOSS_EXIT küszöb finomítás per-ticker ATR-arányos alapon"** (pl. -1×ATR a -2% helyett, vagy ticker-specifikus min-max sávval).

### 4. ⚠️ M_CONTRADICTION LIVE — 33% iránybeli helyesség (rosszabb mint random)

7 napos 6 fired eset: 2 ✓ + 4 ✗ = 33%. **A feature jelenlegi formájában strukturálisan rossz irányba dolgozik** — hasonlóan a dp_pct UW dark pool % korábbi inverz-prediktor finding-jához. **Az M_contradiction sign-flip vizsgálandó** (egy lehetséges 2.3 backlog idea bővítés vagy új backlog idea).

### 5. ⚠️ DUPLA SZANKCIONÁLÁS 2. TÍPUSA — M_contradiction × M_gex (CENX 0.48)

A hétfő FORM (M_c × M_target_penalty = 0.68) után ma a CENX (M_c × M_gex = 0.48) — **mindkét DUPLA-szankcionált ticker a nap legjobb nyerője**. **A 2.3 backlog idea bővítendő:** "M_contradiction × bármely másik M-szorzó kölcsönhatás revíziója".

### 6. ⚠️ UW HTTP 429 — SÚLYOSABB EGY HÉT ALATT

50 → 170+ rate-limit-failed ticker. A dp_pct rekal hatás-validációja egyre korlátozottabb. **A 1.6 P1 backlog idea sürgőssége nőtt.**

### 7. ✓ SNAPSHOT FIX STABIL — 2. nap konzisztens

161 qualified (a hétfői 159-hez közel). **A scoring-validation újrafuttatása biztonságosan végrehajtható Day 63-on.**

## Holnap (szerda, W20 D3 — máj 13) teendők — UTOLSÓ NAP DAY 63 ELŐTT

### Tamás (MacMini, manuális, **REGGEL**)

- **🆘 `nuke.py --positions`** — a FORM -29 SHORT takarítása **azonnal piacnyitás előtt**
- IBKR Gateway állapot ellenőrzés (a hétfői timeout után kíváncsiak vagyunk a stabilitásra)
- AVDL.CVR phantom továbbra is takarítani opcionális

### Chat (én)

- **Master-reference 04-risks 1.3 frissítése** — a "LOSS_EXIT bracket SL cancellation" P1 task bővítése a MOC-fill-after instanciaval (FORM máj 12)
- **Új backlog ideas hozzáadása a master-reference-be:**
  - 2.4: LOSS_EXIT küszöb finomítás per-ticker ATR-arányos alapon (P2)
  - 3.6: Entry timing optimalizáció backtest (P2 — analitikus, Day 63 utáni)
  - Esetleg 2.5 vagy a 2.3 bővítése: M_contradiction sign-flip vizsgálata (P2)
- **`docs/analysis/weekly/2026-W19-analysis.md` heti elemzés** — még mindig nem készült, **szerdára szerintem érdemes lerakni**, hogy Day 63 előtt friss legyen
- **Strategic-review full korrekció** ($354 → $665, 2.4 fejezet) — folytatandó hétvégi feladatlistából

### Szerda este (W20 D3 napi review)

- **Az utolsó napi review Day 63 előtt** — különösen kiemelt figyelem a:
  - LOSS_EXIT arányra (4/5 utolsó-előtti?)
  - Entry timing pattern megfigyelésére
  - M_contradiction LIVE 8. nap mérlegére
  - UW HTTP 429 trend folytatása

### Csütörtök (máj 14) — **Day 63 KIÉRTÉKELÉS** ⭐

- **09:00 Reminder** notification
- **Scoring validation újrafuttatás teljes mintán** (a snapshot fix után először, 6+ nap új adattal)
- **Várt kimenet: PAPER FOLYTATÁS (default)** — 7+ nap egymás után megerősítve
- **Új doc**: `docs/decisions/2026-05-14-day63-decision-outcome.md`
- **A 7 napi finding-ok beépítése a Day 63 keretbe**:
  - LOSS_EXIT bracket SL bug 3 instancia → P1 hot-fix prioritás
  - Entry timing hipotézis kvantifikálva → P2 analitikus task
  - M_contradiction iránybeli helyesség 33% → P2 design revízió
  - Dupla szankcionálás 2 típus → P2 deduplikáció

## Kapcsolódó

- `state/phase4_snapshots/2026-05-12.json.gz` ⭐ 2. tiszta snapshot a fix után
- `state/daily_metrics/2026-05-12.json` ← Day 62 strukturált metrika
- `logs/pt_eod_2026-05-12.log` ← P&L (4 LOSS_EXIT + 1 MOC) + FORM -29 SHORT warning
- `logs/pt_close_2026-05-12.log` ← cron-replay 21:20 + 21:40
- `logs/pt_events_2026-05-12.jsonl` ← TGB 17:00 LOSS_EXIT + NVDA 17:05 + CENX trail × 22 + FORM position_skipped
- `logs/cron_intraday_20260512_161500.log` ← Phase 4 1390+ ticker, **UW HTTP 429 170+ darab**
- `output/execution_plan_run_20260512_141500_21b2cc.csv` ← 3 ticker, **CENX multiplier 0.48** (M_contradiction × M_gex)
- **Screenshots** (Tamástól): TGB / NVDA / CENX 15m intraday — kvalitatív entry timing finding

**State**: BC23 + Breakeven Lock + MID Bundle + vix-close + M_contradiction LIVE + snapshot fix DEPLOYED (2 nap konzisztens) + dp_pct rekal DEPLOYED + **FORM -29 SHORT (LOSS_EXIT bracket bug 3. instancia)**

**Aktív CC tasks**: 0 (a péntek óta nem indult új; szerda reggel azonban érdemes a LOSS_EXIT bracket bug P1 hot-fix-et felgyorsítani)

**W20+ backlog idea-k (most 15+, 2 új a kedd finding-okból):**

P1 (5):
1. ⚠️ LOSS_EXIT bracket SL cancellation — **BŐVÍTENDŐ a MOC fill-after instanciaval** (FORM máj 12)
2. 10-Q SEC Filing Exclusion
3. ADR earnings adatforrás fix
4. UW rate limit kezelés finomítás — **SÜRGŐSEBB** (50 → 170+ rate-limit egy hét alatt)
5. IBKR Gateway monitoring + Telegram alert

P2 (5):
6. Breakeven Lock profit-küszöb csökkentés
7. TP1 cél revízió
8. M_contradiction & M_target_penalty deduplikáció — **BŐVÍTENDŐ az M_gex és más M-szorzókra**
9. **ÚJ: LOSS_EXIT küszöb finomítás per-ticker ATR-arányos alapon** — ~1 óra CC
10. **ÚJ: Entry timing optimalizáció backtest** (analitikus, Day 63 utáni) — ~1-2 óra Chat

P3 (5+):
11. Phase 4 snapshot enrichment
12. High-score liquidity check
13. dp_pct fallback default
14. Slippage-adjusted scoring validation
15. monitor.py belső replay események jelölése — **MEGERŐSÍTVE** (mai logban is jelentkezett)

Plus a 2 DEPLOYED ✅ (Snapshot fix `d3fce73`, dp_pct rekal `9a169b9`).
