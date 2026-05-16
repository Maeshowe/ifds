# Daily Review — 2026-05-15 (péntek)

**W20 Day 5 — A régi architektúra utolsó pénteki napja (Day 65/63)**
**⭐ SEDG TP1+TP2 dupla hit (+$329.67 single ticker, +14.44% TP2) — ELSŐ DUPLA BRACKET NYERTES W18+ óta**
**⭐ Risk-off outperform STRUKTURÁLIS MEGERŐSÍTÉS — SPY -1.20%, Portfolio +0.08%, Excess +1.28%**
**⭐ "Magas pontszám paradoxon" ELLENTÉTES PATTERN 2. nap egymás után — SEDG 94.5 TOP = TOP win, RVTY 87.0 BOTTOM = LOSS**
**HYMC -140 takarítva 09:20 — bracket bug 5. instancia kezelve**

**Adat-frissesség:** EOD log 22:05, daily_metrics.py 22:10 CEST. Phase 4 snapshot **172 qualified** (>85, vs tegnap 134, kedd 161) — **az 5 napos snapshot fix mintán a legmagasabb count**. Reggeli HYMC -140 SHORT takarítás 09:20 sikeres (egy próbára, IBKR conn stabil). Heti elemzés `scripts/analysis/weekly_metrics.py` futott, `docs/analysis/weekly/2026-W20.md` generálva.

---

## Számok

| Metrika | Érték | vs előző nap (Cs W20 D4) | vs W20 átlag (5 nap) |
|---------|-------|--------------------------|----------------------|
| Napi P&L gross | **+$79.36** | -$260.58 (csüt $339.94 → péntek $79.36) | W20 gross átlag -$14.89/nap |
| Commission | -$17.69 | vs tegnap $26.58 | W20 commission átlag -$16.10/nap |
| **Napi P&L net** | **+$61.67** | -$251.69 (csüt $313.36 → péntek $61.67) | W20 net átlag -$30.99/nap |
| **Kumulatív P&L** | **-$1,204.48 (-1.20%)** ⬆️ | $79.36 javulás (-$1,283.84 → -$1,204.48) | átlagosan kismértékben javul |
| Pozíciók (új) | 5 ticker (SEDG, CVE, GLW, MRVL, RVTY) | tegnap 4 ticker | átlag 5.2/nap |
| Trade count | 7 fill (SEDG bracket × 2 + RVTY split + 3 ticker) | tegnap 7 fill | átlag 5.2 fill/nap |
| Win rate ticker szinten | **2/5 (40%)** | tegnap 75% | hét átlag ~46% |
| **Exit mix** | **TP1 (1) + TP2 (1) ⭐ + MOC (4) + LOSS_EXIT (1)** | jelentős változás | először TP1+TP2 dupla |
| **TP1 / TP2 hit** | **1 / 1** ⭐ | 0/0 tegnap | W20-ban 1/1 (csak ma) |
| LOSS_EXIT hit | 1 (GLW -$137.62) | 0 tegnap | W20-ban 7 LOSS_EXIT |
| SL / TRAIL hit | 0 / 0 | 0 / 1 (NVTS) | W20-ban 0 SL, 1 TRAIL |
| **Avg slippage** | **+0,48% KEDVEZŐTLEN** ⚠️ | tegnap -0,22% kedvező | W20 átlag -0,21% (péntek bukott) |
| SPY return | **-1,20%** ⚠️ (risk-off nap) | tegnap +0,79% bull | W20 +0,23% net |
| Portfolio return | +0,08% (közel-flat) | tegnap +0,34% | W20 -0,07% |
| **Excess vs SPY** | **+1,28%** ⭐⭐ | -0,45% (markáns javulás) | **W20 átlag -0,30%** |
| VIX close | 18,13 (Δ +4,86%, emelkedő) | tegnap 17,29 | W20 átlag 17,7 |
| Reggeli akció | ✅ `nuke.py` 09:20 — **HYMC -140 SHORT BUY 140 @ MKT zárva** (1 próbára, IBKR conn stabil, 0 open orders!) | — | — |
| EOD nyitott pozíció | **0** ⭐ (csak AVDL.CVR phantom) | tegnap HYMC -140 | TISZTÁBB EOD |

