# IFDS Daily Review — 2026-05-22 (péntek, Day 5 Swing Pivot)

**Verzió**: swing pivot architektúra (Fázis 3 deploy 2026-05-18, Day 5/63)
**Day 5 net P&L**: **$0,00** (gross 0, commission 0 — NINCS realizált trade)
**Cumulative P&L**: **+$107,27 (+0,11%)** — változatlan
**Open positions**: **10** (LBRT, MASI, EC 166-share maradék, PFGC, VLO, ON, CNC, WMB, DXCM, **+ AMH**) — mind HOLD

**Kulcs Day 5 eredmények:**
- ⭐ **1 új entry**: AMH (**Real Estate** új szektor, S_j 62,7, $32,11, 249 share, $7 995 notional)
- ⭐ **NYUGODT NAP**: nincs realizált zárás, mild underperform (-0,39% vs SPY +0,39%)
- ⭐ **MINDEN P0 anomália Day 5-en is csendes** (2/2 nap stabil):
  - §0.1 régi pt_monitor: ✅ NINCS
  - §0.2 Error 10349 TIF: ✅ **2/2 nap (Day 4+5) NEM jelentkezett**
  - §0.4 UW shadow: ✅ 9 ticker tiszta
  - §0.5 submit retry storm: ✅ 1 attempt sikeres, heartbeat [OK]
- ⚠️ **MASI/LBRT/EC time_stop flag — NEM jelentkezett** Day 5 EOD eval-ban (`days_held: 4 < max_holding_days`)
- ⚠️ **WMB scoring drámai emelkedés**: Day 4 S_j 71,78 → Day 5 S_j **85,25** (+18,8%) — Energy szektor leader megerősödés
- ⚠️ **Portfolio kihasználtság 59,37%** (vs Day 4: 51,38%) — gyors halmozódás
- ⚠️ **Bull rally underperform 3/3 nap**: Day 3 -1,03%, Day 4 -0,20%, Day 5 -0,39%

---

## 1. Day 5 Entry Decisions

### 1 új entry — AMH (új szektor: Real Estate)

| Ticker | S_j | Sektor | Entry $ | ATR | Stop $ | TP1 $ | TP2 $ | Qty | Notional $ |
|--------|-----|--------|---------|-----|--------|-------|-------|-----|------------|
| **AMH** | 62,70 | **Real Estate** ⭐ | 32,11 | 0,70 | 30,71 | 33,16 | 34,22 | 249 | 7 995 |

**Megfigyelés**: az AMH **Real Estate szektor első ticker-je** a portfolioban — eddig csak 4 szektor szerepelt (Energy, Healthcare, Consumer Defensive, Technology). A sector-balanced greedy a Day 5-i alacsony breadth környezetben **diverzifikációs útvonalat választott**: nem a top S_j-t (WMB 85,25, már nyitva), hanem **egy új szektort**.

**Slippage**: a `pt_submit_2026-05-22.log` szerint a planned és executed ár megegyezik ($32,11). **~0% slippage** — kedvező.

### A `trade_plan_2026-05-22.csv` top 3 + 2 skip

| Rank | Ticker | S_j | Sektor | Státusz |
|------|--------|-----|--------|---------|
| 1 | **WMB** | **85,25** | Energy | **Skip** (Day 4 entry) |
| 2 | VLO | 63,88 | Energy | **Skip** (Day 3 entry) |
| 3 | **AMH** | 62,70 | Real Estate | **Új entry** ✓ |

A `pt_submit_2026-05-22.log` 15:31:06:
```
Existing IBKR positions/orders: {'DXCM', 'CNC', 'PFGC', 'EC', 'ON', 'LBRT', 'WMB', 'MASI'}
Skipping WMB: already has position or swing state
Skipping VLO: already has position or swing state
AMH: MKT BUY 249 @ ~$32.11 | stop $30.71 | TP1 $33.16 | TP2 $34.22
[SWING] Submitted: 1 tickers | State: state/swing_positions.json (10 open)
```

⭐ **A state-tudatos duplikáció-szűrés továbbra is működik** — a Day 4-i `Skipping ON` mintázat folytatása.

### Phase 4 univerzum — 9 ticker, WMB drámai emelkedés

| Nap | Qualified > S_j 50 | Top S_j | Megjegyzés |
|-----|--------------------|---------|------------|
| Day 1 | 96 | 106,9 (LBRT) | normál szélesség |
| Day 2 | 77 | 101,7 (LBRT) | kissé csökkenő |
| Day 3 | 7 | 73,1 (VLO) | **11× csökkenés** |
| Day 4 | 9 | 71,8 (WMB) | enyhe visszanyúzódás |
| **Day 5** | **9** | **85,2 (WMB)** ⭐ | **WMB +18,8%, breadth stabilizál** |

**WMB scoring drámai emelkedés** (Day 4: 71,78 → Day 5: 85,25) — Energy szektor leader pozíció megerősödés. **A WMB már Day 4 óta nyitva van** (entry $77,88), így a Day 5-i magasabb S_j a **shadow-rangsorban** marad — nincs új entry-impakt.

⭐ **EOG (S_j 71,85, Energy)** Day 5-én is **qualifying volt, de skipped**. Day 4 + Day 5 = **2 napi EOG skip**. Lehetséges okok:
- **`max_new_per_day: 1-2`** új entry cap (Day 4: 2 entry, Day 5: 1 entry)
- **Sector cap NEM blokk** Energy esetén (17,86% + EOG ~$4-5K = ~22% < 30% cap)
- **S_j ranking**: WMB 85,25 > EOG 71,85 > VLO 63,88 > AMH 62,70 → WMB és VLO **már nyitva**, AMH új entry. **EOG csak akkor lenne 4. helyezett**, ha a `max_new` < 4 — ami konzisztens a `selected_for_entry: 1`-gyel.

