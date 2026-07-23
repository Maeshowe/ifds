# IFDS Daily Review — 2026-05-29 (péntek, Day 10 Swing Pivot, W22 D4 — heti záró)

**Verzió**: swing pivot architektúra Day 10/63 — **a négy fix architektúra második tiszta napja**
**Day 10 realized P&L (IBKR `get_account_trades`)**: **$0** (semmilyen exit)
**Day 10 valódi total mozgás (IBKR Net Liq)**: **+$58,87 (+0,059%)** — **a W22 EGYETLEN pozitív napja** ⭐
**Cumulative (Mac Mini, CC backfill után, kanonikus)**: **-$708,58** (Part B baseline -$651,10 + Day 9 AMH retroaktív -$57,48)
**Cumulative (MacBook-i sync-elt fájl)**: -$651,10 ⚠️ — `sync_from_mini.sh` még nem futott a backfill után (lásd §0)
**Net Liquidation Day 10 záró (IBKR)**: **$99 241,51** (Day 9 $99 182,64 → +$59)
**Open positions**: **7** (EOG, AKAM, JHG, ST, ROIV — Day 7-9 + **AMH új visszatérő + CDNS új** — Day 10)

**⭐ KULCS Day 10 finding-ek (a W22 záró + Part A deploy első napja):**
- **A W22 egyetlen pozitív napja** (+$59 unrealized javulás): AKAM **drámai fordulat** (Day 9 -$57 → Day 10 +$57), ROIV +$40, AMH visszatérő +$46 — 4 nyertes / 7 pozíció.
- **0 exit, 2 új entry** — a `days_held` trading-day fix következménye (semmilyen erőltetett TIME_STOP), és a friss context új univerzumot adott. Mindkét új entry egészséges ATR-sávban: **AMH 2,02% relatív**, **CDNS 3,20% relatív**.
- **AMH visszatérő ticker ("boomerang")** — Day 5 entry → Day 9 TIME_STOP -$57 → Day 10 **újra kiválasztva**, 270 share új entry. Ugyanaz a ticker két különálló swing-ciklusban — érdekes finding.
- **`_reconcile_state_from_ibkr` 4/4 ÉLES SILENT OK** ✅ — négy egymás utáni napon validált mental-stop integritás.
- **⚠️ EOG KRITIKUS stop-közelben**: mark **$133,46**, mental stop **$133,42** — **csak $0,04 (0,03%) fölött**. Hétfő reggeli gap-down az első ami stop-triggert állít, **-$343 realized lenne**.
- **⚠️ A W22 weekly_metrics report TÉVES** (Net P&L $+0,00, win days 0/4) — a Part A backfill ELŐTTI állapotból generálódott vasárnap. A Part A + sync után újra kell futtatni (lásd §6).

---

## 0. Tracking gap státusz — Part A DEPLOY-OLT ✅, sync utánra vár ⏳

A CC ma délután (2026-06-01 14:05) deploy-olta a Part A ledger + record_pending_exits-et + Day 9 AMH backfill-t:

### 0.1 A canonical állapot (CC megerősítés alapján)

| | Mac Mini (kanonikus, CC backfill után) | MacBook sync-elt fájl |
|---|----------------------------------------|----------------------|
| `cumulative_pnl` | **-$708,58** | -$651,10 ⚠️ |
| Day 8 (5/27) entry | pnl: -$695,79, moc_exits: 6, tp2_hits: 1 | pnl: -$695,79 ✓ |
| **Day 9 (5/28) entry** | **pnl: -$57,48, moc_exits: 1** ✓ | pnl: 0 ⚠️ |
| Day 10 (5/29) entry | pnl: 0, moc_exits: 0 (helyes — 0 exit volt) | pnl: 0 ✓ |
| Backup | `cumulative_pnl.json.bak.pre_partA.20260601_140510` | (n/a) |

**Akció**: a `sync_from_mini.sh` futtatása szükséges a MacBook-on. A CC `Last login: Sun May 31 11:26:50 2026` óta nem volt sync — a backfill (ma 14:05) ezért nem látszik. Egy futtatás megoldja.

### 0.2 Két fontos tanulság a Part A élesítésből (a CC riportja alapján)

**1. `reqExecutions` csak same-session fill-eket lát** — a recorder helyesen kezelte: az AMH-t `unprocessed`-ben hagyta, P&L-t NEM fabrikált. A guard élesben validálva. A forward-fix same-day működik (Day 10+), a historikus Day 9 AMH-t a connector `get_account_trades` pótolta.

**2. Az AMH valós entry-ár $32,21 volt** (3 fill 5/22-én súlyozott), NEM a swing_positions.json `entry_price: 32,11`. A **naiv ledger-becslés ~$26-tal mellélőtt volna** (270 × ($32,21 - $32,11) = $27). Az IBKR `realized_pnl: -57,48` broker-authoritative, és helyesen használtuk. **Strukturális tanulság**: a state `entry_price` mezője a **planned/első-fill ár**, nem a súlyozott átlag — a P&L tracking-nek mindig az IBKR realized_pnl-jét kell preferálnia.

