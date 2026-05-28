# Task — State Reconciliation from IBKR + TP/SL Hit Counter Fix

**Created**: 2026-05-23 szombat (Log Review chat)
**Priority**: **P0** — Day 6 kedd (2026-05-26) reggel pipeline futás ELŐTT deploy-andó
**Owner**: Dev chat / Claude Code (CC)
**Discovery source**: 2026-05-23 reggeli IBKR TWS Trades + Positions + Orders képek elemzése a Log Review chat-ben
**Related**:
- `docs/review/2026-05-21-daily-review.md` §9 (Day 4 VLO SL bracket trigger felfedezése)
- `docs/review/2026-05-22-daily-review.md` §9 (Day 5 ON TP1 + W21 reconciled summary)
- `docs/master-reference/04-risks-and-open-questions.md` §0.10 (új P0 anomalia)

---

---

## ⚠️ Frissítés 2026-05-25 — α opció (hibrid status quo), Tamás döntése

**A kódbázis-elemzés (2026-05-25, Log Review chat) megmutatta, hogy az alábbi 4-rétegű finding A pontja téves volt**. Helyesbített finding:

- **Réteg A**: A swing pivot **HELYESEN mental-stop módban van** (`submit_swing_market_only` kódja: `# Single market BUY (no bracket).`). A 7 cron-driven entry parent MKT-only. A Day 4-5 autonóm bracket-trigger-ek **Tamás Day 3-i manuális TWS bracket-jeiből** származtak (Error 354 workaround).
- **Réteg B**: A planned-alapú bracket-szintek **csak Tamás manuális TWS bracket-jeire** releváns. A cron-driven entry-knek NINCS bracket-je.
- **Réteg C és D**: továbbra is helyes (valódi strukturális monitoring + logging hiány).

**Tamás α opció (hibrid status quo) döntése**:
- **Architektúra-váltás NEM szükséges** — a swing pivot már helyesen mental-stop módban van. **Rész 4 (Architektúra-szintű döntés) TRÖLÖTT** ebből a task-ból.
- **CNC élő TWS bracket** Tamás manuálisan cancellálta 2026-05-25 08:26 CEST-kor (IBKR Orders ablak: 2 × Cancelled).
- **Design doc és Day 1 prezentáció NEM kell frissíteni** (helyes volt).

**Csak 3 részes scope** (Rész 1 + 2 + 3) az alábbi szakaszokból, **Rész 4 érvénytelen**.

**Becsült munka frissítve**: ~4-5 óra CC (korábbi 6-10 óra hármadrésze elhagyása miatt).

Referált források:
- A `submit_swing_market_only` kódja: `scripts/paper_trading/submit_orders.py` line ~250-330 (parent MKT only)
- Tamás manuális cancel megerősítés: 2026-05-25 08:26 CEST screenshot
- Átfogalmazott Day 4 review §9, Day 5 review §9, `04-risks` §0.10

---

## 1. Probléma — 4 réteg (eredeti hipotézis, audit trail)

### Réteg A: A swing pivot architektúra IBKR bracket-stop módban fut

A `submit_orders.py` (a `submit_swing_market_only` vagy hasonló függvény) a parent MKT BUY mellett **autonóm IBKR bracket TP1 + SL child order-eket** ad be. Ez **eltér** a `2026-05-17-swing-sizing-phase6.md` design dokumentum "mental stop" megfogalmazásától és a Day 1 prezentáció `docs/presentations/2026-05-19-system-overview.md` 7. fejezetétől.

**Bizonyíték**:
- Day 4 (2026-05-21) 19:19:54 CEST: VLO 16 SLD @ $244,61, **ORDER_REF ÜRES** (NEM `IFDS_SWING_*`). A `pt_submit_2026-05-20.log` 16:05:23 entry-jében a VLO planned stop **$244,71** — a fill $0,10-cel alatta. **Egyértelműen IBKR bracket SL trigger**.
- Day 5 (2026-05-22) 16:40:20 CEST: ON 27 SLD @ $115,41, **ORDER_REF ÜRES**. A `pt_submit_2026-05-20.log` 16:05:24 entry-jében az ON planned TP1 **$115,41** — a fill **EXACT MATCH**. **Egyértelműen IBKR bracket TP1 trigger**.
- IBKR Orders ablak: **CNC SELL Stop $55,50 GTC + CNC SELL Limit $61,89 GTC** függő — a planned-alapú szintek ($55,50 stop + $61,89 TP1).

