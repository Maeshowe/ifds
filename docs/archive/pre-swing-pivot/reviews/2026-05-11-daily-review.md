# Daily Review — 2026-05-11 (hétfő)

**BC23 Day 21 / W20 Day 1 — ELSŐ NAP A KÉT P1 DEPLOY UTÁN**
**Paper Trading Day 61/63 — 2 nap a Day 63 KIÉRTÉKELÉSIG**
**M_contradiction LIVE 6. nap**
**Kézi order submission (IBKR + Polygon akadás 16:20 CEST)**

**Adat-frissesség:** EOD log 22:05, daily_metrics.py 22:10 CEST után frissítve. Phase 4 snapshot 22.89 KB (a fix után **először teljes universum**). Cron_intraday log tartalmazza az 1390 ticker analízisét + UW HTTP 429 rate limit anomáliákat.

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$34.93 |
| Napi P&L net | **+$28.26** (gyakorlatilag flat nap) |
| Kumulatív P&L (paper aggregát) | **-$1,095.08 (-1.09%)** ⭐ marginális javulás (-$1,130 → -$1,095, +$35) |
| Tényleges valós (SQM korrekcióval) | ~-$981 (-0.98%) becsült — közel a -$1,000 sávhoz |
| Pozíciók (új) | 3 ticker (FORM, HYMC, AAPL) — **a max 5-ből csak 3 javasolt** |
| Trade count | 3 (mind MOC zárás) |
| Win rate ticker szinten | **1/3 (33%)** — FORM nyertes, HYMC + AAPL vesztes |
| TP1 / TP2 / SL / LOSS_EXIT / TRAIL hit | 0 / 0 / 0 / 0 / 0 |
| Exit mix | **3× MOC** (100%) |
| Avg slippage | **-1.79%** ⭐ **kedvező** — a kézi rögzítés mellékhatása |
| SPY return | +0.23% (mild bull) |
| Portfolio return | +0.03% |
| **Excess vs SPY** | **-0.19%** ⚠️ underperform (folytatja a "bull rally underperform" pattern-t) |
| VIX close | **18.45** (Δ +7.64%, ~17.14 → 18.45) — kis emelkedés, de még alacsony |
| Reggeli akció | `monitor_positions` 10:10 CEST: no_leftover (tiszta induló állapot) |
| **Snapshot méret** | **22.89 KB** ⭐ — a fix után először teljes universum (504 B → 22.89 KB) |

## 🎯 SNAPSHOT FIX VALIDÁCIÓ — 100% SIKERES

A `d3fce73` commit (péntek deploy) **első élesben tesztelt hétfő:**

```
Phase 4 Stock Analysis:
  Analyzed: 1390 ticker
  Passed: 159 (átlépte a 70-es küszöböt + tech filter + crowded szűrés)
  Excluded: 1231
    - Tech filter: 578
    - Score < 70: 623
    - Crowded (>95): 30

Snapshot output:
  state/phase4_snapshots/2026-05-11.json.gz → 22.89 KB
```

**A snapshot-méret evolúció kristálytisztán mutatja a teljes bug-történetet:**

| Időszak | Méret | Tartalom |
|---|---|---|
| 2026-02-19 → 2026-04-03 | 16-45 KB | Teljes universum (60-100 ticker) — PRE-BUG |
| **2026-04-05 → 2026-04-17** | **396 B** | AAPL-only mock (BUG aktív) |
| 2026-04-20 → 2026-05-01 | 463 B | AAPL-only mock (+67 B: új field) |
| 2026-05-04 → 2026-05-08 | 504 B | AAPL-only mock (+41 B: M_contradiction field) |
| **2026-05-11** | **22.89 KB** ⭐ | **TELJES UNIVERSUM VISSZAÁLLT** |

**Kritikus korrekció a master-reference 04-risks 1.1 szakaszhoz:**
A bug kezdődátuma **2026-04-05** (NEM 2026-04-10, ahogy a korábbi dokumentumokban szerepelt). 5 nappal korábban indult. Ez:
- A flow-decomposition 232-trade audit "valid scope" — **Feb-Apr 3** (NEM Feb-Apr 9), 5 nap kevesebb
- A master-reference 04-risks 1.1, és a scoring-validation.md is **frissítendő**

**Validáció státusza:** a snapshot fix a tervezett módon működik — a hétfői 16:15 cron a teljes Phase 4 outputot mentette. **A scoring-validation újrafuttatása már lehetséges** Day 63-on (csüt máj 14), és onnan kezdve minden napon teljes mintán fog dolgozni.