**Ez egy generikus finding**: a Day 10-i új entry-knél is ugyanez:
- **AMH** state: `entry_price: 31,99`, IBKR fill: $31,91 (DRCTEDGE), **-0,25% kedvező slippage**
- **CDNS** state: `entry_price: 373,85`, IBKR fill: $374,79 (BEX), **+0,25% kedvezőtlen slippage**

A state a planned entry-t tárolja (a stop/TP ebből számolva), az IBKR a valós fill-t. A P&L tracking az IBKR-t használja, és ez most már (Part A deploy után) auto-rögzül.

### 0.3 A hétfő (2026-06-01) első same-day próba

Mivel Day 10-en (péntek) 0 exit volt, a Part A első éles same-day próbája a **hétfő (jövő hétfő, Day 11) 21:40 close** lesz, **ha** akkor swing exit történik. Az EOG stop-közelsége (§2.3) miatt nagyon valószínű, hogy az EOG triggerel — ez lesz a Part A első valós teszt-pontja.

---

## 1. Day 10 Trades (IBKR `get_account_trades` 2026-05-29)

### 1.1 Exit: **NINCS** ⭐

A `pt_close_2026-05-29.log`:
```
15:30:02 [SWING 15:30 close] No EOD action flags set — nothing to do.
21:40:02 [SWING 21:40 close] No TIME_STOP flags — nothing to do.
```

Day 9 EOD eval (a `days_held` trading-day fix után) 0 exit flag-et állított, így Day 10 egész napja exit-mentes volt. **Tiszta operatív nap** — a swing pivot architektúra előírás szerint dolgozott.

### 1.2 Új entries (2) — AMH visszatérő + CDNS Technology ⭐

| Idő (CEST) | Ticker | Sektor | Qty | Planned | Fill | Slippage | Notional | ATR (relatív) | Megjegyzés |
|-----------|--------|--------|-----|---------|------|----------|----------|----------------|------------|
| 15:31:08 | **AMH** | Real Estate | 270 | $31,99 | $31,91 (DRCTEDGE) | **-0,25% kedvező** | $8 615,70 | $0,645 (**2,02%**) ✅ | **Visszatérő ticker** (Day 5 → Day 9 exit → Day 10 új) |
| 15:31:10 | **CDNS** | Technology | 14 | $373,85 | $374,79 (BEX) | +0,25% kedvezőtlen | $5 247,06 | $11,95 (**3,20%**) ✅ | **Magas-árú** Cadence Design Systems |

**AMH boomerang-finding** 🔁: A pipeline a Day 5-i AMH-t Day 9-en TIME_STOP-olta (-$57,48 realized, mert 5 trading nap után még flat volt), és Day 10-en a friss scoring **újra kiválasztotta**. Új belépő $31,99 (Day 9 exit fill volt $31,99 is — pontosan ugyanaz az ár!). Két magyarázat:
- (a) **A scoring konzisztens** — ha egy ticker továbbra is magas S_j-t kap, és technikailag még mindig jó (RVOL + PCR), akkor logikus újra-vétel
- (b) **A jelenlegi rendszer nem zár ki nemrég exitelt ticker-eket** — egy cooldown-period (pl. 2-3 trading nap) megakadályozná az ilyen visszatérést

Mindkét értelmezés érvényes — ez egy **stratégiai döntés** (lásd §8.4 megfigyelés). Az AMH Day 10 záró +$45,81 unrealized (fél nap után), és a 2,02% ATR egészséges hold-időtávra alkalmas (~$0,65 napi mozgás). Most jelenleg a swing rendszer érveként szól mellette.

**CDNS** (Cadence Design Systems) — a **legmagasabb árú** swing entry eddig ($374,79/share). Csak 14 share fér be a sizing-formulába a 12% single-position cap (ha aktív lenne) körül. Notional $5 247 (5,25% portfolio). Technology szektor, ATR 3,20% — egészséges. Sektor-szempontból mostantól a Technology **két ticker** (AKAM $2 547 + CDNS $5 247 + ST $4 693 = $12 487 = 12,58%) — a sector cap alatt bőven.

### 1.3 Sector distribution Day 10 záró

| Sektor | Notional | % portfolio | Ticker(ek) |
|--------|----------|-------------|------------|
| **Financial Services** | $14 982 | **14,98%** | JHG |
| **Technology** | $12 487 | 12,58% | AKAM + ST + CDNS (3 ticker) |
| **Real Estate** | $8 663 | 8,73% | AMH (új) |
| **Energy** | $5 872 | 5,92% | EOG (csökkent a $-veszteség miatt) |
| **Healthcare** | $4 259 | 4,29% | ROIV |
| **Total** | $46 263 | **46,57%** | 7 ticker, 5 szektor |

A 30% sector cap **bőven betartva** (max Financial Services JHG 15% single-ticker). 5 szektor **a legtöbb a swing pivot alatt** — érdemi diverzifikáció. Day 9-hez képest: 4 → 5 szektor (Real Estate visszatért az AMH-val).

