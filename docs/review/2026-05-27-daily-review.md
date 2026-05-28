# IFDS Daily Review — 2026-05-27 (szerda, Day 8 Swing Pivot, W22 D2)

**Verzió**: swing pivot architektúra (Fázis 3 deploy 2026-05-18, Day 8/63)
**Day 8 net P&L (daily_metrics rögzített)**: **$0,00** ⚠️ **TÉVES — lásd §0 KRITIKUS FINDING**
**Day 8 valódi realized P&L (IBKR trades)**: **-$695,77** (7 exit)
**Day 8 valódi total mozgás (IBKR Net Liq)**: **-$428,77** (Net Liq $99 649 → $99 220)
**Cumulative (daily_metrics rögzített)**: **+$39,33** ⚠️ **TÉVES**
**Cumulative (valódi, IBKR Net Liq)**: **-$779,64** ($100k baseline-ról)
**Net Liquidation Day 8 záró (IBKR)**: **$99 220,36**
**Open positions**: **4** (AMH, EOG, AKAM, **JHG új**) — 7 exit Day 8-on (EC TP2 + 6 TIME_STOP)

**⚠️ KULCS Day 8 finding (KRITIKUS):**
- **A Day 8-i 7 exit -$695,77 realized P&L-je NINCS RÖGZÍTVE** a `cumulative_pnl.json`-ban és `daily_metrics.json`-ban (mindkettő Day 8 `pnl: 0`, `exits: mind 0`). A `04-risks` §0.10 **logging réteg (Rész 3)** hiánya — ami a Day 7 review-ban P1-re downgrade-eltem — **valójában P0 KRITIKUS**: a teljes Day 8 exit-hullám láthatatlan a hivatalos tracking számára. **Valódi vs hivatalos cumulative eltérés: $819** ($-779,64 IBKR Net Liq vs +$39,33 daily_metrics).
- **A TIME_STOP hullám lényegesen rosszabb a Day 7 becslésnél**: -$695,77 realized vs becsült -$362. A különbség az Energy szektor Day 8-i mélyülése — **LBRT -$418,66** és **WMB -$379,10** dominálják.
- **EC TP2 = a swing pivot ELSŐ TP2 exit-je**, de a fill a Day 8 market open MARKET SELL-en történt ($14,44-14,51), NEM a $14,65 TP2 limit-en. Realized +$231,87 (a reggeli gap-down -$60 a Day 7 mark-hoz képest).
- **A `days_held` calendar-bug (Day 7 review §5.6 P1) közvetlen megerősítése**: WMB days_held=5 = csak 2 trading nap, mégis TIME_STOP-olt — a legrosszabb pillanatban realizálta a -$379-et.
- **ÚJ Day 8 entry JHG (Janus Henderson, Financial Services)**: ATR $0,09 (**0,17% relatív** — a MASI Day 1 §8.1.1 floor-probléma megismétlése), 289 share, **$14 976 notional = 15% portfolio** koncentrált, S_j 88,5.
- **Második éles `_reconcile_state_from_ibkr` → SILENT OK** (4 state == 4 IBKR ticker).

---

## 0. ⚠️⚠️ KRITIKUS FINDING (P0) — A Day 8 realized P&L NINCS rögzítve

### 0.1 A probléma

A Day 8-on **7 exit** történt az IBKR-en (`get_account_trades` 2026-05-27 megerősíti), összesen **-$695,77 realized P&L**-lel. **Sem a `cumulative_pnl.json`, sem a `daily_metrics/2026-05-27.json` NEM rögzítette ezt.**

| Forrás | Day 8 P&L | Cumulative | Megjegyzés |
|--------|-----------|-----------|------------|
| `daily_metrics/2026-05-27.json` | **$0** (`pnl.gross: 0`) | **+$39,33** | exits.tp1/tp2/sl/moc mind 0 |
| `cumulative_pnl.json` (Day 8 entry) | **$0** (`pnl: 0`) | **+$39,33** | trades/filled/moc_exits mind 0 |
| **IBKR (kanonikus, `get_account_trades`)** | **-$695,77** | **-$656,44** (realized) | 7 valódi exit |
| **IBKR Net Liq (`get_account_summary`)** | -$428,77 | **-$779,64** | realized + unrealized M2M |

**A hivatalos tracking $819-cal felüljelez** ($-779,64 valódi vs +$39,33 hivatalos Net Liq alapon).

### 0.2 Root cause

A `close_positions.py` (`pt_close_2026-05-27.log` szerint a TP2 + 6 MOC exit-et szabályosan végrehajtotta IBKR-en) **frissíti a state-et** (10 → 4 pozíció ✓) **DE NEM ír a `cumulative_pnl.json`-ba és `daily_metrics.json`-ba**. A realized P&L tracking lánc megszakad az exit oldalon.