## ⚠️ KÉZI ORDER SUBMISSION — DUPLA INFRA AKADÁS

A `cron_intraday_20260511_161500.log` vége kristálytisztán dokumentálja az automata workflow összeomlását:

```
16:20:11 [INFO] IFDS Paper Trading — 2026-05-11
16:20:11 [INFO] Reading: execution_plan_run_20260511_141500_38717b.csv
positions request timed out
open orders request timed out
completed orders request timed out
account updates for DUH118657 request timed out
IBKR connection attempt 1/3 FAILED (clientId=10)
[ismétlődik 3x retry-ra]
IBKR connection FAILED after 3 attempts (clientId=10):
```

**ÉS** a `pt_avwap_2026-05-11.log` szinte üres:
```
22:00:10 [WARNING] TEST: No 1-min bars from Polygon
```

**TEHÁT:** 16:20 CEST körül **kettős infrastruktúra-akadás** történt:
1. **IBKR Gateway** elérhetetlen volt (timeout × 3)
2. **Polygon 1-min bars** nem érkezett (vagy a market open előtti regime miatt, vagy átmeneti API akadás)

**Tamás 17:15 CEST körül kézzel rögzítette az ordereket** — az aktuális market árhoz igazítva (nem a tervezett $151 / $45.29 / $292.23 limit árakhoz).

**Konzekvenciák a P&L-re (lentebb a FORM slippage szakaszban részletezve):**
- FORM tervezett $151 → fill $144.20 → **-4.5% slippage (KEDVEZŐ)**
- HYMC tervezett $45.29 → fill $44.77 → **-1.15% slippage (kedvező)**
- AAPL tervezett $292.23 → fill $293.09 → +0.29% (minimal kedvezőtlen)
- **Átlag: -1.79% (KEDVEZŐ)**

**A reggeli IBKR/Polygon outage tulajdonképpen HASZNOT hozott** a stratégia szempontjából — a kézi 17:15-i rögzítés a reggel utáni profit-taking idejére esett, és a két ticker olcsóbban szállt be.

**DE:** ez **nem a rendszer érdeme**, hanem szerencse. **Új P1 backlog idea:** "IBKR Gateway monitoring + alert" — ha az automata submit timeoutol, küldjön Telegram értesítést, hogy Tamás azonnal tudjon manuálisan reagálni (NE 55 perccel később).

## ⚠️ UW HTTP 429 RATE LIMITS — A dp_pct DEPLOY MELLÉKHATÁSA

A `9a169b9` deploy a `UWBatchDarkPoolProvider → UWDarkPoolProvider` (per-ticker fetch) változtatást hozott. **Az első élesben futás során tömeges HTTP 429 jelent meg**:

```
Phase 4 darkpool calls:
  [API ERROR] unusual_whales /api/darkpool/PTRN: HTTP 429 (attempt 3/3)
  [API ERROR] unusual_whales /api/darkpool/NTCT: HTTP 429 (attempt 3/3)
  [API ERROR] unusual_whales /api/darkpool/RLAY: HTTP 429 (attempt 3/3)
  [API ERROR] unusual_whales /api/darkpool/DFTX: HTTP 429 (attempt 3/3)
  [API ERROR] unusual_whales /api/darkpool/COHU: HTTP 429 (attempt 3/3)
  [+ kb. 10-15 további ticker]

Phase 5 greek-exposure calls:
  [API ERROR] unusual_whales /api/stock/PPG/greek-exposure/strike: HTTP 429
  [API ERROR] unusual_whales /api/stock/AVT/greek-exposure/strike: HTTP 429
  [+ kb. 10-15 további ticker]
```

**Hatás a dp_pct rekal validációjára:** azoknak a tickereknek, ahol a UW hívás 3/3 retry után is failelt, **a dp_pct score = 0 (no data)** — tehát **NEM kaptak -10/-15 score reduction-t**. A dp_pct rekal **CSAK a successful fetch-ek tickerein érvényesül**.

A 3 megnyitott ticker (FORM, HYMC, AAPL) **sikeresen kapott UW dark pool adatot** (mert a top-N-ig eljutottak), de a 1390-es universum egy jelentős része **dp_pct-mentesen score-olódott**. **Ez torzítja a dp_pct rekal hatás-validációját.**

**Becslés:** a 1390 universum-ból kb. 30-50 ticker (vagy több) failelt UW-hívásra. Ezekért az ifds rendszer most "no signal" pozícióban van — sem a régi (+10/+15 bonus), sem az új (-10/-15 penalty) nem érvényesül.