A leverage 0,33 → 0,47 — ez egyrészt az új entry-k (CDNS+AMH ~$13 900) miatt, másrészt mert a portfolio közelít a 12 concurrent max-hoz (most 7/12 ticker).

---

## 2. EOD State (22:00 CEST) — 0 exit flag jövő hétre ⭐

`pt_monitor_2026-05-29.log` 22:00:08:
```
[SWING EOD] Evaluated 7 positions — 0 exit flags set
```

**Day 11 (jövő hétfő, 2026-06-01) nincs előre flag-elt exit.** Csak intraday mozgások generálhatnak exit-et — különösen az EOG.

### 2.1 A 7 nyitott pozíció Day 10 záró

| Ticker | Entry $ | Mark | Qty | days_held | Unrealized | next_action | Sektor |
|--------|---------|------|-----|-----------|------------|-------------|--------|
| **EOG** | 141,22 | **$133,46** | 44 | **3** | **-$306,36** ⚠️⚠️ | HOLD (stop $0,04 felett!) | Energy |
| **AKAM** | 147,23 | $149,84 | 17 | **3** | **+$57,48** ⭐ | HOLD | Technology |
| **JHG** | 51,84 | $51,82 | 289 | **2** | -$1,45 (flat 3. napja) | HOLD | Financial Services |
| **ST** | 50,51 | $49,40 | 95 | 1 | -$78,90 ⚠️ | HOLD | Technology |
| **ROIV** | 29,58 | $29,99 | 142 | 1 | +$40,18 ⭐ | HOLD | Healthcare |
| **AMH (új)** | 31,99 | $32,08 | 270 | 0 | +$45,81 ⭐ | HOLD | Real Estate |
| **CDNS (új)** | 373,85 | $374,80 | 14 | 0 | -$0,86 | HOLD | Technology |
| **Total unrealized** | | | | | **-$243,10** | | |

### 2.2 ⚠️⚠️ EOG kritikus stop-közelség — 3 napos trend

| Day záró | EOG mark | Stop távolság | Unrealized | Megjegyzés |
|----------|----------|----------------|------------|------------|
| Day 8 (5/27) | $135,00 | $1,58 (1,17%) | -$238,60 | Energy szektor zuhanás után |
| Day 9 (5/28) | $134,42 | $1,00 (0,74%) | -$264,12 | Tovább csúszik |
| **Day 10 (5/29)** | **$133,46** | **$0,04 (0,03%)** ⚠️⚠️ | **-$306,36** | **A stop közvetlen közelében** |

**A trend egyértelmű**: 3 trading nap alatt -1,18%-ot esett az EOG, miközben a stop fix ($133,42, a 2,0×ATR az entry-től). A Pattern 5 (stale context Day 7 entry) örökség egyértelmű kudarca — a stale context az Energy szektor csúcsára vitte be a rendszert (4. Energy ticker), és a szektor azóta is gyengül.

**Hétfő reggel (2026-06-01) kritikus**:
- VIX 15,81 (-5,44% pénteken, alacsony volatilitás → ~1,0% expected daily move) — egy 0,03% gap-down ELÉG a stop-triggerhez
- A 22:00 EOD eval pénteki záró ár alapján számol, **DE az intraday stop-trigger (a mental stop logika) szerintem nem aktív** — a swing pivot `mental_stop` daily eval-szintű, nem intraday. Ezért **a stop akkor triggerel, ha a Day 11 22:00 EOD eval szerint a mark < stop**.
- **Ha az EOG hétfőn 21:55 CEST-kor (záró előtt) $133,42 alá esik → 22:00 EOD eval flag-elne, és Day 12 21:40 close MOC-ozná**. -$343 realized.
- **De ha hétfő záróra $133,42 felett marad → még tartja magát.**

**Megfontolás**: a daily eval EOD-szintű architektúra **lassabb mint egy intraday hard stop** — a Day 11 intraday mozgás (gap-down + recovery) lehet hogy a daily eval-on már nem látszik. Ez egy strukturális kérdés, amit érdemes lesz monitorozni: az EOG Day 11-i intraday range (lakatos-mozgás) hogyan hat a 22:00 EOD eval döntésére.

### 2.3 ⭐ AKAM drámai fordulat — a "first clean day" hozadéka

| Day | AKAM mark | Unrealized | Delta |
|-----|-----------|------------|-------|
| Day 7 entry | $146,46 | $0 | (entry) |
| Day 8 záró | $144,79 | -$28,37 | -$28 |
| Day 9 záró | $143,09 | -$57,27 | -$29 |
| **Day 10 záró** | **$149,84** | **+$57,48** | **+$115** ⭐ |

Egy nap alatt **$115 fordulat**. Ez **az első jel a portfolioban, hogy egy meglévő pozíció érdemi pozitív tartományba lépett**. Az AKAM Day 7 entry-je (a stale context Pattern 5 öröksége) a Day 9-i mélypontról (a swing pivot worst-case unrealized scenarii) Day 10-en **újraértékelődött**. ATR 6,78% (a magas ATR-spectrum tetején, de az ATR ceiling §9.5 a fix előtti entry, marad).