Ez a `04-risks` §0.10 **Rész 3 (TP1/SL/TP2 hit counter fix + daily_metrics auto-update)** hiányának közvetlen következménye. A `docs/tasks/2026-05-26-daily-metrics-auto-update-from-reconcile.md` task **MÉG NINCS deploy-olva** — csak a Rész 1 (`_reconcile_state_from_ibkr` monitoring, commit `5c8e79a`).

**Fontos megkülönböztetés a Day 7 review-tól**: a Day 7 review-ban a §0.10-et P0 → P1-re downgrade-eltem, azzal az indoklással hogy "a monitoring rétege deploy-olva, a logging anomalia csak retroaktív audit-trail-t érint, nem operatív kockázatot". **A Day 8 ezt MEGCÁFOLJA**: a logging réteg hiánya NEM csak audit-trail — **a teljes napi -$696 realized P&L eltűnt a hivatalos tracking-ből**, ami operatívan kritikus.

### 0.3 Miért rögzült a Day 2-5, de a Day 8 nem?

A `cumulative_pnl.json daily_history` szerint a Day 2-5 exit-ek BE vannak rögzítve:
- 5/19 (Day 2): +$112,31 (EC TP1)
- 5/21 (Day 4): -$227,06 (VLO SL)
- 5/22 (Day 5): +$159,12 (ON TP1)

Ezeket a **`04-risks` §0.10 Rész 2 (retroaktív reconcile script, egyszeri futás 2026-05-25)** rögzítette utólag. A Day 8-i exit-ek **MOST történtek**, és mivel a Rész 3 (folyamatos auto-update) nincs deploy-olva, **nem rögzültek**. Minden jövőbeli TIME_STOP/TP2/SL exit ugyanígy láthatatlan marad, amíg a Rész 3 nem áll.

### 0.4 Hatás és sürgősség

- **A `cumulative_pnl.json` és `daily_metrics.json` jelenleg MEGBÍZHATATLAN** a valódi teljesítmény szempontjából
- **A Day 21 checkpoint (-$1 500 küszöb) értékelése lehetetlen** pontos P&L tracking nélkül — jelenleg a valódi -$779,64 a hivatalos +$39,33 helyett
- **Az IBKR direkt kapcsolat ideiglenesen betölti a gap-et** (a daily review-k mostantól IBKR Net Liq + trades alapon számolnak), de a **persistent file tracking helyreállítása kritikus**

### 0.5 Javasolt akció (P0 escalation)

1. **A `04-risks` §0.10 státusz visszaállítása P1 → P0** (a logging réteg kritikussága a Day 8 evidence alapján)
2. **A `2026-05-26-daily-metrics-auto-update-from-reconcile.md` (Rész 3) AZONNALI deploy** — a `close_positions.py`-be P&L tracking write a TP2/MOC/SL exit-ek után
3. **Retroaktív Day 8 reconcile**: a -$695,77 + Day 8 commission rögzítése a `cumulative_pnl.json` 2026-05-27 entry-jébe + a `daily_metrics.json` `pnl.gross`, `exits.tp2: 1`, `exits.moc: 6` mezőkbe
4. **A Day 1-8 teljes P&L canonical rekonstrukció** az IBKR `get_account_trades(DAYS_30)` alapján — a cumulative_pnl.json teljes újraszámolása a valódi IBKR realized P&L-lel

**Owner**: Dev chat (P0, azonnali) + Tamás (deploy jóváhagyás)

**Ezt a finding-ot a `04-risks` doc tetejére P0 escalation entry-ként javaslom — Tamás jóváhagyásával írom meg (a 04-risks a Dev chat ownership-je, de a P0 escalation path engedélyezi a Log Review chat-nek).**

---

## 1. Day 8 Trades (IBKR `get_account_trades` 2026-05-27)

### 1.1 Exits (7 ticker) — EC TP2 + 6 TIME_STOP

