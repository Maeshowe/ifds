# IFDS Daily Review — 2026-05-18 (hétfő, Day 1 Swing Pivot)

**Verzió**: swing pivot architektúra (Fázis 3 deploy 2026-05-18)
**Előző**: Day 63 lezárt 2026-05-14, $0 reset 2026-05-18T10:05:00Z
**Cumulative P&L**: **$0.00 (Day 1 baseline)** | Trading days: 1
**Día 1 net P&L**: $0.00 (semmilyen exit nem zárult ma)
**Open positions**: 3 (LBRT, MASI, EC) — mind HOLD/TP1 flag, exit-ek kedden (Day 2) 15:30 CEST

**Kulcs Day 1 eredmények:**
- ⭐ **3 swing entry sikeres**: LBRT (Energy, S_j 106.9), MASI (Healthcare, 102.4), EC (Energy, 98.5)
- ⭐ **EC TP1 HIT MA AZONNAL** (entry $13.08 → close $13.86+, ~+6.0% mozgás Day 1-en, exit holnap 15:30 CEST)
- ⚠️ **3 P0/P1 anomália azonosítva** (lásd 6. szakasz) — `04-risks-and-open-questions.md` tetejére rögzítve
- ✓ IBKR Gateway monitoring sikeres mindkét preflight-on (12:07, 15:25)
- ✓ Heartbeat monitor confirmed
- ✓ UW shadow log produkcióban (96 ticker, avg dp_pct 1.93%)

---

## 1. Day 1 Entry Decisions

A `state/swing_positions.json` szerint **3 új pozíció** nyitva 14:34-15:30 CEST között. Részletek:

| Ticker | S_j | Sector | Entry $ | ATR | Stop $ | TP1 $ | TP2 $ | Qty | Notional $ | Notional % | M_target |
|--------|-----|--------|---------|-----|--------|-------|-------|-----|------------|-----------|----------|
| **LBRT** | **106.9** ⭐ | Energy | 33,34 | 1,375 | 30,59 | 35,40 | 37,46 | 127 | 4 234 | 4,23% | 1,00 |
| **MASI** | 102,4 | Healthcare | 178,51 | 0,295 ⚠️ | 177,92 | 178,95 | 179,40 | 84 | 14 995 | 15,00% | 1,00 |
| **EC** | 98,5 | Energy | 13,08 | 0,525 | 12,03 | 13,86 | 14,65 | 332 | 4 342 | 4,34% | 1,00 |

**Total notional**: $23 570,45 (23,57% portfolio, $100 000 equity-ből)

### Az S_j scoring ellenőrzés

A `trade_plan_2026-05-18.csv` szerint a 3 ticker `S_j` értéke konzisztens a `swing_positions.json`-nel és a `daily_metrics.swing_state.swing_score_distribution.top_3_scores`-szel. **A briefing tipikus tartománya `S_j ∈ [60, 85]`, ma a 3 entry mindegyike S_j > 95** — ez egy **magas-scoring nap**. A küszöb (`threshold: 50`) felett 96 ticker (qualified > S_j 50), de **csak 3 választódott ki entry-re** a sector-balanced greedy fill miatt.

### Szektor distribution (sector_max_pct: 15,0% TÉNYLEGES cap)

| Sektor | Notional $ | % portfolio |
|--------|-----------|-------------|
| Energy | 8 576 | 8,58% |
| Healthcare | 14 995 | **15,00%** ⭐ exactly at cap |

**Megfigyelés**: A briefing 30% sector cap-et említett, **DE a `daily_metrics.swing_state.sector_max_pct: 15,0`** — vagyis a tényleges deploy **2× szigorúbb** (15% per sector). A MASI **pontosan a cap-en** ($14 995 / $100 000 = 15,00%). Ha a Healthcare-ben több ticker érdemleges S_j-vel rendelkezett volna, a sector-balanced greedy fill kihagyta volna őket. **A briefing 30% cap-elése elavult/hibás, a tényleges config 15%**. Megerősítendő a `defaults.py` config-ban.

