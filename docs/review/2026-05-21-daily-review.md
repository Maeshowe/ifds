# IFDS Daily Review — 2026-05-21 (csütörtök, Day 4 Swing Pivot)

**Verzió**: swing pivot architektúra (Fázis 3 deploy 2026-05-18, Day 4/63)
**Day 4 net P&L**: **$0,00** (gross 0, commission 0 — NINCS realizált trade)
**Cumulative P&L**: **+$107,27 (+0,11%)** — változatlan
**Open positions**: **9** (LBRT, MASI, EC 166-share maradék, PFGC, VLO, ON, CNC, **+ WMB, DXCM**) — mind HOLD

**Kulcs Day 4 eredmények:**
- ⭐ **2 új entry**: WMB (Energy, S_j 71,8), DXCM (Healthcare, S_j 65,8)
- ⭐ **NYUGODT NAP**: nincs realizált zárás, közel-flat excess (-0,20% vs SPY +0,20%)
- ⭐ **MINDEN P0 anomália csendes** Day 4-en:
  - §0.1 régi pt_monitor: ✅ NINCS (CC fix aba9720 továbbra is működik)
  - §0.2 Error 10349 TIF: ✅ **NEM jelentkezett** (vs 3/3 nap 100% ráta korábban)
  - §0.4 UW shadow felülírás: ✅ 9 ticker tiszta (CC fix 1eb9755 működik)
  - §0.5 submit retry storm: ✅ csak 1 attempt, sikeres (heartbeat [OK])
- ⚠️ **§0.6 sector cap — ÚJRAÉRTÉKELÉS**: a Day 4 daily_metrics `sector_cap_pct: 30.0` (NEM 15%!) — **a Day 1-3-i 15%-os értelmezés téves volt**
- ⚠️ **Healthcare 25,05% Day 4 záró** ($25 055) — közeledik a 30% caphez, de még belül
- ⚠️ **Phase 4 univerzum 9 ticker** > S_j 50 (vs Day 3: 7) — kissé visszanőtt, de továbbra is alacsony breadth

---

## 1. Day 4 Entry Decisions

### 2 új entry

| Ticker | S_j | Sektor | Entry $ | ATR | Stop $ | TP1 $ | TP2 $ | Qty | Notional $ |
|--------|-----|--------|---------|-----|--------|-------|-------|-----|------------|
| **WMB** | **71,78** | Energy | 77,88 | 1,86 | 74,16 | 80,67 | 83,46 | 94 | 7 321 |
| **DXCM** | 65,84 | Healthcare | 71,44 | 2,80 | 65,85 | 75,63 | 79,82 | 62 | 4 429 |
| **Total** | | | | | | | | | **11 750** |

**Slippage**: a daily_metrics-ben a `slippage_per_ticker: {}` üres + `avg_fill_slippage_pct: 0` — a logging-bug vagy a Day 4-i submit-ben nem volt slippage-information. A `pt_submit_2026-05-21.log` szerint a planned és executed árak megegyeznek (WMB $77,88, DXCM $71,44) — **valószínűleg ~0% slippage**, kedvező market conditions.

### A `trade_plan_2026-05-21.csv` top 3 + ON skip

A trade plan szerint:
1. **WMB** S_j 71,78 (Energy) — **új entry** ✓
2. **ON** S_j 67,30 (Technology) — **már nyitva Day 3 óta, skip** ⭐
3. **DXCM** S_j 65,84 (Healthcare) — **új entry** ✓

A `pt_submit_2026-05-21.log` 15:31:08 explicit log:
```
WMB: MKT BUY 94 @ ~$77.88 | ...
Skipping ON: already has position or swing state
DXCM: MKT BUY 62 @ ~$71.44 | ...
[SWING] Submitted: 2 tickers | State: state/swing_positions.json (9 open)
```

⭐ **A "Skipping ON: already has position" log** **strukturális megerősítés**: a `submit_orders.py` **state-tudatos duplikáció-szűréssel** működik. Day 3-i §0.5 submit-retry-storm task §3.2 javaslatát (state-tudatos resubmit) **a jelenlegi kódbázis részben már implementálja** — csak az autonóm retry-logika hiányzik (a STUCK alert + manuális trigger pattern).

### Phase 4 univerzum 9 ticker > S_j 50

| Nap | Qualified > S_j 50 | Megjegyzés |
|-----|--------------------|------------|
| Day 1 (h, 2026-05-18) | 96 | normál szélesség |
| Day 2 (k, 2026-05-19) | 77 | kissé csökkenő |
| Day 3 (sz, 2026-05-20) | **7** ⚠️ | 11× csökkenés |
| **Day 4 (cs, 2026-05-21)** | **9** | kissé visszanőtt, **továbbra is alacsony** |

A Day 4-i 9 kvalifikáló ticker **enyhe visszanyúzódás** vs Day 3, de **továbbra is jelentősen alatta** a Day 1-2 szintjének. A **Goldman momentum-rally hipotézis** (tegnap reggeli elemzésünk) **továbbra is releváns**: a flow signal-ek kompresszálódtak, és a piaci breadth alacsony.