### Réteg B: A bracket levels a PLANNED entry-alapúak, NEM a tényleges fill-alapúak

A `submit_orders.py` a Phase 6 sizing alapján generálja a bracket szinteket (planned_entry ± 1,5×ATR), és a parent MKT BUY-jal **egyidejűleg adja be** az IBKR-be. A tényleges fill ára eltér a planned-től (slippage), de a bracket szintek **NEM módosulnak**.

**Példák a Day 3-i entry-knél**:

| Ticker | Planned entry | Tényleges fill | Slippage | Planned stop | Mental stop (tényleges-alapú) |
|--------|---------------|----------------|----------|--------------|-------------------------------|
| VLO | $262,62 | $258,55 | **-1,55% kedvező** | $244,71 | $240,64 |
| ON | $106,02 | $109,48 | **+3,26% kedvezőtlen** | $93,50 | $96,96 |
| CNC | $59,15 | $59,27 | +0,20% kedvezőtlen | $55,50 | $55,62 |

| Ticker | Planned TP1 | Mental TP1 (tényleges-alapú) | Trigger Day 4-5 |
|--------|-------------|-------------------------------|------------------|
| VLO | $276,05 | $271,98 | (SL triggered előbb) |
| ON | **$115,41** | $118,87 | **Day 5 TP1 $115,41** ✓ |
| CNC | $61,89 | $62,01 | (nyitva) |

**Konzekvencia**:
- VLO esetén kedvező slippage → bracket stop $4,07 szigorúbb mint a mental
- ON esetén kedvezőtlen slippage → bracket TP1 $3,46 korábban trigger mint a mental
- CNC esetén mild kedvezőtlen → bracket szintek ~$0,12 eltérők

### Réteg C: A `pt_monitor.py` 22:00 EOD eval NEM reconcile-eli a state-et az IBKR-ből

A `swing_positions.json` Day 5 záró 10 nyitott pozíciót mutat (LBRT, MASI, EC, PFGC, VLO, ON, CNC, WMB, DXCM, AMH), de **az IBKR Positions csak 8-at** (VLO és ON már zárva). A `pt_monitor.py` `evaluate_eod_exits()` (vagy hasonló) **nem hív** `ib.positions()` API-t, **nem hív** `ib.trades()` vagy `ib.executions()` API-t — csupán a `swing_positions.json` lokális state alapján dolgozik. **A bracket trigger-ek lokálisan láthatatlanok**.

### Réteg D: A `daily_metrics.py` realized P&L NEM tartalmazza a bracket trigger-eket; TP/SL/TP2 hit counterek soha nem update-elnek

Mind a `daily_metrics/2026-05-21.json` (Day 4) és `daily_metrics/2026-05-22.json` (Day 5) `pnl.gross: 0` és `pnl.cumulative: 107.27` — **a $0 realized P&L a Day 4-5-en téves**, mert a VLO SL (-$227,06) és ON TP1 (+$159,12) bracket trigger-ek **nem jelennek meg** a daily_metrics-ben.

**Plus**: a `cumulative_pnl.json daily_history` minden napra `tp1_hits: 0`, `sl_hits: 0`, `tp2_hits: 0` — **soha nem volt update-elve**. Még a Day 2-i EC TP1 fill (a `IFDS_SWING_EC_TP1` order ref-fel logolva a submit_orders-ben!) sem inkrementálta a `tp1_hits` számlálót. Ez egy **különálló, régóta fennálló bug** a daily_metrics-ben / cumulative_pnl logging logikában.

---

## 2. Task scope (3 rész — α opció, frissítve 2026-05-25)

### Rész 1 — State reconciliation a `pt_monitor.py` 22:00 EOD eval-ban