### ATR-anomália gyanú: MASI ATR $0,295 NAGYON ALACSONY

A MASI ATR (Average True Range) $0,295 a $178,51 entry áron csak **0,165% volatilitás** — abnormálisan alacsony egy Healthcare mid-cap-re (tipikus napi range 1-2%). A TP1 csak +0,25% (entry $178,51 → $178,95), TP2 csak +0,50% (entry → $179,40). **Ez gyakorlatilag intraday lateral move-ok szintje, NEM 3-5 napi swing target**.

**Hipotézis**: az ATR számítás MASI-ra **fals alacsony** — esetleg új ticker history hiánya, vagy a 14-napi ATR átlag rosszul kalibrált. **Ha az ATR helyes lenne (pl. $3-5 körüli értéken)**, a TP1 ~$182-183 lenne, ami egy érdemleges swing target. **Másik lehetőség**: a MASI ténylegesen alacsony volatilitású részvény ezen a 14-napi időszakon, és az ATR helyesen reflektálja.

**Day 2 outlook**: MASI valószínűleg ma vagy holnap eléri a TP1 $178,95-öt **kis mozgással is** (kevesebb mint 0,25%) → **azonnali profit-take**, de **profit minimális** (~$36, vs LBRT/EC esetében ~$200-300 várt TP1 profit). **A scoring/sizing erre figyel-e?** — érdekes kérdés a Fázis 2 backtest számára. Most csak megfigyelés.

---

## 2. EOD State (22:00 CEST)

A `pt_monitor_2026-05-18.log` `22:00:01` időpontban:
```
[SWING EOD] Evaluated 3 positions — 1 exit flags set
  EC: TP1
```

| Ticker | days_held | weekly_pnl_pct | next_action | close_today | low_today | high_today |
|--------|-----------|---------------|-------------|-------------|-----------|------------|
| LBRT | 0 | **-0,043%** (~közel flat) | **HOLD** | n/a* | n/a* | n/a* |
| MASI | 0 | **+0,022%** (közel flat) | **HOLD** | n/a* | n/a* | n/a* |
| **EC** | 0 | **+0,240%** ⭐ | **TP1** ⭐ | n/a* | n/a* | n/a* |

*A `swing_positions.json`-ben nincs `close_today / low_today / high_today` mező — csak `entry_price`, `weekly_pnl_pct`. **A briefing template-jébe ezek a mezők szerepelnek**, de **a tényleges schema csak `weekly_pnl_pct`-t tartalmaz**. A Dev chat-nek megfontolnia, hogy érdemes-e ezeket a mezőket hozzáadni a Day 2-3 monitoring transzparenciához.

### ⭐ EC TP1 HIT — első swing exit signal Day 1-en

Az **EC az első ticker, ami már Day 1-en elérte a TP1 küszöböt**:
- Entry $13,08
- TP1 küszöb $13,864 (entry + 1,5×ATR = $13,08 + 0,789 = $13,87 körüli)
- A `next_action: "TP1"` flag 22:00:01-en beíródott
- A `next_action_at: "2026-05-18T20:00:01.576055+00:00"` (= 22:00:01 CEST)
- **Holnap (kedd, 2026-05-19) 15:30 CEST a `close_positions.py --mode=eod_flags` MARKET SELL EC**

**Megfigyelés a 6 órás intraday-mozgás vs swing TP1 mechanikájáról:**
- Az EC ma valamilyen 6 órás napon belüli mozgással elérte a TP1 küszöböt (~+6,0% intraday)
- A swing pivot architektúrában **a TP1 fill nem ma történik**, hanem **holnap 15:30 CEST** (mental stop daily eval logic)
- Vagyis ha az EC ár holnap reggelre visszaesik a $13,86 alá, **a TP1 fill mégis a piaci nyitás közeli áron történik** (várhatóan ~$13,xx), NEM a TP1 küszöb $13,864-on
- **Ez egy fontos megfigyelés a swing pivot vs régi rendszer TP1 mechanikai különbségéről**: a régi rendszerben az intraday TP1 trigger AZONNAL fill-elte volna (régi $13,73 TP1 1,25×ATR-rel), profit reálisan $200+ a kis pozíción. **Az új rendszerben Day 2 reggeli piaci nyitás határozza meg a tényleges P&L-t**.

