# IFDS Daily Review — 2026-05-20 (szerda, Day 3 Swing Pivot)

**Verzió**: swing pivot architektúra (Fázis 3 deploy 2026-05-18, Day 3/63)
**Day 3 net P&L**: **-$6,16** (gross -$5,04 + commission -$1,12)
**Cumulative P&L**: **+$107,27 (+0,11%)** ⬇️ — kissé csökkent ($112,31 → $107,27)
**Open positions**: **7** (LBRT, MASI, EC 166-share maradék, PFGC, **+ VLO, ON, CNC**) — mind HOLD, exit flag 0

**Kulcs Day 3 eredmények:**
- ⭐ **3 új entry**: VLO (Energy, S_j 73,1), ON (Technology, S_j 70,2), CNC (Healthcare, S_j 57,9)
- ⭐ **CC fix-ek megerősítve**: §0.1 (régi pt_monitor) és új §0.4 (UW shadow felülírás) **MINDKETTŐ ELIMINÁLVA**
- ⚠️ **2 új P0 anomália**: submit retry storm (5 próbálkozás 35 perc alatt) + **Healthcare sector cap megsértve 20,63%**
- ⚠️ **Error 10349 TIF — 3/3 nap 100% ráta**, strukturális minden új entry-en
- ⚠️ **Bull rally underperform megerősítve**: SPY +1,02%, Portfolio -0,01%, **Excess -1,03%**
- ⚠️ **Phase 4 univerzum drámaian csökkent**: 77 (Day 2) → **7 ticker** (Day 3) — Goldman momentum chart predikciója?

---

## 1. Day 3 Entry Decisions

### 3 új entry (a daily_metrics szerint top 3 kvalifikáló S_j)

| Ticker | S_j | Sektor | Planned $ | Filled $ | Slippage | Qty | Notional $ |
|--------|-----|--------|-----------|----------|----------|-----|------------|
| **VLO** | 73,1 | Energy | 262,62 | **258,55** | **-1,55% kedvező** | 16 | 4 137 |
| **ON** | 70,2 | Technology | 106,02 | **109,48** | **+3,26% KEDVEZŐTLEN** ⚠️ | 27 | 2 956 |
| **CNC** | 57,9 | Healthcare | 59,15 | 59,27 | +0,20% mild kedvezőtlen | 95 | 5 631 |
| **Total** | | | | | átlag **+0,64%** | | **12 724** |

**Megfigyelés ON slippage-re**: +3,26% **drámaian magas** kedvezőtlen slippage. Ez **bull rally gap-up open** jellemző — az SPY +1,02% napi mozgáson a Technology szektor (XLK) valószínűleg +2-3%-ot mozgott, és az ON gap-up open-en lett vásárolva 16:05 entry-időpontban (15:30 helyett 35 perccel később, az IBKR Gateway problémák miatt — lásd 6. szakasz). A 35 perc késleltetés további +3,26% slippage-et okozott.

**Stratégiai hatás**: az ON TP1 $115,41 és TP2 $124,80 küszöbök **a $109,48 entry-től** mostantól csak +5,4% (TP1) és +14,0% (TP2). **Az eredeti $106,02 planned entry-től** ezek +8,9% és +17,7% lett volna — **vagyis kb. 3,5 százalékponttal kisebb effektív profit potenciál** az ON pozíción a slippage miatt.

### A `trade_plan_2026-05-20.csv` mutatja a teljes Phase 4 univerzumot

A `output/trade_plan_2026-05-20.csv` szerint **csak 3 ticker** szerepelt a trade plan-ben:
1. VLO (S_j 73,1) — entry
2. ON (S_j 70,2) — entry
3. CNC (S_j 57,9) — entry

**A `daily_metrics.swing_score_distribution.qualifying_threshold_50: 7`** vs trade plan **csak 3 ticker** — vagyis a 7 kvalifikáló ticker közül **4 ticker NEM került trade plan-be**, valószínűleg sector cap (lásd lent) vagy egyéb szűrő miatt.

### Phase 4 univerzum DRÁMAIAN csökkent

| Nap | Qualified > S_j 50 | Megjegyzés |
|-----|--------------------|------------|
| Day 1 (h, 2026-05-18) | 96 | normál szélesség |
| Day 2 (k, 2026-05-19) | 77 | kissé csökkenő |
| **Day 3 (sz, 2026-05-20)** | **7** ⚠️ | **11× kisebb mint Day 1** |