**Új függvény**: `pt_monitor.py::reconcile_state_from_ibkr() -> dict[str, Any]`

**Lépések**:
1. **Lekérdezés**: `ib.positions()` → lista a jelenleg nyitott IBKR pozíciókról (ticker, qty, avgCost)
2. **Lekérdezés**: `ib.executions(execFilter=ExecutionFilter(time=today_iso_z))` → lista a mai (és/vagy past N nap) fill-ekről (ticker, side, qty, price, time, orderRef)
3. **Összehasonlítás**:
   - Minden ticker a `swing_positions.json`-ben:
     - Ha `qty_remaining > 0` és NEM szerepel az IBKR `ib.positions()`-ben → **autonóm bracket trigger detektálva**
     - Ha `qty_remaining > 0` és az IBKR-ben `qty` kisebb → **partial fill** (pl. EC TP1 utáni maradék)
     - Ha `qty_remaining == 0` és az IBKR-ben szerepel → state-bug (régen zárt, de nem törölt)
4. **Bracket trigger esetén**:
   - Lekérdezni a megfelelő SLD execution-t az `ib.executions()` listából (egyező ticker, side='SLD', időpont > entry_date)
   - Meghatározni a trigger típust:
     - Ha `fill_price <= stop_level` (a `swing_positions.json` `stop_level` mezője): **SL trigger**
     - Ha `fill_price >= tp1_level` és `qty == initial_qty // 2`: **TP1 trigger** (50% partial close)
     - Ha `fill_price >= tp2_level` és `qty == initial_qty // 2`: **TP2 trigger** (a TP1 utáni maradék)
     - Egyébként: **OTHER** (pl. trail SL, manual close, vagy ismeretlen)
     - **Speciális eset**: a bracket levels a PLANNED entry-alapúak, NEM a fill alapúak. A `swing_positions.json` `stop_level` a tényleges fill-alapú, viszont a tényleges trigger a planned-alapú. A `pt_submit_YYYY-MM-DD.log` fájl `stop $XX | TP1 $YY | TP2 $ZZ` mintázatát kell parse-olni a planned bracket szintekért. **Vagy egyszerűsíteni**: ha a SLD fill ár közelebb van egy bracket szinthez (planned vagy fill-alapú) mint ±0,5% sávban → bracket trigger.
5. **State update**:
   - A `swing_positions.json`-ban a ticker `qty_remaining: 0` (full close esetén) vagy `qty_remaining /= 2` (TP1 partial esetén)
   - Append-elni egy új mezőt: `closed_at`, `close_price`, `close_reason` ("SL" / "TP1" / "TP2" / "OTHER")
   - Ha az archiválandó lista (closed positions) külön fájlban van (pl. `state/closed_positions.json`) → oda másolni
6. **Daily metrics update**:
   - A `state/daily_metrics/YYYY-MM-DD.json` `pnl.gross`, `pnl.net`, `pnl.cumulative` mezőit frissíteni
   - A `pnl.commission` mezőt frissíteni a `ib.executions().commission` alapján
   - Az `exits.{tp1,tp2,sl,loss_exit,trail,moc}` mezők megfelelő szám 1-gyel inkrementálni
   - A `trades.details` listához hozzáfűzni egy új trade-objektum (ticker, qty, entry_price, close_price, gross, net, reason)
7. **Cumulative_pnl update**:
   - A `scripts/paper_trading/logs/cumulative_pnl.json` `cumulative_pnl` mezőt frissíteni
   - A `daily_history[date]` entry-ben a `pnl`, `commission`, `trades`, `tp1_hits`/`sl_hits`/`tp2_hits` mezőket frissíteni
8. **Telegram alert** (P1):
   - "[SWING RECONCILE] Day N: detected M autonomous bracket triggers — {ticker1}: SL -$XXX, {ticker2}: TP1 +$YYY. State updated."

**Trigger frekvencia**: a `pt_monitor.py` 22:00 CEST EOD eval keret-jeben — minden trading day végén lekérdezi az IBKR-t és reconcile-elja.