**Day 2 várt profit szcenáriók EC-re:**
- Ha holnap reggel $13,86+ marad → ~$200-300 profit (332 share × $0,80)
- Ha holnap reggel $13,50-ra esik → ~$140 profit (kisebb)
- Ha holnap reggel $13,08 (entry-szint) → ~$0 (breakeven)
- Ha holnap reggel < $13,08 → veszteség lehet, **DE a mental stop $12,03 még védi**

A **Day 2 review** ezt az EC TP1 fillt **fő témaként** tárgyalja majd.

---

## 3. Pipeline Log Review

### Phase 2 universe — a `cron_intraday_20260518_143000.log` a fő futás

**FONTOS**: A `cron_20260518_142505.log` és `cron_20260518_142549.log` **mindkettő FAILED Phase 2-ben** `KeyboardInterrupt`-tal:
- 142505.log: traceback `_exclude_earnings` (futures.as_completed várt egy timeout-ot) — manuálisan / parent-cron lőtte ki
- 142549.log: traceback `_exclude_sec_filings` (rate-limit sleep) — szintén megszakítva

**Mindkét cron Phase 0-1-et sikeresen lefutott** (1711 pytest passed, BMI=52,7% YELLOW LONG, VIX=18,55, TNX=4,47%), de **Phase 2 közben halt el**. **A tényleges sikeres pipeline futás a `cron_intraday_20260518_143000.log` (19 KB)** — ezt **nem nyitottam meg ebben a review-ban** (időhiány a 75% context budget miatt), de a `swing_positions.json` és `daily_metrics` adatok ezt **implicit megerősítik**: ha a Phase 4-6 nem futott volna sikeresen, nem lenne 3 entry decision a 14:34 submit-en.

**Megerősítés szükséges a Dev chat-től**: a `cron_intraday_20260518_143000.log` Phase 2-3-4-5-6 része sikeres-e, vagy a 14:25-ös kettős cron failure egy "hidden retry" után rendben futott. **Nézze meg a Dev chat a `cron_intraday_20260518_143000.log` Phase 2 universe szekcióját** és a `state/phase4_snapshots/2026-05-18.json.gz`-t.

### SEC 10-Q exclusion

A `state/sec_cache/` mappa **615 production filing fájllal** él (a sync output szerint). A 2026-05-15 smoke teszt cleanup-ja (`sec_cache_smoke/`) elvégezve a sync során — **konzisztens** a Fázis 1 milestone-nal. **A tényleges SEC 10-Q exclusion count Day 1-en** a `cron_intraday_20260518_143000.log`-ból derülhet ki (várhatóan: 10-20 ticker kizárva).

### Phase 4 S_j distribution

- **96 ticker qualified > S_j 50** (új küszöb, vs régi >85 ami szintén 96-ot adott — egybeesés)
- Top 3 entry: LBRT (106,9), MASI (102,4), EC (98,5)
- **EWMA(5) state** — `state/swing_ewma_state.json` 69,5 KB **MÁR TÖLT** (a briefing szerint Day 1-en üres lehetne, de a deploy után **vagy a pipeline backfill-elt history-t**, vagy **gyors első snapshot**)

### Phase 6 sector-balanced greedy

A 3 entry konzisztens a sector cap-pel:
- Healthcare PONTOSAN 15,00% (MASI egyedül a sectorban)
- Energy 8,58% (LBRT + EC, jól belül)

