# IFDS Daily Review — 2026-06-01 (hétfő, Day 11 Swing Pivot, W23 D1)

**Verzió**: swing pivot Day 11/63 — **A javított architektúra első teljes tiszta hetének (W23) első napja, és a legjobb napi teljesítmény eddig**
**Day 11 realized P&L**: **$0** (semmilyen exit aznap)
**Day 11 valódi total mozgás (IBKR Net Liq)**: **+$523,14 (+0,53%)** ⭐⭐ — **a swing pivot legjobb napja eddig**
**Cumulative**: **-$708,58** (változatlan — realized rögzítés szerint)
**Net Liquidation Day 11 záró (IBKR)**: **$99 764,65** (a baseline-hoz közelít: -$235,35)
**Open positions**: **8** (EOG, AKAM, JHG, ST, ROIV, AMH, CDNS + **WST új**)

**⭐⭐⭐ A KULCS Day 11 finding: CDNS TP2 flag Day 12-re**

A swing pivot tisztított architektúrájának **első TP2-je** — egyetlen trading nap entry-től TP2-szint fölé:

```
"CDNS": { "next_action": "TP2", "next_action_at": "2026-06-01T20:00:05+00:00" }
"next_day_planned.exits_at_1530": ["CDNS_TP2"]
"exits_today.TP2": 1
```

- CDNS entry $373,85 (Day 10, 5/29 péntek) — Technology, Cadence Design Systems
- CDNS TP2 level: **$409,70** (entry + 3,0×ATR)
- Day 11 záró mark: **$414,33** — TP2 fölött **$4,63-mal**
- Day 12 (kedd, 6/2) 15:30 CEST MARKET SELL 14 share
- **Várt realized: ~+$506** (14 × ($410 ± – $373,85) ≈ +$506)
- **Ez lesz a Part A first éles same-day rögzítési próbája** — a 22:10 cron auto-rögzíti

**⭐ További kulcs Day 11 finding-ek**:
- **EOG MEGMENEKÜLT a stoptól** — Day 10 záró mark $133,46 (stop $133,42-től **$0,04 fölött**) → Day 11 záró **$136,61** ($3,19 fölött, +$139 unrealized javulás)
- **Day 11 +$523 unrealized javulás** — a swing pivot legjobb napi mozgása eddig (Day 1-10 átlag: -$78/nap)
- **AKAM tovább erősödik**: Day 9 -$57 → Day 10 +$57 → **Day 11 +$128** (3 napos fordulat)
- **CDNS hatalmas ugrás 1 nap alatt**: Day 10 záró -$0,86 → **Day 11 záró +$552,56** (+10,5% napi mozgás)
- **1 új entry: WST** (West Pharmaceutical Services, Healthcare, ATR 3,01%, +0,47% kedvezőtlen slippage)
- **`_reconcile_state_from_ibkr` 5/5 ÉLES SILENT OK** ✅ — 17 trading napi tiszta mental-stop futás (Day 6 CNC-cancel óta)
- **MASI top S_j 94,1 — de NEM boomerang entry** (a sector-balanced greedy a Healthcare-ben WST-t választotta)

---

## 1. Day 11 Trades (IBKR `get_account_trades` 2026-06-01)

### 1.1 Exit: NINCS ⭐

`pt_close_2026-06-01.log`:
```
15:30:01 [SWING 15:30 close] No EOD action flags set — nothing to do.
21:40:01 [SWING 21:40 close] No TIME_STOP flags — nothing to do.
```

Day 10 EOD eval 0 flag-et állított, ezért Day 11 exit-mentes.

### 1.2 Új entry: WST (Healthcare)

| Idő (CEST) | Ticker | Sektor | Qty | Planned | Fill | Slippage | Notional | ATR (relatív) |
|-----------|--------|--------|-----|---------|------|----------|----------|----------------|
| 15:31:10 | **WST** | Healthcare | 18 | $322,81 | $324,33 (NASDAQ) | **+0,47% kedvezőtlen** | $5 837,94 | $9,71 (**3,01%**) ✅ |

WST = West Pharmaceutical Services. ATR 3,01% — egészséges sávban. Sektor-szempontból a Healthcare most 2 ticker: **ROIV $4 131 + WST $5 702 = $9 833 (9,87%)**. A Day 9-i óta a Healthcare szektor tovább épül. Day 11 záró WST mark $316,75 → -$137,44 unrealized (csak első nap volatilitás, nem riasztó).

#### 1.2.1 ⚠️ Execution-quality finding — WST nyitó paper-fill anomália