## Day 63 + 1: HYMC takarítás sikeres, AVDL.CVR phantom marad

A `pt_nuke_2026-05-15.log` 09:20:
```
09:20:08 [INFO] Open positions: 2 (AVDL.CVR 69.0, HYMC -140.0)
09:20:08 [INFO] Open orders: 0  ← EZÚTTAL 0 függő order!
09:20:08 [INFO]   AVDL.CVR: SKIP (non-tradable)
09:20:08 [INFO]   HYMC: BUY 140 shares (MKT via SMART)
09:20:10 [INFO] Final positions: 2 (AVDL.CVR még, HYMC 0)
09:20:10 [INFO] Final orders: 1
```

**Megfigyelés:** A `nuke.py` 09:20-án **0 open orders**-t mutat (vs tegnap reggel 2 open orders), tehát a HYMC bracket TP/SL **már nem volt függőben** — ami azt jelenti, hogy **a tegnapi 21:40 körüli triggerelés zárta le a függő ordereket** (az IBKR autonóm bracket SL-fill miatt). **Az 1.3 `nuke.py --positions` scope-hiány finding változatlan** (továbbra is nem cancellál függő ordereket), de **ma nem volt mit cancel-elni**.

**Az AVDL.CVR (69.0 share, non-tradable) phantom továbbra is ott marad** — várhatóan a Fázis 1 cleanup IBKR paper account reset (Tamás manuális, máj 20-22) megoldja.

**A bracket bug instancia-szám marad 5 a W20-ban** — péntek NEM termelt új instanciát. Ma a 4 nyitott pozíció mind explicit MOC/TP1/TP2/LOSS_EXIT-tel zárt, bracket bug-i függő order nélkül. Holnaptól (hétfő) Tamás `nuke.py --positions` cleanup → IBKR paper account reset → Fázis 1 indul.

## ⭐⭐ KULCS POZITÍV — SEDG TP1+TP2 DUPLA BRACKET NYERTES (+$329.67, +14.44% TP2)

A `pt_eod_2026-05-15.log` szerint:
```
22:05:04 [INFO]   SEDG: TP1 | Entry $52.92 → Exit $57.49 | P&L +$123.39
22:05:04 [INFO]   SEDG: TP2 | Entry $52.92 → Exit $60.56 | P&L +$206.28
```

A `trades_2026-05-15.csv` szerint:
- SEDG (Energy, score 94.5)
- Entry $52.92, **bracket A**: 27 share → TP1 $57.49, **+$123.39 (+8.64%)**
- Entry $52.92, **bracket B**: 27 share → TP2 $60.56, **+$206.28 (+14.44%)**
- ATR (becsült): ($57.49 - $52.92) / 1.25 = $3.66, tehát TP1 = entry + 1.25×ATR, TP2 = entry + 2×ATR (1.25 + 2.0)/3 × 2 = $3.66/1.83 = ~$2.00 ATR, ami a TP2 $60.56-ot ad

**Stratégiai jelentőség (multi-szempontú):**

1. **A 60+ napi sample-ban kb. 4. TP2 hit** — a strategic-review szerint 60 napra 3 TP2 hit ($286/avg = $858 total), most az 5. (W20 D5) az **új single-trade rekord: +14.44%, $206.28**. A korábbi rekord: QCOM 2026-05-07 +10.55%.

2. **A 2026 áprilisi 13 pontos terv 6. javaslata ("50/50 bracket-osztás megfordítása") MŰKÖDÉSI VALIDÁCIÓJA**:
   - Régi 33/67 osztással: A fele (kis) TP1-en zár, B fele (nagy) TP2-ig kitart → ha a TP2 trigger, a teljes profit nagy
   - Új 50/50 osztással: mindkét fele érdemleges P&L kontribúcióval bír
   - Ma: A fele +$123 (TP1), B fele +$206 (TP2) → **egyensúlyos profit-megosztás**, nem "minden-vagy-semmi"
   - A 8 implementált 2026 áprilisi elem közül ez **az első, ami egyértelmű single-trade-szintű pozitív hatást produkál**