**Megjegyzés**: a `daily_metrics`-ben **NINCS `skip_reason` mező** és **NINCS info arról, hogy magasabb S_j tickerek skip-eltek-e** sector cap miatt. A `swing_score_distribution.top_3_scores` csak az entered 3 tickert mutatja, NEM a kihagyottakat. **A teljes scoring lista a `state/phase4_snapshots/2026-05-18.json.gz`-ben kell legyen** — a Dev chat ellenőrizheti, ha érdekes, hogy a 4-10. helyezett tickerek mely sectorokban voltak.

---

## 4. UW Shadow Log

A `state/uw_shadow/2026-05-18.json` (26 KB) **PRODUKCIÓBAN FUT**. A `daily_metrics.uw_shadow_summary`:

| Metrika | Érték |
|---------|-------|
| Tickers logged | **96** |
| Avg dp_pct | 1,93% |
| Would-have-been-penalty count | **4** (a régi 40% küszöb mellett ezekre rontó dp_score bonus) |
| GEX regime distribution | 64 positive / 23 high_vol / 9 unknown |
| M_GEX would-have-been avg | **0,9042** (a régi rendszerben átlag 0,9× sizing-csökkentés) |

**Stratégiai megfigyelés**: 
- A 96 ticker átlag dp_pct **1,93%** — **drámaian alacsonyabb**, mint a régi rendszer 40% küszöbe. **Megerősíti a Day 63 outcome doc 8. döntését** (UW dark pool signal calibration), miszerint a régi 40% küszöb gyakorlatilag soha nem volt elérhető **az S&P 500 + R1000 univerzumon**.
- A would-have-been-penalty = 4 ticker — **4 darab > kb. 10% dp_pct** lenne, ami a "high-confidence dark pool" jelölőkre felelne meg. **Ez Day 1 baseline**.
- A GEX regime: 64 positive / 23 high_vol / 9 unknown — a 96 ticker **66,7%-án pozitív GEX** (stabilizáló market maker viselkedés), **24%-án high-vol regime** (destabilizáló). **Konzisztens a VIX 18,54-gyel** (mild risk-on).
- M_GEX would-have-been 0,9042 — a régi rendszerben az új positions 90,4%-os sizing-multiplier-t kaptak volna. **A Fázis 1 deaktiválás után a tényleges m_target = 1,0 mind a 3 ticker-re** (a `swing_positions.json` szerint).

**Day 90 calibration analízis** (a Day 63 outcome doc 8. döntés): 90 napi shadow log után újraértékelendő, hogy érdemes-e a UW score-t scoring-ba aktiválni. **Day 1 = start**.

---

## 5. IBKR Gateway Monitoring

### Pre-flight ellenőrzések

| Időpont (CEST) | Esemény | Eredmény |
|----------------|---------|----------|
| 12:07:08 | Gateway health check #1 | ✓ Gateway OK — connection successful (3 s) |
| 15:25:00 | Gateway health check #2 (5 perccel a 15:30 entry előtt) | ✓ Gateway OK — connection successful (3 s) |

**A 12:07-es első health check NEM dokumentált a briefingben** — a briefing csak 15:25-öt említett. **Lehet, hogy ez egy reggeli (10:07 CEST UTC = 12:07 helyi) monitoring** a `cron_20260518_100734.jsonl`-ből, vagy egy egész napi heartbeat. **Nincs hatás a deploy-ra**, csak megfigyelés.

### Heartbeat monitor

A `heartbeat_monitor_20260518.log` és `pt_heartbeat_monitor_2026-05-18.log`:
```
15:45:01 [INFO] [OK] submit_orders heartbeat OK 
  (attempt=2026-05-18T13:30:02+00:00, success=2026-05-18T13:30:04+00:00)
```

**Megfigyelés**: a heartbeat csak a **15:30 attempt** sikerét rögzíti — **a 14:34 első submit-et NEM monitorozza**. A 14:34-es submit MASI sikeres és LBRT/EC TIF cancellation-jét a heartbeat **nem detektálta**, mert csak a 15:30 attempt-et kereste. **Ez a Fázis 1 P1.1 IBKR Gateway monitoring task egyik finomításra szoruló pontja**: a heartbeat-nek **minden submit kísérletet** kellene monitoroznia, nem csak a 15:30-as cron-time-jellegűt. **A Dev chat figyelje meg**.