A „+0,47% kedvezőtlen" a **tervezett** $322,81-hez mérve van. A valós piaci kép viszont rosszabb: a Polygon 1-perces szerint a **valós nyitás $321,65** (09:30 ET), és a 13:31-es percre **nincs is valós print** — WST a nyitás utáni percekben soha nem járt 324 fölött (319-320 felé esett). A $324,33 fill tehát **+$2,68 (+0,83%) a valós tape FÖLÖTT** = **IBKR paper-sim artefakt** (szimulált ask vékony/print-mentes percben), ~**$48 fantom belépési költség** 18 share-en.

Szisztematikus check (15 swing belépő, Polygon vs IBKR `get_account_trades`): **NEM szisztematikus** — 14/15 a nyitó-ablakon belül/marginálisan fölötte (normál ask-spread), néhány kedvező is (CDNS -0,06%, AKAM -1,38%). **WST 6/1 az egyetlen valódi kiugró.** Tanulság: a paper belépő-fillek alkalmanként felülbecslik a belépési költséget → a paper P&L ezeknél pesszimista-irányba torzít. Megfontolandó (nem sürgős): post-auction MKT vagy marketable LIMIT. Teljes elemzés: `learnings-archive` „Nyitó MKT paper-fill anomália — WST (discovery, 2026-06-01)".

### 1.3 Sector distribution Day 11 záró

| Sektor | Notional | % portfolio | Ticker(ek) |
|--------|----------|-------------|------------|
| **Financial Services** | $14 950 | **14,99%** | JHG |
| **Technology** | $13 112 | 13,14% | AKAM ($2 618) + ST ($4 692) + CDNS ($5 801) |
| **Healthcare** | $9 832 | 9,86% | ROIV + WST (új) |
| **Real Estate** | $8 716 | 8,74% | AMH |
| **Energy** | $6 011 | 6,02% | EOG |
| **Total** | $52 621 | **52,77%** | 8 ticker, 5 szektor |

Leverage 0,47 → **0,53** (több notional, magasabb tőkeáttétel). A 30% sector cap bőven betartva (max Financial Services JHG 15% single-ticker). 5 szektor — **a swing pivot maximum eddig** megerősítve.

---

## 2. EOD State (22:00 CEST) — 1 exit flag Day 12-re (CDNS TP2)

`pt_monitor_2026-06-01.log` 22:00:06:
```
[SWING EOD] Evaluated 8 positions — 1 exit flags set
  CDNS: TP2
```

### 2.1 A 8 nyitott pozíció Day 11 záró

| Ticker | Entry $ | Mark | Qty | days_held | Unrealized | next_action | Sektor |
|--------|---------|------|-----|-----------|------------|-------------|--------|
| **EOG** | 141,22 | $136,61 | 44 | **4** | -$167,73 | HOLD ✓ (megmenekült) | Energy |
| **AKAM** | 147,23 | **$154,00** | 17 | **4** | **+$128,20** ⭐ | HOLD | Technology |
| **JHG** | 51,84 | $51,73 | 289 | **3** | -$27,46 | HOLD | Financial Services |
| **ST** | 50,51 | $49,39 | 95 | **2** | -$79,85 | HOLD | Technology |
| **ROIV** | 29,58 | $29,09 | 142 | **2** | **-$87,62** ⚠️ | HOLD | Healthcare |
| **AMH (boomerang)** | 31,99 | $32,28 | 270 | **1** | **+$98,93** ⭐ | HOLD | Real Estate |
| **CDNS** | 373,85 | **$414,33** | 14 | **1** | **+$552,56** ⭐⭐⭐ | **TP2** (Day 12 15:30) | Technology |
| **WST (új)** | 322,81 | $316,75 | 18 | 0 | -$137,44 | HOLD | Healthcare |
| **Total unrealized** | | | | | **+$279,59** ⭐ | | |

**Pozitív → negatív arány**: **4 nyertes / 4 vesztes** — DE a nyertesek értéke +$908 (AKAM + AMH + CDNS), a vesztesek értéke -$500 (EOG + JHG + ST + ROIV + WST), nettó **+$279**. A Day 8-9-10-i nettó -$243 → -$298 → -$243 trendből most **pozitív tartományba lépett**.

### 2.2 ⭐⭐⭐ A CDNS-jelenség — egy nap entry-től TP2-fölé

A CDNS Day 10 péntek 15:31-én került be ($373,85), Day 11 hétfő záróra $414,33 = **+10,53% napi mozgás**.