### Rész 2 — Retroaktív Day 4 + Day 5 reconcile (egyszeri futás Day 6 reggel)

A Rész 1 logikája utólag is alkalmazható a Day 4 (2026-05-21) és Day 5 (2026-05-22) napokra. Egy egyszeri scriptet kell írni:

**Új script**: `scripts/admin/retroactive_reconcile_w21.py`

**Lépések**:
1. Lekérdezni az IBKR `ib.executions(execFilter=ExecutionFilter(time='20260521 00:00:00'))` (a Day 4 első time-pointtól) — VLO 16 SLD @ $244,61 19:19:54 CEST-et találja
2. Lekérdezni az IBKR `ib.executions(execFilter=ExecutionFilter(time='20260522 00:00:00'))` — ON 27 SLD @ $115,41 16:40:20 CEST-et találja
3. Update a `state/daily_metrics/2026-05-21.json`:
   - `pnl.gross: -222.97`
   - `pnl.commission: 4.09`
   - `pnl.net: -227.06`
   - `pnl.cumulative: -119.79` (= +112,31 − 5,04 + 0 − 227,06)
   - `exits.sl: 1`
   - `trades.details`: append {ticker: VLO, qty: 16, entry: 258.55, close: 244.61, reason: SL, gross: -222.97, net: -227.06}
   - `trades.worst`: {ticker: VLO, net: -227.06}
4. Update a `state/daily_metrics/2026-05-22.json`:
   - `pnl.gross: 161.19`
   - `pnl.commission: 2.07`
   - `pnl.net: 159.12`
   - `pnl.cumulative: 40.33` (= -119,79 + 159,12)
   - `exits.tp1: 1`
   - `trades.details`: append {ticker: ON, qty: 27, entry: 109.48, close: 115.41, reason: TP1, gross: 161.19, net: 159.12}
   - `trades.best`: {ticker: ON, net: 159.12}
5. Update a `scripts/paper_trading/logs/cumulative_pnl.json`:
   - `cumulative_pnl: 42.63`
   - `cumulative_pnl_pct: 0.043`
   - `daily_history[2026-05-21]`: `pnl: -227.06`, `commission: 4.09`, `trades: 1`, `filled: 1`, `sl_hits: 1`
   - `daily_history[2026-05-22]`: `pnl: 159.12`, `commission: 2.07`, `trades: 1`, `filled: 1`, `tp1_hits: 1`
6. Update a `state/swing_positions.json`:
   - VLO entry: `qty_remaining: 0`, `closed_at: "2026-05-21T17:19:54+00:00"`, `close_price: 244.61`, `close_reason: "SL"`
   - ON entry: `qty_remaining: 0`, `closed_at: "2026-05-22T14:40:20+00:00"`, `close_price: 115.41`, `close_reason: "TP1"`
   - VLO és ON entry-k mozgatása a `closed_positions.json`-ba (ha létezik a fájl), vagy `positions` listából való eltávolítás
7. Backup: `state/swing_positions.json.bak.pre_retroreconcile.2026-05-23` + `scripts/paper_trading/logs/cumulative_pnl.json.bak.pre_retroreconcile.2026-05-23`

**Futtatás**: `python scripts/admin/retroactive_reconcile_w21.py --dry-run` (audit, NEM ír state-et), majd `--apply` (tényleges update).

### Rész 3 — TP1/SL/TP2 hit counter fix (a daily_metrics + cumulative_pnl logging-ban általában)

A jelenlegi `daily_metrics.py` és `cumulative_pnl.py` (vagy a `pt_eod.py` aggregátor) **NEM** inkrementálja a `tp1_hits`/`sl_hits`/`tp2_hits` mezőket még akkor sem, ha az IFDS_SWING_*_TP1 order ref-fel logolt fill van. Pl. a Day 2-i EC TP1 fill (`IFDS_SWING_EC_TP1` order ref a `pt_submit_2026-05-19.log`-ban) MEGTÖRTÉNT, de a `cumulative_pnl.json daily_history[2026-05-19].tp1_hits: 0` és a `daily_metrics/2026-05-19.json exits.tp1: 0`.