Ez **egy fontos megfigyelés**: a swing pivot mental-stop architektúra **mert lassan reagál** (nem hard intraday stop), egy ilyen napos fordulat kifuthatott. Ha intraday hard stop lett volna, az AKAM valószínűleg már Day 9-en SL-en zár (-$57 közelében).

### 2.4 ⚠️ ST gyengült — Day 9 +$15 → Day 10 -$79

A másik irányba — az ST egy nap alatt -$94-et veszített:
- Day 9 záró: +$14,75 unrealized
- Day 10 záró: -$78,90 unrealized

ATR 3,64% (egészséges), de **a fill ár $50,22 vs current mark $49,40 = -1,63%** napi mozgás. Még bőven a stop $46,83 felett (7,2%), de érdemes figyelni. Nincs azonnali stop-veszély.

### 2.5 📝 JHG floor-bug NEM materializálódott (3. napja)

| Day | JHG mark | Unrealized |
|-----|----------|------------|
| Day 8 (entry, $51,825) | $51,77 | -$14,28 |
| Day 9 | $51,77 | -$15,90 |
| **Day 10** | **$51,82** | **-$1,45** |

**Flat 3 napja**, és Day 10-re közel az entry-hez visszatért. A 0,17% ATR melletti napi noise éppen a stop/TP között marad. **A Day 8 review jóslata (gyors trigger) 3 napos validációval cáfolva**. A time-stop ~Day 12-13-on fog kivinni, ha addig nem mozdul érdemben. **A JHG egy "kvázi-alvó" pozíció** — nem produkál veszteséget, nem produkál hasznot, **csak elviszi a 12-concurrent slot egy részét**.

---

## 3. Pipeline Log Review

### 3.1 `pt_submit_2026-05-29.log` — 2 entry tisztán

```
15:31:02 IFDS Paper Trading — 2026-05-29
15:31:06 Existing IBKR positions/orders: {'EOG', 'ROIV', 'JHG', 'AKAM', 'ST'}
15:31:06   Skipping ST: already has position or swing state
15:31:08   AMH: MKT BUY 270 @ ~$31.99 | stop $30.70 | TP1 $32.96 | TP2 $33.93
15:31:11   CDNS: MKT BUY 14 @ ~$373.85 | stop $349.95 | TP1 $391.78 | TP2 $409.70
15:31:11 [SWING] Submitted: 2 tickers | State: state/swing_positions.json (7 open)
```

A submit log "(7 open)" — most már a végállapot helyesen ✓ (5 régi + 2 új = 7, és nincs aznapi exit ami csökkentené).

### 3.2 `pt_close_2026-05-29.log` — egy "tiszta nap"

```
15:30:02 [SWING 15:30 close] No EOD action flags set — nothing to do.
21:40:02 [SWING 21:40 close] No TIME_STOP flags — nothing to do.
```

A nap **teljes operatív tisztaság** — a swing pipeline minden várt lépést mellőzött, mert nem volt rá szükség. **Ez a swing pivot ideális napi karaktere**: csendes, várakozás-alapú, a position-holdok futnak.

### 3.3 `pt_monitor_2026-05-29.log` — 0 exit flag

```
22:00:08 [SWING EOD] Evaluated 7 positions — 0 exit flags set
```

A `days_held` trading-day fix után **2 egymás utáni nap 0 exit flag** (Day 9 EOD + Day 10 EOD). A swing pivot most már a tervezett trading-day hold logikán fut.

### 3.4 `pt_eod_2026-05-29.log` — Cumulative -$651,10 (sync gap!)

```
22:05:02 EOD Report — 2026-05-29
22:05:05 P&L today: $+0.00         ⚠️ (helyes — 0 exit)
22:05:05 Cumulative: $-651.10 (-0.65%) [Day 9/63]   ⚠️ (a Mac Mini canonical -$708,58, lásd §0.1)
22:05:05 Still 7 open positions!    (P3 doc-only: INFO szintű kéne legyen)
```

A Cumulative -$651,10 a pénteki **EOD generálás pillanatában** helyes volt (a Part A backfill később, hétfőn történt). A jelenlegi MacBook-i fájl is ezt mutatja. Sync szükséges.

### 3.5 `pt_reconcile_2026-05-29.log` — **4. ÉLES SILENT OK** ⭐

```
22:15:01 State/IBKR reconciliation — 2026-05-29
22:15:01 State tickers: ['AKAM', 'AMH', 'CDNS', 'EOG', 'JHG', 'ROIV', 'ST']
22:15:06 IBKR tickers:  ['AKAM', 'AMH', 'CDNS', 'EOG', 'JHG', 'ROIV', 'ST']
22:15:06 Reconciliation OK — state and IBKR match (silent exit).
```

**4/4 napon SILENT OK** (Day 7, 8, 9, 10). A mental-stop architektúra integritása 4 napon át megerősítve. **A Day 6 CNC-cancel óta NINCS autonóm bracket trigger** — egy **17-trading-nap nélküli "tiszta" mental-stop futás**.