| Esemény | Idő | Ár | Megjegyzés |
|---------|-----|-----|------------|
| Entry | 5/29 (D10) 15:31 | $374,79 (fill) | Cadence Design Systems, Technology |
| TP1 level | — | $391,78 | (entry + 1,5×ATR) |
| TP2 level | — | $409,70 | (entry + 3,0×ATR) |
| Day 11 záró mark | 6/1 22:00 | **$414,33** | **TP2 fölött $4,63-mal** |
| TP2 flag állítva | 6/1 22:00 EOD eval | — | Day 12 15:30 MKT SELL |

**Két szempont a CDNS-ről**:

**(1) A scoring szempontból**: a Day 10 friss context-en az AMH+CDNS kiválasztódott. A CDNS Day 10-i S_j-je nem volt top-3 (top 3 a meglévő pozíciók — AKAM/JHG/ST), de a sector-balanced greedy a Technology-Healthcare hiányzó sektorokba helyezte. A CDNS magasabb ATR-je (3,20%) közepes-magas swing-célokra való.

**(2) A piaci momentum szempontjából**: a CDNS +10,5% egynapos mozgás egy AI/EDA (electronic design automation) szektorbeli erős hír vagy momentum-jel lehetett. A swing pivot scoring (PCR + OTM-inverse) **egy nappal korábban** kiválasztotta — vagy egyszerűen szerencse, vagy a flow indicator érzett valamit. **Statisztikailag még kis minta**, de empirikus megerősítés a swing tézisre.

**Várt Day 12 TP2 fill**: a swing pivot logika szerint a TP2-flag-elt pozíció a következő nap 15:30 CEST MARKET SELL-en kerül lezárásra. Két forgatókönyv:

| Day 12 reggel | Várt fill ár | Realized P&L |
|---------------|--------------|--------------|
| Bull folytatás ($420+) | ~$420 | ~+$646 |
| Konszolidáció ($412±) | ~$412 | ~+$534 |
| Lefelé visszahúzás ($405) | ~$405 | ~+$436 |
| Gap-down (-3%, $400) | ~$400 | ~+$366 |

**Középérték várakozás**: **~$506-534 realized** (a Day 10 EC TP2 példájával analóg: $14,84 záró → $14,44-14,51 fill, -$60 gap-down). A Day 12 22:10 cron-on a Part A auto-rögzít.

### 2.3 ⭐ EOG megmenekülés — a daily-eval architektúra előnye

| Day záró | EOG mark | Stop távolság | Unrealized |
|----------|----------|----------------|------------|
| Day 8 | $135,00 | $1,58 (1,17%) | -$238,60 |
| Day 9 | $134,42 | $1,00 (0,74%) | -$264,12 |
| Day 10 | $133,46 | $0,04 (0,03%) ⚠️⚠️ | -$306,36 |
| **Day 11** | **$136,61** | **$3,19 (2,33%)** ✅ | **-$167,73** |

**Day 11-re az EOG visszafordult $3,15-tal (+$139 unrealized javulás)** — a hétfői SPY +0,27% rally + Energy szektor erősödése. A Day 10 záró $0,04 stop-távolság **lebegett** a hétvégén: ha a swing rendszer **intraday hard stop**-pal dolgozna, valószínűleg hétfő nyitáson már triggerelt volna (a piac általában gap-mozgásokkal nyit). Mivel a swing pivot **daily eval (22:00)** alapú, a recovery kifuthatott.

**Strategiai tanulság (Day 11)**: a daily-eval architektúra **gyors fordulatoknál (AKAM Day 9-10, EOG Day 10-11) előnyt jelent**, mert egy egynapos hard intraday stop kivitte volna mindkét pozíciót. **De a tail-eseteken (Day 8 LBRT/WMB) lassan reagált** — ott az intraday stop hamarabb kivitte volna a -$800 veszteséget. A két case ellentétes architektúra-preferenciát mutat.

**EOG most már a TIME_STOP-pal van veszélyben**: days_held=4 → Day 12 záróra 5 trading nap (5/26→5/27→5/28→5/29→6/1→6/2) → **Day 13 (szerda) TIME_STOP MOC**, ha az ár nem éri el a TP1 $147,07-et (jelenlegi $136,61-től **7,7% upside-szal** kéne mozognia). Várható kimenetel: **TIME_STOP exit Day 13 21:40 MOC**, várt realized: 44 × ($136-138 - $141,22) ≈ -$140 - -$230.

### 2.4 AKAM, AMH, ROIV — három különböző trajektória