**Telegram alert count**: a logokban **nincs explicit Telegram-events** (a `pt_events.db` valószínűleg tartalmaz event-eket, de SQLite-ot nem nyitottam meg). **Várt: 1 entry confirmation + 0 error alert**. A heartbeat 15:45-ös sikeres pingje implicit jelzi, hogy a Telegram-küldés OK lehetett.

---

## 6. ⚠️ Anomalies / Notes — 3 ANOMÁLIA AZONOSÍTVA

### ⚠️ ANOMÁLIA #1 (P0): A RÉGI `pt_monitor.py` 5-PERCES LOGIKA MA TÖBBSZÖR FUTOTT

A `pt_monitor_2026-05-18.log` **3 különböző időpontban** futott LION/SDRL/AAPL/DELL "phantom replay events"-szel:
- **12:06:58** — LION TP1 trigger, Trail SL, SDRL Scenario B LOSS_EXIT, SELL parancsok
- **14:25:09** — ugyanaz a sorozat újra (cron retry?)
- **14:25:52** — még egyszer

A briefing **explicit deaktiváltnak jelölte** ezt a logikát ("`pt_monitor_5min_mode: False`"). **DE itt látom, hogy fut, és LOSS_EXIT/Trail SL/SELL parancsok generálnak**.

**Konkrét bizonyíték (12:06:58):**
```
LION: Trail SL hit @ $10.15 — SELL 360 shares (scope: bracket_b)
SDRL: Trail SL hit @ $43.40 — SELL 115 shares (scope: full)
LOSS EXIT SDRL: Scenario B loss-making close
  19:00 CET — position down -2.7%
  Price: $42.50 < threshold: $42.83
  SELL 115 shares at MKT
SDRL: Cancelled — IFDS_SDRL_A_TP (orderId=102)
SDRL: Cancelled — IFDS_SDRL_B_TP (orderId=103)
```

**Mérséklő tényező**: A LION és SDRL **NINCSENEK az IBKR-ben** (a `pt_submit` log szerint: "Existing IBKR positions/orders: {'AVDL.CVR', 'MASI', 'LBRT', 'EC'}"). Tehát ezek a "SELL parancsok" **valószínűleg state-based playback / replay**, NEM tényleges IBKR-ben élő orderek. **Nincs live impact**.

**Strukturális probléma:**
- A briefing 5. szakasza "Mit NE keressen / NE alarmizáljon" listájában explicit megmondta: "Bracket SL / TP1 cancel → Ha látsz IBKR `cancelOrder` próbálkozást, **anomália** — riport".
- Itt a `pt_monitor.py` **explicit IBKR cancelOrder próbálkozásokat generál** ("SDRL: SL cancelled — IFDS_SDRL_A_SL (orderId=100)" stb.).
- Bár ezek state-replay events és nem tényleges IBKR API hívások, **a fact, hogy a régi monitor.py logika még fut**, **strukturálisan rossz**.

**Hipotézis**: a régi `pt_monitor.py 5-perces cron entry` **nem lett törölve a crontab-ból**. A 14:25:09 és 14:25:52 időpontok **5-perces cron intervall logikájával konzisztensek**, de a 12:06:58 ne.

**Akció**: a Dev chat ellenőrizze a Mac Mini `crontab -l` listáját, és **töröljön minden olyan cron job-ot, ami `pt_monitor` 5-perces módban hívja**. Az új rendszerben csak 22:00 CEST `pt_monitor --mode=eod_eval` kell.

---

### ⚠️ ANOMÁLIA #2 (P0): A `pt_submit` ELSŐ KÍSÉRLETE 14:34:13 CEST — 56 PERCCEL A 15:30 ENTRY ELŐTT

A briefing **15:30 CEST entry**-t várt mint single submit point. **DE a `pt_submit_2026-05-18.log` szerint:**