| Idő (CEST) | Ticker | Típus | Qty | Fill | Realized P&L | Sektor |
|-----------|--------|-------|-----|------|--------------|--------|
| 15:30:07 | EC | TP2 (MKT open) | 100 | $14,51 | **+$142,06** | Energy |
| 15:30:13 | EC | TP2 (MKT open) | 66 | $14,44 | **+$89,80** | Energy |
| 21:59:30 | MASI | TIME_STOP MOC | 84 | $178,73 | **+$16,99** | Healthcare |
| 21:59:31 | LBRT | TIME_STOP MOC | 127 | $30,05 | **-$418,66** ⚠️ | Energy |
| 21:59:31 | WMB | TIME_STOP MOC | 94 | $74,34 | **-$379,10** ⚠️ | Energy |
| 21:59:31 | CNC | TIME_STOP MOC | 95 | $58,77 | **-$48,68** | Healthcare |
| 21:59:32 | DXCM | TIME_STOP MOC | 62 | $70,25 | **-$100,06** | Healthcare |
| 21:59:42 | PFGC | TIME_STOP MOC | 57 | $96,62 | **+$1,87** | Consumer Def. |
| **Day 8 realized total** | | | | | **-$695,77** | |

**EC TP2 részletes**: a `pt_close_2026-05-27.log` 15:30:06 "EC: TP2 → SELL 166 (MKT)" — a Day 7 EOD eval `next_action: TP2` flag-et **15:30 CEST market open MARKET SELL**-ként hajtotta végre, NEM a $14,65 TP2 limit-en. A Day 8 reggel gap-down nyitott (Day 7 záró mark $14,84 → Day 8 open ~$14,44-14,51), így a realized +$231,87 (a Day 7-i unrealized +$292-höz képest **-$60 a reggeli gap miatt**).

**EC teljes hold eredmény** (332 share entry $13,08 Day 1):
- TP1 (Day 2, 5/19): 166 share → +$112,31
- TP2 (Day 8, 5/27): 166 share → +$231,87
- **EC összesen: +$344,18** ⭐ — a swing pivot **legjobb teljes pozíció-eredménye** eddig

### 1.2 ⚠️ A TIME_STOP hullám realized-je sokkal rosszabb a Day 7 becslésnél

| Ticker | Day 7 becslés | Day 8 valódi | Delta | Ok |
|--------|---------------|--------------|-------|-----|
| LBRT | -$178,80 | **-$418,66** | -$239,86 | Energy Day 8 további esés ($31,93 → $30,05) |
| WMB | -$180,54 | **-$379,10** | -$198,56 | Energy Day 8 további esés ($76,44 → $74,34) |
| DXCM | +$5,82 | -$100,06 | -$105,88 | Healthcare gyengült ($71,94 → $70,25) |
| CNC | -$161,55 | -$48,68 | +$112,87 | Recovery ($57,57 → $58,77) |
| MASI | +$13,28 | +$16,99 | +$3,71 | ~stabil |
| PFGC | -$152,43 | +$1,87 | +$154,30 | Recovery ($93,89 → $96,62) |
| EC TP2 | +$260--292 | +$231,87 | -$30--60 | Reggeli gap-down |
| **Total** | **~-$362** | **-$695,77** | **-$333,77** | |

A Day 7 becslés a Day 7 záró mark-okat használta. A Day 8 intraday mozgás (különösen az Energy szektor mélyülése) **majdnem megduplázta** a realizált veszteséget. **LBRT és WMB (mindkettő Energy) együtt -$797,76** — az Energy szektor Day 8-i gyengesége dominálta a napot.

### 1.3 Új entry Day 8: JHG (Janus Henderson, Financial Services)

| Paraméter | Érték |
|-----------|-------|
| Idő | 15:31:07 CEST (2 fill: 200 NYSE + 89 IEX) |
| Planned entry | $51,84 |
| **IBKR fill** | **$51,82** (mindkét fill, -0,04% slippage) |
| Qty | 289 share |
| Notional | **$14 975,98 (15,0% portfolio)** ⚠️ |
| ATR | **$0,09 (0,17% relatív!)** ⚠️⚠️ |
| Stop level | $51,66 (**-0,35% távolság**) |
| TP1 level | $51,97 (**+0,25%**) |
| TP2 level | $52,11 (**+0,52%**) |
| S_j | **88,5** (legmagasabb a Day 8 univerzumban) |
| Sektor | **Financial Services** (új szektor) |

**⚠️⚠️ JHG = a MASI Day 1 §8.1.1 floor-probléma MEGISMÉTLÉSE**: ATR 0,17% (MASI Day 1 0,165% volt). A swing TP/SL sáv (±0,25-0,52%) **kisebb mint a tipikus napi noise** (VIX 16,92 → ~1,06% expected daily move). A pozíció strukturálisan **fals trigger-érzékeny**: a JHG TP1 ($51,97) vagy stop ($51,66) **bármelyik nap random noise-on kiüthet**. Ráadásul az alacsony ATR a sizing formulán keresztül **óriási qty-t** (289 share) és **koncentrált 15% notional-t** generál.