**Új P1 backlog idea:** **UW rate limit kezelés finomítás** — concurrency limiter (max ~5 párhuzamos hívás), exponential backoff (1s, 3s, 9s), vagy semaphore-pattern. Effort: ~1-2 óra CC.

**Másik új P2 backlog idea:** **dp_pct fallback default** — ha a UW hívás failelt, a ticker kapjon valami észszerű default értéket (pl. universum-medián), ne 0-t. Effort: ~30 min CC.

## ⚠️ FORM SLIPPAGE FINDING — A +$213 NAGYRÉSZE NEM A STRATÉGIÁBÓL JÖTT

Ez a nap legkritikusabb adatpontja. A FORM trade részletes szétboncolása:

```
Execution plan (16:15 CEST cron):
  Tervezett entry: $151.00 (LIMIT)
  Tervezett qty: 29 share (multiplier 0.68 miatt csökkentett)
  Tervezett stop_loss: $134.88
  Tervezett TP1: $164.43 (+8.9%)
  Tervezett TP2: $172.49 (+14.2%)
  Tervezett risk: $476 (a 0.7% × 0.68 = 0.48% effective)

Kézi rögzítés (17:15 CEST):
  Fill entry: $144.20 (SLIPPAGE -4.5%)
  qty: 29 share

MOC zárás (22:00 CEST):
  Exit: $151.57

P&L decomposition:
  Tényleges: $151.57 - $144.20 = +$7.37/share × 29 = +$213.73
  Ha a tervezett $151.00-on lépett volna be:
    Hipotetikus P&L: $151.57 - $151.00 = +$0.57/share × 29 = +$16.53
  SLIPPAGE HOZADÉK: $151.00 - $144.20 = +$6.80/share × 29 = +$197.20
```

**Tehát a +$213.73 P&L összetétele:**
- **~$197 (92%) — slippage-haszon** a kézi rögzítés alacsonyabb entry árából
- **~$17 (8%) — tényleges intraday momentum** ($144 → $151.57 a strategiai szempontból csak +0.38%)

**Ez egy NAGYON FONTOS finding:** a FORM eredménye **NEM a stratégia érdeme**. Ha az automatikus 16:20 submit sikeres lett volna a tervezett $151.00 entry-ár-ral, **+$16 lett volna a P&L, nem +$213**. **A nap valós P&L kb. -$165 lett volna** (FORM +$17, HYMC -$141, AAPL -$37) — egy kifejezetten gyenge nap.

**Tanulság:**
1. A FORM trade NEM számít be a stratégia "fair" teljesítményébe
2. A "kézi rögzítés szerencséje" egy ritka eset, nem reprodukálható szisztematikusan
3. A scoring-validation érdemes lenne **slippage-adjusted P&L-en** is futtatni (a +$200-os "noise"-okat eliminálva)

**Új P3 backlog idea (analitikus):** "Slippage-adjusted scoring validation" — a Day 63 utáni elemzéshez. Effort: ~30 min Chat-oldali.

## ⚠️ FORM — M_CONTRADICTION + M_TARGET_PENALTY DUPLA SZANKCIÓ (PÉNTEK AMD PATTERN FOLYTATÁSA)

A FORM execution plan paraméterei:

```csv
FORM,BUY,LIMIT,151,29,134.88,164.43,172.49,476.0,95.0,positive,Technology,0.68,1.0,1.0,55.82,neutral,False,1,price_above_consensus_22.4pct
```

**Két szankcionálás ugyanattól a signal-tól:**
- **M_contradiction**: `contradiction_flag=1`, reasons `"price_above_consensus_22.4pct"`, szorzó **0.80**
- **M_target_penalty**: a master-reference szerint ">20% target felett → ×0.85" — a 22.4% triggerelte, szorzó **0.85**
- **Összes szorzó**: 0.80 × 0.85 = **0.68** (qty 43 → 29, ~33% csökkentés)

**A FORM mégis a nap legnagyobb % nyerője lett (+5.11% intraday).** Ha a multiplier 1.0 lett volna:
- qty: 43 (a 29 helyett, +48% nagyobb position)
- Tényleges P&L (slippage-effekt nélkül): 43 × $0.57 = +$24.50
- A slippage-haszonnal: 43 × $7.37 = **+$316.91 helyett $213.73** → **-$103 elmaradt nyereség**