**Új függvény** (vagy meglévő javítása): `daily_metrics.py::compute_exits_from_executions()`

**Lépések**:
1. Lekérdezni az IBKR-ből az aznapi `ib.executions()`-t
2. Minden SLD execution esetén:
   - Megnézni az `orderRef` mezőt
   - Ha `orderRef` tartalmazza `_TP1` substring-et → `exits.tp1 += 1`
   - Ha `orderRef` tartalmazza `_TP2` → `exits.tp2 += 1`
   - Ha `orderRef` tartalmazza `_SL` → `exits.sl += 1`
   - Ha `orderRef` tartalmazza `_TRAIL` → `exits.trail += 1`
   - Ha `orderRef` üres + a fill ár közelebb van egy bracket szinthez:
     - Ha fill_price közelebb a TP1 szinthez (planned vagy fill-alapú) → `exits.tp1 += 1`
     - Ha fill_price közelebb a SL szinthez → `exits.sl += 1`
     - Egyébként `exits.loss_exit += 1` vagy `exits.moc += 1`

**Plus a daily_metrics-be új mező**: `exits.detection_method` = `"order_ref"` / `"bracket_level_match"` / `"manual_close"`. Transzparenseggel jelzi, hogy a hit counter milyen forrásból származik.

---

## 3. Output / acceptance criteria

### 3.1 Retroaktív Day 4-5 reconcile (Rész 2)

- ✅ `state/daily_metrics/2026-05-21.json` `pnl.net: -227.06`, `exits.sl: 1`, `trades.details` nem üres
- ✅ `state/daily_metrics/2026-05-22.json` `pnl.net: 159.12`, `exits.tp1: 1`, `trades.details` nem üres
- ✅ `scripts/paper_trading/logs/cumulative_pnl.json` `cumulative_pnl: 42.63`
- ✅ `state/swing_positions.json` 8 open positions (NEM 10), VLO és ON kizárva
- ✅ Backup fájlok megléte: `*.bak.pre_retroreconcile.2026-05-23`

### 3.2 Új `pt_monitor.py::reconcile_state_from_ibkr` (Rész 1)

- ✅ Day 6 reggeli első futás során NEM talál divergence-t (a retroaktív reconcile után)
- ✅ Future trading napokon (Day 7+) az autonóm bracket trigger-eket detect-eli + state-et update-eli
- ✅ Telegram alert küldés bracket trigger detektálás esetén

### 3.3 TP/SL/TP2 hit counter fix (Rész 3)

- ✅ A retroaktív reconcile után `cumulative_pnl.json daily_history`-ban:
  - `2026-05-19.tp1_hits: 1` (EC Day 2)
  - `2026-05-21.sl_hits: 1` (VLO Day 4)
  - `2026-05-22.tp1_hits: 1` (ON Day 5)
- ✅ A `weekly_metrics.py` Day 6 reggel újrafuttatva **2/10 TP1 hit** és **1/10 SL hit** értékeket mutatja (NEM 0/3)

### 3.4 Tamás architektúra döntés (Rész 4)

- ⏳ Day 7-10 (kedd-péntek) ablakban Tamás döntése
- Mindkét opció implementációja **különálló task fájlokban** (egyik sem deploy-andó addig, amíg Tamás nem dönt)

---

## 4. Rollback plan

Ha a retroaktív reconcile (Rész 2) hibás eredményt ad:

1. **State rollback**: `cp state/swing_positions.json.bak.pre_retroreconcile.2026-05-23 state/swing_positions.json`
2. **Cumulative rollback**: `cp scripts/paper_trading/logs/cumulative_pnl.json.bak.pre_retroreconcile.2026-05-23 scripts/paper_trading/logs/cumulative_pnl.json`
3. **Daily metrics rollback**: a 2026-05-21 és 2026-05-22 json-okat **NEM kell** backup-olni a retroaktív reconcile előtt — ha hibás, kézzel törölni a `trades.details` listából a hozzáadott trade-objektumokat és `exits.sl`/`tp1` mezőket 0-ra állítani. (Mert eredetileg üres + 0 mezők voltak.)