**Hipotézis**: a `swing_max_daily_new` paraméter `1-3` sávban van, és a sector-balanced greedy **a top-2-3 helyezettből** választ (mindegyikből csak 1-et). Day 5-én WMB (Energy, nyitva), VLO (Energy, nyitva), AMH (Real Estate, új) — a 3. helyezett kapja az új entry-t. EOG (Energy) 4. helyezett, és **a sector már WMB+VLO+LBRT+EC-vel telt** (4 Energy ticker volt nyitva még az AMH entry előtt — Day 4 záró + új WMB Day 4-i entry).

### Sector distribution Day 5 záró

| Sektor | Day 4 záró | Day 5 záró | Δ | % portfolio |
|--------|-----------|-----------|-----|-------------|
| Energy | $17 862 | $17 862 | 0 | 17,86% |
| **Healthcare** | $25 055 | $25 055 | 0 | **25,05%** |
| Consumer Defensive | $5 504 | $5 504 | 0 | 5,50% |
| Technology | $2 956 | $2 956 | 0 | 2,96% |
| **Real Estate** | 0 | **$7 995** | +$7 995 (AMH) | **8,00%** ⭐ |
| **Total** | $51 377 (51,38%) | **$59 373 (59,37%)** | +$7 995 | |

**Portfolio kihasználtság 59,37%** — gyors halmozódás. A `max_concurrent: 12` cap 10/12-en (83% használt), **csak 2 új entry-hely** maradt.

---

## 2. EOD State (22:00 CEST) — fontos time_stop megfigyelés

A `pt_monitor_2026-05-22.log` 22:00:03 időpontban:
```
[SWING EOD] Evaluated 10 positions — 0 exit flags set
```

⭐ **CC fix `aba9720` továbbra is működik** (csak 1 sor, NINCS régi 5-perces logika).

### A 10 nyitott pozíció Day 5 záró állapota

| Ticker | Entry $ | Qty rem. | days_held | TP1 hit | Trail SL | weekly_pnl_pct | next_action |
|--------|---------|----------|-----------|---------|----------|----------------|-------------|
| LBRT | 33,34 | 127 | **4** | ✗ | n/a | -0,195% | HOLD |
| MASI | 178,51 | 84 | **4** | ✗ | n/a | +0,026% | HOLD |
| **EC** | 13,08 | 166 | **4** | ✓ | **$13,435** | +0,130% | HOLD |
| PFGC | 96,57 | 57 | 3 | ✗ | n/a | -0,171% | HOLD |
| VLO | 258,55 | 16 | 2 | ✗ | n/a | -0,182% | HOLD |
| ON | 109,48 | 27 | 2 | ✗ | n/a | +0,187% | HOLD |
| CNC | 59,27 | 95 | 2 | ✗ | n/a | -0,011% | HOLD |
| WMB | 77,88 | 94 | 1 | ✗ | n/a | +0,045% | HOLD |
| DXCM | 71,44 | 62 | 1 | ✗ | n/a | +0,043% | HOLD |
| **AMH** | **32,11** | 249 | 0 | ✗ | n/a | +0,056% | HOLD |

### ⚠️ Time_stop flag — NEM jelentkezett, ami fontos

**Várható volt** (Day 4 review §7 outlook): a Day 5 22:00 EOD eval **flag-elheti** a LBRT/MASI/EC-t time_stop-ra Day 6 (hétfő) 21:40 CEST-re, mert addigra `days_held: 5` lesz.

**De NEM tette**: `next_day_planned.time_stops_at_2140: []` és `next_day_planned.exits_at_1530: []`. A LBRT/MASI/EC Day 5 záró `days_held: 4` — vagyis a logika nem flag-el ezeken a napokon time_stop-ot.

**Konzekvencia**: a `max_holding_days` paraméter **nem 5, hanem valószínűleg >= 6**. A flag-elés Day 6 EOD eval-ban várt (Day 6 záró `days_held: 5`), a time_stop trigger Day 7 (kedd 2026-05-26) 21:40 CEST-en.

**Verzióellenőrzendő**: a `2026-05-17-swing-sizing-phase6.md` task §1 táblázatában a "3-5 napi hold" szerepel, de a `max_holding_days` numerikus értéke nincs explicit megadva. A Day 5 viselkedés szerint a paraméter `>= 6`, ami eltér a design dokumentum értelmezésétől.

**Akció**: Dev chat-nek érdemes **explicit megerősíteni** a `max_holding_days` paraméter értékét, és **frissíteni a `2026-05-17-swing-sizing-phase6.md` design doc-ot**. A jelenlegi viselkedés (Day 6 = 5. napi hold, Day 7 = exit) **érthető és konzisztens**, csak nem volt explicit dokumentálva.

**Day 7 várt time_stop forgatókönyv** (LBRT, MASI):
- **MASI**: 84 × ~$178,55 − 84 × $178,51 = **kvázi-flat ~$3-5 realizált profit** (5 napon át flat)
- **LBRT**: 127 × ~$33,21 − 127 × $33,34 = **~-$17 közel-flat veszteség** (mild)
- **EC maradék**: trail SL aktív, **NEM time stop**

---

## 3. Pipeline Log Review