**Az `04-risks` §8.1.1 ATR_pct floor (`swing_atr_pct_floor: 0.005`) MÉG NINCS deploy-olva** — ezért került be a JHG (0,17% ATR < 0,5% floor). **Day 9 megfigyelés kritikus**: a JHG várhatóan gyors TP1/stop triggert vagy fals exit-et fog produkálni.

---

## 2. EOD State (22:00 CEST) — 4 pozíció, 1 exit flag Day 9-re

`pt_monitor_2026-05-27.log` 22:00:05:
```
[SWING EOD] Evaluated 4 positions — 1 exit flags set
  AMH: TIME_STOP
```

### 2.1 A 4 nyitott pozíció Day 8 záró

| Ticker | Entry $ | Qty | days_held | Unrealized (IBKR) | next_action | Sektor |
|--------|---------|-----|-----------|-------------------|-------------|--------|
| AMH | 32,11 | 249 | **5** | **-$33,98** | **TIME_STOP** (Day 9 21:40) | Real Estate |
| EOG | 141,22 | 44 | 1 | **-$238,60** ⚠️ | HOLD | Energy |
| AKAM | 147,23 | 17 | 1 | -$28,37 | HOLD | Technology |
| JHG | 51,84 | 289 | 0 | -$14,28 | HOLD | Financial Services |
| **Total unrealized** | | | | **-$315,23** | | |

### 2.2 ⚠️ EOG romlik — -$238,60 unrealized (-3,86%)

A stale context bug Day 7 EOG entry-je ($141,22) Day 8 záróra $135,00-ra esett (**-$238,60 unrealized**, IBKR market price). A stop $133,42 — a Day 8 záró ár ($135,00) **csak $1,58-cal (1,17%) van a mental stop felett**. Ha Day 9-en eléri a stop-ot, az **-$343 realized** lesz. Az EOG a stale context bug "öröksége", ami rosszul öregszik.

### 2.3 Sector distribution Day 8 záró

| Sektor | Notional | % portfolio |
|--------|----------|-------------|
| Financial Services (JHG) | $14 982 | **14,98%** |
| Real Estate (AMH) | $7 995 | 8,00% |
| Energy (EOG) | $6 214 | 6,21% |
| Technology (AKAM) | $2 503 | 2,50% |
| **Total** | $31 694 | **31,69%** |

Az Energy szektor a Day 7-i 4 ticker / 19,94%-ról **1 ticker / 6,21%-ra** zsugorodott (LBRT, EC, WMB exit). A 30% cap bőven betartva. De a JHG single-position **15% koncentráció** figyelő pont.

---

## 3. Pipeline Log Review

### 3.1 `pt_close_2026-05-27.log` — 2 fázisú exit végrehajtás ⭐

```
15:30:06 [INFO]   EC: TP2 → SELL 166 (MKT)
15:30:06 [INFO] [SWING 15:30 close] Submitted 1 exits | open: 9
21:40:06 [INFO]   LBRT: TIME_STOP → MOC SELL 127
21:40:08 [INFO]   MASI: TIME_STOP → MOC SELL 84
21:40:09 [INFO]   PFGC: TIME_STOP → MOC SELL 57
21:40:11 [INFO]   CNC: TIME_STOP → MOC SELL 95
21:40:12 [INFO]   WMB: TIME_STOP → MOC SELL 94
21:40:14 [INFO]   DXCM: TIME_STOP → MOC SELL 62
21:40:14 [INFO] [SWING 21:40 close] MOC submitted 6 | open: 4
```

**A close mechanika működik** — a TP2 a 15:30 market open-on (MKT), a 6 TIME_STOP a 21:40 MOC-on. **DE a P&L tracking NEM követi** (lásd §0). A `close_positions.py` az IBKR SELL-eket és a state update-et elvégzi, de a `cumulative_pnl.json` write hiányzik.

### 3.2 `pt_submit_2026-05-27.log` — 1 új entry (JHG)

```
15:31:01 Reading: execution_plan_run_20260527_123001_e155c0.csv
15:31:06 Existing IBKR positions/orders: {'EOG','AKAM','AMH','PFGC','WMB','LBRT','CNC','MASI','DXCM'}
15:31:08   JHG: MKT BUY 289 @ ~$51.84 | stop $51.66 | TP1 $51.97 | TP2 $52.11
15:31:08   Skipping AKAM: already has position or swing state
15:31:08 [SWING] Submitted: 1 tickers | State: state/swing_positions.json (10 open)
```