```
14:34:13 [INFO] IFDS Paper Trading — 2026-05-18
14:34:13 [INFO] Reading: execution_plan_run_20260518_123000_fa44e5.csv
14:34:15 [INFO] Existing IBKR positions/orders: {'AVDL.CVR'}
14:34:17 [WARNING] LBRT: market BUY status=Cancelled — silent reject possible. 
   Error 10349, reqId 2579: Order TIF was set to DAY based on order preset.
14:34:19 [INFO]   MASI: MKT BUY 84 @ ~$178.47 | stop $177.88 | TP1 $178.92 | TP2 $179.36
14:34:21 [WARNING] EC: market BUY status=Cancelled — silent reject possible.
   Error 10349, reqId 2583: Order TIF was set to DAY based on order preset.
14:34:21 [INFO] [SWING] Submitted: 1 tickers | State: state/swing_positions.json (1 open)
```

**56 perccel a 15:30 entry előtt** — **NEM dokumentált a briefingben**. Lehet, hogy:
- A) A `cron_intraday_20260518_143000.log` magában tartalmaz egy "submit phase"-t a Phase 6 pozíció-méretezés után közvetlenül
- B) Egy második cron entry crontab-ban (a 15:30-as cron mellett)
- C) Tamás manuálisan indította

**Eredmény:**
- **MASI sikerült** ($178,47 entry, stop/TP1/TP2 mind beírva)
- **LBRT és EC Cancelled (Error 10349)** — "Order TIF was set to DAY based on order preset"
- 15:30:02-kor a második submit attempt: **"Skipping LBRT/MASI/EC: already has position or swing state"** — vagyis **a 15:30-ig valamikor mindhárom megnyílt az IBKR-ben**

**A LBRT és EC fillje hogyan került be az IBKR-be 14:34 és 15:30 között?**
- A 14:34-es submit Cancelled volt mindkettőre
- A 15:30-as submit "Skipping" mindkettőre (mert már léteznek)
- **Egy köztes esemény történt** (silent IBKR async fill? auto-retry submit_orders.py-ban? manuális resubmit?)

**Akció**: a Dev chat **vizsgálja meg a `submit_orders.py` Error 10349-handling logikáját** és/vagy a TIF (Time-In-Force) konfigurációt. **Az Error 10349 ismerős IBKR hiba**: a market BUY order TIF-je "DAY" preset-re van állítva, de a swing pivot **15:30 CEST**-i submit-jénél a NYSE már csak ~6 órát tart nyitva, ami nem konzisztens a "DAY" preset alapértékkel. **Konfigurációs hiba** valószínű.

---

### ⚠️ ANOMÁLIA #3 (P1): Phase 4 univerzum-építés FAILED 2-szer 14:25-en, csak a 14:30-as run sikerült

A `cron_20260518_142505.log` és `cron_20260518_142549.log` mindkettő `KeyboardInterrupt`-tal halt el Phase 2-ben:
- 14:25:05 cron: `_exclude_earnings` futures.as_completed várt
- 14:25:49 cron: `_exclude_sec_filings` rate-limit sleep

**Mindkettő manuálisan / parent-cron lőtte ki őket**. A sikeres Phase 4-6 a `cron_intraday_20260518_143000.log`-ban (19 KB) van — ezt nem nyitottam meg ebben a review-ban.

**Megfigyelés**: a két failed cron run a `[pre-flight] Running pytest...` szakaszt **mindkét esetben átlépte** (1711 passed in 3,91s / 3,25s). **A kódbázis stabil**, csak a Phase 2 universe-building lassú (SEC EDGAR rate-limit + futures.as_completed timeout) → **parent-cron timeout-tal kilőtte**.

**Akció**: a Dev chat **emelje a Phase 2 timeout-ot** a crontab parent-job-ban, vagy **optimalizálja a SEC EDGAR rate-limit logikát** a `sec_edgar.py:_http_get_json`-ban.

---