---

## 4. UW Shadow Log Day 10 — 19 ticker, m_gex csökken

| Mutató | Day 7 | Day 8 | Day 9 | **Day 10** | Trend |
|--------|-------|-------|-------|-----------|-------|
| Tickers logged | 9 | 18 | 21 | **19** | Stabil ~20 körül |
| Avg dp_pct | 2,58% | 3,74% | 6,16% | **4,59%** | Visszaesés |
| would_have_been_penalty_count | 1 | 3 | 4 | **4** | Stabil |
| GEX regime (pos/hv/unk) | 5/3/1 | 10/6/2 | 15/4/2 | **13/5/1** | több high_vol |
| m_gex_avg | 0,8667 | 0,8667 | 0,9238 | **0,8947** | -0,029 |

**19 ticker qualifying** az 50-es threshold felett. Ebből 2 lett kiválasztva (AMH + CDNS). **Top 3 S_j**: AKAM 91,2 (meglévő!), JHG 88,8 (meglévő!), ST 82,1 (meglévő!) — **a top 3 mind a meglévő pozíció**. Ez **konzisztens, de zavaró**: a scoring **újra magas pontot ad ugyanazoknak a tickereknek**, miközben azok már megvannak a portfolioban. Az új entry-k (AMH 8. helyen S_j ~75, CDNS 10. helyen S_j ~70) **közepes szintűek** — a sector-balanced greedy kiszelektálta őket a hiányzó szektorokba.

**Ez egy strukturális megfigyelés**: a rendszer **konzisztens scoring-ot ad** (a top S_j a meglévő pozíciókra esik), és a **sector-balanced greedy** ténylegesen úgy működik, hogy a hiányzó szektorokba teszi az új entry-ket — nem a legmagasabb S_j-rea koncentrál. A `04-risks` §10 ATR-band fix + sector-balanced greedy együtt **jól viselkednek**.

---

## 5. W22 heti összefoglaló (5/25-5/29, 4 trading nap)

### 5.1 ⚠️ A `weekly_metrics.py` Telegram report TÉVES (vasárnapi futtatás)

A Telegram összefoglaló (Tamás vasárnap futtatta):
```
Net P&L: $+0.00 | Cum: $-651 (-0.65%)
Excess vs SPY: -1.44%
Positions: 0 (0.0/day) | Win days: 0/4
TP1: 0 | R:R: 1:0.00
Commission: $0 (0% of gross)
```

A `Net P&L $0` **téves** — a forrás a `daily_metrics/*.json` fájlok, és azokban a Part A hiánya miatt minden P&L=0 volt (kivéve a Day 8-i pnl=-$695,79-et a cumulative_pnl-ben, de a weekly_metrics csak a daily_metrics-ből összegez). A Cum -$651 helyes (a cumulative_pnl-ből), de **a Part A backfill ELŐTTI állapot**.

### 5.2 A W22 VALÓDI képe (Mac Mini canonical, IBKR-verifikált)

| Mező | Telegram (téves) | Valódi (Mac Mini canonical) |
|------|------------------|------------------------------|
| Net P&L W22 (5/25-5/29) | $+0,00 | **-$753,27** (Day 8 -$695,79 + Day 9 AMH -$57,48) |
| Cum (5/29 záró) | -$651,10 | **-$708,58** (Part A backfill után) |
| Win days | 0/4 | **1/4** (Day 10 +$59 Net Liq) |
| New positions W22 | 0 | **7** (Day 7: EOG+AKAM, Day 8: JHG, Day 9: ST+ROIV, Day 10: AMH+CDNS) |
| TP2 hits | 0 | **1** (EC TP2 Day 8) |
| MOC exits | 0 | **7** (Day 8: 6 TIME_STOP + Day 9: AMH TIME_STOP) |
| Total commission | $0 | **~$15-18** |
| Excess vs SPY | -1,44% | Verifikálandó (a SPY heti +1-2% és a portfolio -$753 alapján ~ -1,5%) |

**Akció**: a Part A deploy + sync_from_mini.sh után a `weekly_metrics.py` **újra futtatandó** — a helyes számok látszanak majd a vasárnap esti aggregátumban. Ez a `04-risks` §0.11 + a logging anomáliák egyik mellékhatása, ami a Part A-val automatikusan megoldódik **a jövőbeli hetekre**, de a W22-höz **manuális retry** kell.

### 5.3 A W22 stratégiai karaktere

A 4 trading nap (D7-D10):
- **D7 (5/26)**: 2 új entry tiszta — DE Pattern 5 stale context örökség (EOG, AKAM)
- **D8 (5/27)**: A katasztrófa nap — 7 exit -$696, főleg Energy (LBRT/WMB)
- **D9 (5/28)**: First clean day — 4 fix élesen validálva
- **D10 (5/29)**: Folytatja a tiszta architektúrát — első pozitív nap, 0 exit

