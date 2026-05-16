# 02 — Exit-mechanika: trigger-ek és állapot-diagram

**Utoljára frissítve**: 2026-05-08
**Aktív verzió**: BC23 (50/50 bracket) + Breakeven Lock + LOSS_EXIT whipsaw audit

---

## 1. Pozíció-nyitás és bracket struktúra

Minden long pozíció **két részre osztódik 50/50** arányban (BC23 átalakítás óta; korábban 33/67).

### Bracket A (50% pozíció-méret)

| Trigger | Küszöb | Akció |
|---------|--------|-------|
| **TP1 (profit cél)** | Entry + **1,25×ATR** | Eladja a Bracket A 100%-át; a maradék (Bracket B) trail-re vált |
| **Stop-loss (hard)** | Entry - **1,5×ATR** | Hard stop, IBKR bracket order szinten |
| **Loss-exit (soft)** | Intraday -**2%** Entry-től | Soft stop, monitor script triggerel MARKET SELL-t |
| **MOC** | 21:40 CEST swing close | Ha még nyitva van, MOC orderre állítja |

### Bracket B (50% pozíció-méret)

| Trigger | Küszöb | Akció |
|---------|--------|-------|
| **TP2 (profit cél)** | Entry + **2,0×ATR** | Eladja a Bracket B 100%-át |
| **Trail aktiváció** | TP1 fill után (Bracket A → trail) | Trail = 1×ATR az aktuális ártól |
| **Breakeven Lock (window-based)** | 19:00:00-19:04:59 CEST + profit > 0 | Trail SL emelése max(trail_sl, entry_price)-re |
| **Breakeven Lock (profit-based)** | Profit ~+1% felett bármikor | Trail SL emelése max(trail_sl, entry_price)-re |
| **Stop-loss (hard)** | Entry - 1,5×ATR | Hard stop, IBKR bracket order |
| **Loss-exit (soft)** | Intraday -2% Entry-től | Soft stop, monitor script |
| **MOC** | 21:40 CEST swing close | MOC order |

## 2. A 7 exit-trigger állapot-diagramja

```
                ┌─────────────────────────────────┐
                │  POZÍCIÓ NYITVA (16:15 CEST)    │
                │  Bracket A: 50% pos              │
                │  Bracket B: 50% pos              │
                └────────────┬────────────────────┘
                             │
                             ▼
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   [Profit irány]      [Loss irány]         [Lateral]
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐          ┌─────────┐
   │  TP1    │         │  -2%    │          │  Trail  │
   │ +1,25   │         │  Loss   │          │  aktiv  │
   │  ×ATR   │         │  Exit   │          │  ?      │
   └────┬────┘         └────┬────┘          └────┬────┘
        │                   │                    │
        │ (Bracket A fill)  │ (mind két bracket  │
        │                   │  market sell)      │
        ▼                   ▼                    │
   ┌─────────┐         ┌─────────┐               │
   │ Trail   │         │ ZÁRVA   │               │
   │ aktív   │         │  -2%    │               │
   │ Bracket │         │  loss   │               │
   │   B     │         └─────────┘               │
   └────┬────┘                                   │
        │                                        │
        ├────► Breakeven Lock?  ◄────────────────┘
        │      ┌─────────────────────────────┐
        │      │ ha profit >+1% (becsült)    │
        │      │ VAGY 19:00-19:05 CEST       │
        │      │ + profit > 0                │
        │      └─────────────────────────────┘
        │      → trail_sl = max(trail_sl, entry)
        │
        ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │  TP2    │    │  Trail  │    │  MOC    │
   │ +2×ATR  │    │  trigg  │    │ 21:40   │
   │         │    │  fill   │    │  CEST   │
   └─────────┘    └─────────┘    └─────────┘
```

## 3. A 6 exit-típus statisztikája (60 nap, 378 ügylet)

| Exit típus | N | % | Átlag P&L | Total P&L | Win? |
|-------------|---|---|-----------|-----------|------|
| **TP1** | 36 | 9,5% | +$32,95 | +$1 186 | ✅ |
| **TP2** | 3 | 0,8% | +$286,03 | +$858 | ✅ |
| **Trail** | 3 | 0,8% | +$33,39 | +$100 | ✅ |
| **MOC** | 280 | 74,1% | +$3,36 | +$940 | semi |
| **SL (hard)** | 15 | 4,0% | -$78,87 | -$1 183 | ❌ |
| **Loss Exit (soft)** | 32 | 8,5% | -$98,50 | -$3 152 | ❌ |
| **Nuke (manuális)** | 9 | 2,4% | +$6,51 | +$59 | n/a |

**Strukturális finding**:
- **Profit-oldal nettó**: +$3 084 (TP1+TP2+Trail+MOC)
- **Loss-oldal nettó**: -$4 335 (SL+LossExit)
- **Strukturális deficit**: -$1 251 csak az exit-mechanikából

## 4. Risk-reward elemzés

A jelenlegi paraméterekkel:
- **TP1** = +1,25×ATR profit cél
- **SL** = -1,5×ATR loss cél
- **Naiv R:R arány** = 1,25 / 1,5 = **0,83 : 1** (kedvezőtlen)