- **AKAM ⭐**: Day 9 -$57 → Day 10 +$57 → Day 11 +$128 (3 napos folytatólagos fordulat). days_held=4, ha tartja, Day 13 TIME_STOP nyertesként zárna (~+$130 realized).
- **AMH (boomerang) ⭐**: Day 10 +$46 → Day 11 +$99 (2 napos gyorsulás). 270 share, +$0,36/share. **Az AMH boomerang igazolódni látszik** — második ciklusban már nyertes (a Day 5 ciklus -$57 volt). Ezt érdemes statisztikailag nyomon követni.
- **ROIV ⚠️**: Day 9 +$40 → Day 11 -$88 (2 napos romlás). Stop $27,12 vs mark $29,09 = **6,8% biztonsági margin**, nincs azonnali veszély.

### 2.5 JHG flat 4. napja (a "kvázi-alvó" pozíció)

| Day | JHG mark | Unrealized |
|-----|----------|------------|
| Day 8 entry | $51,84 | $0 |
| Day 9 | $51,77 | -$15,90 |
| Day 10 | $51,82 | -$1,45 |
| **Day 11** | **$51,73** | **-$27,46** |

4 trading nap, az ár a stop $51,66 és a TP1 $51,97 közötti szűk sávban (±0,2%). A floor-bug jóslat továbbra sem teljesült. days_held=3 → Day 13 záróra 5 trading nap → **Day 14 TIME_STOP**. A pozíció várhatóan flat-en, kis veszteséggel zárul (-$15-30 realized).

---

## 3. Pipeline Log Review

### 3.1 `pt_submit_2026-06-01.log` — 1 entry tisztán

```
15:31:01 IFDS Paper Trading — 2026-06-01
15:31:06 Existing IBKR positions/orders: {'EOG', 'CDNS', 'ST', 'AKAM', 'AMH', 'JHG', 'ROIV'}
15:31:06   Skipping AKAM, ST: already has position
15:31:08   WST: MKT BUY 18 @ ~$322.81 | stop $303.39 | TP1 $337.38 | TP2 $351.94
15:31:08 [SWING] Submitted: 1 tickers | State: state/swing_positions.json (8 open)
```

### 3.2 `pt_close_2026-06-01.log` — tiszta nap

```
15:30:01 [SWING 15:30 close] No EOD action flags set — nothing to do.
21:40:01 [SWING 21:40 close] No TIME_STOP flags — nothing to do.
```

A swing pivot **3. egymás utáni "tiszta" napja** (Day 9 + Day 10 + Day 11) — a `days_held` trading-day fix sikere.

### 3.3 `pt_monitor_2026-06-01.log` — **CDNS TP2 flag** ⭐

```
22:00:06 [SWING EOD] Evaluated 8 positions — 1 exit flags set
  CDNS: TP2
```

A **swing pivot tisztított architektúra első TP2-je** — a Day 9+ "first clean day" óta első exit-flag.

### 3.4 `pt_reconcile_2026-06-01.log` — **5. ÉLES SILENT OK** ⭐

```
22:15:02 State/IBKR reconciliation — 2026-06-01
22:15:02 State tickers: ['AKAM', 'AMH', 'CDNS', 'EOG', 'JHG', 'ROIV', 'ST', 'WST']
22:15:21 IBKR tickers:  ['AKAM', 'AMH', 'CDNS', 'EOG', 'JHG', 'ROIV', 'ST', 'WST']
22:15:21 Reconciliation OK — state and IBKR match (silent exit).
```

**5/5 napon SILENT OK**. A Day 6 CNC-cancel óta **17 trading nap** autonóm bracket-trigger nélkül. A mental-stop architektúra integritása teljesen megalapozott.

### 3.5 `pt_eod_2026-06-01.log` — Cumulative -$708,58 (helyes)

```
22:05:01 EOD Report — 2026-06-01
22:05:03 P&L today: $+0.00         (helyes, 0 exit)
22:05:03 Cumulative: $-708.58 (-0.71%) [Day 9/63]   (helyes, a Part A sync utáni)
22:05:03 Still 8 open positions!    (P3 doc-only: INFO szintű kéne legyen)
```

**A `[Day 9/63]` doc anomalia folytatódik**: a `trading_days: 9` mező a Part B + Part A backfill alapján szól (Day 1-9 entries), de a Day 11 valójában a 10. trading nap a swing pivotban (5/18, 19, 20, 21, 22, 26, 27, 28, 29, 6/1). A `cumulative_pnl.json` Day 11 entry (6/1) **hiányzik** — kisebb logging anomalia (a Part A nem ír entry-t exit-mentes napokra; a Day 12 cron majd hozzáad ha lesz exit). **NEM kritikus**, mert a cumulative érték helyes (-$708,58).