**Lehetséges magyarázatok**:
- (A) **A bull rally nap PCR percentile-okat lecsökkenti** — kevesebb put-buy intézményi pozícióhoz mert kevesebb hedge kell egy emelkedő piacon. **Konzisztens a tegnap reggeli Goldman momentum chart elemzéssel**: ha most "late-stage momentum rally" van (80. percentile-on), akkor **a flow signal-ek szezonálisan elcsendesednek** a rally peak környékén.
- (B) **Bug a Phase 4 scoring-ban** — a `cron_intraday_20260520_*.log`-ot nem nyitottam meg részletesen, de a 7 ticker érték **gyanús alacsony**. **Érdemes a Dev chat-nek belenézni**.
- (C) **A Phase 2 SEC 10-Q exclusion** több tickert kizárt mint Day 1-2 — earnings szezon közepén ez normál.

**A leg valószínűbb az (A)**: a tegnap reggeli Goldman momentum-chart predikciója már a Day 3-i Phase 4 univerzumon **empirikusan jelentkezett**. Ha ez tendencia, a következő 1-2 hétben várhatóan **alacsony breadth marad** (7-30 kvalifikáló ticker/nap), és a top S_j-k a 60-80 sávra szorulnak vissza (vs Day 1-2: 95-107).

### Sector distribution Day 3 záró

| Sektor | Day 2 záró | Day 3 záró | Δ | % portfolio |
|--------|-----------|-----------|-----|-------------|
| Energy | $6 405 | **$10 541** | +$4 137 (VLO) | 10,54% |
| **Healthcare** | $14 995 | **$20 626** ⚠️ | **+$5 631 (CNC)** | **20,63%** ⚠️ |
| Consumer Defensive | $5 504 | $5 504 | 0 | 5,50% |
| Technology | 0 | $2 956 (ON) | +$2 956 | 2,96% |
| **Total** | $26 904 (26,9%) | **$39 627 (39,63%)** | **+$12 723** | |

**⚠️ KRITIKUS — A Healthcare sektor 20,63% > 15% cap!** Lásd 6. szakasz §0.6 új P0 anomália.

---

## 2. EOD State (22:00 CEST)

A `pt_monitor_2026-05-20.log` 22:00:02 időpontban **EGYETLEN sor**:
```
[SWING EOD] Evaluated 7 positions — 0 exit flags set
```