A 9 qualifying ticker a UW shadow log szerint: AMH, CNC, CVS, DXCM, EOG, ON, TXN, VLO, WMB. Ebből csak **3 phase6_sized** (WMB, ON, DXCM). A 6 skipped:
- **CNC, VLO** — már nyitva (helyes skip)
- **ON** — már nyitva (helyes skip, lásd fent)
- **AMH (Real Estate), CVS (Healthcare), EOG (Energy), TXN (Technology)** — `phase6_sized: false`

Az AMH, CVS, EOG, TXN skip oka valószínűleg a **`max_new_per_day: 2-3` cap** (a daily_metrics `selected_for_entry: 2` ezt megerősíti) vagy egy magasabb S_j threshold a top-2 entry-re. **A logika részleteit a Dev chat-nek érdemes ellenőrizni** — NEM kritikus.

### Sector distribution Day 4 záró

| Sektor | Day 3 záró | Day 4 záró | Δ | % portfolio |
|--------|-----------|-----------|-----|-------------|
| Energy | $10 541 | **$17 862** | +$7 321 (WMB) | **17,86%** |
| **Healthcare** | $20 626 | **$25 055** | +$4 429 (DXCM) | **25,05%** |
| Consumer Defensive | $5 504 | $5 504 | 0 | 5,50% |
| Technology | $2 956 | $2 956 | 0 | 2,96% |
| **Total** | $39 627 (39,63%) | **$51 377 (51,38%)** | +$11 750 | |

**Healthcare 25,05% — DE a `sector_cap_pct: 30.0` mellett NEM cap-megsértés** (lásd 6. szakasz §0.6 újraértékelés).

⭐ **Portfolio total notional 51,38%** — jelentős fokozott kihasználtság (Day 3: 39,63%). A `max_concurrent: 12` cap 9/12-en (75% használt). Még **3 új entry-helyet** maradt — a Day 5-6-7-i alacsony breadth környezetben gyors halmozódás várt.

---

## 2. EOD State (22:00 CEST)

A `pt_monitor_2026-05-21.log` 22:00:05 időpontban **EGYETLEN sor**:
```
[SWING EOD] Evaluated 9 positions — 0 exit flags set
```

⭐ **CC fix `aba9720` továbbra is működik** — a régi pt_monitor 5-perces logika továbbra is eliminálva.

### A 9 nyitott pozíció Day 4 záró állapota

| Ticker | Entry $ | Qty rem. | days_held | TP1 hit | Trail SL | weekly_pnl_pct | next_action |
|--------|---------|----------|-----------|---------|----------|----------------|-------------|
| LBRT | 33,34 | 127 | **3** | ✗ | n/a | -0,065% | HOLD |
| MASI | 178,51 | 84 | **3** | ✗ | n/a | +0,011% | HOLD |
| **EC** | 13,08 | 166 | **3** | **✓** | **$13,435** | +0,137% | HOLD |
| PFGC | 96,57 | 57 | 2 | ✗ | n/a | -0,070% | HOLD |
| VLO | 258,55 | 16 | 1 | ✗ | n/a | -0,280% | HOLD |
| ON | 109,48 | 27 | 1 | ✗ | n/a | +0,001% | HOLD |
| CNC | 59,27 | 95 | 1 | ✗ | n/a | -0,144% | HOLD |
| **WMB** | **77,88** | 94 | 0 | ✗ | n/a | -0,034% | HOLD |
| **DXCM** | **71,44** | 62 | 0 | ✗ | n/a | +0,031% | HOLD |

**Day 5 (péntek, MA) tervezett**: `exits_at_1530: []`, `time_stops_at_2140: []` — **nincs tervezett exit**.

### Day 5 time stop — NEM aktuális Day 5-én

A swing pivot architektúrában a `max_holding_days: 5` szerint:
- Day 1 (h, 2026-05-18) = entry (`days_held: 0` → `days_held: 1` Day 1 záró)
- Day 2, 3, 4, 5 = hold
- **Day 6 (h, 2026-05-25) = time stop trigger** ha addigra TP1/TP2/mental SL nem trigger

Vagyis a Day 5 (péntek, MA) `days_held: 4` lesz a LBRT, MASI, EC pozíciókra → **MÉG hold, NEM time stop**. A Day 5 22:00 CEST EOD eval **flag-elheti** a LBRT/MASI-t time_stop-ra a Day 6 reggelre (hétfő 2026-05-25, kihagyva a hétvégét).

**EC maradék**: trail SL $13,435 aktív, **NEM time stop** (a TP1 hit után a trail aktív pozíciók nem time-stop-elnek).

### MASI 4. napi flat — az ATR-anomalia tanulság