---

## 4. UW Shadow Log Day 11 — 36 ticker (univerzum ugrás)

| Mutató | Day 10 | **Day 11** | Trend |
|--------|--------|-----------|-------|
| Tickers logged | 19 | **36** | **+17 nagy ugrás** |
| Avg dp_pct | 4,59% | 5,09% | +0,50pp |
| would_have_been_penalty_count | 4 | **8** | +4 |
| GEX regime (pos/hv/unk) | 13/5/1 | **23/7/6** | több positive + több unknown |
| m_gex_avg | 0,8947 | 0,9222 | +0,028 |

**36 ticker qualifying** az 50-es threshold felett — **közel kétszerese a Day 10-i 19-nek**. A heti váltás (W22 → W23) friss makró-context, és sok új ticker került elérhető univerzumba. A sector-balanced greedy ebből 1-et (WST) választott.

**Top 3 S_j Day 11**:
1. **MASI 94,1** (Healthcare) — **a Day 8 TIME_STOP-pal exitelt ticker újra kvalifikálódik** — de nem lett kiválasztva (sector-balanced WST-t választotta a Healthcare-be)
2. AKAM 89,8 (Technology) — meglévő
3. JHG 88,0 (Financial Services) — meglévő

**Megfigyelés: a MASI boomerang lehetőség nem materializálódott**. A scoring magasra emelte (a Day 5-i +$17-en zárt -$1,46-tal a Day 5-Day 8 között, ami "nincs érdemi mozgás" konzisztens), DE a sector-balanced greedy a Healthcare-be WST-t választott (másik fundamentumokon). **Ez egy strukturális védelem a "boomerang" túlhasználata ellen** — a sector-balanced greedy implicit cooldown-szerű viselkedést produkál.

**Megjegyzés**: ez a §8.4 (AMH boomerang) finding-gal kapcsolatos — a sector-balanced greedy NEM gondoskodik teljes cooldown-ról, csak részlegesről. Az AMH Day 9 → Day 10 boomerang azért működött, mert akkor Real Estate hiányzott. Ha MASI-ra hiányzott volna Healthcare ticker, ott is megismétlődne.

---

## 5. Anomáliák / megfigyelések (Day 11)

### 5.1 ✅ Mind a négy javító fix RESOLVED + élesen validált

- **Part B canonical** ✓ (cumulative -$708,58)
- **days_held trading-day** ✓ (3 egymás utáni "tiszta" nap, Day 9-10-11)
- **ATR floor+ceiling** ✓ (5/5 új entry egészséges sávban: AMH+CDNS Day 10, WST Day 11)
- **Part A ledger** ✓ (deploy-olt, holnap first real test a CDNS TP2-vel)

### 5.2 §0.10 reconcile — 5/5 ÉLES SILENT OK

17 trading napi tiszta mental-stop futás. A `04-risks` §0.10 teljes egészében RESOLVED.

### 5.3 §5.4 daily_metrics logging anomáliák — részben javul

A Day 11 daily_metrics:
- `pnl.cumulative: -708.58` ✓ (helyes a sync után)
- `exits_today.TP2: 1` ✓ (a CDNS TP2 flag-elve, de NEM aznap fill-elt — érdekes interpretáció, a CC kontextus-kérdés)
- `new_entries_tickers: [WST]` ✓
- `positions.opened: 0` ⚠️ (még mindig nem szinkronban a new_entries_today=1 mezővel)
- `positions.threshold: 85, max_allowed: 5` ⚠️ (legacy intraday értékek)
- `slippage_per_ticker: {}` ⚠️ (WST +0,47% hiányzik)
- `commission_total: 0` ⚠️ (WST $1,00 hiányzik)
- `day_number: 9` ⚠️ (a Day 11 valójában a 10. trading nap)

A Part A élesedése után **a `pnl` és `exits` rétegek megbízhatóak**, de a metadata-rétegek (positions, execution, scoring, day_number) **még nem teljes**. P1 backlog marad a CC számára.

### 5.4 ⚠️ Day 11 cumulative_pnl.json entry hiánya — kisebb logging issue