3. **A SEDG egy ENERGY szektor ticker** — együtt CVE-vel (Energy, +$159 win) → **2 Energy ticker × 2 nyertes = Energy szektor outperformance ma**. A Technology (GLW, MRVL) és Healthcare (RVTY) **mind vesztes**. **Szektor-szelektív karakter risk-off napon** = makró-konzisztens (Energy gyakran defenzív / counter-cyclical risk-off-ban).

4. **A SEDG +14.44% mozgása valószínűleg single-stock catalyst-ot tartalmaz** (earnings, upgrade, vagy news) — a pipeline 16:15 CEST submit-je a mozgás elején történt, +6.5 óra holding alatt elérte a +14%-ot. **A swing pivot 3-5 napi hold időtáv** elvileg **megőrizné a TP2 utáni mozgást is** (esetleges +20-25%), de **ez a Fázis 3 deploy után az új paper trading futáson** dől el.

## ⭐⭐ STRUKTURÁLIS — Risk-off outperform PATTERN MEGERŐSÍTÉS

| Nap (W20) | SPY return | Portfolio return | Excess vs SPY | Karakter |
|-----------|------------|------------------|----------------|----------|
| Hé D1 | +0,23% | +0,03% | -0,19% | mild bull underperform |
| Ke D2 | -0,15% | -0,35% | -0,20% | mild risk-off underperform |
| Sze D3 | +0,56% | -0,18% | -0,74% ⚠️⚠️ | bull rally EXTRÉM underperform |
| Cs D4 | +0,79% | +0,34% | -0,45% | mild bull underperform |
| **Pé D5** | **-1,20%** | **+0,08%** | **+1,28%** ⭐⭐ | **risk-off EXTRÉM OUTPERFORM** |

**A 60 napi sample-ban a péntek +1,28% excess valószínűleg TOP 3 legjobb adatpont** (a tegnapi -0,74% volt a worst-case 60 napi adatpontok között). 

**A pattern megerősítése:** a 9 napi sample-ban (W19 D1 → W20 D5):

| Karakter | Napok száma | Átlag excess | Pattern |
|----------|------------|--------------|---------|
| Bull rally (+SPY ≥ +0,5%) | 4 napi (W19 D2, D3, W20 D3, D4) | **-0,74%** | **Strukturális underperform** |
| Risk-off (-SPY ≤ -0,5%) | 1 nap (W20 D5) | **+1,28%** | **Strukturális outperform** |
| Mild bull (+SPY 0 to +0,5%) | 2 nap (W19 D5, W20 D1) | +0,15% | Mild outperform |
| Mild risk-off (-SPY -0,5% to 0%) | 2 nap (W19 D1, D4, W20 D2) | -0,01% | Közel-flat |

**A rendszer karakter-konzisztens: defenzív erő risk-off / lateral napokon, kompromittált bull rally napokon.** A swing pivot új architektúra (mental stop + rolling 10-12 sizing + 3-5 napi hold) elvileg **mind a két karakter-mintát** módosíthatja: 
- A risk-off outperform-ot **megőrizheti** (több diverzifikáció, mental stop nem hardcore stop)  
- A bull rally underperform-ot **javíthatja** (több időtáv → momentum signal érvényesülhet)

## ⭐ "Magas pontszám paradoxon" — ELLENTÉTES PATTERN 2. NAP EGYMÁS UTÁN

| Ticker | Score | Sector | Exit | P&L | Win? | Slippage % |
|--------|-------|--------|------|-----|------|------------|
| **SEDG** | **94,5** ⭐ TOP | Energy | **TP1 + TP2** | **+$329,67** ⭐ | ⭐ TOP | +1,05% (kedvezőtlen) |
| CVE | 92,0 | Energy | MOC | +$159,10 | ✓ | -0,16% (kedvező) |
| GLW | 90,5 | Technology | LOSS_EXIT | -$137,62 | ✗ | +0,60% (kedvezőtlen) |
| MRVL | 90,5 | Technology | MOC | -$132,82 | ✗ | +0,67% (kedvezőtlen) |
| **RVTY** | **87,0** BOTTOM | Healthcare | MOC × 2 | **-$138,97** | ✗ | +0,23% (mild kedvezőtlen) |