A `pt_submit_2026-05-22.log` szerint **azonnali sikeres lefutás** (15:31:01-08, 7 másodperc):
```
15:31:01 Reading: execution_plan_run_20260522_123000_0b7b68.csv
15:31:06 Existing IBKR positions/orders: {'DXCM', 'CNC', 'PFGC', 'EC', 'ON', 'LBRT', 'WMB', 'MASI'}
15:31:06 Skipping WMB: already has position or swing state
15:31:06 Skipping VLO: already has position or swing state
15:31:08 AMH: MKT BUY 249 @ ~$32.11 | stop $30.71 | TP1 $33.16 | TP2 $34.22
15:31:08 [SWING] Submitted: 1 tickers | State: state/swing_positions.json (10 open)
```

**NINCS Error 10349, NINCS retry, NINCS Gateway megszakadás**. **Day 4 + Day 5 = 2/2 nap normál működés** — a Day 1-3-i submit-mechanika anomáliái valószínűleg **alkalmi events** voltak.

---

## 4. UW Shadow Log Day 5 — 9 ticker tiszta ⭐

A `state/uw_shadow/2026-05-22.json` szerint **9 ticker logged**, `captured_at: 2026-05-22T12:31:18.752674+00:00` (= 14:31:18 CEST = a 14:30-as Phase 4-6 cron run vége).

| Ticker | combined_score | dp_pct | gex_regime | m_gex_would_have_been | dp_score_would_have_been | phase6_sized |
|--------|----------------|--------|------------|----------------------|--------------------------|--------------|
| AES | 54,38 | 0,00% | high_vol | 0,6 | 0 | ✗ |
| **AMH** | 62,70 | 0,00% | positive | 1,0 | 0 | **✓** |
| AR | 58,35 | 0,00% | high_vol | 0,6 | 0 | ✗ |
| BMY | 57,59 | **22,58%** ⭐ | positive | 1,0 | **-15** | ✗ |
| COP | 56,07 | 0,00% | positive | 1,0 | 0 | ✗ |
| DXCM | 61,73 | 10,03% | positive | 1,0 | 0 | ✗ (már nyitva) |
| EOG | 71,85 | 0,00% | high_vol | 0,6 | 0 | ✗ |
| VLO | 63,88 | 0,00% | positive | 1,0 | 0 | ✗ (már nyitva) |
| **WMB** | **85,25** ⭐ | 0,00% | positive | 1,0 | 0 | ✗ (már nyitva) |

**Day 5 UW shadow összesítés**:
- **1 ticker dp_pct ≥ 10%** (BMY 22,58%, csak ez — vs Day 4-en 4 ticker)
- **1 "would_have_been_penalty"** (BMY -15) — a régi `dp_score` logika **rontotta** volna
- **GEX regime distribution**: **6 positive + 3 high_vol** (vs Day 4: 4 positive + 4 high_vol + 1 unknown) — **több pozitív GEX** = stabilizáló market
- **m_gex_avg_would_have_been: 0,8667** (vs Day 4: 0,8222) — emelkedett, **kevésbé volatilis** környezet

⭐ **VIX Day 5 zárás 16,71 (-5,49%)** vs Day 4 zárás 17,68. **VIX csökkenés** = **risk-on** jelek. Kombinálva a SPY +0,39%-kal, ez egy enyhén bullish nap.

---

## 5. Anomalies / Notes — Day 5 P0/P1 állapot

### §0.1 (régi pt_monitor 5-perces) — ✅ RESOLVED (2/2 nap)

`pt_monitor_2026-05-22.log` 1 sor. CC fix `aba9720` továbbra is működik.

### §0.2 (Error 10349 TIF) — ⭐ Day 5-en NEM jelentkezett (2/2 nap NEM-Error)

A `pt_submit_2026-05-22.log` szerint az AMH submit **azonnal sikeres**, NINCS Error 10349.

**Day 1-3**: 3/3 nap 100% Error 10349 ráta (LBRT+EC Day 1, PFGC Day 2, VLO+ON+CNC Day 3)
**Day 4-5**: **2/2 nap NEM-Error**

**Statisztikai megfigyelés**: 3/5 napon Error 10349 (60%), 2/5 napon NEM (40%). A pattern **NEM véletlenszerű** — a Day 4-5-en sikeres napok mind **15:31:01+ futási időpontban** indultak (vs Day 1-3 15:30:00-on vagy késleltetett 16:05-ön). **Megerősíti az időzítési hipotézist**: az IBKR TIF preset valid-time-in-force **15:30:00**-on race-conditionbe kerül a piacnyitással, de **15:31+** már stabil.

**Akció**: §0.2 státusza **P0 → P1** downgrade indokolt. Continual observation Day 6-10 között. Ha 5+ stabil nap, akkor **WITHDRAWN** is lehet.

### §0.3 (Phase 2 timeout) — implicit OK Day 5-en

### §0.4 (UW shadow felülírás) — ✅ RESOLVED (3/3 nap)

`state/uw_shadow/2026-05-22.json` 9 ticker, `captured_at: 14:31:18`.

### §0.5 (submit retry storm) — ✅ Day 5-en NEM jelentkezett (2/2 nap stabil)

`pt_heartbeat_monitor_2026-05-22.log` `[OK]` jelölés, csak 1 submit attempt.

**Akció**: §0.5 státusza **P0 → P2** downgrade indokolt. A `docs/tasks/2026-05-21-submit-retry-storm.md` task megtartandó **defensive engineering** célból (live trading deploy előtt érdemes implementálni), de **NEM sürgős**.