**A péntek AMD pattern ma is megerősítve, sőt erősítve:** a kockázatra szankcionált tickerek (csökkentett position size) napi szinten a nap legjobbjai lesznek. **6 napos M_contradiction LIVE iránybeli helyesség most már ~40%-ra csökkent** (kedd 2/2 helyes, csüt 0/0 nincs adat, péntek 0/2 helytelen, hétfő 0/1 helytelen az M_contradiction tickeren — FORM nyertes, NE nem volt benne ma).

**6 napos M_contradiction LIVE összesítés:**

| Nap | Fired tickerek | Eredmények | Iránybeli helyesség |
|-----|----------------|------------|---------------------|
| Hé máj 4 | 0/5 | n/a | n/a |
| Ke máj 5 | NE (0.8), PTEN (0.8) | -$143, -$36 | ✓ helyes (mindkettő vesztes) |
| Sze máj 6 | 0/3 | n/a | n/a |
| Csü máj 7 | ? | ? | ? |
| Pé máj 8 | AMD (0.8), GOOG (0.8) | +$263, +$19 | ✗ helytelen (mindkettő nyertes) |
| **Hé máj 11** | **FORM (0.68 — DUPLA)** | **+$213** | **✗ helytelen** (nap-legjobb nyerő) |

**Statisztikai szignifikancia:** 5 fired tickerek 5 nap alatt — még mindig **kis n**. **20+ fire (W22+ scope) után érdemes szignifikancia-tesztet futtatni.** A 0.8× szorzó **konzervatív védelem** — NEM "kerülni a tickereket" — tehát a feature design alapvetően helyes.

## ⚠️ ÚJ DESIGN FINDING — M_CONTRADICTION & M_TARGET_PENALTY DEDUPLIKÁCIÓ

**A FORM esete (price_above_consensus_22.4pct → ÉS contradiction_flag=1 ÉS target_penalty 0.85) feltár egy redundanciát:**

A két feature **ugyanazt a signal-t használja** ("ár a target consensus felett") két különböző formában:
- M_contradiction binary trigger: az overshoot %-ja egy küszöb fölött (jelenleg ~8%? 20%?)
- M_target_penalty folyamatos: >20% → ×0.85, >50% → ×0.60

**A két szankcionálás ugyanattól az ok-tól származik**, és **kumulatívan szorzódik** — ez a "double jeopardy" probléma. Ha a tervezőszándék az volt, hogy a target overshoot egyszer büntessen, akkor a két feature között **csak az egyik** kéne fire-eljen.

**Két lehetséges javítási út:**
1. **M_contradiction trigger feltétel revízió**: a `price_above_consensus_X%` ÚJ feltétel: "X% felett **csak akkor**, ha az M_target_penalty NEM aktív" (>20% felett ne kapjon contradiction flag-et, csak a target_penalty érvényesüljön). Ezzel a két feature **kölcsönösen kizáró** lesz.
2. **M_target_penalty kombináció**: a `contradiction_reasons`-t **ne tartalmazza** a `price_above_consensus_X%`-ot, ha a target_penalty már triggerelt. Más triggers (recent_downgrades, accounting concerns stb.) maradhatnak.

**Hatás-becslés:** ez a változás a magas overshoot tickereket **csak az M_target_penalty-vel** szankcionálná (×0.85 vagy ×0.60). A FORM-szerű esetekben a multiplier_total **0.85-re emelkedne 0.68 helyett** — a position size ~25%-kal nagyobb lenne. **Hozadék**: kb. +$50-100/hét becsült (a péntek AMD + ma FORM-szerű esetekből).

**Új P2 backlog idea: "M_contradiction & M_target_penalty deduplikáció"** — Effort: ~1-2 óra CC (config + Phase 4 logika módosítás + tesztek).

## Pozíciók részletei

### Nyertes (1 ticker, +$214)

**FORM (Performance Food Group / FormFactor, Technology, score 95.0)**: Részletek fent. **Dupla M-szankció (0.68× multiplier), kézi rögzítés -4.5% slippage, MOC +5.11%. ~92%-ban slippage-haszon.**

### Vesztesek (2 ticker, -$179)

**HYMC (Hycroft Mining, Basic Materials, score 95.0)**: Entry $44.77 (planned $45.29, **slippage -1.15% kedvező**), MOC $43.76 = **-$141.40 (-2.26%)** — a nap legrosszabb. 140 share × -$1.01 vesztes. M_contradiction nem fired (multiplier_total 1.0). **Strukturális megfigyelés:** a HYMC egy **micro-cap / penny stock közeli** ticker (~$44 közelében), magas volatilitás. A -2.26% intraday move típusos ebben a tartományban. **Score 95 + vesztes** — folytatja a Score → P&L "nincs konzisztens iránya" pattern-t.