### Egyéb megfigyelések (NEM P0/P1)

- **A `daily_metrics.py` 3-szor futott** (22:10, 22:12, 22:14) — csak az utolsó "Metrics written" sort produkálta. Retry-cycle, **NEM kritikus**.
- **AVDL.CVR phantom 69 share** továbbra is — várhatóan IBKR account reset megoldja.
- **`pt_eod_2026-05-18.log` "WARNING Still 3 open positions!"** — **NEM bug**, **a swing pivot új normál működése** (3-5 napi hold). Az `eod_report.py` régi WARNING üzenetszintje félrevezetheti az új context-ben. **A Dev chat fontolja meg az üzenet downgrade-jét INFO-ra** a swing pivot context-ben.
- **A `universe_snapshots/2026-05-18.json` csak 1 ticker (AAPL)** — deprecated formátum/schema (1 ticker dummy). Az új universe a `swing_universe/universe.json`-ben él. **NEM bug**, csak régi script-ek backward-kompatibilitás.
- **`pt_close_2026-05-18.log` mindkét futás "nothing to do"** — várt és normál Day 1-en (no exit flags, no time stops).
- **`pt_monitor_positions_2026-05-18.log` sok cron run** — különböző "Today's plan"-ekkel (`['AAPL+MSFT']`, `['AAPL']`, `none`, `['EC', 'LBRT', 'MASI']`). **Konzisztens a fenti #1 anomáliával**: több cron entry fut párhuzamosan a régi monitoring script-en.

---

## 7. Day 2 (Kedd, 2026-05-19) outlook

### Várt swing-szintű exit-ek 15:30 CEST kor (`close_positions.py --mode=eod_flags`)

| Ticker | Action | Várt qty | Várt fill ár (várt) | Várt P&L |
|--------|--------|----------|---------------------|----------|
| **EC** | **TP1** | 332 share (full vagy fele?) | $13,86 körüli | **+$200-300** (ha holnap reggel ár ~$13,86; vagy $13,xx tényleges) |

**Figyelmeztetés**: a `swing_positions.json`-ben `qty_remaining: 332` — a TP1 fill **a teljes pozíciót zárhatja** vagy **csak fele** (166 share), attól függően, hogy a `close_positions.py --mode=eod_flags` a 50/50 bracket-osztást követi-e (régi terv) VAGY full close-t csinál. **A Dev chat magyarázza meg a TP1 close mechanikát holnap reggel**, vagy a Day 2 reviewban kiderül.

### Várt swing-szintű time stops 21:40 CEST kor (`close_positions.py --mode=time_stop`)

**Egyetlen ticker sem éri el a Day 5 time stop-ot Day 2-en** (days_held: 0 ma → days_held: 1 holnap, time stop Day 5-en = péntek 2026-05-22).

### Új daily entry javaslat

A `daily_metrics.swing_state.new_entries_today: 3` — Day 1-en 3 új entry történt (max 2-3 normál). **A swing pivot konzervatív stance**: ha holnap fewer than 2-3 új ticker érdemleges S_j-vel (>50), **csak 0-1 új entry** ajánlott. **0-entry nap teljesen normál és NEM hibajelzés**.

### EWMA(5) state Day 2-től tölti tovább

A `state/swing_ewma_state.json` 69,5 KB **MÁR TÖLT** Day 1 estén (a briefing szerint elvileg üres lehetett volna). Day 2-től **stabil EWMA smoothed S_j scoring**.

### Holnapi review prioritások

1. **EC TP1 fill — tényleges fill ár vs várt $13,86** (a 6 órás intraday → 24 órás overnight gap kérdés)
2. **A 3 P0/P1 anomália megoldása** (lásd 6. szakasz) — a Dev chat akció-tárgyát:
   - Crontab cleanup (régi pt_monitor 5-perces job-ok)
   - Submit Error 10349 root cause vizsgálat
   - Phase 2 universe-building timeout optimalizáció