⚠️ Megfigyelés: a submit log "(10 open)" szöveget ír, de valójában Day 8 záróra **4 pozíció** maradt (a 7 exit a 21:40 close-on futott, a submit 15:31-kor). A "10 open" a submit pillanatában (a 9 régi + JHG, az exit-ek előtt) volt — **NEM hiba, csak timing**. A friss context (Day 7 19:14-19:18 manuális Phase 1-3) most helyesen 1 entry-t (JHG) választott — **a stale context bug Day 8-on már NEM jelentkezett** (Tamás reggeli fix + manuális Phase 1-3 megerősítve).

### 3.3 `pt_eod_2026-05-27.log` — "Still 4 open positions" + `[Day 7/63]`

```
22:05:05 Trades: 0
22:05:05 P&L today: $+0.00         ← ⚠️ TÉVES (lásd §0)
22:05:05 Cumulative: $+39.33 (+0.04%) [Day 7/63]   ← ⚠️ TÉVES
22:05:05 Still 4 open positions!
```

A `[Day 7/63]` itt a `daily_metrics::day_number: 7` (a trading_days: 7 alapján — 5/18,19,20,21,22,26,27). A STATUS.md "Day 8" konvenció. **Doc-szintű inkonzisztencia folytatás** (Day 7 review §3.3).

### 3.4 `pt_monitor_2026-05-27.log` + `pt_reconcile_2026-05-27.log` — silent OK

```
pt_reconcile: State tickers: ['AKAM','AMH','EOG','JHG']
              IBKR tickers:  ['AKAM','AMH','EOG','JHG']
              Reconciliation OK — state and IBKR match (silent exit).
```

**Második éles `_reconcile_state_from_ibkr` futás → SILENT OK.** A 7 exit (TP2 + 6 MOC) mind a swing rendszer által vezérelt — NINCS autonóm bracket trigger. A state ≡ IBKR (4 == 4). **A mental-stop architektúra integritása 2/2 napon megerősítve.**

### 3.5 `cumulative_pnl.json` — Day 8 entry mind 0 ⚠️

Lásd §0. A Day 8 `pnl: 0, trades: 0, tp2_hits: 0, moc_exits: 0` — **mind téves**, a 7 exit (-$695,77, 1 TP2 + 6 MOC) hiányzik.

---

## 4. UW Shadow Log Day 8 — 18 ticker (univerzum kétszereződés)

`state/uw_shadow/2026-05-27.json` (`daily_metrics.uw_shadow_summary`):

| Mutató | Day 7 | Day 8 | Delta |
|--------|-------|-------|-------|
| Tickers logged | 9 | **18** | +9 (friss context, nagyobb univerzum) |
| Avg dp_pct | 2,58% | 3,74% | +1,16pp |
| would_have_been_penalty_count | 1 | **3** | +2 |
| GEX regime | 5 pos / 3 hv / 1 unk | **10 pos / 6 hv / 2 unk** | univerzum ×2 |
| m_gex_avg | 0,8667 | 0,8667 | változatlan |

A **18 ticker** (vs Day 7 9) a friss Phase 1-3 context következménye — a stale context Day 7-en szűkebb univerzumot adott. **A Day 8-i univerzum normalizálódott**. A `swing_score_distribution.qualifying_threshold_50: 18` megerősíti: 18 ticker ütötte át az 50-es swing threshold-ot, ebből 1 (JHG, S_j 88,5) lett kiválasztva entry-re.

**Megfigyelés**: JHG S_j 88,5 a legmagasabb — de extrém alacsony ATR-rel (0,17%). A swing scoring (PCR + OTM-inverse) **magas pontszámot adott egy strukturálisan problémás (alacsony volatilitású) ticker-nek**. Ez a "magas pontszám paradoxon" (`04-risks` §5.1) egy új megnyilvánulása lehet a swing kontextusban — figyelő pont.

---

## 5. Anomáliák / megfigyelések (frissített állapotok)

### 5.1 §0.10 (state ≡ IBKR + logging) — ⚠️ P1 → **P0 visszaminősítés** (Day 8 evidence)

Lásd §0. A monitoring réteg (Rész 1) 2/2 napon silent OK. **De a logging réteg (Rész 3) hiánya a Day 8-on -$695,77 realized P&L-t tüntetett el a tracking-ből.** Visszaminősítés P0-ra.

### 5.2 §5.6 (Day 7 review — days_held calendar-bug) — ⚠️ KÖZVETLEN MEGERŐSÍTÉS

A Day 8-i TIME_STOP hullám a calendar-day bug **valódi költségét** demonstrálta:
- **WMB**: entry 5/21, days_held=5 (calendar) = **2 trading nap** (5/21, 5/22, 5/27 — de a 5/27 az exit nap). Mégis TIME_STOP-olt, realizálva **-$379,10**-et az Energy szektor mélypontján.
- **DXCM**: entry 5/21, ugyanaz, -$100,06.
- **CNC**: entry 5/20, days_held=6 (calendar) = 3 trading nap, -$48,68.