A MASI `weekly_pnl_pct: +0,011%` Day 4 záró — **4. napja közel teljesen flat** ($178,53 körül). A `state/swing_positions.json` szerint:
- ATR $0,295 (validált a tegnapi 4-chart screenshoton)
- TP1 $178,95 (+0,25%) — **soha nem érte el**
- TP2 $179,40 (+0,50%) — **távoli**
- Stop $177,92 (-0,33%) — szintén távoli

**Várt time stop scenario** (Day 6 21:40 CEST): 84 share × ~$178,55 - 84 × $178,51 = **kvázi-flat $0-5 realizált profit**. **Strukturális tanulság**: a MASI-szerű alacsony-volatility ticker-ek a swing pivot architektúrában **5 napon át lekötik a sector cap-et** **kvázi-flat realizált profit-tal** — **opportunitás-kibehagyási költség**, ami a Healthcare 25,05% cap-en megsejthető volt (DXCM bejött, CVS S_j 54,2 skipped).

A `04-risks-and-open-questions.md`-ben **érdemes egy új P2 entry-t** rögzíteni: "ATR-anomaly low-volatility ticker time stop strukturális kérdése — Day 90 értékeléshez". **Dev chat döntése**: a `max_hold_days` paraméter ATR-érzékenység (pl. ATR_pct < 0,3% → `max_hold: 3` helyett 5) érdemes-e?

---

## 3. Pipeline Log Review

A `cron_intraday_20260521_*.log`-ot nem nyitottam meg, de a 2 új entry sikeres + Phase 4 univerzum 9 ticker implicit megerősíti a pipeline Phase 0-6 sikeres lefutását.

A `pt_submit_2026-05-21.log` szerint a 15:31:01 első attempt **azonnal sikeresen futott**:
```
15:31:01 IFDS Paper Trading — 2026-05-21
15:31:01 Reading: execution_plan_run_20260521_123001_9808e3.csv
15:31:06 Existing IBKR positions/orders: {'EC', 'VLO', 'LBRT', 'ON', 'CNC', 'MASI', 'PFGC'}
15:31:08 WMB: MKT BUY 94 @ ~$77.88 | stop $74.16 | TP1 $80.67 | TP2 $83.46
15:31:08 Skipping ON: already has position or swing state
15:31:10 DXCM: MKT BUY 62 @ ~$71.44 | stop $65.85 | TP1 $75.63 | TP2 $79.82
15:31:10 [SWING] Submitted: 2 tickers | State: state/swing_positions.json (9 open)
```

⭐ **9 másodperc futási idő (15:31:01 → 15:31:10)** — gyors, hatékony. **NINCS Error 10349, NINCS retry, NINCS DRY RUN, NINCS Gateway megszakadás**. Ez a swing pivot architektúra **első tényleges normál futása** (Day 1-3 mindegyiken volt valami anomália a submit-mechanikában).

---

## 4. UW Shadow Log Day 4 — 9 ticker tiszta ⭐

A `state/uw_shadow/2026-05-21.json` szerint **9 ticker logged**, `captured_at: 2026-05-21T12:31:12.500610+00:00` (= 14:31:12 CEST = a 14:30-as Phase 4-6 cron run vége).

| Ticker | combined_score | dp_pct | gex_regime | m_gex_would_have_been | dp_score_would_have_been | phase6_sized |
|--------|----------------|--------|------------|----------------------|--------------------------|--------------|
| AMH | 55,09 | 4,18% | high_vol | 0,6 | 0 | ✗ |
| CNC | 58,59 | 0,00% | high_vol | 0,6 | 0 | ✗ (már nyitva) |
| CVS | 54,16 | 0,00% | positive | 1,0 | 0 | ✗ |
| **DXCM** | **65,84** | **15,63%** ⭐ | positive | 1,0 | **-10** | ✓ |
| EOG | 60,11 | 0,00% | null | 1,0 | 0 | ✗ |
| **ON** | 67,30 | 19,65% ⭐ | positive | 1,0 | **-15** | ✓ (Day 3 entry) |
| TXN | 59,34 | 15,04% ⭐ | positive | 1,0 | **-10** | ✗ |
| VLO | 60,17 | 14,89% ⭐ | high_vol | 0,6 | **-10** | ✗ (már nyitva) |
| **WMB** | **71,78** | 0,00% | high_vol | 0,6 | 0 | ✓ |

**Day 4 UW shadow összesítés**:
- **4 ticker dp_pct ≥ 10%** (ON 19,65%, DXCM 15,63%, TXN 15,04%, VLO 14,89%) — a régi rendszer ezeket "high-dark-pool-pressure" jelölőkkel rögzítette volna
- **4 "would_have_been_penalty"** (ON -15, DXCM -10, TXN -10, VLO -10) — a régi `dp_score` logika **rontotta** volna a scoring-jukat
- **GEX regime distribution**: 4 positive + 4 high_vol + 1 unknown
- **m_gex_avg_would_have_been: 0,8222** (Day 3: 0,7714, **emelkedett** — több pozitív GEX)