**Plus a Rész 1 `pt_monitor.py::reconcile_state_from_ibkr` deploy-andó csak a Rész 2 sikeres futása után**, mert a Rész 1 function-ja a `swing_positions.json` Day 5 záró VLO+ON nyitottnak látott state-jét kombinálná az IBKR Day 6 záró 8-pozíciós state-jével, és **kétszer detektálná** a bracket trigger-eket.

---

## 5. Testing plan

### 5.1 Unit tesztek

- `tests/test_pt_monitor_reconcile.py`:
  - `test_reconcile_detects_full_close_when_ibkr_position_missing`
  - `test_reconcile_detects_partial_close_tp1`
  - `test_reconcile_assigns_correct_close_reason_from_bracket_levels`
  - `test_reconcile_updates_daily_metrics_with_realized_pnl`
  - `test_reconcile_updates_cumulative_pnl_with_hit_counters`
  - `test_reconcile_does_nothing_when_state_matches_ibkr`

### 5.2 Integration teszt

- `tests/test_pt_monitor_reconcile_e2e.py`:
  - Mock IBKR Positions: `[LBRT, MASI, EC, PFGC, CNC, WMB, DXCM, AMH]` (8 ticker, NEM VLO/ON)
  - Mock IBKR Executions Day 4-5: `[VLO SLD 16 @ 244.61, ON SLD 27 @ 115.41]`
  - Initial state: `swing_positions.json` 10 ticker (Day 5 záró állapot)
  - Expected post-reconcile state: 8 ticker, daily_metrics + cumulative_pnl-ben a tényleges P&L

### 5.3 Smoke teszt (Day 6 reggel)

- Lefuttatni a `retroactive_reconcile_w21.py --dry-run` scriptet → audit output
- Lefuttatni a `retroactive_reconcile_w21.py --apply` scriptet
- Verify-olni a `state/swing_positions.json` 8 ticker, `cumulative_pnl: 42.63`, `daily_history[2026-05-21].sl_hits: 1`, `daily_history[2026-05-22].tp1_hits: 1`
- Lefuttatni a `weekly_metrics.py` scriptet a `2026-W21.md` regenerálásához → `Net: $+40.43`, `Win days: 2/5`, `TP1 hits: 2/10`, `SL hits: 1/10`

---

## 6. Notes / context

- **Day 6 (hétfő 2026-05-25) USA Memorial Day ünnepnap** — nincs piaczárás. A pipeline NEM fut.
- **Day 7 (kedd 2026-05-26)** az első piaci nap a hétvége után — **ezelőtt deploy-andó** a retroaktív reconcile és a Rész 1 új `pt_monitor.py` reconcile_state logika
- A jelenlegi `swing_positions.json` Day 5 záró VLO és ON pozíciókat MÉG nyitottnak látja. **Ha Day 7 reggel a `submit_orders.py` futna a state-tudatos duplikáció-szűréssel**, akkor a VLO és ON ticker-eket "already has position or swing state" miatt skipping-elné, miközben **az IBKR-ben mindkettő zárva van**. **Ez NEM kritikus** (a TWS state alapján csak nem-entry, NEM duplikáció), de a Day 7-i Phase 4 univerzum 4-5 helyezettjeire a sector cap és max_concurrent számítások **téves baseline-ról** indulnak.
- **Architektúra-döntés (Tamás, 2026-05-25)**: α opció (hibrid status quo). A swing pivot HELYESEN mental-stop módban van (a kódbázis-elemzés megerősítette). NINCS szükség architektúra-váltásra, NINCS szükség design doc frissítésre. A CNC élő TWS bracket Tamás manuálisan cancellálta 08:26 CEST-kor.

---

**Becsült munka**: ~4-5 óra CC-ben (Rész 1 + 2 + 3, tesztekkel együtt). α opció (Tamás döntés 2026-05-25) miatt a korábbi Rész 4 (architektúra-döntés) elhagyva.

**Deadline**: 2026-05-26 (kedd) 14:00 CEST — az első piaci nap előtt