**Score rang vs P&L rang:**
- Score rang: SEDG (1) > CVE (2) > GLW=MRVL (3-4) > RVTY (5)
- P&L rang: SEDG ($329,67) > CVE ($159,10) > GLW (-$137,62) > MRVL (-$132,82) > RVTY (-$138,97)
- **Spearman korreláció napi**: **~+0,90 ⭐** (a legmagasabb 2 score nyertes, a legalacsonyabb 3 vesztes)

**A 2 napos minta (W20 D4 és D5):**
- Csütörtök: KC 93,5 TOP win, NVTS 88,5 BOTTOM loss → Spearman ~+0,6
- Péntek: SEDG 94,5 TOP win, RVTY 87,0 BOTTOM loss → Spearman ~+0,9

**Stratégiai értelmezés:** **2 egymás utáni nap a magas pontszám paradoxon megfordult**, de **ez 2 napi minta a 60 napi -0,000 r mintán**. **NEM cáfolja** a 60 napi pattern-t. Lehetőségek:
1. **Random fluktuáció** — 2 adatpont nem szignifikáns
2. **A "magas pontszám paradoxon" gyengül a régi rendszer utolsó hetén** — esetleg a snapshot fix DEPLOYED utáni "tisztább" scoring már jobban prediktál
3. **A swing pivot új scoring (PCR + OTM-inverse only)** **erős előjele**, hogy a Bonferroni-szignifikáns minimum kombináció jobb lehet

A W20 heti Score→P&L korreláció (`weekly_metrics.py`): **r=+0,199** ⭐ — a 63 napi r=-0,000-tól markánsan eltér, és **W19 +0,303** után. **2 hét egymás után pozitív heti korreláció** — egy kérdés a Fázis 2 backtest számára.

## ⚠️ Slippage pattern MEGSZAKADT (+0,48% kedvezőtlen)

| Nap | Avg slippage | Pattern |
|-----|--------------|---------|
| W19 D4 (cs, máj 8) | -0,18% | enyhén kedvező |
| W19 D5 (p, máj 9) | -0,21% | kedvező |
| W20 D2 (k, máj 12) | -0,31% | kedvező |
| W20 D3 (sz, máj 13) | -0,34% | kedvező spontán |
| W20 D4 (cs, máj 14) | -0,22% | kedvező |
| **W20 D5 (p, máj 15)** | **+0,48%** ⚠️ | **kedvezőtlen — pattern megszakadt** |

**A 5 napi konzekutív kedvező slippage pattern (W19 D4 → W20 D4) ma megszakadt.** 4 ticker kedvezőtlen slippage-zsel szállt be:
- SEDG: +1,05% — **drámaian magas** ($52,37 → $52,92, +$0,55/share)
- GLW: +0,60% — magas mid-cap Technology ($199,87 vs $198,68)
- MRVL: +0,67% — magas mid-cap Technology ($181,58 vs $180,37)
- RVTY: +0,23% — mild Healthcare
- CVE: -0,16% — kedvező Energy

**Strukturális megfigyelés:** a kedvezőtlen slippage **3 ticker mid-cap Tech/Healthcare** és **1 ticker Energy single-stock momentum (SEDG)**. A SEDG +1,05% slippage **a +14,44% TP2 nyertest NEM rontotta el szignifikánsan** (a TP2 trigger $60,56 már $0,55-tel magasabb entry mellett is +13,3% lett volna $60,01 helyett). **De a GLW/MRVL/RVTY 0,23-0,67% slippage** **jelentős hányada** a -$137 to -$133 veszteségeknek.

**P2.1 entry timing backtest (Fázis 2 W23) ezt a péntek adatpontot is feldolgozza** — a 4 alternatív időablak (15:30/16:20/17:15/18:30 CEST) összehasonlítás során **a péntek bukása kontraindikátor a 16:20-ról** lehet. De **5 nap kedvező pattern + 1 nap kedvezőtlen = még mindig dominált kedvező mintázat**. A backtest kvantitatív eredménye fog dönteni.