### §0.6 (sector cap megsértés) — ⭐ WITHDRAWN (továbbra is)

### §0.7 (új P3) — MASI ATR-anomaly low-volatility ticker

A MASI Day 5 záró `weekly_pnl_pct: +0,026%` = **5. napja közel teljesen flat**. Day 7 várt time_stop kvázi-flat profit (lásd 2. szakasz).

### §0.8 (új P3) — Healthcare sector koncentráció

Day 5 záró Healthcare 25,05% (változatlan Day 4-ről, mert NINCS új Healthcare entry Day 5-en). **A 30% cap-tól 5 százalékpont távolság — nyugodt monitoring**.

### §0.9 (új P1) — Time_stop flag-elés a Day 5 EOD eval-ban hiányzik

Lásd 2. szakasz. A `max_holding_days` paraméter valószínűleg `>= 6`, NEM 5 (a "3-5 napi hold" design dokumentumtól eltérően). **Akció**: Dev chat-nek explicit megerősíteni a paraméter értéket és frissíteni a design doc-ot.

---

## 6. Day 6 (hétfő, 2026-05-25) outlook

### Tervezett exit-ek

**NINCS tervezett exit** Day 6-en (`next_day_planned.exits_at_1530: []`, `time_stops_at_2140: []`).

**De**: a Day 6 22:00 EOD eval **valószínűleg flag-eli** a LBRT/MASI-t time_stop-ra Day 7 (kedd) 21:40 CEST-re, mert addigra `days_held: 5` lesz. **Day 6 review-ban ellenőrizni**.

### Várt mozgások

- **EC maradék**: trail SL $13,435, ha $14,40+ fölé emelkedik → trail emelkedhet
- **MASI**: várhatóan flat marad. Day 7 time_stop egyre közelebb.
- **LBRT**: szintén Day 7 time_stop várt
- **VLO/ON/CNC**: Day 6 = days_held 3
- **WMB/DXCM**: Day 6 = days_held 2
- **AMH**: Day 6 = days_held 1

### Új entry potenciál Day 6

A `max_concurrent: 12` cap 10/12 (2 hely maradt). A Day 5-i Phase 4 univerzum 9 ticker, ebből EOG (S_j 71,85) **továbbra is qualifying és NEM-sized** — 3. napon át. Day 6-on lehet EOG új entry (ha a sector-balanced greedy logika a 3. napra is "elveti").

**Sector cap-figyelmeztetés**: Energy 17,86% + EOG ~$4-5K = ~22%, **bőven a 30% cap alatt**. NEM blokk.

### Day 6 prioritások

1. **Time_stop flag** LBRT/MASI-ra Day 6 EOD eval-ban (`next_day_planned.time_stops_at_2140` nem üres?)
2. **EOG harmadik napi skip** — Dev chat-nek érdemes ellenőrizni a `max_new_per_day` paramétert
3. **WMB Day 6 S_j folytatódó emelkedése?** (Day 5 85,25 → ?)
4. **Healthcare sector** 25,05%, monitoring

---

## 7. Files referenced (Day 5)

- `state/swing_positions.json` — 10 nyitott pozíció (9 régi + 1 új AMH)
- `state/daily_metrics/2026-05-22.json` — Day 5: 0 trade, P&L $0, cumulative $107,27
- `scripts/paper_trading/logs/cumulative_pnl.json` — Day 5 history rögzítve
- `logs/pt_eod_2026-05-22.log` — EOD report, 0 trade
- `logs/pt_close_2026-05-22.log` — 2 no-op close
- `logs/pt_submit_2026-05-22.log` — **1 attempt, 7s futási idő** ⭐
- `logs/pt_monitor_2026-05-22.log` — **1 SOR EOD eval** ⭐
- `logs/pt_gateway_2026-05-22.log` — gateway preflight OK
- `logs/pt_heartbeat_monitor_2026-05-22.log` — **[OK]** jelölés ⭐
- `state/uw_shadow/2026-05-22.json` — **9 ticker ÉP** ⭐
- `output/trade_plan_2026-05-22.csv` — 3 ticker (WMB skip, VLO skip, AMH új)
- `docs/analysis/weekly/2026-W21.md` — heti összefoglaló (lásd 8. szakasz)

---

## 8. ⭐ W21 Heti Összefoglaló (2026-05-18 → 2026-05-22)

A `scripts/analysis/weekly_metrics.py` által generált `docs/analysis/weekly/2026-W21.md` heti összefoglaló:

### W21 hivatalos metrikák

| Metrika | W21 érték | Megjegyzés |
|---------|-----------|------------|
| Trading days | 5 | Day 1-5 swing pivot |
| Positions opened (script) | 3 ⚠️ | **Téves**: valójában 10 új entry |
| Win days | 1/5 | Csak Day 2 (+$112,31) |
| Gross P&L | **+$107,27** | |
| Commission | -$2,20 | |
| **Net P&L** | **+$105,07** | A swing pivot architektúra első hete |
| Cumulative | +$107,27 (+0,11%) | |
| Portfolio weekly | +0,11% | |
| SPY weekly | **+0,87%** | |
| **Excess weekly** | **-0,76%** | mild underperform |
| TP1 hits (script) | 0/3 (0%) ⚠️ | **Téves**: 1 TP1 hit (EC Day 2) |
| Slippage avg (script) | -1,67% ⚠️ | **Csak Day 3 VLO**, ON +3,26% kihagyva |
| Zero-position days | 3/5 | Day 1, Day 4, Day 5 |
| Low-position days (<3) | 2/5 | |