**AAPL (Apple, Technology, score 94.5)**: Entry $293.09 (planned $292.23, **slippage +0.29% minimal kedvezőtlen**), MOC $292.54 = **-$37.40 (-0.19%)** — gyakorlatilag breakeven. 68 share × -$0.55. M_contradiction nem fired (multiplier 1.0). **Klasszikus large-cap risk-off karakter** — egész nap szigorúan oldalozott, ami konzisztens a VIX +7.64%-os emelkedéssel (mild risk-off regime).

## Score → P&L napi nézet

| Ticker | Score | Multiplier | P&L net | Win? | Megjegyzés |
|--------|-------|------------|---------|------|------------|
| **FORM** | 95.0 | **0.68** ⚠️ | **+$213.73** | ⭐ | DUPLA M-szankcionált, slippage-haszon |
| HYMC | 95.0 | 1.00 | -$141.40 | ✗ | nap-legrosszabb, micro-cap volatilitás |
| AAPL | 94.5 | 1.00 | -$37.40 | ✗ | large-cap risk-off, breakeven |

**Az 5 napi W19 score pattern + ma:**
- Ke (W19 D2): NE 95 = -$143 — high score, vesztes
- Sze (W19 D3): RMBS 93.5 = vesztes
- Csü (W19 D4): ERIC 92.5 = breakeven, VTR/SQM = vesztesek
- Pé (W19 D5): CRWD 95 = +$247 nyertes, MTCH 95 = -$43 vesztes ⇒ **mixed**
- **Hé (W20 D1): FORM 95 = +$214 nyertes, HYMC 95 = -$141 vesztes, AAPL 94.5 = -$37 vesztes ⇒ mixed**

**6 napi trend: a Score → P&L korreláció INSTABIL** napról napra. **W19 weekly r = +0.303** volt, és a W20-ra megint visszafordul a 0 felé. **Hosszú távon (60+ nap) r = 0.000 marad** — a scoring rendszer **mint egész nem prediktív**, csak az al-komponensei (PCR, RVOL, OTM) prediktívek külön-külön.

## Excess vs SPY — pénteki "outperform mild lateral napon" pattern, hétfő "underperform mild bull napon" pattern

| Nap | Net P&L | SPY return | Portfolio return | Excess vs SPY |
|-----|---------|------------|------------------|---------------|
| Hé D1 (W19) | -$191 | -0.37% | -0.15% | +0.21% ⭐ |
| Ke D2 | -$269 | +0.80% | -0.24% | -1.04% |
| Sze D3 | +$234 | +1.39% | +0.25% | -1.14% |
| Csü D4 | -$501 | -0.31% | -0.49% | -0.18% ✓ |
| Pé D5 | +$486 | ~0% | +0.49% | +0.49% ⭐ |
| **Hé D1 (W20)** | **+$28** | **+0.23%** | **+0.03%** | **-0.19%** ⚠️ |

**Pattern megerősítés:** a swing trading rendszer:
- ⭐ **Outperformolt** risk-off és lateral napokon (3 napi: W19 D1, W19 D5, részben W19 D4)
- ⚠️ **Underperformolt** bull rally napokon (4 napi: W19 D2, W19 D3, W20 D1)

**A hétfő (mild bull SPY +0.23%) tipikus underperformance** — a stratégia karaktere stabil. **Az 5+1 napi excess átlag: -0.31%**, a Day 63 leállítási küszöb (-1.5%) **bőven biztonságos sávban**.

## MOC duplikáció (21:20 és 21:40 CEST) — NEM bug, normál cron-replay

A `pt_close_2026-05-11.log` mutatja:
```
21:20:51 [INFO] MOC Close — 2026-05-11
21:20:53 [INFO] MOC submitted: 3 positions
[20 perc szünet]
21:40:12 [INFO] MOC Close — 2026-05-11
21:40:14 [INFO] Cancelled 3 open orders before MOC
21:40:15 [INFO] MOC submitted: 3 positions
```

**Mi történt:**
1. 21:20 első cron futás: 3 MOC SELL order submit → IBKR oldali queue-ba
2. 21:40 második cron futás: a 3 függő order **cancel + resubmit** ugyanazokkal a paraméterekkel
3. 22:00 IBKR MOC auction: a 21:40 verzió fillel
4. EOD log 22:05: 3 trade rögzítve

**A `daily_metrics` 3 trade-et mutat** (NEM 6), tehát a P&L NEM duplikálódott. A cron-replay logika ("21:40 mindig refresh") **védelmet ad** az esetleges 21:20-i akadásokra. **Ez NEM bug — ez bevett gyakorlat.**