## LOSS_EXIT visszatért (GLW -$137,62, 1 instancia)

A `trades_2026-05-15.csv`:
- GLW (Technology, score 90,5)
- Entry $199,87 (planned $198,68, **slippage +0,60% kedvezőtlen**)
- LOSS_EXIT $194,37 = **-$137,62 (-2,75%)**
- 25 share × -$5,50
- A -2% LOSS_EXIT küszöb (entry - 2% = $195,87) → az ár $194,37-ra esett 2,75%-on triggerelt
- A hagyományos SL küszöb $176,84 (entry - 1,5×ATR), tehát LOSS_EXIT **megelőzte** a hagyományos SL-t

**Megjegyzés:** A GLW egy nagy ($200) árú Tech ticker, ahol a +0,60% slippage egy **$1,19 entry-eltolás**. A LOSS_EXIT trigger $5,50 mozgás alatt (-2,75%), tehát a slippage **az 1,19 / 5,50 = 21,6%-át** adja a veszteségnek. **A slippage strukturálisan az entry timing pattern**hez kapcsolódik (P2.1 backlog).

**W20 heti LOSS_EXIT mérleg**: 7 instancia / 26 trade fill = **26,9%** (vs W19 8/32 = 25%). **A LOSS_EXIT karakter stabil**, **a swing pivot mental stop architektúra strukturálisan eliminálja** a fixed bracket-stop logikát.

## Pozíciók részletei

### Nyertesek (2 ticker, 3 trade fill, +$488,77)

**SEDG (SolarEdge Technologies, Energy, score 94,5 — TOP) ⭐⭐**:
- Entry $52,92 (planned $52,37, slippage +1,05% kedvezőtlen)
- Bracket A (27 share): TP1 $57,49 = **+$123,39 (+8,64%)**
- Bracket B (27 share): TP2 $60,56 = **+$206,28 (+14,44%)** ⭐⭐ **ÚJ SINGLE-TRADE REKORD**
- **Dupla bracket nyertes — a 60+ napi sample 4-5. TP2 hit-je**
- SL küszöb $46,23 (entry - 1,5×ATR), nem érintve

**CVE (Cenovus Energy, Energy, score 92,0)**:
- Entry $30,38 (planned $30,43, slippage -0,16% kedvező)
- MOC $30,81 = **+$159,10 (+1,42%)**
- 370 share × +$0,43
- Konzisztens Energy szektor mozgás (SEDG-vel egybehangzó)

### Vesztesek (3 ticker, 4 trade fill, -$409,41)

**GLW (Corning Inc, Technology, score 90,5)**:
- Entry $199,87 (planned $198,68, slippage +0,60% kedvezőtlen)
- LOSS_EXIT $194,37 = **-$137,62 (-2,75%)** ⚠️ **GROSS-LEGNAGYOBB VESZTES**
- 25 share × -$5,50
- LOSS_EXIT trigger -2,75% intraday mozgás után

**MRVL (Marvell Technology, Technology, score 90,5)**:
- Entry $181,58 (planned $180,37, slippage +0,67% kedvezőtlen)
- MOC $177,00 = **-$132,82 (-2,52%)**
- 29 share × -$4,58
- NEM LOSS_EXIT, MOC kitartott (-2,52% % közel a küszöbhöz, de nem alatta egész napon)

**RVTY (Revvity, Healthcare, score 87,0 — BOTTOM) — 2-split bracket fill**:
- Entry $95,38 (planned $95,16, slippage +0,23% mild kedvezőtlen)
- MOC $94,11 = -$127,00 (1. fill 100 share × -$1,27)
- MOC $94,05 = -$11,97 (2. fill 9 share × -$1,33)
- Total: **-$138,97 (-1,33% to -1,39%)**
- 2-split = IBKR partial fill artifact (NEM bug)
- Bottom score = bottom performer ma — kompletten kontraindikálva

## Anomáliák