Ha a `days_held` trading-day alapú lett volna, WMB/DXCM (2 trading nap) **NEM exit-elt volna Day 8-on** — kapott volna 3 további trading napot. A becsült megtakarítás: WMB/DXCM Day 8-i együttes -$479,16 **nem realizálódott volna** (legalábbis nem Day 8-on, az Energy mélyponton).

**Ez a finding most P1 → magas prioritású P1** (a Day 8 -$479 közvetlen kár demonstrálja a hatást). Javaslat változatlan: `swing_positions.py` trading-day alapú `days_held` (`utils/calendar.py::trading_days_between()`).

### 5.3 §8.1.1 (ATR_pct floor — MASI Day 1) — ⚠️ JHG MEGISMÉTLÉS

A JHG (ATR 0,17%) a MASI Day 1 (0,165%) floor-problémát megismételte. **A `swing_atr_pct_floor: 0.005` deploy elmaradása** miatt a JHG bekerült. **P1 prioritás emelés javasolt** — két instancia 8 napon belül (MASI Day 1, JHG Day 8), és a JHG ráadásul koncentrált 15% pozíció.

### 5.4 daily_metrics.py logging anomáliák — folytatólagos + súlyosbodó

A Day 7 review §5.5 4 anomáliája Day 8-on is fennáll, PLUSZ a §0 P&L tracking gap. Konszolidált lista:

1. `positions.opened: 0` vs `swing_state.new_entries_today: 1` (JHG)
2. `positions.threshold: 85, max_allowed: 5` — legacy intraday értékek (swing: 50 / 12)
3. `execution.slippage_per_ticker: {}` — JHG slippage hiányzik (IBKR: -0,04%)
4. `exits_today: {TIME_STOP: 1}` — csak az AMH Day 9-flag-et számolja, NEM a Day 8-i 7 tényleges exit-et ⚠️
5. **`pnl.gross/net: 0` + `exits.tp2/moc: 0`** — a Day 8 -$695,77 realized teljes hiánya (§0, P0)

### 5.5 §0.2 (Error 10349 TIF) / §0.5 (retry storm) — ✅ 4/4 nap stabil

Day 4, 5, 7, 8 mind kedvező. **§0.2 P0 → WITHDRAWN javasolt** (4 nap stabil). **§0.5 P0 → P2 megerősítve**.

### 5.6 ⚠️ ÚJ megfigyelés — a swing pivot ELSŐ teljes kohorsz-eredménye negatív

A Day 1-5 entries (most mind lezárult, kivéve AMH):

| Ticker | Entry nap | Exit nap | Realized | Hold (trading nap) |
|--------|-----------|----------|----------|--------------------|
| EC | Day 1 | Day 2 TP1 + Day 8 TP2 | **+$344,18** | 1 / 5 |
| LBRT | Day 1 | Day 8 TIME_STOP | **-$418,66** | 5 |
| MASI | Day 1 | Day 8 TIME_STOP | +$16,99 | 5 |
| PFGC | Day 2 | Day 8 TIME_STOP | +$1,87 | 4 |
| VLO | Day 3 | Day 4 SL | -$227,06 | 1 |
| ON | Day 3 | Day 5 TP1 | +$159,12 | 2 |
| CNC | Day 3 | Day 8 TIME_STOP | -$48,68 | 3 |
| WMB | Day 4 | Day 8 TIME_STOP | -$379,10 | 2 |
| DXCM | Day 4 | Day 8 TIME_STOP | -$100,06 | 2 |
| **Closed total** | | | **-$651,40** | |

A swing pivot első ~8 napos closed-kohorsz **-$651,40 realized**. A két nyertes (EC +$344, ON +$159) NEM ellensúlyozza a három nagy vesztest (LBRT -$419, WMB -$379, VLO -$227). 

**Kontextus / mérséklő tényezők** (miért NEM pánikolunk 8 nap után):
- **n=9 closed, kis minta** — statisztikai következtetés értelmetlen
- **A days_held calendar-bug** korai TIME_STOP-okat erőltetett (WMB/DXCM 2 trading nap) — a swing edge-nek nem volt ideje érvényesülni
- **A stale context bug** (Day 7 EOG/AKAM) + **az ATR floor hiánya** (MASI, JHG) torzít
- **Memorial Day** + **Energy szektor Day 8-i gyengesége** egyszeri tényezők
- A swing pivot **kvantitatív tézise** (mathematical doc §5.2: $h=5$ trading day = 5× mutual information) **trading-day hold-ot feltételez**, NEM a jelenlegi calendar-day-t. A jelenlegi rendszer **NEM a tervezett swing-et futtatja** a days_held bug miatt.