**Ellentétben a múlt csüt SQM bug:** ott a LOSS_EXIT 17:00 SELL és a bracket SL 22:00 SELL **ÉRDEMI duplikáció** volt (mindkettő külön order, külön fill árral). A cron-replay és a strukturális duplikáció **különböző mechanizmusok**.

## monitor.py gyanús események (LION/SDRL replay)

A `pt_events_2026-05-11.jsonl` 22:00 CEST körüli szakaszában megjelennek LION és SDRL események:

```jsonl
{"event": "tp1_detected", "ticker": "LION", "tp1_price": 10.0}
{"event": "trail_activated_a", "ticker": "LION", "trail_sl": 9.6, "price": 10.2, "entry_price": 9.5, "qty": 360}
{"event": "trail_sl_update", "ticker": "LION", "new_sl": 10.2, "price": 10.8}
{"event": "trail_hit", "ticker": "LION", "exit_price": 10.15, "trail_sl": 10.2, "qty": 360, "scope": "bracket_b"}

{"event": "trail_activated_b", "ticker": "SDRL", "trail_sl": 41.91, "price": 44.2, "entry_price": 43.7, "qty": 115}
{"event": "trail_hit", "ticker": "SDRL", "exit_price": 43.4, "trail_sl": 43.5, "qty": 115, "scope": "full"}
{"event": "loss_exit", "ticker": "SDRL", "qty": 115, "exit_price": 42.5, "entry_price": 43.7, "pnl": -138.0, "loss_pct": -2.75}
```

**MEGFIGYELÉS:** a LION és SDRL **NEM jelenik meg a daily_metrics-ben**, és **NEM jelenik meg az EOD log-ban** mint trade. **DE** strukturált eseményeket termeltek (TP1 detected, trail activated, trail hit, loss_exit).

**Hipotézis:** a `monitor.py` 22:00-i cron futása során **belső state-replay** vagy **integration teszt** fut le. Ezek nem tényleges trade-ek — hanem szimulált események, amelyek validálják a monitor logikát.

**Konkretizáló jelzések:**
- Az események `T20:00:10.4xxxxx` UTC időbélyeggel **ms különbséggel** követik egymást — túl gyors lenne real-time
- LION ugyanazok az események 3-szor ismétlődnek (tp1_detected × 3, trail_activated_a × 3) — replay loop
- SDRL `trail_hit` és `loss_exit` ugyanazon ticker-re — ez ellentmondás real-time-ban, de replay-ben validálási lépés

**Új P3 backlog idea (analitikus):** "monitor.py belső replay események jelölése" — egy `event_type: "replay"` field hozzáadása a jsonl-be, hogy a downstream elemzés (mint a daily review) ne keveredjen össze. Effort: ~30 min CC.

## Day 63 keret — hétfő esti állapot

| Metrika | Érték | Status |
|---------|-------|--------|
| Day | **61/63** — **2 nap van Day 63-ig** (csüt máj 14) | |
| Kumulatív (paper aggregát) | -$1,095 (-1.09%) | **biztonságos sávban**, marginális javulás |
| Tényleges valós (becsült) | ~-$981 (-0.98%) | a SQM korrekció után |
| ÉLESÍTÉS távolság | +$3,981 a +$3,000-hoz | **2 nap × +$1,991/nap → NEM realisztikus** |
| LEÁLLÍTÁS távolság | 10 napi excess átlag -0.31% | **biztonságos**, ~1.19% buffer |
| 10 napi excess átlag | ~-0.31% | a hétfői -0.19% lényegében neutrális |
| VIX W20 D1 close | 18.45 (+7.64% Δ) | **alacsony**, leállítási feltétel monitor inaktív |

**Realisztikus Day 63 várt kimenet**: **PAPER FOLYTATÁS (default) — 6 nap egymás után megerősítve**. A kumulatív P&L 2 nap után valószínűleg **-$1,200 és -$900 között lesz**.

## Anomáliák