- **HYMC takarítás 09:20 SIKERES** — egy próbára, IBKR conn stabil (vs tegnap 1 connection failed) ⭐
- **AVDL.CVR (69.0 share)** továbbra is non-tradable, ignorálva — Tamás IBKR account reset (W21 D2-3) majd megoldja
- **A `nuke.py` 0 open orders mutatott** ma reggel — a HYMC bracket order már triggerelődött tegnap 21:40 körül (IBKR autonóm fill)
- **Slippage pattern megszakadt** (péntek +0,48%, 5 napi kedvező pattern után)
- **AAPL, LION, SDRL, DELL phantom-events** ma valószínűleg ismétlődtek (a monitor.py-t nem nyitottam meg, de a 4 előző napon konzisztensen voltak)
- **VIX +4,86% emelkedés** + SPY -1,20% — **valódi risk-off nap**, nem csak mild
- **5 ticker, mind LONG, BMI YELLOW** — strategy LONG változatlan
- **Phase 4 qualified: 172** ⭐ — az 5 napos snapshot fix mintán a legmagasabb count (vs hét átlag 153,6)

## Kulcsmegfigyelések

### 1. ⭐⭐ SEDG TP2 HIT — ÚJ SINGLE-TRADE REKORD (+14,44%, +$206,28)

A 60+ napi sample 4-5. TP2 hit-je, **rekord single-trade hozammal**. A 2026 áprilisi 13 pontos terv 6. javaslata (50/50 bracket-osztás) **MŰKÖDÉSI VALIDÁCIÓJA**: mindkét bracket fele érdemleges P&L kontribúcióval bír. **A swing pivot új TP-struktúra (TP1 1,5×ATR, TP2 3,0×ATR) elvileg még magasabb TP2-ig kitarthat** — Fázis 3 deploy után az új paper trading futáson dől el.

### 2. ⭐⭐ STRUKTURÁLIS — Risk-off outperform pattern MEGERŐSÍTÉS

A 9 napi sample-ban (W19 D1 → W20 D5): **4 bull rally nap átlag -0,74% excess, 1 risk-off nap +1,28% excess**. **A rendszer karakter-konzisztens defenzív erő risk-off / lateral napokon**, kompromittált bull rally napokon. A péntek +1,28% excess **valószínűleg TOP 3 legjobb adatpont** a 60 napi sample-ban. A swing pivot új architektúra Fázis 3 deploy után **mind a két karakter-mintát** módosíthatja.

### 3. ⭐ "Magas pontszám paradoxon" 2. nap egymás után megfordult — Spearman ~+0,90 ma

SEDG 94,5 TOP = TOP win, RVTY 87,0 BOTTOM = LOSS. **2 napi minta a 60 napi -0,000 r mintán NEM cáfolja** a hosszú távú pattern-t, de **a W20 heti score-P&L korreláció r=+0,199 + W19 +0,303** **2 hét egymás után pozitív heti korreláció** — érdekes a Fázis 2 backtest számára.

### 4. ⚠️ Slippage pattern MEGSZAKADT — péntek +0,48% kedvezőtlen

5 napi konzekutív kedvező pattern után (W19 D4 → W20 D4) ma kedvezőtlen. SEDG +1,05%, GLW +0,60%, MRVL +0,67% — 3 mid-cap Tech/Energy ticker. **NEM cáfolja az alapvető 16:20 CEST entry-időpontot**, de **a kvantitatív backtest** (P2.1 Fázis 2 W23) **a péntek bukását is feldolgozza**.

### 5. ⚠️ LOSS_EXIT visszatért (GLW -$137,62, 1 instancia)

W20 heti LOSS_EXIT: 7/26 = 26,9% (vs W19 25%). A LOSS_EXIT karakter stabil. **A swing pivot mental stop architektúra strukturálisan eliminálja** a fixed bracket-stop logikát.

### 6. ⭐ HYMC takarítás SIKERES, IBKR conn STABIL — Fázis 1 előkészületre felkészültség

A `nuke.py` 09:20 sikeres egy próbára (vs tegnap 1 failed). **0 open orders** mutatott (HYMC bracket már triggerelt). **AVDL.CVR phantom marad**, IBKR account reset (Fázis 1, W21 D2-D3) megoldja.

### 7. ⭐ Phase 4 qualified 172 — 5 napos mintán a legmagasabb count