**A 9,5%-os TP1 hit ráta** túl alacsony ahhoz, hogy a 0,83:1 R:R kompenzálja:
- Várt profit ügyletenként = 0,095 × 1,25 = +0,12 R
- Várt loss ügyletenként = (kockázat-mentes ráta) ~0,30 × 1,0 = -0,30 R
- **Várt nettó** = -0,18 R/ügylet — strukturálisan negatív

A loss-exit (-2% intraday) gyakran **a hard SL előtt** triggerel, mert a -2% ($x dollar) abszolút mozgás **kisebb** lehet, mint az 1,5×ATR távolság (sebesség-érzékeny).

## 5. Timing — a kereskedési nap

```
22:00 CEST (előző nap)  Phase 1-3: BMI, univerzum, szektor-rotáció
                        → state/phase13_ctx.json.gz ment

15:30 CEST (US piac nyit) opening range első percei

16:00 CEST              IBKR Gateway health check (15 perc a submit előtt)

16:15 CEST              Phase 4-6 + submit
                        → execution plan CSV
                        → IBKR bracket orderek beadva

16:00-21:55 CEST        Monitor script (5 perces ciklusok)
                        - TP1 detektálás → trail_a aktiváció
                        - Loss-exit -2% küszöb
                        - Trail SL frissítés
                        - Breakeven Lock kalkuláció

19:00:00-19:04:59 CEST  Breakeven Lock window (legacy logika)
                        → ha profit > 0, trail_sl = max(trail_sl, entry)

21:40 CEST              Swing close trigger
                        → minden még-nyitott pozíció MOC-ra állítva
                        (max_hold_trading_days: 5, de ritka kivétel)

22:00 CEST              NYSE close (16:00 ET)
                        → MOC orderek fill-elnek

22:05 CEST              EOD report — napi P&L

22:10 CEST              daily_metrics.py — strukturált JSON output

22:45 CEST              events_to_sqlite.py — SQLite import
```

## 6. Strukturális kockázatok és nyitott kérdések

### 6.1 LOSS_EXIT bracket SL cancellation bug (P1, 2 alkalom 6 napban)

**Probléma**: amikor a loss-exit triggerel, a `monitor` script egy MARKET SELL-t küld a teljes pozícióra. **DE** az IBKR-ben már létező bracket SL ordereket **NEM törli**. Amikor az ár átesik a bracket SL ár alá, az IBKR autonóm módon triggereli a SL-t **és short pozíciót nyit** a long zárása után.

**2 dokumentált eset**:
- DTE 2026-05-01: 4-split, leftover -130 short, valós kár ~-$988
- SQM 2026-05-07: 3-split, leftover -91 short, valós kár ~-$425

**Megoldás (P1 backlog)**: a `pt_monitor.py` loss-exit logikájának módosítása — a meglévő bracket SL ordereket explicit kancellálni a SELL submit előtt.

### 6.2 TP1 cél túl szigorú alacsony ATR-en (P2)

A `tp1_atr_multiple: 1,25` egy szűkítendő paraméter alacsony ATR-ű tickereken. Példa: DBRG 2026-05-05, ATR ~$0,07 → TP1 cél = +0,13% (gyakorlatilag spread-szerű).

**Megoldás (P2 backlog)**: alacsony ATR esetén **arányos cél-emelés** (pl. ha ATR < 1% entry-höz, alkalmazni 1,5×ATR).

### 6.3 Breakeven Lock window túl szigorú (P2)

A "Breakeven Lock" csak **két feltétel egyikére** aktivál:
- 19:00:00-19:04:59 CEST window + profit > 0
- Profit ~+1% (becsült) felett bármikor

**Probléma**: a 60 napi adatban a trail aktivációk gyakran **+0,5-0,7% profit** közelében történnek (pl. PTEN 2026-05-05, BEKE 2026-05-05), amelyek **NEM kapnak Breakeven Lock-et**, és gyakran retracement-en visszafutnak.

**Megoldás (P2 backlog)**: a profit-küszöb csökkentése **0,5%-ra**, ezzel a +0,5-0,7% trail aktivációkat is védve.

## 7. Ami NEM része a jelenlegi exit-mechanikának

- **Trailing stop az opening range előtt** (a 30 perces opening volatilitás védelme nélkül a fillek közelében instant stop-loss kockázat)
- **Volume-weighted stop** (csak ATR-alapú)
- **Time-based exit** (csak 21:40 swing close, nincs intraday hold-day-1 exit)
- **Multi-day hold** (a `max_hold_trading_days: 5` paraméter rögzítve, de a gyakorlatban 95%+ pozíció D+0 zár)
- **Mean reversion overlay** (nincs "profit > 2,5×ATR → tighter trail" logika)

A backlog tartalmaz több ilyen ötletet a `docs/planning/backlog-ideas.md`-ben, de **W19+ scope-ban**.

---

**A frissítésért felel**: Chat (Claude) — eseményalapú (exit-logika változás után). A 60 napi statisztika péntek 22:00 weekly metric után frissítendő.