**Stratégiai következtetés**: a days_held bug (§5.2) javítása **a swing pivot tézis tisztességes teszteléséhez elengedhetetlen**. A jelenlegi -$651 closed eredmény egy **bug-torzított, nem-reprezentatív** minta.

---

## 6. Day 9 (csütörtök, 2026-05-28) outlook

### 6.1 Tervezett exit
- **AMH TIME_STOP** Day 9 21:40 MOC (days_held=5 calendar, = 4 trading nap). Unrealized -$33,98 → várt ~-$34 realized.

### 6.2 Figyelő pozíciók
- **EOG** (-$238,60 unrealized, stop $133,42 közelében $135,00) — ha Day 9-en eléri a stop-ot, -$343 realized. **Kritikus megfigyelés.**
- **JHG** (ATR 0,17%, ±0,3-0,5% TP/SL sáv) — várhatóan gyors TP1/stop trigger vagy fals exit. **A floor-bug első éles tesztje.**
- **AKAM** (ATR 6,78%) — még days_held=1, várhatóan stabil.

### 6.3 Várt új entries Day 9
A friss Phase 1-3 context (Day 8 cron) alapján 1-3 új entry várt. Megfigyelendő szektor + ATR (a floor-bug miatt).

### 6.4 Day 9 prioritások a Log Review chat-nek
1. **P0 §0 tracking gap** — deploy-olt-e a Dev chat a Rész 3-at? A Day 9 exit-ek (AMH + esetleg EOG) rögzülnek-e a cumulative_pnl.json-ba?
2. **EOG stop közelség** — IBKR `get_price_snapshot` real-time + `get_account_positions` unrealized
3. **JHG floor-bug viselkedés** — TP1/stop trigger?
4. **Harmadik éles `_reconcile_state_from_ibkr`** — silent OK?
5. **Valódi cumulative tracking** — az IBKR Net Liq alapján Day 9 záró (a hivatalos +$39,33 helyett)

---

## 7. Files referenced (Day 8)

- `state/swing_positions.json` — 4 pozíció, last_updated 2026-05-27T20:00:05Z
- `state/daily_metrics/2026-05-27.json` — ⚠️ Day 8 pnl 0, exits mind 0 (TÉVES, §0)
- `scripts/paper_trading/logs/cumulative_pnl.json` — ⚠️ Day 8 entry mind 0 (TÉVES, §0)
- `logs/pt_close_2026-05-27.log` — **7 exit (TP2 15:30 + 6 MOC 21:40)** ⭐
- `logs/pt_submit_2026-05-27.log` — 1 entry (JHG)
- `logs/pt_monitor_2026-05-27.log` — 4 pozíció EOD eval, 1 flag (AMH)
- `logs/pt_reconcile_2026-05-27.log` — **SILENT OK (2. éles futás)** ⭐
- `logs/pt_eod_2026-05-27.log` — ⚠️ "P&L today $+0.00" (TÉVES)
- `state/uw_shadow/2026-05-27.json` — 18 ticker, m_gex 0,8667
- **IBKR direkt API** (kanonikus P&L forrás a §0 gap miatt):
  - `get_account_summary` → Net Liq **$99 220,36** (valódi cumulative **-$779,64**)
  - `get_account_positions` → 4 pozíció, unrealized -$315,23
  - `get_account_trades(DAYS_7)` → **7 Day 8 exit, -$695,77 realized** ⭐

---

## 8. ⭐ Strukturális finding-ek összefoglaló

### 8.1 P0 — Day 8 realized P&L tracking gap (§0)
A legkritikusabb finding eddig a swing pivot alatt. A `close_positions.py` exit-jei (TP2/MOC/SL) NEM frissítik a `cumulative_pnl.json`/`daily_metrics.json`-t. A Day 8 -$695,77 realized eltűnt. **$819 eltérés** a valódi (IBKR Net Liq -$779,64) és hivatalos (+$39,33) cumulative között. **A `2026-05-26-daily-metrics-auto-update-from-reconcile.md` Rész 3 azonnali deploy szükséges.**

### 8.2 P1 (magas) — days_held calendar-bug valódi költsége (§5.2)
A Day 8 TIME_STOP hullám demonstrálta: WMB/DXCM 2 trading nap után exit-elt (calendar=5), -$479 az Energy mélyponton. A swing pivot tézis (trading-day hold) tisztességes teszteléséhez a fix elengedhetetlen.