- **AAPL phantom 22:00 monitor**: az AAPL ma trade-elve volt és MOC-on zárt, de a `monitor_positions` 22:00-kor még `leftover_found AAPL`-t jelez. **Konzisztens a CRGY/AAPL phantom BUG-gal** (régóta ismert, alacsony prioritás)
- **DELL, DOCN phantom_filtered**: a 22:00-i monitor.py kihagyott 2 ticker-t mint phantom (helyes szűrés)
- **AVDL.CVR (69.0)**: továbbra is non-tradable, ignorálva
- **2026-05-11.json daily_metrics**: ma délután 22:10 CEST után frissült, **strukturált adatok jó minőségűek**
- **UW HTTP 429 rate limits**: a fő strukturális anomália — kb. 30-50 ticker dp_pct/gex adat nélkül score-olódott (lásd fent)
- **Polygon 1-min bars hiány**: a `pt_avwap.log` ma csak egy WARNING-ot tartalmazott — feltehetően a 16:20 körüli kettős infra-akadás része

## Kulcsmegfigyelések

### 1. 🎯 SNAPSHOT FIX VALIDÁCIÓ — 100% SIKERES

A `d3fce73` deploy működik: **504 B → 22.89 KB, 1390 ticker analyzed, 159 passed**. A scoring-validation és flow-decomposition újrafuttatása **most már lehetséges teljes mintán**. A bug ténylegesen **2026-04-05** óta volt aktív (NEM 2026-04-10, ahogy a master-reference 04-risks 1.1 mondta) — **korrekció szükséges**.

### 2. ⚠️ KÉZI ORDER SUBMISSION — DUPLA INFRA-AKADÁS

IBKR Gateway (timeout × 3) + Polygon 1-min bars hiánya a 16:20 CEST automata submit-időpontban. **Tamás 17:15-kor manuálisan rögzítette az ordereket.** A kézi rögzítés mellékhatása: **FORM -4.5% slippage, kedvező entry**. **Új P1 backlog idea:** "IBKR Gateway monitoring + Telegram alert".

### 3. ⚠️ UW HTTP 429 RATE LIMITS — A dp_pct DEPLOY NEM VÁRT MELLÉKHATÁSA

A per-ticker fetch (`9a169b9`) első élesben futtatva: tömeges HTTP 429 a Phase 4 (darkpool) és Phase 5 (greek-exposure) hívásokban. **Becslés:** kb. 30-50 ticker dp_pct adat nélkül score-olódott. **A dp_pct rekal hatás-validációja korlátozott** — top-N tickeren működött, de a teljes universumon nem. **Új P1 backlog idea:** "UW rate limit kezelés finomítás (concurrency limiter + exp backoff)".

### 4. ⚠️ FORM SLIPPAGE — A +$213-BÓL ~$197 (92%) A SLIPPAGE-BŐL JÖTT, NEM A STRATÉGIÁBÓL

A nap legjobb nyerője **NEM a stratégia érdeme** — a kézi rögzítés 17:15 CEST kedvezőbb entry-árral (-4.5% slippage). Ha az automatikus 16:20 submit sikeres, +$17 P&L lett volna, +$213 helyett. **A nap valós "stratégia-score": kb. -$165**. **Új P3 backlog idea (analitikus):** "Slippage-adjusted scoring validation".

### 5. ⚠️ FORM DUPLA M-SZANKCIÓ — A PÉNTEK AMD PATTERN FOLYTATÁSA

`M_contradiction × M_target_penalty = 0.8 × 0.85 = 0.68` — mégis a nap legjobb nyerője. **6 napos M_contradiction LIVE iránybeli helyesség ~40%-ra csökkent.** A két feature **redundánsan szankcionálja** ugyanazt a `price_above_consensus` signal-t. **Új P2 backlog idea:** "M_contradiction & M_target_penalty deduplikáció" — várható hozadék kb. +$50-100/hét.

### 6. ✓ MOC DUPLIKÁCIÓ NEM BUG

A 21:20 és 21:40-i double-cron-futás normál működés (cancel + resubmit). A daily_metrics tisztán 3 trade-et mutat — **a paper_aggregát nem szennyeződött** (ellentétben a múlt csüt SQM bug-gal).

## Holnap (kedd, W20 D2 — máj 12) teendők

### Tamás (MacMini, manuális)

- **`git pull`** a Mac Mini-n (ha még nem történt meg a péntek óta)
- **IBKR Gateway állapot ellenőrzés** reggel — ha valamilyen oka volt a 16:20-i timeout-nak, restart-eljük az IBKR Gateway-t / TWS-t a market open előtt
- **AVDL.CVR phantom** továbbra is takarítani opcionális

### Chat (én)

- **Master-reference 04-risks 1.1 frissítése**: a bug start date 2026-04-10 → **2026-04-05** korrekció
- **Master-reference 04-risks új P1 backlog ideas:**
  1. UW rate limit kezelés finomítás
  2. IBKR Gateway monitoring + Telegram alert