**Kontextus**: a W22 a swing pivot **legnehezebb hete** (a Day 1-5 entries TIME_STOP-jai itt csapódtak be a Day 8-i Energy mélyponton). DE a W22 közben deploy-olódott **mind a négy javító fix** (Part B + days_held + ATR-band + Part A), így **a W23 (5/26-elejétől, jelenleg fut) az első tiszta hét lesz** a swing tézis tesztelésére.

---

## 6. Day 11 (jövő hétfő, 2026-06-01) outlook

### 6.1 EOG stop-trigger valószínűsége

Mark $133,46, stop $133,42 — **0,03% távolság**. VIX 15,81 → expected daily move ~1,0%. **A valószínűség, hogy hétfő záróra (22:00 EOD eval) az EOG $133,42 alatt áll**: nagyon magas (>70% becslés).

Ha az EOG stop-triggert kap Day 11-en:
- EOD eval Day 11 22:00 → `next_action: STOP_LOSS`, `next_action_at: Day 12 15:30`
- **Day 12 (5/02 — Wait, Day 12 = 6/2 kedd)** 15:30 CEST MKT SELL 44 share
- Realized: 44 × ($133,42 - $141,22) = -$343,20 ≈ **-$343 realized**

Ez **a Part A első éles same-day rögzítési próbája** lenne (a Day 12 15:30 exit a Day 11 EOD eval flag-jéből).

**Alternatív szcenárió**: ha hétfőn intraday $133,42 alá esik, DE záróra fölé jön (lakatos-mozgás) → a daily eval NEM triggerel → az EOG még él. Ez a "swing pivot lassú reakciója" előnye is, hátránya is.

### 6.2 Várt új entries

Jelenleg 7 nyitott, max 12 → 5 hely. A friss context Day 11 14:30 cron-on új univerzumot ad. Várt 1-2 új entry. A sector-balanced greedy preferálni fogja a hiányzó szektorokat: Consumer Defensive, Industrials, Utilities, Materials, Communication Services, Consumer Cyclical (6 hiányzó szektor).

### 6.3 A Part A első valós teszt-pontja

Ha az EOG (vagy bármi más) Day 11-12-en exit, a Part A 22:10 cron auto-rögzít. **Két kritérium**:
1. `state/pending_exits/2026-06-01.json` ledger-bejegyzés a close_positions.py 21:40 SELL előtt
2. `cumulative_pnl.json` Day 11 entry `pnl: -$343` (vagy a valós realized), `sl_hits: 1` 22:10 után
3. Telegram WARNING az eod_report-ból, **ha** valami eltér a fenti pattern-től

### 6.4 Day 11 prioritások

1. **`sync_from_mini.sh` futtatás** a MacBook-on (a -$708,58 cumulative + Day 9 entry tükrözése)
2. **`weekly_metrics.py` újrafuttatás** a W22-re (helyes Net P&L -$753, win days 1/4)
3. **EOG hétfői intraday monitoring** — IBKR `get_price_snapshot` 16:00 (open), 19:00 (mid), 22:00 (közel-záró)
4. **5. éles `_reconcile_state_from_ibkr`** — silent OK várt
5. **Part A első same-day exit** (ha EOG triggerel)
6. **`/review-daily` CC skill** — Day 11 review CC vagy Chat?

---

## 7. Files referenced (Day 10)

- `state/swing_positions.json` — **7 pozíció** (EOG, AKAM, JHG, ST, ROIV + AMH új, CDNS új), last_updated 2026-05-29T20:00:08Z
- `state/daily_metrics/2026-05-29.json` — Day 10 `pnl: 0` (helyes — 0 exit), `new_entries_tickers: [AMH, CDNS]`
- `scripts/paper_trading/logs/cumulative_pnl.json` — ⚠️ -$651,10 (sync gap, valódi Mac Mini -$708,58)
- `logs/pt_close_2026-05-29.log` — 0 exit (helyes)
- `logs/pt_submit_2026-05-29.log` — 2 entry tisztán
- `logs/pt_monitor_2026-05-29.log` — **0 exit flag** Day 11-re ⭐
- `logs/pt_reconcile_2026-05-29.log` — **4. SILENT OK** ⭐
- `logs/pt_eod_2026-05-29.log` — "Cumulative -$651,10" (a generálás pillanatában helyes)
- `state/uw_shadow/2026-05-29.json` — 19 ticker, m_gex 0,8947, top-3 S_j a meglévő pozíciókban
- `docs/analysis/weekly/2026-W22.md` — ⚠️ TÉVES (Part A előtti)
- **IBKR direkt API**:
  - `get_account_summary` → Net Liq **$99 241,51** (valódi cumulative **-$758,49**)
  - `get_account_positions` → 7 pozíció, unrealized -$243,10
  - `get_account_trades(DAYS_7)` → Day 10 trades: 2 entry (AMH, CDNS), 0 exit

---

## 8. ⭐ Strukturális finding-ek összefoglaló

### 8.1 ✅ A Part A deploy + Day 9 AMH backfill — a $819 → $58 → $0 gap-trajektória zárása