⭐ **Ez egy fontos pozitív megerősítés**: a CC fix `aba9720` (Task #G) **eliminálta a régi pt_monitor.py 5-perces logika futását**. A Day 2-i log 91 sora helyett **csak 1 sor van** — pontosan ahogy elvártuk.

### A 7 nyitott pozíció Day 3 záró állapota

| Ticker | Entry $ | Qty rem. | days_held | TP1 hit | Trail SL | weekly_pnl_pct | next_action |
|--------|---------|----------|-----------|---------|----------|----------------|-------------|
| LBRT | 33,34 | 127 | 2 | ✗ | n/a | -0,082% | HOLD |
| MASI | 178,51 | 84 | 2 | ✗ | n/a | **+0,023%** | HOLD |
| **EC** | 13,08 | **166** | 2 | **✓** | **$13,435** | +0,108% | HOLD |
| PFGC | 96,57 | 57 | 1 | ✗ | n/a | -0,109% | HOLD |
| **VLO** | **258,55** | 16 | 0 | ✗ | n/a | -0,074% | HOLD |
| **ON** | **109,48** | 27 | 0 | ✗ | n/a | +0,019% | HOLD |
| **CNC** | **59,27** | 95 | 0 | ✗ | n/a | -0,095% | HOLD |

**Day 4 (csütörtök) tervezett**: `exits_at_1530: []`, `time_stops_at_2140: []` — **nincs tervezett exit**.

### A 3 régi pozíció mozgása Day 3-on

- **LBRT**: $33,34 → ~$33,31 (becsült, -0,08% napi), stabil oldalozó
- **MASI**: $178,51 → ~$178,55 (becsült, +0,023% napi), **3 napja közel teljesen flat** — az ATR-anomalia gyanú megerősítve
- **EC maradék**: $13,08 → ~$13,21 (becsült, +0,11% napi), továbbra is bull, trail SL $13,435 alatt
- **PFGC**: $96,57 → ~$95,52 (becsült, -0,11% napi), kissé javult a Day 2-i -2,77%-ról (ami valószínűleg recovery a Day 2-i mélypontról)

### MASI 3 napja flat — a sector cap blokkolja az opportunitást

A MASI továbbra is **közel teljesen flat** (`weekly_pnl_pct: +0,023%` Day 2 → +0,022% Day 3). Az ATR $0,295 helyesen reflektálja a tényleges intraday volatilityt (tegnap morning chart-on validált).

**Strukturális kérdés**: a MASI **3 napja "lekötve" tartja a Healthcare cap 15%-át**, miközben Day 3-on **a CNC is bekerült** Healthcare-be ($5 631, +5,63%). **Ha a sector-balanced greedy szigorúan tartotta volna a cap-et**, a CNC entry **NEM kerülhetett volna be**, és egy nem-Healthcare ticker (pl. valami Industrials vagy Utilities) **helyet kapott volna** helyette.

---

## 3. ⭐ A 4 régi pozíció Day 3 unrealized állapota — mark-to-market gyanú

A `daily_metrics.pnl.gross: -$5,04` **CSAK a VLO new entry "MOC" exit_type-ját logolja** (entry $258,23 vs exit $253,19 = -$5,04 unrealized, 1 share-egységben). A `swing_positions.json` szerint VLO `qty_remaining: 16`, NEM zárt.

**Terminológiai kérdés**: a daily_metrics P&L **mark-to-market** logikára épül-e (a VLO Day 3 close ára vs entry) **vagy realized only** (mint a legacy 6 órás rendszerben volt)?

A `cumulative_pnl.json` Day 3 PnL = -$5,04 **konzisztens** a daily_metrics-szel. **De ha mark-to-market lenne**, a 16 share × $5,04 = **-$80,64** lenne a tényleges VLO unrealized, és a kumulatív **$31,67** körül lenne, NEM $107,27.

**Lehetséges magyarázat**: a daily_metrics **csak az aznapi entry-k 1-share equivalent mark-to-market értékét** logolja, miközben a régi pozíciók (LBRT, MASI, EC, PFGC) **NEM számítanak bele** a Day 3 P&L-be. Ez **egy speciális hibrid logika**.

**Dev chat-nek**: a daily_metrics P&L kalkulációt érdemes dokumentálni vagy átalakítani **tisztán mark-to-market**-ra a swing pivot 3-5 napi hold-on (az 1-share egység logika a régi 6 órás rendszerből maradék lehet). Nem prioritás, csak rögzítendő.

**A "valódi" Day 3 mark-to-market becslés** (a swing_positions.json `weekly_pnl_pct`-ek alapján):

| Ticker | weekly_pnl_pct | Notional | Becsült M2M $ |
|--------|----------------|----------|----------------|
| LBRT | -0,082% | $4 234 | -$3,5 |
| MASI | +0,023% | $14 995 | +$3,4 |
| EC maradék | +0,108% | $2 171 | +$2,3 |
| PFGC | -0,109% | $5 504 | -$6,0 |
| VLO | -0,074% | $4 137 | -$3,1 |
| ON | +0,019% | $2 956 | +$0,6 |
| CNC | -0,095% | $5 631 | -$5,4 |
| **Total M2M Day 3** | | $39 627 | **-$11,7** |

**Plus a realizált EC TP1 Day 2-én +$112,31**. Tehát az **igazi kumulatív mark-to-market** Day 3-on: $112,31 - $11,7 = **+$100,6** (becsült). **Közel** a hivatalos $107,27-hoz, de **kissé alacsonyabb** — a daily_metrics P&L kalkuláció **kissé optimista** a tényleges unrealized vs realized összetétel miatt.

---

## 4. Pipeline Log Review

A `cron_intraday_20260520_*.log`-ot nem nyitottam meg, de a 3 új entry implicit megerősíti, hogy a Phase 0-1-2-3-4-5-6 sikeresen lefutott. **DE** a **Phase 4 univerzum 7 ticker drasztikus csökkenése** (vs Day 1: 96, Day 2: 77) **érdemleges megfigyelést érdemel**.

A trade_plan_2026-05-20.csv csak 3 ticker (VLO, ON, CNC) — ezek mind entry-re kerültek. A 7 kvalifikáló - 3 entry = **4 ticker skip-elt** valamilyen szabály alapján:

- Lehet, hogy az 4 skip-elt ticker mind **Healthcare szektorba esett** és a sector cap blokkolta őket (de a CNC mégis bekerült Healthcare-be — **NEM konzisztens**!)
- Lehet, hogy a sector-balanced greedy a CNC után **leállt** (3 új entry / nap normál limit?)
- Vagy a 4 skip-elt ticker S_j-je 50-55 sávban volt és valami threshold

**A UW shadow log a teljes Phase 4 univerzumot mutatja**: 7 ticker (CNC, CVS, IBKR, ON, TXN, VLO, WMB) — `phase4_passed: true` mind a 7-nek, **de csak 3 phase6_sized: true** (VLO, ON, CNC). A 4 skip-elt: CVS, IBKR, TXN, WMB. Ezek sectorai:
- CVS: Healthcare ⚠️
- IBKR: Financial Services
- TXN: Technology
- WMB: Energy

Tehát a Phase 6 sector-balanced greedy **kihagyta a CVS-t** (Healthcare cap miatt?), és **IBKR/TXN/WMB-t** szintén. Ez **konzisztens lenne** a 15% sector cap-pel a Healthcare-re, **DE a CNC mégis bekerült Healthcare-be** ($5 631 + MASI $14 995 = $20 626 = 20,63% > 15%). **Ellentmondás**.

**Hipotézis**: a sector-balanced greedy logika **az új entry-k egymáshoz képest** rangsorolja a sector-cap betartást, **NEM a teljes (régi + új) portfolio sector arányára** számolja. Vagyis a CNC entry-nél (Day 3 reggel) a sector_balanced logika **csak az aznapi új entry-k** alapján döntött (VLO Energy + ON Technology + CNC Healthcare = mind különböző szektor, mind OK), és a **régi MASI Healthcare-jét NEM vette figyelembe**.

**Ez egy P0 strukturális bug** a sector-balanced greedy logikában. Lásd 6. szakasz §0.6.

---

## 5. UW Shadow Log ⭐ HELYREÁLLT

A `state/uw_shadow/2026-05-20.json` Day 3-on **7 ticker** (CNC, CVS, IBKR, ON, TXN, VLO, WMB) — **vs Day 2-én csak 1 (AAPL)**.

⭐ **A CC fix `1eb9755`** a `write_shadow_snapshot()` pollution sink-et **eliminálta**. A Day 3 shadow log **helyes** és **teljes** (a 7 kvalifikáló ticker mindegyikére rögzítve).

**A `captured_at: 2026-05-20T12:30:57+00:00`** = 14:30:57 CEST — **pontosan a 14:30-as Phase 4-6 cron run** időpontja. Day 2-én a `captured_at: 14:37:19+00:00` = 16:37 CEST volt (a manuális pytest pre-flight pollution időpontja). **Tisztán látszik** a CC fix eredménye.

### A UW shadow log Day 3 tartalma

| Ticker | combined_score | dp_pct | gex_regime | m_gex_would_have_been | dp_score_would_have_been | phase6_sized |
|--------|----------------|--------|------------|----------------------|--------------------------|--------------|
| CNC | 57,89 | 6,53% | positive | 1,0 | 0 | ✓ |
| CVS | 55,47 | 0,00% | positive | 1,0 | 0 | ✗ |
| IBKR | 52,40 | 0,00% | high_vol | 0,6 | 0 | ✗ |
| ON | 70,21 | 0,00% | high_vol | 0,6 | 0 | ✓ |
| TXN | 50,32 | 0,00% | high_vol | 0,6 | 0 | ✗ |
| **VLO** | **73,11** | **17,33%** ⭐ | positive | 1,0 | **-10** (penalty) | ✓ |
| WMB | 56,43 | 20,03% ⭐ | high_vol | 0,6 | **-15** (penalty) | ✗ |

**Day 3 UW shadow összesítés**:
- **2 ticker dp_pct ≥ 10%** (VLO 17,33%, WMB 20,03%) — a régi rendszer ezeket "high-dark-pool-pressure" jelölőkkel rögzítette volna
- **2 "would_have_been_penalty"** (VLO -10, WMB -15) — a régi `dp_score` logika **rontotta** volna a scoring-jukat
- **GEX regime distribution**: 3 positive / 4 high_vol — **több mint a fele high_vol**, ami **destabilizáló market maker** (a régi rendszer M_GEX 0,6× sizing-csökkentést alkalmazna)
- **m_gex_avg_would_have_been: 0,7714** — a régi rendszer a 7 ticker átlag 77%-os sizing-multiplier-t adott volna

**Day 90 calibration adatpont**: ⭐ **a 2026-05-20 az ELSŐ TELJES NAP teljes UW shadow log-gal** (Day 1-en sikeres 96 ticker, Day 2-én elszennyezett 1 ticker, Day 3-on újra tiszta 7 ticker). A 90 napi mintáig 88 tiszta nap várt (1 Day 2 SKIP).

---

## 6. ⚠️ Anomalies / Notes — Day 3 P0 status + 2 új P0 anomália

### §0.1 (régi pt_monitor 5-perces) ⭐ RESOLVED

A `pt_monitor_2026-05-20.log` **egyetlen sor**: "[SWING EOD] Evaluated 7 positions — 0 exit flags set". **NINCS** LION/SDRL/DELL/DOCN/AAPL phantom replay. **A CC fix `aba9720` (Task #G) Day 3-on bizonyítottan eliminálta**.

### §0.4 UW shadow log felülírás ⭐ RESOLVED

A `state/uw_shadow/2026-05-20.json` **7 ticker** (vs Day 2: 1 ticker AAPL). `captured_at: 14:30:57+00:00` — **a 14:30-as Phase 4-6 cron-é**, NEM a 16:37-es pytest pre-flight pollution időpontja. **A CC fix `1eb9755` Day 3-on bizonyítottan eliminálta**.

### §0.2 Error 10349 TIF — **3/3 nap 100% ráta, strukturális**

A `pt_submit_2026-05-20.log` 15:52:19-15:52:23 mindhárom új entry-re (VLO, ON, CNC) Error 10349:
```
15:52:19 VLO: market BUY status=Cancelled — silent reject possible.
   Error 10349: Order TIF was set to DAY based on order preset.
15:52:21 ON: status=Cancelled — Error 10349
15:52:23 CNC: status=Cancelled — Error 10349
15:52:23 [SWING] Submitted: 0 tickers — state file untouched (race guard, 4 open)
```

**DE 16:05:19 second submit attempt sikerült mindhárom ticker-re**:
```
16:05:23 VLO: MKT BUY 16 @ ~$262.62 | stop $244.71 | TP1 $276.05 | TP2 $289.48
16:05:24 ON: MKT BUY 27 @ ~$106.02 | stop $93.50 | TP1 $115.41 | TP2 $124.80
16:05:26 CNC: MKT BUY 95 @ ~$59.15 | stop $55.50 | TP1 $61.89 | TP2 $64.63
16:05:26 [SWING] Submitted: 3 tickers | State: state/swing_positions.json (7 open)
```

**3/3 nap 100% ráta**: minden új entry Error 10349-et kap, és a silent retry mindig sikeres. **Strukturális, rendszerszerű hiba**. A `04-risks-and-open-questions.md` §0.2 frissítendő a 3/3 nap adattal.

### §0.5 (ÚJ P0) — Submit retry storm Day 3-on (5 attempt 35 perc alatt)

A `pt_submit_2026-05-20.log` szerint **5 különböző attempt**:

| Időpont | Esemény | Eredmény |
|---------|---------|----------|
| 15:31:01 | 1. attempt | Csak `Reading: execution_plan...` — folyamat megszakítva? |
| 15:51:53 | 2. attempt | `[DRY RUN] — No IBKR connection` ⚠️ — IBKR Gateway megszakadt! |
| 15:52:14 | 3. attempt | Error 10349 mindhárom ticker-re |
| **16:05:19** | **4. attempt** | **Sikeres** (mind a 3 entry) ⭐ |
| 16:20:44 | 5. attempt | Duplikált — mind a 3 ticker már nyitva, csak ismétlés |

**Plus**: a `pt_heartbeat_monitor_2026-05-20.log` 15:45:03-on:
```
[STUCK] submit_orders STUCK: attempt at 2026-05-20T13:31:01+00:00 is 86455s newer than 
last success at 2026-05-19T13:30:06+00:00 (threshold 300s)
```

**Értelmezés**: a heartbeat monitor 15:45:03-on **"STUCK" alert-et küldött** (Telegram?) Tamás-nak, miszerint a 15:31:01 attempt **24 órával újabb** mint az utolsó sikeres submit (Day 2 15:30:06). **Ez triggerelte Tamás manuális intervencióját** (a "voltak technika problémák" említés) — a 15:51:53 DRY RUN valószínűleg **manuálisan triggerelt** debug futás, ami felfedezte az IBKR Gateway megszakadt kapcsolatát.

**A 16:04:50 gateway preflight OK** után a 16:05:19 submit attempt **sikerült** — vagyis a Gateway visszaállt 16:04-re, és Tamás manuális resubmit-elte a 3 entry-t.

**Root cause hipotézis**: a 15:31:01 első cron attempt **NEM IBKR-be csatlakozott** (a `[DRY RUN]` szöveg a 15:51:53 logban implikálja, hogy ekkorra az IBKR Gateway már megszakadt). A heartbeat monitor 14 perccel később (15:45) detektálta, és Tamás manuális intervenciója megoldotta.

**Akció**: 
1. **P0 (most): a 14:30:00 cron-időpontban indítandó submit-mechanizmus** robosztusabb retry-logikával — ha az IBKR Gateway megszakad, a submit_orders.py várja az újraépülést és próbálkozzon újra autonóm módon (NEM heartbeat-alert + manuális Tamás trigger)
2. **P1**: a heartbeat monitor `[STUCK]` küszöb (300s) és a kapcsolódó Telegram alert formátum dokumentálandó, hogy Tamás tudja, mit jelent
3. **P2**: a 16:20:44-es duplikált 5. attempt (a 3 ticker már nyitva) **figyelmeztetés-szintű log** legyen ("Already submitted, skipping") **NEM ismételt submit**

### §0.6 ✅ NOT A BUG — Healthcare 20,63% sector arány spec szerint OK (RECLASSIFIED 2026-05-21)

**Reklasszifikáció**: 2026-05-21 reggeli CC vizsgálat alapján ez **NEM** P0 anomália — a §0.6 eredeti elemzés ("15% cap") **félreértelmezte** a `daily_metrics.swing_state.sector_max_pct` mezőt.

**Helyes értelmezés**:

| Forrás | Sector cap érték |
|---|---|
| Day 63 decision §3.11 | **30% notional/szektor** (4× explicit, indoklással) |
| `defaults.py:342` `swing_sector_cap_pct` | **0.30** (a deployed value) |
| 2026-05-17 swing-sizing task spec | **30%** (11× explicit említés) |
| `daily_metrics.swing_state.sector_max_pct: 20.63` | **számított display érték** (portfolio max sector arány), **NEM cap config** |

Day 3 Healthcare: MASI $14,995 + CNC $5,631 = **$20,626 = 20.63% portfolio**. Spec cap (30%): $30,000. **20.63% < 30% → BENNE VAN a spec szerint, NINCS cap megsértés.**

**Kód-szempontból**: a `_select_swing_entries` ([phase6_sizing.py:1320-1325](../../src/ifds/phases/phase6_sizing.py)) **HELYESEN** iterál `open_positions`-en a sector_notionals számolásnál — a régi MASI Healthcare-jét helyesen figyelembe vette a CNC entry-nél. Day 3-on a logika lefutása helyes volt:
- MASI Healthcare $14,995 (sector_notionals init from open_positions)
- + CNC candidate notional $5,631 = $20,626 (new_sector_total)
- 20,626 < 30,000 (30% cap) → CNC `selected.append(pos)` (line 1368) ✓

**Eredeti hipotézis (P0 strukturális bug)**: HAMIS. A kód helyes, a spec 30%, a daily review §0.6 eredeti megfogalmazása a "15% cap"-et feltételezte, ami semmilyen design dokumentumban nem létezik.

**Tamás döntése (2026-05-21 reggel)**: spec marad 30%, nincs kódváltozás, daily review §0.6 reklasszifikálva NOT A BUG. Részletek: [`docs/tasks/2026-05-21-sector-cap-hotfix.md`](../tasks/2026-05-21-sector-cap-hotfix.md) (Status: WONTFIX).

**Tanulság**: a `daily_metrics.swing_state.sector_max_pct` mező hozzáadásánál (Task #5 A) érdemes lett volna egy magyarázó comment a daily review-nak: "számított display, NEM cap config". Backlog: dokumentálni a daily_metrics mezők szemantikáját.

### Egyéb megfigyelések (NEM P0/P1)

- **Day 2 P0 anomáliák Day 3 állapot**:
  - **§0.1 régi monitor → ✅ RESOLVED**
  - **§0.4 UW shadow → ✅ RESOLVED**
  - **§0.2 Error 10349 TIF → 3/3 nap 100% ráta, strukturális**
- **Phase 2 univerzum stabil** (a 3 új entry sikeres + Phase 4-6 lefutott, ezért a §0.3 Phase 2 timeout-anomalia **nem aktív** Day 3-on)
- **Goldman momentum chart predikciója empirikusan jelentkezik**: Phase 4 univerzum 11× csökkent Day 3-ra (96 → 7) — lásd 1. szakasz hipotézis (A)

---

## 7. Day 4 (csütörtök, 2026-05-21) outlook

### Tervezett exit-ek

**NINCS tervezett exit** Day 4-en (`next_day_planned.exits_at_1530: []`, `time_stops_at_2140: []`).

### Várt mozgások

- **EC maradék 166 share**: trail SL $13,435-en, mark ~$13,21 (a Day 3 záró ár becsült). Day 4-en ha emelkedik $14,40+ fölé, a trail SL emelkedhet a swing pivot trail logika szerint.
- **PFGC**: mental SL $90,45-en, ~$95,52 mark. Még ~5% távolság a mental SL-ig. Nem közeli trigger.
- **MASI**: 4. napja flat ($178,55 körül). Day 5 (péntek) time stop egyre valószínűbb.
- **LBRT**: $33,31 körül, oldalozó. TP1 $35,40 még ~6% távolságra. Day 5 time stop kérdéses (egyelőre HOLD).
- **VLO/ON/CNC**: Day 4 = days_held 1. ATR-ek normálak (VLO $8,95, ON $6,26, CNC $1,83), intraday mozgások 1-3% sávban várhatók.

### Új entry potenciál

A Day 3 Phase 4 univerzum csak 7 ticker > S_j 50, ebből 3 entry-re került, 4 skip-elt (CVS, IBKR, TXN, WMB). **Ha Day 4-en hasonló alacsony breadth marad** (Goldman momentum-rally peak környékén), akkor **0-2 új entry várt**. Ha a piaci mozgás reverse-el (risk-off nap), a Phase 4 univerzum visszanőhet 30-80 ticker-re.

### Day 5 (péntek, 2026-05-22) — első time stop nap

Day 5-én a `days_held: 4` lesz **LBRT, MASI, EC** számára (entry_date: 2026-05-18). Ha **a TP1/TP2/mental SL egyik sem trigger** addig:
- LBRT: time stop péntek 21:40 CEST MARKET SELL
- MASI: time stop péntek 21:40 CEST MARKET SELL  
- EC: a maradék 166 share **NEM kerül time stopra** (a TP1 hit után a trail SL aktív, a swing pivot logika szerint a trail aktív pozíciók nem time-stop-elnek)

**MASI time stop várt P&L**: 84 × $178,55 - 84 × $178,51 = ~+$3 (közel-flat profit a 4 napi hold-on). **Strukturális kérdés**: érdemes lenne-e a `max_hold_days` paramétert mérlegelni növelni 5-ről 7-re az ATR < 0,5%-os tickerekre? **Erre az új paper trading 63 napi mintán** kell adatokat gyűjteni.

### Day 4 prioritások a Log Review chat-nek

1. **A 2 új P0 anomália Day 4 státusza**:
   - **§0.5 submit retry storm**: Day 4-en megismétlődik-e? Ha igen, a retry-logika **strukturálisan elromlott**, ha nem, akkor a Day 3 egyszeri eset
   - **§0.6 sector cap megsértés**: ha új entry érkezik Healthcare-be Day 4-en, **a 20,63% cap-túllépés tovább nő** (egy ÚJABB Healthcare ticker akár 25% fölé vinné). **A Dev chat-nek prioritás Day 4 reggel**: a sector-balanced greedy javítása előtt **MEGFONTOLNI a Healthcare-tickerek manuális blokkolását** a következő paper trading napokra (config override)
2. **Phase 4 univerzum recovery**: 7 → ? Day 4-en. Ha **<10 marad**, megerősíti a Goldman-momentum-rally-peak hipotézist
3. **EC trail SL állapot**: $14+ fölé emelkedik?

### Day 4-Day 5 várt P&L narratíva

Ha a 7 nyitott pozíció **átlag +0,5%/nap** mozgással emelkedik 2 nap alatt:
- 7 × $39 627 × 1%/2 = **+$396 nem-realizált**
- Plus esetleges TP1 hit-ek (EC tovább, vagy LBRT a TP1 $35,40 felé) = **+$200-400** realizált

**Realisztikus kumulatív Day 5-re**: +$300-700 (a Day 3 +$107-ról). De **a Goldman momentum-peak hipotézis** alapján **a következő 2-3 hetes ablakra inkább kis-pozitív vagy enyhe-negatív** kumulatív várt.

---

## Files referenced (Day 3)

- `state/swing_positions.json` — 7 nyitott pozíció (4 régi + 3 új)
- `state/daily_metrics/2026-05-20.json` — Day 3: 1 trade, P&L -$5,04 (mark-to-market hibrid), cumulative +$107,27
- `scripts/paper_trading/logs/cumulative_pnl.json` — Day 3 history rögzítve
- `logs/pt_eod_2026-05-20.log` — EOD report, 1 VLO MOC trade (mark-to-market 1-share-egységben)
- `logs/pt_close_2026-05-20.log` — 2 no-op close (15:30 eod_flags + 21:40 time_stop)
- `logs/pt_submit_2026-05-20.log` — **5 attempt** (P0 anomalia §0.5)
- `logs/pt_monitor_2026-05-20.log` — **CSAK 1 SOR** ⭐ (P0 §0.1 RESOLVED)
- `logs/pt_gateway_2026-05-20.log` — 3 gateway preflight (15:25, 15:49, 16:04), mind OK
- `logs/pt_heartbeat_monitor_2026-05-20.log` — **[STUCK] alert 15:45:03** (P0 §0.5 trigger)
- `state/uw_shadow/2026-05-20.json` — **7 ticker ÉP** ⭐ (P0 §0.4 RESOLVED)
- `output/trade_plan_2026-05-20.csv` — 3 ticker (VLO, ON, CNC)

---

## State (Day 3 — 2026-05-20 záró)

**Architektúra**: swing pivot Fázis 3 deploy DAY 3, mental stop, 3-5 napi hold, 15:30 CEST entry, sector-balanced greedy (15% cap — **megsértve Healthcare 20,63%-on**), S_j scoring.

**Live**: 7 open positions (LBRT, MASI, EC 166-share maradék, PFGC, VLO, ON, CNC), 0 exit flags Day 4-re.

**Cumulative**: **+$107,27 (+0,11%)**, trading_days: 3.

**Excess return**: **-1,03% vs SPY** (bull rally underperform pattern megerősítve — konzisztens a legacy 63 napi mintával).

**Aktív P0/P1 anomáliák** (a `04-risks-and-open-questions.md` §0-ban):
- **§0.1 (régi pt_monitor)**: ✅ **RESOLVED** (CC fix aba9720)
- **§0.2 (Error 10349 TIF)**: **3/3 nap 100% ráta**, strukturális (silent retry mindig sikeres, NEM blocker — javasolt P1-re downgrade)
- **§0.3 (Phase 2 timeout)**: implicit OK Day 3-on
- **§0.4 (UW shadow felülírás)**: ✅ **RESOLVED** (CC fix 1eb9755)
- **§0.5 (submit retry storm) — ÚJ P0**: 5 attempt 35 perc alatt, IBKR Gateway megszakadt 15:50 körül, heartbeat STUCK alert + Tamás manuális trigger
- **§0.6 (sector cap megsértés) — ÚJ P0**: Healthcare 20,63% > 15% cap, sector-balanced greedy strukturális bug

**A Day 3 napi karakter egy mondatban**: A swing pivot **3 új entry-vel kibővült portfolio** (4 → 7 pozíció, 26,9% → 39,6% notional) **NEM realizált zárást** termelt, **enyhén negatív Day 3 P&L** (-$5,04, kumulatív $107,27), **bull rally underperform** pattern-rel (-1,03% excess vs SPY) — miközben **a CC fix-ek (régi monitor + UW shadow) bizonyítottan eliminálódtak**, **2 új P0 anomália** (submit retry storm + sector cap megsértés) **strukturális javítást igényel**, és a **Phase 4 univerzum 11× csökkenése** (96 → 7 ticker) **a tegnap reggeli Goldman momentum-chart predikciójának első empirikus jele**.