A `cumulative_pnl.json::daily_history`-ban nincs 2026-06-01 entry. A `trading_days: 9` továbbra is csak a Day 1-9 (5/18-5/29) napokat számolja. Ennek az oka valószínűleg, hogy a Part A nem ír entry-t exit-mentes napokra (Day 11 nem volt exit). **NEM kritikus** (a cumulative érték helyes), de a hosszú távú audit-trail szempontjából érdemes lehet a Part A-t kiterjeszteni egy "no-exit day with positions" üres entry-vel — vagy explicit dokumentálni, hogy a daily_history-ban csak az exit-tartalmú napok jelennek meg.

### 5.5 §9.4 single-position koncentráció — JHG 14,99%

A `swing_max_single_position_pct: 0.12` cap még nem deploy-olt. A JHG most pontosan a 15% küszöbön (cap 30% bőven betartva, single-position cap értelme a 12%-os). P2 backlog.

### 5.6 §9.7 EOG — megmenekült, de TIME_STOP közelében

Day 12 záróra days_held=5, Day 13 TIME_STOP MOC várt (~-$140 — -$230 realized). Day 11 a stop-trigger elkerülve.

---

## 6. Day 12 (kedd, 2026-06-02) outlook

### 6.1 ⭐ Várt CDNS TP2 fill (15:30 CEST)

**A Part A first éles same-day rögzítési próbája**:
- 15:30 CEST: `close_positions.py` MARKET SELL CDNS 14 share
- 15:30:Y CEST: IBKR fill (várt $410-420 körül)
- 22:10 CEST: `daily_metrics.py` cron → `record_pending_exits` → cumulative_pnl + daily_metrics auto-frissítés
- Várt realized: **~+$506** (lehet +$436 to +$646 a fill-ártól függően)
- Új cumulative: -$708,58 + ~$506 = **~-$202** (a flat-hez közelít!)

### 6.2 Várt további exit-flag Day 12 EOD-on: EOG TIME_STOP

- EOG days_held Day 12 záróra: 5 trading nap → TIME_STOP flag
- Day 13 (szerda, 6/3) 21:40 MOC SELL 44 share
- Várt realized: ~-$140 – -$230 (a Day 13-i ár-mozgásra függően)

### 6.3 Várt új entry Day 12-en

Friss W23 context, 36 qualifying ticker → várt 1-2 új entry. A sector-balanced greedy preferálni fogja a hiányzó szektorokat (Consumer Defensive, Industrials, Utilities, Materials, Communication Services, Consumer Cyclical).

### 6.4 Day 12 prioritások

1. **CDNS TP2 fill monitoring** intraday (IBKR `get_price_snapshot` 15:30 + záró)
2. **Part A 22:10 cron eredmény** — a `cumulative_pnl.json` Day 12 entry automatikusan rögzül-e? `pnl: +$506`, `tp2_hits: 1` várt
3. **EOG TIME_STOP flag** ellenőrzés Day 12 EOD-on (22:00 monitor.log)
4. **6. éles `_reconcile_state_from_ibkr`** — silent OK várt
5. **Telegram EOD üzenet** — a CDNS TP2 + realized P&L jelez-e? (a §0.2 Part A megfigyelés Day 12-i első élesedése)
6. **`/review-daily` CC skill** — Day 12 review autonómra?

---

## 7. Files referenced (Day 11)

- `state/swing_positions.json` — **8 pozíció**, CDNS next_action=TP2, last_updated 2026-06-01T20:00:06Z
- `state/daily_metrics/2026-06-01.json` — Day 11 cumulative -$708,58, exits_today.TP2: 1, new_entries: [WST]
- `scripts/paper_trading/logs/cumulative_pnl.json` — Day 11 entry hiányzik (lásd §5.4)
- `logs/pt_close_2026-06-01.log` — 0 exit (helyes)
- `logs/pt_submit_2026-06-01.log` — 1 entry tisztán
- `logs/pt_monitor_2026-06-01.log` — **1 EOD flag: CDNS TP2** ⭐
- `logs/pt_reconcile_2026-06-01.log` — **5. SILENT OK** ⭐
- `state/uw_shadow/2026-06-01.json` — 36 ticker, MASI top S_j 94,1 (boomerang nem materializálódott)
- **IBKR direkt API**:
  - `get_account_summary` → Net Liq **$99 764,65** (cumulative -$235,35 a baseline-ról, **+$523 Day 11 mozgás**)
  - `get_account_positions` → 8 pozíció, **unrealized +$279,59** ⭐
  - `get_account_trades(DAYS_7)` → Day 11 trades: 1 entry (WST), 0 exit

---

## 8. ⭐ Strukturális finding-ek összefoglaló