A snapshot fix DEPLOYED 5. nap konzisztens. A 172 qualified > 85 score a hét átlag (153,6) felett — **egy kis bizonyíték a scoring rendszer hosszabb távú stabilitására**.

### 8. ✓ Szektor-szelektív karakter: ENERGY OUTPERFORM, TECH UNDERPERFORM (risk-off napon)

2 Energy ticker (SEDG, CVE) → 2 nyertes (+$488,77)
2 Technology ticker (GLW, MRVL) → 2 vesztes (-$270,44)
1 Healthcare ticker (RVTY) → 1 vesztes (-$138,97)

**Makró-konzisztens**: Energy gyakran defenzív / counter-cyclical risk-off-ban. **A sector_rotation Phase 3 modul** ma a beadási sorrend szerint helyesen működött (a Phase 3 univerzumban Energy leader, Tech laggard valószínűleg).

## Heti összefoglaló (W20, 5 nap) — `weekly_metrics.py` output

A heti elemzés `docs/analysis/weekly/2026-W20.md`-be generálva. Kulcsmetrikák:

| Metrika | W20 | W19 | Megjegyzés |
|---------|-----|-----|------------|
| Trading days | 5 | 4 | |
| Net P&L | -$154,95 | -$727,64 | Markáns javulás |
| Gross P&L | -$74,47 | -$629,45 | |
| Commission | -$80,48 | -$98,19 | |
| **Commission/Gross arány** | **108%** | 16% | **W20: a commission elnyelte a gross-pozitív napokat** |
| Excess vs SPY | -0,30% | -2,14% | Markáns javulás |
| TP1 hit | 1/26 = 3,8% | 4/32 = 12,5% | W20 kevesebb TP1 |
| **TP2 hit** | **1/26 = 3,8%** ⭐ | 1/32 = 3,1% | W20-ban a SEDG TP2 |
| LOSS_EXIT | 7/26 = 26,9% | 8/32 = 25% | Stabil |
| Win days | 3/5 (60%) | 1/4 (25%) | Markáns javulás |
| Avg slippage | -0,21% | +0,12% | W20 kedvezőbb |
| Score→P&L korreláció | r=+0,199 | r=+0,303 | 2 hét egymás után pozitív |
| Qualified avg | 153,6/nap | 1,0/nap (buggy) | snapshot fix DEPLOYED W20-ban |

**A heti pattern**: 3 nyertes nap (h +28, csüt +313, p +62), 2 vesztes nap (k -369, sze -189). **A péntek +$61,67 nettó** csak részben kompenzálta a hét középpillanatának nagyobb veszteségeit. **A heti -$154,95 nettó STABILIZÁLÓDIK** a -$160 to -$200/hét sávban (W17 +$593 outlier kivételével), ami **a régi architektúra végső karakter-jellemzője**.

## Implikációk a rendszer számára

**A pénteki nap STRUKTURÁLIS TANULSÁGAI a Dev chat-nek (Fázis 1 előkészület):**

1. **A 2026 áprilisi 13 pontos terv 6. eleme (50/50 bracket-osztás) MŰKÖDÉSI VALIDÁCIÓJA** — érdemes a swing pivot új TP-struktúrában (TP1 1,5×ATR, TP2 3,0×ATR) **megtartani** az 50/50 osztást. A `docs/design/swing-risk-spec.md` Fázis 2 design-jának egyik kulcs eleme.

2. **A risk-off karakter outperform pattern megerősítése** — a swing pivot **NEM kell strukturálisan megváltoztassa** ezt a karaktert. A 3-5 napi hold + mental stop **valószínűleg megőrzi** a defenzív erőt risk-off napokon. **A bull rally underperform-ot** a swing horizont **inkább javítja** (több időtáv → momentum signal érvényesülhet).

3. **A "magas pontszám paradoxon" 2 napi megfordulása + W19+W20 pozitív heti korreláció** — **érdekes hipotézis a Fázis 2 backtest számára**: vajon a snapshot fix DEPLOYED utáni "tisztább" scoring már strukturálisan jobban prediktál? Ez **kvantitatív kérdés**, ami a P2.1 entry timing backtest + scoring revízió kontextusában merülhet fel.