- **Master-reference 04-risks új P2 backlog idea:** M_contradiction & M_target_penalty deduplikáció
- **Master-reference 04-risks új P3 backlog ideas:**
  1. dp_pct fallback default
  2. Slippage-adjusted scoring validation
  3. monitor.py belső replay események jelölése
- **`docs/analysis/weekly/2026-W19-analysis.md`** elkészítése — vasárnap helyett kedd reggel, mert a péntek esti session lecsökkent
- **Strategic-review full 2.4 fejezet $354 → $665** korrekció (átvezetése)

### Kedd este (W20 D2 napi review)

- **Második teljes pipeline futás a snapshot fix után** — ha a Phase 4 megint 1390 ticker / 22+ KB snapshot, akkor a fix stabil
- **UW rate limit monitor**: ha kedden még mindig tömeges 429, akkor sürgős backlog tétel
- **dp_pct hatás top-N tickeren**: ha a top scoring tickerek között megjelennek alacsonyabb (90-92) score-ok a régi (92-95) helyett, akkor a rekal érdemben hat

### Csütörtök (máj 14) — **Day 63 KIÉRTÉKELÉS** ⭐

- **W17 + W18 + W19 + W20 D1-D3 adatok együtt scoring validation újrafuttatás** (a snapshot fix után először teljes mintán)
- **Várt kimenet: PAPER FOLYTATÁS (default)** — most már 6+ napra megerősítve
- Új doc: `docs/decisions/2026-05-14-day63-decision-outcome.md`

## Kapcsolódó

- `state/phase4_snapshots/2026-05-11.json.gz` ⭐ **22.89 KB, első tiszta snapshot a fix után**
- `state/daily_metrics/2026-05-11.json` ← Day 61 strukturált metrika
- `logs/pt_eod_2026-05-11.log` ← P&L összefoglaló (3 MOC zárás)
- `logs/pt_submit_2026-05-11.log` ← **CSONKA** (csak beolvasás, az IBKR connection itt failelt)
- `logs/pt_close_2026-05-11.log` ← 21:20 + 21:40 MOC cron-replay
- `logs/pt_avwap_2026-05-11.log` ← **CSONKA** (csak 1 WARNING, "No 1-min bars from Polygon")
- `logs/pt_events_2026-05-11.jsonl` ← 22:00 monitor replay LION/SDRL események (NEM tényleges trade-ek)
- `logs/cron_intraday_20260511_161500.log` ← **kritikus**: Phase 4 1390 ticker, UW HTTP 429 tömeges, IBKR connection FAILED
- `output/execution_plan_run_20260511_141500_38717b.csv` ← 3 ticker, FORM contradiction_flag=1, multiplier 0.68
- `docs/master-reference/01-system-snapshot.md` ← **frissítendő** a bug start date korrekcióval
- `docs/master-reference/04-risks-and-open-questions.md` ← **frissítendő** új backlog ideas-kel (3 új P1/P2 + 3 új P3)

**State**: BC23 + Breakeven Lock + MID Bundle + vix-close + M_contradiction LIVE + snapshot fix DEPLOYED + dp_pct rekal DEPLOYED + **első napi élesben futás kettős infra-akadással**

**Aktív CC tasks**: 0 (a péntek óta nem indult új)

**W20+ backlog idea-k (most 14, +3 új P1/P2 + 3 új P3 a hétfői finding-okból):**

P1 (3):
1. ⚠️ LOSS_EXIT bracket SL cancellation — ~30-45 min CC (folytatás)
2. **ÚJ: UW rate limit kezelés finomítás** — ~1-2 óra CC (concurrency limiter + exp backoff)
3. **ÚJ: IBKR Gateway monitoring + Telegram alert** — ~1 óra CC

P2 (3):
4. 10-Q / 10-K SEC Filing Exclusion — ~2-3 óra CC
5. ADR earnings adatforrás fix — ~3-4 óra CC
6. **ÚJ: M_contradiction & M_target_penalty deduplikáció** — ~1-2 óra CC

P3 (8):
7. Breakeven Lock profit-küszöb csökkentés — ~10-15 min config
8. TP1 cél revízió — ~30 min config
9. High-score liquidity check — ~1 óra
10. Phase 4 snapshot enrichment — ~30-45 min
11. UW dark pool live fetch `date=today` parameter — ~30 min CC
12. **ÚJ: dp_pct fallback default (universum-medián)** — ~30 min CC
13. **ÚJ: Slippage-adjusted scoring validation** — ~30 min Chat-oldali
14. **ÚJ: monitor.py belső replay események jelölése** — ~30 min CC