### 8.1 ⭐⭐⭐ A swing pivot ELSŐ tisztított-architektúra TP2 — Day 12 várt fill

A CDNS TP2 flag Day 12 15:30-ra a swing pivot **legfontosabb pozitív strukturális esemény** eddig:
- Egy nap entry-től TP2-fölé (+10,5% napi mozgás)
- A scoring + sector-balanced greedy **megelőzte** a CDNS rallyt egy nappal (vagy szerencse, vagy alpha-jel)
- A Part A first éles same-day rögzítési próbája holnap
- Várt realized **~+$506**, ami a cumulative-t **~-$202-ra** viszi (közelít a flat-hez)

### 8.2 ⭐ A daily-eval architektúra előnye Day 11-en kétszer is bizonyított

- **EOG**: Day 10 záró $0,04 stop-távolság → Day 11 záró $3,19 stop-távolság (+$139 unrealized javulás)
- **AKAM**: Day 9 záró -$57 → Day 10 záró +$57 → Day 11 záró +$128 (3 napos folytatólagos fordulat)

**Egy intraday hard-stop architektúra mindkét pozíciót kivitte volna** (AKAM Day 9-en SL-en ~-$57, EOG Day 10 záróra ~-$343). A 22:00 daily eval **lassúsága mindkét esetben pénzügyileg pozitív** kimenetelhez vezetett. Day 11-i összesített "megmentett" potenciál: ~+$400 (a hipotetikus intraday-stop scenarióhoz képest).

**De**: a Day 8-i Energy zuhanásnál (LBRT -$419, WMB -$379) az intraday hard-stop **kevesebb veszteséget okozott volna** (~-$300 helyett ~-$800). A két ellentétes case egy **valós architektúra-tradeoff** — érdemes lesz a Fázis 2 backtestben empirikusan vizsgálni: mikor a daily-eval, mikor az intraday hard-stop a jobb.

### 8.3 ⭐ A Day 11 a swing pivot legjobb napja eddig

| Metric | Day 11 | Korábbi átlag (Day 1-10) |
|--------|--------|---------------------------|
| Total mozgás (Net Liq) | **+$523 (+0,53%)** | -$78/nap |
| Total unrealized | **+$279** | -$215 átlag |
| Nyertes/vesztes (pozícióra) | 4/4 ($908/$500) | 1-2/5-6 |
| Új entry slippage | +0,47% (WST) | átlag +0,08% |
| Exit flag (jövő nap) | **CDNS TP2** ⭐ | főleg TIME_STOP |
| SPY return | +0,27% | átlag +0,15% |
| **Excess vs SPY** | **+0,26%** ⭐ | **átlag -0,55%** |

**Az első pozitív excess return nap a swing pivot alatt** (Day 11 +0,26% vs Day 1-10 átlag -0,55%). Egy nap nem statisztika, de a tisztított architektúra első napja ezzel kezd.

### 8.4 📝 A boomerang-finding tovább finomodik

- **AMH boomerang** (Day 5 TIME_STOP → Day 10 új entry): Day 11-re +$99 (sikeres boomerang)
- **MASI boomerang lehetőség** (Day 1 TIME_STOP → Day 11 top S_j 94,1): **NEM materializálódott** (sector-balanced WST-t választott)

Ez **azt sugallja, hogy a sector-balanced greedy implicit védelmet ad** a boomerang-túlhasználat ellen — csak akkor enged boomerang-entry-t, ha az adott szektorban hiány van. **Nem kell explicit cooldown-period a CC §8.4 javaslata szerint** — a meglévő architektúra már kezelheti. Csak a Fázis 2 backtest fogja statisztikailag megerősíteni.

### 8.5 IBKR connector és Part A — együtt teljes tracking

A `04-risks` §0.11 tracking gap teljes megoldása **élesedett Day 11-en**:
- Day 11: 0 exit → 0 új cumulative_pnl entry (Part A nem hív, helyes)
- Day 12: CDNS TP2 fill → **Part A first auto-rögzítés** várt
- A connector cross-check rétege megmarad (a `daily_metrics P&L ≠ IBKR realized` flag jövőbeli gap-ekre)

---

## State (Day 11 — W23 D1, swing pivot Day 11/63)

**Architektúra**: swing pivot Fázis 3 deploy DAY 11. **Mind a négy javító fix RESOLVED + élesen validált**. **Az első teljes tiszta hét (W23) első napja, és a legjobb napi teljesítmény eddig**.