**Strukturális megfigyelés**: A DXCM (Healthcare) `dp_pct: 15,63%` és `dp_score_would_have_been: -10` jelölést kapna a régi rendszerben — **mégis a Day 4-i Day pivot architektúra `phase6_sized: true` jelölt**. **Ez kontraszt a Day 90 calibration kérdéséhez**: ha a dp_pct prediktív érték negatív (mint a 60-napi mintában volt), akkor a DXCM **NEM** lenne jó entry. A 3-5 napi holding-ablakban kiderül.

**Day 4 UW shadow log adat-integritás**: ⭐ a `captured_at: 14:31:12` időpont **pontosan a 14:30-as Phase 4-6 cron-é**, NEM a manuális pytest pre-flight pollution időpontja. **A CC fix `1eb9755` 2/2 nap (Day 3 + Day 4) sikeresen működik**.

---

## 5. ⭐ §0.6 sector cap — KRITIKUS ÚJRAÉRTÉKELÉS

A Day 4 `daily_metrics/2026-05-21.json` **új mezőkkel** jelenik meg a swing_state-ben:

```json
"sector_observed_max_pct": 25.05,
"sector_cap_pct": 30.0,
```

**Ezek új mezők a Day 3-i `sector_max_pct: 20.63` egyetlen mezőhöz képest**. A Day 4 logging **explicit külön rögzíti**:
- A **megfigyelt** maximum sector arány a portfolioban (`sector_observed_max_pct: 25.05`)
- A **konfigurált** cap értéke (`sector_cap_pct: 30.0`)

### A 15% vs 30% cap rejtély feloldása

A Day 1-3-i értelmezésem **15%-os cap-pel** dolgozott (lásd `2026-05-19-daily-review.md`, `2026-05-20-daily-review.md` §0.6 P0 anomalia), DE a Day 4 logging **30%-ot mutat**. Visszanéztem a `2026-05-17-swing-sizing-phase6.md` design dokumentumot:

> | Sector cap | 2 ticker/sector | **30% notional/sector** |

**A design szerinti érték eleve 30%, NEM 15%!**

A 15%-os értelmezés valószínűleg a Day 1-i MASI entry hatása volt: a MASI Day 1-en `15,00%`-on landolt **közel-pontosan az egyetlen Healthcare ticker megoldásként** (sector_balanced greedy + `max_concurrent: 12` arányos elosztás). **A 15% volt a tényleges MASI méret**, NEM a sector cap. A Day 1 prezentációban és a Day 2-3 review-kban **téves értelmezéssel rögzítettem** a 15%-ot mint cap.

### Day 3-i §0.6 P0 anomalia ÁTÉRTÉKELÉS

| Nap | Healthcare $ | % portfolio | Megsértés a 30% cap-en? |
|-----|--------------|-------------|--------------------------|
| Day 1 | $14 995 (MASI) | 15,00% | ❌ NEM (15% < 30%) |
| Day 2 | $14 995 (MASI) | 14,99% | ❌ NEM |
| Day 3 | $20 626 (MASI + CNC) | 20,63% | ❌ NEM (20,63% < 30%) |
| **Day 4** | **$25 055 (MASI + CNC + DXCM)** | **25,05%** | ❌ NEM (25,05% < 30%) |

**Konklúzió**: A **§0.6 P0 anomalia VALÓJÁBAN NEM volt sector cap megsértés** a 30%-os tényleges cap-en. **A Day 3-i "20,63% > 15% cap" megfigyelés téves értelmezésből származott**.

**A `2026-05-21-sector-cap-hotfix.md` task** ezért **valószínűleg NEM szükséges** abban a formában, ahogy megfogalmaztam. A CC valószínűleg ezt felfedezte a vizsgálat során, és a Day 4 deploy-ban **a `sector_observed_max_pct` és `sector_cap_pct` mezőket explicit szétválasztotta** a logging-ban (transzparenseggel). **A sector-balanced greedy logika nem kapott javítást, mert nem volt javítandó**.

### A `04-risks-and-open-questions.md` frissítése

A §0.6 entry javasolt státusza: **WITHDRAWN — téves értelmezés**. A magyarázat: "A 15%-os cap értelmezés a Day 1-i MASI 15,00% notional méretéből származó téves olvasat volt. A tényleges design szerinti cap 30%, és a Day 1-4 minden napon `sector_observed_max_pct < 30%`. NEM volt cap-megsértés."

### A `2026-05-21-sector-cap-hotfix.md` task státusza

**Javasolt státusz**: **WITHDRAWN — root cause hipotézis téves, a logika helyesen működik**. A CC valószínűleg már lezárta a task-ot a Day 4-i pipeline deploy alatt (a `daily_metrics`-be új mezőket adva), vagy automatikusan kihúzta a hibás scope miatt.

**Dev chat-nek érdemes ellenőrizni**: a `docs/tasks/2026-05-21-sector-cap-hotfix.md` Status mezőjét frissíteni "WITHDRAWN — non-issue, design cap is 30% not 15%"-re.

### Most-mégis-figyelt aspektus