### 8.3 P1 — ATR_pct floor hiánya (§5.3)
JHG (0,17% ATR) megismételte a MASI Day 1 problémát + koncentrált 15% pozíció. A `swing_atr_pct_floor: 0.005` deploy javasolt.

### 8.4 Pozitív: mental-stop architektúra + reconcile 2/2 silent OK
A `_reconcile_state_from_ibkr` második éles futása ismét tiszta. A 7 exit mind swing-vezérelt, NINCS autonóm bracket. EC TP2 = a swing pivot első teljes TP1→TP2 ciklus-záró (+$344,18 total). A mechanika (close logika, exit-flagek) **működik** — csak a P&L tracking write hiányzik (§0).

### 8.5 IBKR direkt MCP kapcsolat — most kritikus szerep
A §0 tracking gap miatt az IBKR direkt kapcsolat **NEM csak kényelmi eszköz, hanem a daily review egyetlen megbízható P&L forrása** jelenleg. A `get_account_summary` (Net Liq) + `get_account_trades` (realized) pótolja a hiányzó file tracking-et, amíg a Rész 3 nem áll. **Operating environment doc frissítés** továbbra is javasolt (Day 7 review §8.5).

---

## State (Day 8 — W22 D2, swing pivot Day 8/63)

**Architektúra**: swing pivot Fázis 3 deploy DAY 8. Mental-stop + reconcile 2/2 silent OK. **DE a P&L tracking lánc megszakadt az exit oldalon (P0, §0).**

**Live**: 4 open positions (AMH TIME_STOP flag Day 9, EOG -$239 unrealized, AKAM, JHG új 15% koncentrált).

**Cumulative (HIVATALOS, téves)**: +$39,33. **Cumulative (VALÓDI, IBKR Net Liq)**: **-$779,64**.

**Day 8 realized (IBKR)**: **-$695,77** (EC TP2 +$232, 6 TIME_STOP -$928). **Day 8 commission**: ~$9,47.

**Net Liq (IBKR)**: **$99 220,36** ($-780 a baseline-ról).

**Excess return Day 8**: SPY -0,02% (flat nap), portfolio realized -0,70% (IBKR Net Liq M2M -0,43%), **valódi excess ~-0,41% -- -0,68% vs SPY**.

**Aktív P0/P1 (frissített):**
- **§0 / §0.10 ÚJ P0** — Day 8 realized P&L tracking gap (logging Rész 3 deploy KRITIKUS)
- **§5.2 P1 (magas)** — days_held calendar-bug ($479 Day 8 kár demonstrálva)
- **§5.3 P1** — ATR_pct floor hiánya (JHG = 2. instancia MASI után)
- **§5.4 P1** — daily_metrics 5 logging anomalia (P&L tracking is)
- **§0.2 P0 → WITHDRAWN** (Error 10349, 4/4 nap stabil)
- **§0.5 P2** (retry storm, stabil)
- **§5.6 megfigyelés** — első closed kohorsz -$651 (bug-torzított, kis minta)

**P0 ESCALATION**: a §0 tracking gap-et a `04-risks` doc tetejére P0 entry-ként javaslom — **Tamás jóváhagyását kérem** (a doc Dev chat ownership-je; az escalation path engedélyezi a Log Review chat-nek).

**A Day 8 napi karakter egy mondatban**: A swing pivot **első teljes exit-napja** — 7 pozíció zárult (EC TP2 = az első TP1→TP2 teljes ciklus +$344, és 6 TIME_STOP, köztük LBRT -$419 + WMB -$379 az Energy szektor mélypontján), **-$695,77 realized**, ami a valódi cumulative-t **-$779,64-ra** viszi (IBKR Net Liq) — **DE a `cumulative_pnl.json`/`daily_metrics` ezt NEM rögzítette (P0 tracking gap, $819 eltérés)**, miközben a `days_held` calendar-bug a TIME_STOP-okat 2-3 trading nap után erőltette ki az Energy mélyponton (a swing pivot tézis trading-day hold-ot feltételez), a JHG entry pedig 0,17% ATR-rel megismételte a MASI floor-problémát koncentrált 15% pozícióban — a **mental-stop architektúra és reconcile 2/2 silent OK** marad a stabil pont, és az **IBKR direkt kapcsolat** most a tracking gap egyetlen megbízható ellensúlya.

---

**A Day 8 review vége.** A Day 9 fókusz: P0 tracking gap deploy-status + EOG stop-közelség + JHG floor-bug első éles teszt + valódi IBKR-alapú cumulative tracking.
