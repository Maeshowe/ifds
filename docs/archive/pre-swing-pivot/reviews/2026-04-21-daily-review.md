# Daily Review — 2026-04-21 (kedd)

**BC23 Day 7 / W17 Day 2**  
**Paper Trading Day 47/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$566.40 |
| Napi P&L net | **+$553.41** |
| Kumulatív P&L | **-$543.05 (-0.54%)** |
| Pozíciók (új) | 3 (POWI, AMD, GME) |
| Win rate | 3/5 trade (a POWI TP1+TP2 külön; ticker-szinten 2/3) |
| **TP1 hit rate** | **2/5 (40%)** ← **első TP hit a BC23 óta** |
| **TP2 hit rate** | **2/5 (40%)** |
| LOSS_EXIT | 4 (mind GME split) |
| MOC | 1 (AMD) |
| SPY return | -0.65% |
| Portfolio return | +0.57% |
| **Excess vs SPY** | **+1.22%** ← **első pozitív >1% a BC23 óta** |
| VIX close | 19.49 (+3.34%) |

## Piaci kontextus

- **VIX +3.34%** — harmadik napja emelkedik (17.44 → 18.86 → 19.49)
- **SPY -0.65%** — folytatódó negatív trend
- **MID regime:** STAGFLATION Day 4
- **Portfolio divergence:** +1.22% excess — **semi sector rally mentette a napot**

## Pozíciók

| Ticker | Score | Sector | Entry | Exit | P&L | Exit Type | Note |
|--------|-------|--------|-------|------|-----|-----------|------|
| POWI | **95.0** | Tech/Semi | $63.97 | $66.80 / $68.50 | **+$758** | TP1 + TP2 | Full exit chain |
| AMD | 93.5 | Tech/Semi | $280.78 | $284.44 | **+$95** | MOC | Trail aktív, nem triggerelt |
| GME | 92.5 | Cons. Cyclical | $25.29 | $24.73-74 | **-$287** | LOSS_EXIT -2.06% | Gyors bevágás |

## A nap története — POWI

**Tankönyvi swing setup, teljes BC20A exit chain élesben:**

```
14:18 UTC  Entry: $63.97 (score 95.0, legmagasabb)
           SL $60.57, TP1 $66.80 (+4.42%), TP2 $68.50 (+7.08%)
           Bracket split: 103A + 103B

17:00 UTC  Trail B activated @ $65.09 (+1.75%, breakeven buffer fölött)
17:25      Trail SL $61.72 → $62.27 (fokozatos)
17:40      $62.48
17:50      $62.82
18:10      $63.25

18:15 UTC  TP1 HIT @ $66.80
           ↓ A bracket félig zárva (+$283 + $8.49 = $291.49)
           ↓ Trail A activated @ $63.97 (breakeven!)

18:55      Trail SL $64.25
19:10      $64.40
19:20      $64.85 (tovább emelkedik)

19:25+     Záró rally $68.50 felé
20:05 EOD  TP2 fill @ $68.50 → +$453 + $13.59 = $466.59
```

**Total POWI P&L: +$758.08** (4 trade a state-split miatt: 103×TP1 + 103×TP2)

**Ez POWI egyedül fedezi a napi +$566 nyereséget.** AMD +$95 és GME -$287 kiegyenlíti egymást (~-$192 net), a POWI az igazi alpha.

## AMD — a csendes nyertes

- Entry $280.78, TP1 $294.38 (+4.84%), TP2 $302.25
- Intraday max ~$285.68, TP1-et nem érte el
- Trail B aktív volt, SL fokozatosan $267 → $269.94
- 19:40 MOC submit, fill @ $284.44 (+1.3%)

**Figyelemreméltó:** ha a trail SL triggerelt volna (~$269.94), a P&L -$283 lett volna (SL @ $269.94 × 26 = -$10.84 × 26 = -$282). A MOC mentette meg. Ez rámutat: a trail SL **túl lazán** skálázódik AMD-szerű high-price tickereken ($15+ buffer). **Érdemes lesz a héten nézni**, hogy más tickereken hasonló minta-e.

## GME — gyors bevágás

- Entry $25.29, SL $24.12 (-4.63%), TP1 $26.24 (+3.83%)
- 14:18 submit → 17:10 loss_exit @ $24.75 (-2.06%)
- Csak **2 óra 52 perc** a belépéstől a bevágásig
- 4 split miatt összesen **-$287** (514 shares × -0.55)

**A LOSS_EXIT a második napon is kulcs volt:**
- Tegnap SKM: -2.53% @ $38.46 → -$298
- Ma GME: -2.06% @ $24.75 → -$287

**2 nap alatt ~-$585 loss_exit** — ha ezek **stop loss -4.63%-nál** triggereltek volna (SL level), az körülbelül **duplán annyi** lett volna. A loss_exit mechanika élesben **bizonyítottan értéket ad**.

## Exit mix változás

| Exit type | W16 (5 nap) | W17 Day 1 | **W17 Day 2** |
|-----------|-------------|-----------|---------------|
| TP1 hit rate | 0/18 (0%) | 0/5 (0%) | **2/5 (40%)** |
| TP2 hit rate | 0 | 0 | **2/5 (40%)** |
| LOSS_EXIT | 0 | 1/5 | 4/5 (mind GME) |
| MOC only | ~100% | 4/5 | 1/5 |

**Az első TP1 és TP2 hit a BC23 deploy óta** (ápr 13). Ráadásul ugyanazon a tickeren **mindkét bracket** kijátszott — ez a BC20A swing hybrid exit design **teljes validálása** élesben.

## Kulcs megfigyelések

### 1. Semi sector divergence