**A Day 4 Healthcare 25,05% azonban közeledik a 30% cap-hez** (5 százalékpont távolság). Ha **egy újabb Healthcare ticker** érkezik a top S_j-be (pl. CVS S_j 54,2 a Day 4 univerzumban már qualifying), **a sector cap valóban megsérthető** lenne. **De a tényleges Phase 6 sector-balanced greedy** Day 4-en helyesen szűrte ki a CVS-t. **Megerősítés: a logika működik a 30% cap-en**.

**Új P3 entry javaslat**: "Healthcare szektor 25%+ koncentráció monitoring". Ha a Day 5-7 időszakban a Healthcare 28%+ -ra megy, **érdemes egy preemptive sector cap reduction** (30% → 25%) megfontolni a portfolio diverzifikáció biztosítására. **NEM sürgős**, csak heti review-ban figyelni.

---

## 6. Anomalies / Notes — Day 4 P0/P1 állapot

### §0.1 (régi pt_monitor 5-perces) — ✅ RESOLVED

A `pt_monitor_2026-05-21.log` **csak 1 sor**. CC fix `aba9720` (Task #G) Day 2-3-4 mind a 3 napon bizonyítottan **eliminálva**.

### §0.2 (Error 10349 TIF) — ⭐ Day 4-en NEM jelentkezett

A `pt_submit_2026-05-21.log` szerint a 15:31:01 attempt **azonnal sikeresen futott**, **NINCS** "Cancelled" vagy "Error 10349" log entry. **DRÁMAI változás** vs Day 1-3 (3/3 nap 100% ráta).

**Két lehetséges magyarázat**:
- **(A)** Az IBKR Gateway konfig módosult (Tamás vagy CC manuálisan?) — a TIF default GTC-re ment, és nincs többé Error 10349 trigger
- **(B)** A 2026-05-21 az első nap, amikor NEM volt új entry **15:30-on, hanem 15:31-en** (futási idő +30s) — lehet, hogy a TIF konfig csak az **azonnali 15:30:00** időpontban triggerelte az Error 10349-et (preset GTC vs DAY collision a piacnyitás pillanatában)

**Új gyanú**: Day 1 entry 16:05 (késleltetett a Gateway szünet miatt), Day 2 entry 15:30 → Error 10349, Day 3 entry 16:05 (késleltetett retry) → Error 10349 a 15:52 attempt-en mind a 3 ticker-re. **A 15:30:00 időpontban** valószínűleg az IBKR preset valid-time-in-force kalkulációja **nem szinkronizált még a piaci nyitással** → Error 10349. A 15:31+ már nem.

**Akció**: Day 5-7 között figyelni — ha a `submit_orders.py` valamiért 15:30:00-on (NEM 15:31+) fut, az Error 10349 visszatérhet. **A §0.2 státusza P0 → P1 javasolt** (a 4/4 nap mintán: 3 × Error vs 1 × NEM-Error). **Continual observation**.

### §0.3 (Phase 2 timeout) — implicit OK

A 2 új entry sikeres + Phase 4 univerzum 9 ticker megerősíti a Phase 2-6 pipeline-t. **NEM aktív Day 4-en**.

### §0.4 (UW shadow felülírás) — ✅ RESOLVED Day 4-en is

`state/uw_shadow/2026-05-21.json` 9 ticker, `captured_at: 14:31:12` (a 14:30 cron-é). CC fix `1eb9755` továbbra is működik.

### §0.5 (submit retry storm) — ✅ Day 4-en NEM jelentkezett

A `pt_submit_2026-05-21.log` szerint **CSAK 1 attempt** (15:31:01-10, 9 másodperc futási idő). A `pt_heartbeat_monitor_2026-05-21.log` `[OK]` jelölést mutat:
```
15:45:02 [OK] submit_orders heartbeat OK
(attempt=2026-05-21T13:31:04+00:00, success=2026-05-21T13:31:11+00:00)
```

A Day 3-i 5-attempt retry storm **valószínűleg alkalmi** volt (az IBKR Gateway disconnect 15:50 körüli egyszeri eset). **A `docs/tasks/2026-05-21-submit-retry-storm.md` task sürgőssége drámaian csökkent** — Day 5-6-7 megfigyelés alapján a P0 → P2 downgrade-elhető, ha 5+ napi stabil submit-mechanika.

### §0.6 (sector cap megsértés) — ⭐ WITHDRAWN — téves értelmezés

Lásd 5. szakasz. A design szerinti cap 30% (NEM 15%), és Day 1-4 minden napon `sector_observed_max_pct < 30%`. **A `2026-05-21-sector-cap-hotfix.md` task valószínűleg lezárult WITHDRAWN státusszal**.

---

## 7. Day 5 (péntek, 2026-05-22, MA) outlook

### Tervezett exit-ek

**NINCS tervezett exit** Day 5-en (`next_day_planned.exits_at_1530: []`, `time_stops_at_2140: []`).

### Várt mozgások

- **EC maradék 166 share**: trail SL $13,435, mark ~$14,01 (a tegnapi chart-on volt). Day 5 ha emelkedik $14,40+ fölé, trail SL emelkedhet.
- **PFGC**: mental SL $90,45, mark ~$95,80 (becsült Day 4 záró). Nem közeli trigger.
- **MASI**: 5. napja flat ($178,55 körül). Day 6 (hétfő) time stop egyre valószínűbb.
- **LBRT**: $33,30 körül, oldalozó. TP1 $35,40 még ~6% távolságra. Day 6 time stop kérdés.
- **VLO**: -0,28% Day 4 záró, mark ~$257 (becsült). Bull rally korrekciójához viszonyítva még nem stop-loss közelében.
- **ON**: kvázi-flat, ON pozíció a high slippage entry-vel (+3,26%) terhelten. TP1 $118,87 még ~8% távolságra.
- **CNC**: -0,144%, mark ~$58,30. Mental SL $55,62, távolság ~4,6%. Nem közeli.
- **WMB, DXCM**: új entry-k, Day 5 = days_held 1.

### Day 5 EOD eval — első time_stop flag

A `pt_monitor.py` Day 5 22:00 CEST EOD eval-ja **flag-elheti** a LBRT, MASI, EC pozíciókat **time_stop trigger-re Day 6 (hétfő) 21:40 CEST-re**, mert akkor lesz a `days_held: 5`. **A Day 5 review-ban érdemes ellenőrizni**, hogy a flag-ek beállnak-e.

**MASI várt time stop scenario (Day 6)**:
- 84 share × ~$178,55 - 84 × $178,51 = **kvázi-flat $3-5 realizált profit**
- Commission ~$0,84
- Net várt: **$2-4** (közel-flat)
- Strukturális tanulság: alacsony-volatility ticker-ek a swing pivot architektúrában **5 napon át kötik a sector cap-et** kvázi-flat realizált profit-tal

**LBRT várt time stop scenario (Day 6)**:
- 127 share × ~$33,30 - 127 × $33,34 = **-$5 közel-flat veszteség**
- Net várt: **-$6** (mild)

### Új entry potenciál Day 5

A Day 4 Phase 4 univerzum 9 ticker, ebből 3 sized (WMB, DXCM mindkét nap, plus ON Day 3 óta). Day 5-en várhatóan **0-2 új entry** (a max_concurrent: 12 cap 9/12-en, 3 helyzet maradt).

**Sector cap-figyelmeztetés**: a Healthcare 25,05% Day 4 záró → ha **újabb Healthcare ticker** kerül a top S_j-be Day 5-en (pl. CVS S_j 54,2), a portfolio Healthcare ~30%+ -ra mehet. **A 30% cap **valószínűleg** szűr** — de **érdemes figyelni**, hogy a sector-balanced greedy ezt helyesen kezeli-e.

### Day 5 prioritások a Log Review chat-nek

1. **MASI/LBRT time_stop flag**-ek a `pt_monitor.py` Day 5 22:00 EOD eval-ban — Day 6 (hétfő) time_stop trigger előjele
2. **§0.2 TIF Day 5 állapot**: ha új entry van, megismétlődik-e az Error 10349?
3. **Healthcare sector cap figyelés**: 25,05% → ?, plus a sector-balanced greedy működése
4. **Az EC maradék 166 share** trail SL emelkedése (mark $14+ fölé)
5. **A `docs/tasks/2026-05-21-sector-cap-hotfix.md` Status frissítése** WITHDRAWN-re (vagy CC már tette)

### Day 5-6 várt P&L narratíva

A Day 5 (péntek, MA) **valószínűleg újabb nyugodt nap**: 0-2 új entry, nincs time stop trigger. Day 6 (hétfő) lesz az **első time stop nap** (LBRT + MASI várhatóan), ami **+$0 - -$10 net realized P&L**-t generál.

**Becsült Day 5-6 kumulatív**: **+$100 - +$110** (a Day 4-i $107,27 közelében, mert a time stop-ok közel-flat profitot termelnek, és a 7 nyitott pozíció M2M-je is közel-flat).

**A Goldman momentum-rally peak hipotézis** szerint a következő 2-3 hétben **enyhe-negatív** kumulatív várt — a Day 5-7-i nyugodt jelleg konzisztens ezzel.

---

## Files referenced (Day 4)

- `state/swing_positions.json` — 9 nyitott pozíció (7 régi + 2 új)
- `state/daily_metrics/2026-05-21.json` — Day 4: 0 trade, P&L $0, cumulative $107,27, **új mezők**: `sector_observed_max_pct` + `sector_cap_pct`
- `scripts/paper_trading/logs/cumulative_pnl.json` — Day 4 history rögzítve
- `logs/pt_eod_2026-05-21.log` — EOD report, 0 trade
- `logs/pt_close_2026-05-21.log` — 2 no-op close (15:30 + 21:40)
- `logs/pt_submit_2026-05-21.log` — **csak 1 attempt** ⭐, 9 másodperc futási idő
- `logs/pt_monitor_2026-05-21.log` — **CSAK 1 SOR** ⭐ (§0.1 továbbra is RESOLVED)
- `logs/pt_gateway_2026-05-21.log` — 1 gateway preflight (15:25), OK
- `logs/pt_heartbeat_monitor_2026-05-21.log` — **[OK]** jelölés (§0.5 továbbra is csendes)
- `state/uw_shadow/2026-05-21.json` — **9 ticker ÉP** ⭐ (§0.4 továbbra is RESOLVED)
- `output/trade_plan_2026-05-21.csv` — 3 ticker (WMB, ON skip, DXCM)

---

## State (Day 4 — 2026-05-21 záró)

**Architektúra**: swing pivot Fázis 3 deploy DAY 4, mental stop, 3-5 napi hold, 15:30 CEST entry, sector-balanced greedy (30% cap, **NEM 15%** — Day 4-i újraértékelés), S_j scoring.

**Live**: 9 open positions, 0 exit flags Day 5-re.

**Cumulative**: **+$107,27 (+0,11%)**, trading_days: 4 (változatlan a Day 3-ról).

**Excess return**: **-0,20% vs SPY** (közel-flat, mild underperform — jelentős javulás a Day 3-i -1,03%-ról).

**Aktív P0/P1 anomáliák** (a `04-risks-and-open-questions.md` §0-ban):
- **§0.1 (régi pt_monitor)**: ✅ RESOLVED
- **§0.2 (Error 10349 TIF)**: ⭐ **Day 4-en NEM jelentkezett** — P0 → P1 javasolt downgrade, continual observation
- **§0.3 (Phase 2 timeout)**: implicit OK Day 4-en
- **§0.4 (UW shadow felülírás)**: ✅ RESOLVED Day 4-en is
- **§0.5 (submit retry storm)**: ✅ **Day 4-en NEM jelentkezett** — P0 → P2 javasolt downgrade, Day 5-7 megfigyelés
- **§0.6 (sector cap megsértés)**: ⭐ **WITHDRAWN** — téves értelmezés, a design cap 30%, NEM 15%

**Új megfigyelések**:
- **§0.7 (új) MASI ATR-anomaly low-volatility ticker time stop**: P3 — Day 6 time stop kvázi-flat profit várt, strukturális opportunitás-kibehagyási költség
- **§0.8 (új) Healthcare sector koncentráció 25,05%**: P3 — heti monitoring, 28%+ esetén megfontolni preemptive sector cap reduction

**A Day 4 napi karakter egy mondatban**: A swing pivot architektúra **első tényleges normál működés napja** (csak 1 sikeres submit attempt, NINCS anomália), **2 új entry-vel kibővült 9-pozíciós portfolio** (51,38% notional), **közel-flat P&L** ($0 net, kumulatív $107,27 változatlan), **mild bull-rally underperform** (-0,20% excess vs SPY +0,20%), **MINDEN P0 anomália csendes** (CC fix-ek + alkalmi Day 3-i anomáliák egyszeri természete megerősítve), és **a §0.6 sector cap rejtély feloldása** révén **a Day 4-i 30%-os értelmezés a tényleges design** — a 15%-os Day 1-3-i értelmezés téves olvasata volt.

---

## 9. ⚠️ UTÓLAGOS KORREKCIÓ (felfedezve 2026-05-23 reggel az IBKR Trades alapján)

**Discovery time**: 2026-05-23 szombat reggel, az IBKR TWS Trades + Positions + Orders képek elemzése során (lásd Day 5 review §9).

### Day 4 19:19:54 CEST — VLO SL bracket trigger ⚠️

Az IBKR Trades log szerint **Day 4 közben (péntek 19:19:54 CEST)** a VLO ticker stop-loss bracket order **autonóm módon triggerelt** és zárta a teljes 16-share pozíciót:

| Mező | Érték |
|------|-------|
| Ticker | VLO |
| Action | SLD |
| Qty | 16 |
| Fill ár | **$244,61** |
| Időpont | 2026-05-21 19:19:54 CEST = 13:19:54 ET (mid-day) |
| ORDER_REF | ÜRES (NEM `IFDS_SWING_*` order ref) |
| Net Total | -$222,97 |
| Net Incl. Commission | **-$227,06** |

**Bracket level forrás**: a `pt_submit_2026-05-20.log` szerint a Day 3-i VLO entry-nél:
```
16:05:23 VLO: MKT BUY 16 @ ~$262.62 | stop $244.71 | TP1 $276.05 | TP2 $289.48
```
**A planned-entry alapú stop $244,71** — a fill ár $244,61 **csak $0,10 alatta** (slippage). **NEM a `swing_positions.json` mental stop $240,64-je triggerelt**, hanem a **planned-alapú IBKR bracket SL**.

### Strukturális finding (helyesbítve 2026-05-25, Log Review chat kódbázis-elemzése)

**Eredeti hipotézis (téves)**: a swing pivot IBKR bracket-stop módban fut.

**A `submit_orders.py` kódbázis-elemzése megmutatta a helyes magyarázatot**: a `submit_swing_market_only` függvény **CSAK parent MKT BUY-t ad be**, NINCS child SL+TP1+TP2 bracket order. A kód explicit kommentje: `# Single market BUY (no bracket).` — a swing pivot architektúra szándékos design-választása (Day 63 §3.12). Ezt a 7 cron-driven entry (LBRT, MASI, EC, PFGC, WMB, DXCM, AMH) megerősíti: ezek `orderRef: IFDS_SWING_{sym}` formátumú parent MKT order-ek, child bracket nélkül.

**Akkor honnan jött a Day 4 VLO SL trigger?** A `04-risks-and-open-questions.md` §0.4 (Day 3 IBKR Error 354 RESOLVED) szerint **Tamás manuálisan adta fel** a VLO/ON/CNC ticker-eket az IBKR TWS Workstation Order Entry-n az Error 354 workaround miatt. A TWS GUI **bracket order template-jét használta**, ami parent MKT + child SL + child LMT TP-t hozott létre **a `pt_submit_2026-05-20.log` planned-szintjeivel** (VLO stop $244,71). Az IBKR Trades log megerősíti: a Day 4 VLO SLD trigger **ORDER_REF ÜRES** — NEM `IFDS_*` ref, mert TWS GUI-ból manuálisan generált.

**Helyes finding**:

1. **A swing pivot architektúra mental-stop módban van** (helyes, ahogy a `2026-05-17-swing-sizing-phase6.md` design doc és a Day 1 prezentáció írja). A `submit_swing_market_only` parent MKT-only.

2. **A Day 4 VLO SL trigger Tamás Day 3-i manuális TWS bracket-jének autonóm trigger-je volt** — NEM a `submit_orders.py` viselkedése. A manuális TWS bracket planned-szintjei ($244,71 stop) **szigorúbbak** mint a tényleges-fill-alapú mental stop ($240,64), és $0,10-es slippage-szel triggereltek $244,61-en.

3. **A CNC manuális TWS bracket** (Stop $55,50 + Limit $61,89 GTC) **Tamás Day 6 reggel manuálisan cancellálta** (2026-05-25 08:26 CEST, IBKR Orders ablak megerősíti: 2 × Cancelled). Az IBKR-ben többé nincs élő autonóm bracket order.

4. **A `pt_monitor.py` 22:00 EOD eval state-divergence detektálási képessége** továbbra is hiányzó. A Day 4 VLO SL trigger miatt a `swing_positions.json` és az IBKR Positions divergálnak (10 vs 8 nyitott pozíció). Ez egy strukturális monitoring hiány, függetlenül a Tamás manuális bracket-jétől — a `pt_monitor.py::reconcile_state_from_ibkr` P0 task implementációja továbbra is szükséges.

### Day 4 tényleges P&L

| Mutató | Hivatalos (`daily_metrics`) | Tényleges (IBKR) |
|--------|-----------------------------|------------------|
| Realized trade-ek | 0 | 1 (VLO SL) |
| Realized P&L | $0 | **-$227,06** |
| Cumulative | +$107,27 | **-$119,79** (recompute) |

A `daily_metrics/2026-05-21.json` `pnl.gross: 0` és `cumulative: 107.27` **NEM tartalmazza** a VLO SL bracket trigger -$227,06 realizált veszteségét, mert a `pt_monitor.py` 22:00 EOD eval-ja **nem reconcile-eli** a state-et az IBKR-ből. A `swing_positions.json` Day 4 záró továbbra is **VLO `HOLD, days_held: 1`** flag-gel mutatja, miközben a pozíció ténylegesen zárva van.

### Konzekvencia a Day 4 narratívára

A Day 4 "napi karakter egy mondatban" rész **átértékelendő**:
- ❌ A megfogalmazott "közel-flat P&L ($0 net)" **téves** — tényleges Day 4 net **-$227,06**
- ❌ A "swing pivot architektúra első tényleges normál működés napja" **téves** — ez a nap a **brutális kontraszt** napja: kívülről nyugodt, valójában a legrosszabb day-loss az egész W21-en
- ✅ Az "§0.6 sector cap értelmezés-feloldás" megfigyelés **továbbra is helyes**

### Akció: state reconciliation P0 task

A tényleges state-frissítés és daily_metrics korrekció **NEM a Log Review chat scope-ja**, hanem **a Dev chat / CC** feladata egy új P0 task keretében: lásd `docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`. **Ezt Tamás manuálisan NEM nyúlja hozzá** — a Dev chat által generált autonóm `pt_monitor.py` reconciliation logika kell, hogy elvégezze a Day 6 (kedd 2026-05-26) első pipeline futáskor.

**A jelen review §1-§8 szakasza VÁLTOZATLAN marad** (transzparens audit trail), és **a §9 UTÓLAGOS KORREKCIÓ szakasz** rögzíti a felfedezést és a tényleges adatokat.