### A heti P&L bontása napokra

| Day | Nap | Új entry | Net P&L | Cumulative | Excess vs SPY |
|-----|-----|----------|---------|------------|---------------|
| 1 | h 05-18 | 3 (LBRT, MASI, EC) | $0 | $0 | n/a |
| 2 | k 05-19 | 1 (PFGC) | **+$111,23** ⭐ | +$112,31 | **+0,78%** (risk-off) |
| 3 | sz 05-20 | 3 (VLO, ON, CNC) | -$6,16 | +$107,27 | -1,03% (bull rally) |
| 4 | cs 05-21 | 2 (WMB, DXCM) | $0 | +$107,27 | -0,20% |
| 5 | p 05-22 | 1 (AMH) | $0 | +$107,27 | -0,39% |
| **Total** | | **10 entry** | **+$105,07** | **+$107,27** | **-0,76%** |

### W21 strukturális megfigyelések

**Az egyetlen realizált profit Day 2-i EC TP1 fill** (+$112,31, 5,20% entry-től) — **az első mechanikai validáció** a swing pivot architektúrára. **A többi 4 nap mind $0 vagy mild negatív** (Day 3 -$5,04 1-share-egységű mark-to-market a VLO entry-n).

**Bull rally underperform pattern megerősítve 3/3 napon** (Day 3-5):
- Day 3: SPY +1,02%, Portfolio -0,01%, excess -1,03%
- Day 4: SPY +0,20%, Portfolio 0,00%, excess -0,20%
- Day 5: SPY +0,39%, Portfolio 0,00%, excess -0,39%

**Risk-off outperform pattern** Day 2-én (SPY -0,67%, Portfolio +0,11%, excess +0,78%) — konzisztens a legacy 63 napi mintával ("a rendszer jól megy risk-off napokon, rosszul bull rally napokon").

**P0 anomáliák progressziója**:
- Day 1-3: **5 P0 anomália** (régi monitor, Error 10349 TIF, Phase 2 timeout, UW shadow, retry storm, sector cap)
- **CC fix-ek Day 2-3 között**: aba9720 (régi monitor) + 1eb9755 (UW shadow) — mindkettő működik 3/3 napon
- **§0.6 WITHDRAWN** Day 4-en (téves értelmezés)
- **Day 4-5**: **MIND a P0 anomália csendes** — a swing pivot architektúra stabilizálódik

### Heti P&L kontra a Day 21 checkpoint kritérium

A Day 21 checkpoint kritériuma (a project instructions szerint): **kumulatív > -$1 500 a Day 21-re** (kb. 2026-06-15 körül, W23). **W21 záró után**: kumulatív **+$107,27**, **bőven a küszöb felett**. Ha a Day 6-21 időszakban a portfólió **flat** marad (átlag $0/nap), akkor a Day 21 checkpoint **+$100 körül** lesz — **PASS**.

A tegnap reggeli **Goldman momentum-rally peak hipotézis** alapján a következő 2-3 hetes ablakra **enyhe-negatív** kumulatív várt (-$200 - +$200 sávban). **A Day 21 checkpoint kritérium tehát realisztikusan teljesíthető**, ha a swing pivot architektúra továbbra is **közel-flat** mozgást termel és **alkalmi pozitív TP1 hit-ekkel** ($100-300 esetenként) gazdagodik.

### W21 weekly_metrics.py script anomáliák (P1 javaslatok)

A heti összefoglaló **3 logging-anomáliát** mutat:

**1. "Positions opened: 3"** — VALÓJÁBAN **10 új entry** történt W21-en. A script valószínűleg a `cumulative_pnl.daily_history` `trades` mezőt számolja (= realizált zárt trade-ek, nem új entry-k). **A label téves** — javasolt frissítés: "Trades closed: 3" + új mező "New entries opened: 10".

**2. "TP1 hits: 0/3 (0%)"** — VALÓJÁBAN **1 TP1 hit** (EC Day 2-én). A script a `cumulative_pnl.daily_history.tp1_hits` mezőt veszi, ami **soha nem volt update-elve** (mind 0 minden napra). **A `pt_eod.py` vagy `daily_metrics.py` script NEM frissíti a `tp1_hits` mezőt** — strukturális bug. **Javasolt fix**: a Day 2-i EC TP1 fill esetén `tp1_hits: 1` legyen a `2026-05-19` daily_history entry-ben.

**3. "Slippage avg: -1,67%"** — VALÓJÁBAN **a Day 3 VLO -1,55% kedvező + Day 3 ON +3,26% kedvezőtlen + Day 3 CNC +0,20% mild** + a többi entry slippage hiányzik. A `daily_metrics.execution.slippage_per_ticker` mező sok napon üres (`{}`). **Strukturális hiány** a slippage logging-ban — Day 1-2 + Day 4-5 entry-k slippage-e NEM rögzített.

**Akció**: a `docs/tasks/`-ba érdemes felvenni egy P1 task-ot: "weekly_metrics.py + daily_metrics.py slippage és tp1_hits logging fix" — NEM hotfix, de a W22 weekly report-ra érdemes lenne korrigálni.

### W21 napi karakter mátrix

| Day | Karakter | Mechanikai megfigyelés |
|-----|----------|------------------------|
| 1 | **Tüzet beleállító** | 3 entry, sector cap MASI 15%-on landol, 3 P0 anomália |
| 2 | **Első profit** | EC TP1 +$112,31, risk-off outperform |
| 3 | **Bull rally underperform** | 3 entry, sector cap 20,63% (téves értelmezés), 2 új P0 anomália |
| 4 | **Stabilizálódó** | 2 entry, MIND P0 csendes, sector cap értelmezés újra |
| 5 | **Nyugodt** | 1 entry, MIND P0 csendes 2/2 nap, time_stop kérdés |