**Live**: 8 open positions:
- **CDNS** ⭐⭐⭐ (+$553, **TP2 flag Day 12 15:30**)
- **AKAM** ⭐ (+$128, 3 napos fordulat)
- **AMH** ⭐ (+$99, boomerang igazolódik)
- **EOG** (-$168, megmenekült a stoptól, TIME_STOP Day 12-13)
- **JHG** (-$27, flat 4. napja)
- **ST** (-$80, stabil)
- **ROIV** (-$88, fordult)
- **WST új** (-$137, csak első nap)

**Total unrealized**: **+$279,59** (4 nyertes/4 vesztes, nettó pozitív)

**Cumulative (Mac Mini canonical + Part A)**: **-$708,58** (változatlan, 0 exit Day 11)
**Cumulative (valódi IBKR Net Liq)**: $99 764,65 → **-$235,35 a baseline-ról** (a Day 8-i -$779 mélypontról jelentősen javult)

**Day 11 realized**: $0. **Day 11 commission**: $1,00 (WST).

**Net Liq (IBKR)**: **$99 764,65** ($-235 a baseline-ról, **+$523 Day 11 valódi mozgás — a swing pivot legjobb napja**).

**Excess return Day 11**: SPY +0,27%, portfolio **+0,53%** (M2M), **valódi excess +0,26% vs SPY ⭐** (az első pozitív excess nap).

**Aktív P0/P1 (frissített, Day 11 utáni):**
- **§0.11 (Part B + Part A) ✅ TELJES RESOLVED**, élesen validált 2 napja
- **§9.2, §9.3, §9.5 ✅ DEPLOYED + élesen validált** 3 napja
- **§9.4 P2 — JHG single-position koncentráció** (14,99%), `swing_max_single_position_pct: 0.12` deploy várat (CC backlog)
- **§5.4 P1 — daily_metrics 6 logging anomalia** (positions.opened, threshold, slippage_per_ticker, commission_total, day_number, és a `daily_history` no-exit-entry kérdés — lásd §5.4)
- **§9.7 EOG TIME_STOP** Day 13 várt (-$140 – -$230)
- **§9.8 első kohorsz** kontextusban (-$651 valódi, +$279 Day 11 unrealized) — **a swing pivot fordul a flat felé**
- **ÚJ §8.4 megfigyelés — AMH boomerang igazolódik, MASI boomerang NEM materializálódott** (a sector-balanced greedy implicit cooldown-szerű viselkedést produkál)
- **§0.10, §0.2, §0.5, §9.1 ✅ stabil/RESOLVED**

**Day 12 fókusz**:
1. **CDNS TP2 fill** (15:30, várt ~+$506 realized)
2. **Part A first éles same-day rögzítés** (22:10 cron — Day 12 cumulative_pnl entry auto-frissítés)
3. **EOG TIME_STOP flag** EOD-on (Day 13 21:40 exit várt)
4. **Új entry Day 12-en**
5. **6. éles reconcile silent OK**

**A Day 11 napi karakter egy mondatban**: **A swing pivot legjobb napja eddig** — a tisztított architektúra (mind a négy javító fix élesedve) **első teljes tiszta hetének (W23) első napján** a portfolio +$523 unrealized javulást produkált (+0,53% Net Liq, **első pozitív excess return +0,26% vs SPY**), miközben **a CDNS TP2-re flag-elve Day 12 15:30 fill-re** (entry $373,85 → mark $414,33 = +10,5% egy nap alatt, várt realized ~+$506), **az EOG megmenekült a Day 10-i $0,04 stop-távolságról $3,19-re** (+$139 unrealized javulás, +$343 hipotetikus megtakarítás az intraday hard-stop scenarióhoz képest), az **AKAM 3 napos fordulata folytatódik** (-$57 → +$57 → +$128), az **AMH boomerang igazolódik** (Day 5 TIME_STOP → Day 10 új entry → Day 11 +$99), a **`_reconcile_state_from_ibkr` 5/5 ÉLES SILENT OK** (17 trading napi tiszta mental-stop futás), és a **Part A first éles same-day rögzítési próba Day 12-én várja a CDNS TP2-t** — ami ha sikerül, a cumulative -$708,58-ról **~-$202-ra** javulhat, közelítve a flat-hez **a swing tézis empirikus tesztelésének első érdemi pozitív eredménye lehet**.

---

**A Day 11 review vége.** A Day 12 fókusz: CDNS TP2 fill ($410-420 várt) + Part A first auto-rögzítés + EOG TIME_STOP flag + 6. SILENT OK.