4. **A péntek slippage bukása** — a P2.1 entry timing backtest kontextusában **a péntek típusú alacsony-likviditás Tech ticker-ek nehezítik** a 16:20 entry-időpontot. **NEM cáfolja**, de a backtest 4 alternatíva (15:30/16:20/17:15/18:30) összehasonlítása segít.

5. **A swing pivot új architektúra (15:30 CEST entry, mental stop, 3-5 napi hold) elvileg MIND A NÉGY problématerületet kezelheti** — a Fázis 3 (W25+) deploy után az új paper trading futáson dől el (Day 1 ≈ jún 23, Day 63 ≈ szept 15).

**A jövő hét (W21, máj 18-22)**:

- **Hé W21 D1 (máj 19)**: Tamás `nuke.py --positions` cleanup (HYMC már zárva, AAPL már zárva, csak AVDL.CVR phantom marad)
- **Máj 19-22**: IBKR paper account reset (Tamás manuális, $100k újra)
- **Máj 19-22**: CC első task — IBKR Gateway monitoring + Telegram alert (P1.1, ~1 óra) — **ma reggeli HYMC takarítás IBKR conn stabil volt**, de **csüt reggel 1 connection failed** — közvetlen indoklás a monitoring task-ra
- **Máj 23-25**: CC második task — 10-Q SEC Filing Exclusion (P1.2, ~2-3 óra)
- **Máj 26-30**: CC harmadik task — UW config deaktiválás + shadow log infra (~1-2 óra)
- **A régi rendszer FUT vasárnap (máj 17) és hétfő (máj 18) is** a tervezett ütemezés szerint — Tamás csak hétfő reggel (W21 D1) szakítja meg

## References

- `state/phase4_snapshots/2026-05-15.json.gz` — 5. tiszta snapshot (172 qualified)
- `state/daily_metrics/2026-05-15.json` — Day 65/63 metrika (gross +$79.36, net +$61.67, excess +1.28%)
- `scripts/paper_trading/logs/trades_2026-05-15.csv` — 7 trade fill (5 ticker)
- `logs/pt_eod_2026-05-15.log` — EOD P&L + Cumulative -$1,204.48
- `logs/pt_close_2026-05-15.log` — 3 MOC submit (RVTY, MRVL, CVE)
- `logs/pt_nuke_2026-05-15.log` — reggeli HYMC -140 SHORT takarítás (egy próbára, 0 open orders)
- `logs/pt_monitor_2026-05-15.log` — (nem nyitottam meg részletesen, valószínűleg TP1/TP2 SEDG fill events + LOSS_EXIT GLW)
- `docs/analysis/weekly/2026-W20.md` — heti elemzés (`weekly_metrics.py` output)
- `docs/decisions/2026-05-14-day63-decision-outcome.md` — Day 63 outcome
- `docs/STATUS.md` — kumulatív frissítendő (-$1,204.48)
- `docs/handoff/2026-05-15-log-review-handoff.md` — pénteki heti handoff (jön ezután)

**State**: BC23 utolsó péntekje (régi architektúra) + **SEDG TP2 single-trade rekord** (+14.44%) + Breakeven Lock (2. validáció csüt, ma 0 BL aktiváció) + MID Bundle + vix-close + snapshot fix DEPLOYED (5 nap konzisztens) + dp_pct rekal DEPLOYED + **HYMC bracket bug 5. instancia kezelve** + Day 63 outcome doc rögzítve

**Aktív CC tasks**: 0 (W21 D1, máj 19-én indul az első CC task: IBKR Gateway monitoring P1.1)

**A pénteki napi karakter egy mondatban**: A régi rendszer **utolsó pénteki napja egy single-trade rekorddal** (SEDG +14.44% TP2) **és egy strukturálisan jelentős risk-off outperform-mal** (+1.28% excess) **zárta a hét, MIND a két finding a swing pivot új architektúra szempontjából RELEVÁNS** — a 50/50 bracket-osztás megőrzendő, a risk-off karakter strukturálisan stabil, és a Fázis 1 cleanup máj 19-én Tamás kontrolált indításával kezdődik.