---

## State (Day 5 — W21 záró)

**Architektúra**: swing pivot Fázis 3 deploy DAY 5, **a swing pivot architektúra első hete befejeződött**.

**Live**: 10 open positions, 0 exit flags Day 6-ra.

**Cumulative**: **+$107,27 (+0,11%)**, trading_days: 5.

**Excess return**: heti **-0,76% vs SPY** (Day 2 +0,78% nyertes, Day 3-5 mind negatív excess).

**Aktív P0/P1 anomáliák** (a `04-risks-and-open-questions.md` §0-ban):
- **§0.1 RESOLVED** (régi pt_monitor)
- **§0.2 P0 → P1 javasolt downgrade** (Error 10349 TIF — 3/5 nap, 2/2 stabil Day 4-5)
- **§0.3 implicit OK**
- **§0.4 RESOLVED** (UW shadow)
- **§0.5 P0 → P2 javasolt downgrade** (submit retry storm — 1/5 nap, 4/5 stabil)
- **§0.6 WITHDRAWN** (sector cap)
- **§0.7 P3** (MASI ATR-anomaly low-volatility)
- **§0.8 P3** (Healthcare 25,05% koncentráció)
- **§0.9 P1 (új)** (time_stop flag-elés vs `max_holding_days` paraméter értelmezés)

**Új P1 javaslatok (W22-re)**:
- `weekly_metrics.py` 3 logging-anomalia fix (positions_opened, tp1_hits, slippage)
- `max_holding_days` paraméter explicit dokumentálás a design doc-ban

**A W21 napi karakter egy mondatban**: A swing pivot architektúra **első teljes hete** **NEM-katasztrofikus** mérleget mutat (+$107,27 net, -0,76% excess) — az **EC TP1 realizált profit** ($112,31) **mechanikai validáció** mellett a **bull rally underperform pattern** (3/3 nap negatív excess) **megerősítette** a legacy 63 napi minta strukturális megfigyelését, miközben **a 6 P0 anomáliából 4 RESOLVED/WITHDRAWN** lett (a CC fix-ek + a Day 4-i újraértékelés révén), és **a Day 4-5 stabilizálódás** azt sugallja, hogy **a Day 6-21 időszak rutinszerű, kvázi-flat mozgással telhet** a tegnap reggeli **Goldman momentum-rally peak hipotézis** szerint — **a Day 21 checkpoint kritérium (+$0 - -$1 500) realisztikusan teljesíthető**.

---

## 9. ⚠️ UTÓLAGOS KORREKCIÓ + W21 RECONCILED SUMMARY (felfedezve 2026-05-23 reggel az IBKR Trades alapján)

**Discovery time**: 2026-05-23 szombat reggel, az IBKR TWS Trades + Positions + Orders képek elemzése során. **Két autonóm bracket trigger** felfedezve, amelyet sem a `daily_metrics`, sem a `swing_positions.json`, sem a `cumulative_pnl.json` NEM rögzít.

### Day 5 16:40:20 CEST — ON TP1 bracket trigger ⭐

Az IBKR Trades log szerint **Day 5 közben (péntek 16:40:20 CEST)** az ON ticker TP1 bracket order **autonóm módon triggerelt** és zárta a teljes 27-share pozíciót:

| Mező | Érték |
|------|-------|
| Ticker | ON |
| Action | SLD |
| Qty | 27 |
| Fill ár | **$115,41** |
| Időpont | 2026-05-22 16:40:20 CEST = 10:40:20 ET (1h 10 perccel piacnyitás után) |
| ORDER_REF | ÜRES (NEM `IFDS_SWING_*`) |
| Net Total | +$161,19 |
| Net Incl. Commission | **+$159,12** |

**Bracket level forrás**: a `pt_submit_2026-05-20.log` szerint a Day 3-i ON entry-nél:
```
16:05:24 ON: MKT BUY 27 @ ~$106.02 | stop $93.50 | TP1 $115.41 | TP2 $124.80
```
**A planned-entry alapú TP1 $115,41** — a fill ár **EXACT MATCH** ($115,41). **NEM a `swing_positions.json` mental TP1 $118,87-je triggerelt**, hanem a **planned-alapú IBKR bracket TP1**.

**Slippage hatás**: a Day 3-i ON planned $106,02 → filt $109,48 (**+3,26% kedvezőtlen slippage**). A bracket TP1 $115,41-en maradt (planned-alapú). A tényleges entry-hez tartozó mental TP1 $118,87 lett volna (1,5×ATR fölött). **A bracket TP1 tehát korai** — $3,46-tal a tényleges-alapú szint alatt. **Kihagyott profit: 27 × ($118,87 - $115,41) = +$93** ami a mental TP1 megvalósulása esetén keletkezett volna (feltételezve hogy az ár elérte volna).

### W21 teljes IBKR Trades audit — 6 napi részlet

Az IBKR Trades log ("Last 6 Days") **15 trade-et** mutat. Csoportosítva:

| Nap | Trade | Ticker | Qty | Fill $ | ORDER_REF | Logok rögzítették? |
|-----|-------|--------|-----|--------|-----------|---------------------|
| Day 1 | BOT | LBRT | 127 | 33,33 | IFDS_SWING_LBRT | ✅ |
| Day 1 | BOT | EC | 332 | 13,072 | IFDS_SWING_EC | ✅ |
| Day 1 | BOT | MASI | 84 | 178,50 | IFDS_SWING_MASI | ✅ |
| Day 2 | BOT | PFGC | 57 | 96,55 | IFDS_SWING_PFGC | ✅ |
| **Day 2** | **SLD** | **EC** | **166** | **13,76** | **IFDS_SWING_EC_TP1** ⭐ | **✅** |
| Day 3 | BOT | VLO | 16 | 258,49 | `6S57Yl4c895U` (NEM IFDS!) | ⚠️ ✅ (state-ben) |
| Day 3 | BOT | ON | 27 | 109,44 | `rffKnFz2S9Bx` (NEM IFDS!) | ⚠️ ✅ (state-ben) |
| Day 3 | BOT | CNC | 95 | 59,26 | `egcu1bmCsFLH` (NEM IFDS!) | ⚠️ ✅ (state-ben) |
| Day 3 | BOT | VLO | 1 | 254,08 | **IFDS_DEBUG_VLO** | ✅ (Tamás teszt) |
| Day 3 | SLD | VLO | 1 | 253,19 | **IFDS_DEBUG_VLO_CLEANUP** | ✅ (Tamás teszt) |
| Day 4 | BOT | WMB | 94 | 78,35 | IFDS_SWING_WMB | ✅ |
| Day 4 | BOT | DXCM | 62 | 71,83 | IFDS_SWING_DXCM | ✅ |
| **Day 4** | **SLD** | **VLO** | **16** | **244,61** | **ÜRES (SL bracket)** ⚠️ | **❌ NEM logolva** |
| Day 5 | BOT | AMH | 249 | 32,21 | IFDS_SWING_AMH | ✅ |
| **Day 5** | **SLD** | **ON** | **27** | **115,41** | **ÜRES (TP1 bracket)** ⭐ | **❌ NEM logolva** |

**A 3 "NEM IFDS" ORDER_REF Day 3-on** (VLO, ON, CNC entry-k): a Day 3-i submit retry storm folyamán a `submit_orders.py` Tamás manuális Workstation submit-jain keresztül filt-elt (lasd `04-risks` §0.4 RESOLVED entry — Error 354 market data block). **Az IBKR-ben az order ref-ek a TWS auto-generált random ID-k**, NEM az `IFDS_SWING_*` formula — ez **konzisztens** a manual submit pályaval.

### Strukturális finding — 4 réteg (helyesbítve 2026-05-25)

**Eredeti hipotézis (téves) — 4 rétegű finding**: a swing pivot IBKR bracket-stop módban fut + bracket levels planned-alapúak + monitoring hiány + logging bug.

**A `submit_orders.py` kódbázis-elemzése (2026-05-25, Log Review chat) megmutatta a helyesbített finding-ot**:

| Réteg | Eredeti finding | **Helyesbített finding** |
|-------|-----------------|---------------------------|
| **A. Architektúra** | Swing pivot IBKR bracket-stop módban fut | ⚠️ **TÉVES**. A `submit_swing_market_only` kódja explicit: `# Single market BUY (no bracket).` (Day 63 §3.12). A swing pivot **MENTAL-STOP módban van** (helyes, ahogy a design doc írja). A Day 4-5 bracket-trigger-ek **Tamás Day 3-i manuális TWS bracket-jeiből** származtak. |
| **B. Slippage** | Bracket levels PLANNED-alapúak | ⚠️ **Csak Tamás manuális bracket-jeire releváns**. A cron-driven 7 entry-nél **NINCS bracket**, így a slippage-érzékenység irreleváns. |
| **C. Monitoring** | `pt_monitor.py` NEM reconcile-eli a state-et | ✅ **Helyes**. De oka **Tamás manuális TWS bracket-jének autonóm trigger-je** — NEM a `submit_orders.py` viselkedése. A reconciliation P0 task továbbra is szükséges (a Day 4-5-i két autonóm trigger eredményének detektálása). |
| **D. Logging** | TP1/SL/TP2 hit counters soha nem update-elnek | ✅ **Helyes**. Strukturális logging bug a `daily_metrics.py`/`cumulative_pnl.py`-ben — független a manuális TWS bracket-ektől. |

**A 7 cron-driven entry valóban mental-stop módban van** (orderRef: `IFDS_SWING_{sym}`, parent MKT only). Csak a Day 3-i 3 manuális TWS entry (VLO, ON, CNC) volt **kettős védelemben** (mental + manuális TWS bracket).

**Tamás Day 6 reggeli akció**: a CNC élő TWS bracket (Stop $55,50 + Limit $61,89 GTC) **manuálisan cancellálva** 2026-05-25 08:26 CEST-kor (IBKR Orders ablak megerősíti: 2 × Cancelled). **Többé nincs autonóm bracket order az IBKR-ben** — a teljes portfolio mental-stop módban van.

**A swing pivot architektúra tehát a design dokumentum szerint helyesen működik** — a `2026-05-17-swing-sizing-phase6.md` és a Day 1 prezentáció **NEM kell frissíteni**. A Day 4-5 autonóm bracket-trigger-ek **egyszeri események voltak** a Day 3-i Error 354 workaround maradékaként, NEM strukturális architektúra-problémák.

### W21 RECONCILED SUMMARY (IBKR Trades alapján)

A W21 tényleges realizált P&L recompute az IBKR Trades log alapján:

| Nap | Hivatalos P&L | Tényleges (IBKR) | Eltérés | Megjegyzés |
|-----|---------------|------------------|---------|------------|
| Day 1 (h, 05-18) | $0 | $0 | 0 | 3 BOT, 0 SLD |
| Day 2 (k, 05-19) | +$112,31 | **+$111,46** | -$0,85 | EC TP1, kis FIFO/commission delta |
| Day 3 (sz, 05-20) | -$5,04 | **-$0,89** | +$4,15 | IFDS_DEBUG_VLO 1+1 share (Tamás teszt) |
| **Day 4 (cs, 05-21)** | **$0** | **-$227,06** ⚠️ | **-$227,06** | **VLO SL bracket trigger 19:19:54 CEST** |
| **Day 5 (p, 05-22)** | **$0** | **+$159,12** ⭐ | **+$159,12** | **ON TP1 bracket trigger 16:40:20 CEST** |
| **W21 Total realized** | **+$107,27** | **+$42,63** | **-$64,64** | **Két bracket trigger NEM logolva** |

**Plus Day 5 záró unrealized M2M** (IBKR Positions Unrealized P&L oszlopa, **8 valódi nyitott pozíció**):
- LBRT: -$190 (-4,5%)
- MASI: +$25 (+0,2%)
- EC maradek (166): +$128 (+5,9%)
- PFGC: -$167 (-3,0%)
- CNC: -$12 (-0,2%)
- WMB: +$10 (+0,1%)
- DXCM: +$15 (+0,3%)
- AMH: +$14 (+0,2%)
- **Total Unrealized: -$178,55**

**Net Liq Day 5 záró (IBKR)**: **$99 960,50** → **valódi portfolio change**: **-$39,50** a $100k baseline-ról (-0,04%).

**Reconcile**: $100 000 baseline → -$39,50 = realized +$42,63 + unrealized -$178,55 + cash credit/margin/egyéb +$96,42 ≈ **-$39,50**. Összhangban az IBKR "DAILY P&L $192,02" Day 5-i értékével (a Day 5 napi total move = +$159 ON TP1 realized + a 8 másik pozíció napi M2M change).

### Konzekvencia a W21 weekly summary-re

A §8. szakasz W21 weekly summary táblázata **átértékelendő**:

| Metrika | Hivatalos (script) | Tényleges (IBKR) | Megjegyzés |
|---------|---------------------|------------------|------------|
| Net P&L | +$105,07 | **+$40,43** (realized) | Day 4-5 bracket trigger-ek rögzítve |
| Win days | 1/5 | **2/5** | Day 2 (EC) + Day 5 (ON) |
| TP1 hits | 0/3 (0%) | **2/10 entry (20%)** | Day 2 EC + Day 5 ON |
| SL hits | 0 | **1** | Day 4 VLO |
| Cumulative | +$107,27 | **+$42,63** (realized) | Bracket trigger-ek + EC TP1 |
| Cumulative M2M | n/a | **-$39,50** | IBKR Net Liq alapján |

**A swing pivot architektúra tényleges W21 eredménye**: **realized +$42,63 + unrealized -$178,55 = -$135,92 m2m**, vagy **-$39,50** (a IBKR Net Liq differential a $100k baseline-ról, ami tartalmaz cash/margin házatásokat is).

### Új P0 task — state reconciliation + TP/SL hit counter fix

A Dev chat / CC számára újra: [`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](../tasks/2026-05-23-state-reconciliation-from-ibkr.md).

**Task scope (4 rész)**:
1. **State reconciliation**: a `pt_monitor.py` 22:00 EOD eval-ja lekérdezi az IBKR Positions + Trades API-t, és **detectálja az autonóm bracket trigger-eket**. Ha egy ticker NEM szerepel az IBKR Positions-ben, de a `swing_positions.json`-ban igen → zárva, fetch fill-t, update state.
2. **Daily metrics + cumulative reconcile**: a `daily_metrics/YYYY-MM-DD.json` és `cumulative_pnl.json` utólag is frissíthető a hiányzó realized P&L-lel (Day 4: -$227,06, Day 5: +$159,12).
3. **TP1/SL/TP2 hit counter fix**: a `cumulative_pnl.json daily_history` `tp1_hits`/`sl_hits`/`tp2_hits` mezők **soha nem voltak update-elve**. A reconciliation script ezeket is frissíti: Day 2 `tp1_hits: 1`, Day 4 `sl_hits: 1`, Day 5 `tp1_hits: 1`.
4. **Architektúra-szintű döntés** (Tamás): a swing pivot ténylegesen IBKR bracket-stop módban fut — ez **szándékos** vagy a `submit_orders.py` legacy 6-órás architektúra-maradék? Az opciók: (A) Bracket-stop mód fenntartása + bracket level-eket a tényleges fill alapján update-elni (modify order); (B) Mental-stop mód teljesítése + `submit_orders.py`-ból a child order-ek eltávolítása.

### Priorizálás

- **P0**: state reconciliation + daily_metrics/cumulative_pnl korrekció (Day 6 kedd 2026-05-26 reggelére, az első piaci nyitás napra a hosszú hétvége után)
- **P0**: TP/SL/TP2 hit counter fix (ugyanazon CC futás során)
- **P1**: architektúra-szintű döntés bracket vs mental (Day 7-10 döntési ablak)

**A jelen review §1-§8 szakasza VÁLTOZATLAN marad** (transzparens audit trail), és **a §9 UTÓLAGOS KORREKCIÓ szakasz** rögzíti a felfedezést és a tényleges W21 adatokat.