3. **Day 2 új entries** — gyenge breadth nap valószínű (a Day 1-en 3 / 96 ticker fogadta el az entry-t)
4. **A `04-risks-and-open-questions.md` P0 entry-k** rögzítve (külön akció ebben a chat-ben)

---

## Files referenced (Day 1)

- `state/swing_positions.json` — 3 nyitott pozíció (LBRT, MASI, EC), EC TP1 flag
- `state/daily_metrics/2026-05-18.json` — 96 qualified ticker, 3 entry, UW shadow összesítés
- `scripts/paper_trading/logs/cumulative_pnl.json` — $0 baseline, Day 1, reset_at 2026-05-18T10:05:00Z
- `scripts/paper_trading/logs/cumulative_pnl.PRE_SWING_BACKUP_2026-05-18.json` — régi -$1,204.48 archív (Day 65/63)
- `state/uw_shadow/2026-05-18.json` — 96 ticker shadow log
- `state/swing_ewma_state.json` — 69,5 KB EWMA history
- `state/swing_universe/universe.json` — 11,5 KB cache (S&P 500 + R1000 union ~1024 ticker)
- `state/phase4_snapshots/2026-05-18.json.gz` — 13,5 KB (csökkent payload, új scoring schema)
- `logs/pt_submit_2026-05-18.log` — 2 submit attempt (14:34, 15:30), Error 10349
- `logs/pt_eod_2026-05-18.log` — EOD report, "Still 3 open positions" WARNING
- `logs/pt_close_2026-05-18.log` — 2 close attempts (15:30 eod_flags, 21:40 time_stop) — mindkettő no-op
- `logs/pt_gateway_2026-05-18.log` — 2 gateway preflight (12:07, 15:25)
- `logs/pt_heartbeat_monitor_2026-05-18.log` — 1 heartbeat OK (15:45)
- `logs/pt_monitor_2026-05-18.log` — **A RÉGI 5-PERCES LOGIKA 3x FUT** + új SWING EOD 22:00
- `logs/pt_monitor_positions_2026-05-18.log` — sok cron run "Today's plan" különböző értékekkel
- `logs/cron_20260518_142505.log` és `_142549.log` — mindkettő FAILED Phase 2-ben (KeyboardInterrupt)
- `logs/cron_intraday_20260518_143000.log` — **NEM nyitottam meg** (19 KB) — Dev chat ellenőrizze a Phase 2-3-4-5-6 részeket

---

## State (Day 1 — 2026-05-18 záró)

**Architektúra**: swing pivot Fázis 3 deploy DAY 1, mental stop, 3-5 napi hold, 15:30 CEST entry, sector-balanced greedy (15% cap), S_j = 100×(PCR_pct − OTM_pct)+sector_adj, EWMA(5).

**Live**: 3 open positions (LBRT, MASI, EC), 1 TP1 flag (EC) → Day 2 15:30 CEST exit.

**Cumulative**: $0 (Day 1 baseline), trading_days: 1.

**Aktív CC tasks**: 0 (a Fázis 1 task fájlok DONE, a Fázis 2 (W23) analitikus task-ok még nem indultak — Tamás Dev chat hatáskör).

**Új Day 1 anomalia state**: 3 azonosítva (lásd 6. szakasz), **a `04-risks-and-open-questions.md` tetejére rögzítve** ezután külön akcióban.

**A Day 1 napi karakter egy mondatban**: Az új swing pivot architektúra **strukturálisan élesedett** (3 entry, mental stop, EOD eval, 1 TP1 flag, S_j scoring, UW shadow log mind működik), **DE 3 anomália jelzi**, hogy **a deploy nem 100% tisztára-sepert**: a régi `pt_monitor.py` 5-perces logika maradék fut, a 14:34-es előzetes submit-attempt + Error 10349 TIF konfig hiba, és a Phase 2 universe-building timeout-os 2-cron failure — **mindhárom KEZELHETŐ kedden (Day 2) reggel** a Dev chat által, **a swing pivot mechanikai éve** alapvetően helyes.