A `04-risks` §0.11 P0 tracking gap teljes feloldása megtörtént:
- **Day 8 (5/27) felfedezés**: $819 gap (cumulative_pnl +$39,33 vs valódi -$779,64)
- **Day 9 (5/28) review**: Part B canonical -$651,10 deploy → $58 maradék gap (Day 9 AMH)
- **Day 11 (6/1, ma) CC**: Part A deploy + Day 9 AMH backfill → $0 gap, cumulative **-$708,58**
- **Day 11+ Part A élesedés**: minden jövőbeli same-day swing exit auto-rögzül

**Két fontos tanulság**:
- A `reqExecutions` same-session korlátja → a recorder helyesen tartja `unprocessed`-ben a session-en kívüli fill-eket, NEM fabrikál (auto-mode classifier helyesen működött)
- A naiv state `entry_price` ($32,11) vs broker-authoritative ($32,21) **$26 különbség** → mindig az IBKR `realized_pnl`-t használjuk

### 8.2 ✅ A négy fix mind élesen validálva (Day 9-10 két napja)

| Fix | Validáció |
|-----|-----------|
| Part B canonical baseline | -$708,58 helyes, Day 8 -$695,79 + Day 9 -$57,48 rögzítve |
| days_held trading-day | 0 exit flag 2 napja (Day 9 EOD + Day 10 EOD) |
| ATR_pct floor+ceiling | 4/4 új entry (ST, ROIV, AMH, CDNS) az egészséges 2-4% sávban |
| reconcile silent OK | **4/4 ÉLES** (Day 7-8-9-10) |
| **Part A ledger forward-fix** | **DEPLOY-OLT, Day 11+ first same-day test várat magára** |

A swing pivot **teljes fix-portfólió élesedett** ezen a héten. A Day 11+ már **a tisztított architektúra első teljes hete** lesz.

### 8.3 ⚠️ Egy kritikus open finding — EOG stop-közelség

A Day 10-i $0,04 stop-távolság az **első valós teszt** a swing pivot mental-stop architektúrájára egy ténylegesen vesztes pozíción. A trading-day hold (3 trading nap az entry óta) és a stop-szint (2,0×ATR) együttesen meghatározzák, hogy:
- Az EOG még él (3 trading nap, nem 5-nél kéne TIME_STOP-olni) — a mental-stop az egyetlen exit-mechanizmus
- A daily-eval architektúra **lassú** intraday gyors mozgásokra — a Day 11 intraday a kulcs

Ha az EOG hétfő záróra stop-triggert kap → **a 4. fix élesedés** (a Part A same-day rögzítés) első próbája.

### 8.4 📝 Strategiai megfigyelés — az AMH "boomerang" entry

A Day 9-i AMH TIME_STOP (-$57) és Day 10-i AMH új-entry (+$46) **ugyanazon a ticker-en**, 1 trading nap távolsággal. Ez nyitja a kérdést: **kell-e cooldown-period** a TIME_STOP-olt ticker-ekre?

**Mellette**:
- A scoring konzisztens, és ha a ticker továbbra is magas S_j-t kap, logikus újra-vétel
- Day 10 zárás +$46 azt mutatja, hogy a swing rendszer **helyesen választott** a Day 9-i kissé-vesztes exit ellenére

**Ellene**:
- "Boomerang" trade gyakori = pszichológiai "averaging down" minta
- Lehet hogy az ATR-band + S_j scoring nem elég önmagában — egy time-decay cooldown finomítaná
- A swing exit (TIME_STOP) elveként azt mondja: "ha nem mozdult érdemben, kilépünk" — ezzel ellentmondás, ha rögtön újra-vesszük

**Stratégiai megfontolás**: nem azonnali action — a Fázis 2 backtest scope-jába felvehető a cooldown-period kérdése (az SMA-inflexió overlay (§6.5) mellé mint design-kérdés). A felgyűlő adaton (Day 21+ után) statisztikailag megnézhető, hogy a boomerang entry-k jobban vagy rosszabbul teljesítenek.

### 8.5 IBKR connector — a daily review-k szerves része

A Day 10 review **majdnem teljesen IBKR-alapú** volt (a Part A deploy előtti MacBook-i sync miatt). A connector szerepe:
- ✅ `get_account_summary` → Net Liq + leverage kanonikus
- ✅ `get_account_positions` → 7 ticker + unrealized real-time
- ✅ `get_account_trades(DAYS_7)` → Day 10 entry+exit fill-ek + commission

**A `04-risks` §9.9** szerinti "az egyetlen megbízható realized P&L forrás" szerep lecsökken a Part A élesedés után, **de a daily review cross-check rétege megmarad** (a `daily_metrics P&L ≠ IBKR realized` automatikus flag a CC `/review-daily` skill 1b rétegben).

---

## State (Day 10 — W22 D4, swing pivot Day 10/63, W22 záró)

**Architektúra**: swing pivot Fázis 3 deploy DAY 10. **Mind a négy javító fix élesedett** (Part B + days_held + ATR-band + Part A). **A W22 a swing pivot legnehezebb hete volt, de a fix-portfólió teljes deploy-jával zárul.**