Miközben a SPY -0.65%-ot mozgott, a technology/semi szektor tickerei erősen rally-ztek:
- POWI +8.96% napon belül
- AMD +3.47% napon belül

**A MID tegnapi CAS heatmap** már mutatta: XLK tartósan **ACCUMULATING/OVERWEIGHT** állapotban. A mai napi divergence ezt élesben erősíti meg.

**Ez jelentőség:** a piac-szintű negatív trend **nem** jelenti, hogy minden szektor elesik. A BC23 scoring ma **helyesen azonosított** két semi tickert (POWI, AMD), amik a broad market ellen rally-ztek. **Ebben a specifikus esetben a scoring jól működött.**

### 2. Contradiction flag — második nap adatpont

Ma:
- **0 CONTRADICTION flag** a 3 ticker közül (POWI, AMD, GME)
- Eredmény: 2/3 nyertes ticker, +$553 net

Tegnap:
- **3 CONTRADICTION flag** az 5 ticker közül (CNK, GFS, SKM)
- Eredmény: 3/3 flagged veszített, -$433 net

**Összesített hipotézis (2 nap, nem bizonyíték):**
- Contradiction flag = rossz jel
- Flag-mentes ticker = jobb prognózis

**Ez a backlog-ideas `M_contradiction multiplier` javaslat erősödő indoklása.** Ha a péntek heti metrika is ezt mutatja, W18 elején implementálni lehet.

### 3. A position count dinamika

Ma csak **1 qualified above threshold**, és **3 pozíció** összesen. Tegnap 5. A Phase 6 ma fewer-but-higher-conviction filozófiát alkalmazott.

**Eredmény:** a POWI +$758 egyedül **fedezte a napot**, az AMD és GME összességében flat lenne.

**Kérdés:** ha ma 5 pozíció lett volna (mint tegnap), a 4-5. pozíció lehet hogy veszített volna (legalacsonyabb score). A **kevesebb pozíció = magasabb konverzió** hipotézis megtámogatódik. Érdemes a hét végére megnézni, és W18-ban fontolóra venni a threshold 85 → 90 emelést.

### 4. A TP1 1.25×ATR feltételes működése

**Tegnap:** 0/5 TP1 hit (alacsony realized vol napon 1.25×ATR elérhetetlen)  
**Ma:** 2/5 TP1 hit, 2/5 TP2 hit (magas realized vol, szektor rally)

**Tanulság:** a fix ATR multiplier nem univerzális. Olyan napokon ahol a realized volatility magas (pl. POWI +8.96%), a TP1 könnyen elérhető. Alacsony napokon (tegnap) a TP soha sem triggerel.

**Hosszú távú megoldás (BC24+):** TP távolság skálázása a várható napi volatilitáshoz (GARCH forecast vagy dinamikus ATR-multiplier). **Nem most.**

### 5. Score rank ma

- POWI 95.0 → **legnagyobb nyertes (+$758)**
- AMD 93.5 → flat (+$95)
- GME 92.5 → **legnagyobb vesztes (-$287)**

**Pozitív rank korreláció egy napon belül.** Ez ellentmond a tegnapi (és W16) inverz mintának. **Egy nap nem statisztikai bizonyíték** — lehet random, lehet hogy a contradiction-mentes tickerek tisztábban differentiable-ak.

## Anomáliák

- **Leftover-k:** 20:00-kor `leftover_found: CRGY`, `leftover_found: AAPL`. CRGY régi márciusi maradék (ismert), AAPL új — ez **nem volt a mai új pozíciók között**. Valószínűleg tegnapi/korábbi napok nem tisztán zárt pozíciója. **Hétvégi teendő:** Tamás nuke manuálisan.
- **DELL + DOCN phantom_filtered:** tegnapi DELL pozíció zárása után maradt, a monitor phantom_filtered sor ezt kiszűri — nem hiba.
- **LION + SDRL late events:** 20:00-kor bemelegedtek régi pozíciók (LION TP1 hit, SDRL loss_exit -$138). Ezek nincsenek a napi P&L-ben (napi metrics csak POWI/AMD/GME), de a pt_events.jsonl-be bekerültek.

## A nap tanulsága

**Egy jó nap nem mentesít a hosszú távú mérés alól** — pozitív excess +1.22%-kal is. De:

1. **A BC23 exit chain MŰKÖDIK** (POWI TP1 → Trail → TP2 kristály tiszta)
2. **A loss_exit MŰKÖDIK** (GME -2.06% bevágás, nem engedett -4.63% SL-ig)
3. **A contradiction-mentes tickerek jobban teljesítenek** (2 nap után mintázat épül)
4. **A momentum scoring értékes szektor-divergencia idején** (ma a semi rally)

**Ami még mindig nyitott:**

1. TP1 fix ATR vs dinamikus vol-alapú
2. Score inverz vs pozitív korreláció — 2 nap alatt mindkét mintát láttuk, zaj vagy szignál?
3. Pozíciószám (3 vs 5) — fewer = better?
4. Leftover-k kezelése — miért nem tisztul magától

## Teendők

- **Nincs most** — egy jó nap nem indok változtatásra
- **Péntek (ápr 24):** W17 heti metrika — mindhárom nap adata (hétfő, kedd, szerda, csütörtök, péntek)
- **Hétvégén:** 
  - Tamás: CRGY/AAPL leftover nuke
  - Chat: MID vs IFDS sector rotation összehasonlítás (CAS heatmap 20 napos adatból)

## Kapcsolódó

- `state/phase4_snapshots/2026-04-21.json.gz`
- `logs/pt_events_2026-04-21.jsonl`
- `state/daily_metrics/2026-04-21.json`
- `logs/cron_intraday_20260421_161500.log`
- Screenshot: TradingView IFDS watchlist (POWI +8.96%, AMD +3.47%)