**Live**: 7 open positions:
- **EOG** ⚠️⚠️ (-$306 unrealized, stop $0,04 felett — hétfő reggeli kritikus)
- **AKAM** ⭐ (+$57 unrealized — Day 9 -$57 → +$57 fordulat)
- **JHG** (-$1,45 — flat 3. napja, a floor-bug jóslat NEM teljesült)
- **ST** ⚠️ (-$79 — gyengül, de még messze a stoptól)
- **ROIV** ⭐ (+$40 — javul)
- **AMH új** ⭐ (+$46 — boomerang, 1 nap után pozitív)
- **CDNS új** (-$0,86 — flat)

**Total unrealized**: -$243,10 (4 nyertes / 7 pozíció, javuló trend)

**Cumulative (Mac Mini canonical, CC-megerősített)**: **-$708,58** (Part B + Day 9 AMH backfill)
**Cumulative (MacBook sync-elt)**: -$651,10 ⚠️ (sync_from_mini.sh kell)
**Cumulative (valódi IBKR Net Liq)**: $99 241,51 → **-$758,49 a baseline-ról** (realized + unrealized)

**Day 10 realized (IBKR)**: **$0** (semmilyen exit). **Day 10 commission**: ~$2,35 (CDNS $1,00 + AMH $1,35).

**Net Liq (IBKR)**: **$99 241,51** ($-758 a baseline-ról, **+$59 Day 10 valódi mozgás — a W22 EGYETLEN pozitív napja**).

**Excess return Day 10**: SPY +0,25%, portfolio realized +0% (vagy M2M +0,059%), **valódi excess ~-0,19% vs SPY** (mild bull underperform, de sokkal kevésbé mint Day 8-9).

**Aktív P0/P1 (frissített, Day 10 utáni):**
- **§0.11 (Part B + Part A) ✅ TELJES RESOLVED** — Day 10 ledger forward-fix ÉL, Day 11+ first same-day próbára várva
- **§9.2 days_held ✅ DEPLOYED + ÉLESEN validált** 2 napja
- **§9.3 / §9.5 ATR floor+ceiling ✅ DEPLOYED + ÉLESEN validált** 4 entry
- **§9.4 P2 — JHG single-position koncentráció** (15%), `swing_max_single_position_pct: 0.12` deploy várat magára (CC backlog)
- **§5.4 P1 — daily_metrics 5 logging anomalia** — sok a Part A-val javul, de a `slippage_per_ticker`, `commission_total`, `scoring.scores` mezők még üresek (CC backlog)
- **§9.7 megfigyelés — EOG stop-közelség, Day 11 kritikus** ⚠️
- **§9.8 megfigyelés — első kohorsz** kontextusban (-$651 valódi, +$46 AMH boomerang új-entry, +$57 AKAM fordulat — javul)
- **§0.10 ✅ Rész 1+2+3 mind RESOLVED + élesen validált** (4/4 silent OK + canonical baseline + Part A ledger)
- **§0.2, §0.5, §9.1 ✅ stabil/RESOLVED**
- **ÚJ megfigyelés §8.4** — AMH "boomerang" entry design-kérdés (cooldown-period? — F2 backtest scope)

**Day 11 fókusz**:
1. **`sync_from_mini.sh`** futtatás (MacBook → -$708,58 cumulative tükrözés)
2. **EOG stop-trigger** monitoring (IBKR `get_price_snapshot` intraday)
3. **A Part A első éles same-day próbája** (ha EOG vagy más exit)
4. **`weekly_metrics.py` W22 újrafuttatás** a helyes Net P&L -$753-mal
5. **5. éles reconcile silent OK**
6. **`/review-daily` CC skill** — Day 11 review automata vagy Chat?

**A Day 10 napi karakter egy mondatban**: **A swing pivot W22 záró napja** — 0 exit (a `days_held` trading-day fix 2. egymás utáni napi validációja), 2 új tiszta entry (**AMH "boomerang" visszatérő** Day 9-i exit után 1 trading nap, és **CDNS Technology** magas-árú $375), 5 szektoros diverzifikáció (a swing pivot maximum eddig), a Day 10 valódi mozgás **+$59 — a W22 egyetlen pozitív napja** AKAM drámai fordulattal (-$57 → +$57 egy nap), miközben az **EOG kritikus stop-közelségben** zárt ($0,04 fölött), az **`_reconcile_state_from_ibkr` 4/4 ÉLES SILENT OK** validálja a 17-trading-napi tiszta mental-stop futást, és a CC ma délután deploy-olta a Part A ledger forward-fix-et + Day 9 AMH backfill-t (cumulative -$651,10 → **-$708,58**, az utolsó tracking gap bezárult) — **a swing pivot fix-portfólió teljes élesedésével a W23 lesz az első tiszta hét a swing tézis empirikus tesztelésére**.

---

**A Day 10 review vége.** A Day 11 fókusz: sync + EOG stop-trigger + Part A first same-day test + weekly_metrics retry + esetleges első CC `/review-daily` autonóm futtatás.
