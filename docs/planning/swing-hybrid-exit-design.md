# Swing Trading Hybrid Exit — Design Document

**Státusz:** APPROVED — 2026-02-19
**Dátum:** 2026-02-19
**Scope:** Pipeline timing, entry, TP, trailing stop, VWAP, max hold
**Érint:** runner.py, submit_orders.py, close_positions.py, phase6_sizing.py, SimEngine

---

## 1. Motiváció

### Jelenlegi rendszer (BC16)
```
22:00 CET    Pipeline fut (Phase 1-6), execution plan CSV generálás
09:25 CET    submit_orders.py: LMT buy + bracket (SL + TP1 + TP2)
21:45 CET    close_positions.py: MOC minden nyitott pozícióra
```

**Problémák:**
1. **0/12 TP hit** az első 2 paper trading napon — TP1 (2× ATR) és TP2 (3× ATR) elérhetetlen 1 nap alatt
2. **Pre-market gap** — a 22:00-kor generált entry limit price reggel 9:25-re irreleváns, nem fill-el
3. **Nincs swing holding** — mindent MOC-vel zárunk, holott a breadth/funda/OBSIDIAN faktorok 3-5 napos horizontot tükröznek
4. **Nincs VWAP** — az entry minőség nem optimalizált

### Tervezett rendszer
```
22:00 CET    Pipeline Phase 1-3 (BMI, Universe, Sectors) — teljes napi adat
15:45 CET    Pipeline Phase 4-6 (Scoring, GEX, Sizing) — intraday adat, friss árak
15:48 CET    submit_orders.py: MKT buy + bracket (SL + TP1@50% + TRAIL maradék)
21:45 CET    close_positions.py: napi management (hold tracking, trail update, max day check)
```

---

## 2. Döntési Pontok

### D1: Pipeline Split Timing
**Döntés:** 22:00 CET (Phase 1-3) + 15:45 CET (Phase 4-6)
**Indoklás:**
- 15:45 CET = 9:45 ET = NYSE nyitás + 15 perc
- Az opening auction lezárult, VWAP értelmes, spread normalizálódott
- Phase 1-3 amúgy is napi záróadatokból dolgozik — nem kell intraday
- Phase 4-6 profitál az intraday adatból (friss ár, RVOL, buy pressure)

**Implementáció:** Két cron job a Mac Mini-n:
```cron
# Phase 1-3: napi adat (BMI, Universe, Sectors)
0 22 * * 1-5  cd ~/SSH-Services/ifds && ./scripts/deploy_daily.sh --phases 1-3

# Phase 4-6: intraday adat (Scoring, GEX, Sizing) + order submission
45 15 * * 1-5 cd ~/SSH-Services/ifds && ./scripts/deploy_intraday.sh
```

**Megjegyzés:** A `deploy_intraday.sh` a Phase 4-6-ot futtatja, majd automatikusan hívja a `submit_orders.py`-t.

### D2: Entry Type — Market Order
**Döntés:** MKT order (nem LMT)
**Indoklás:**
- 15:45 CET-re a spread normalizálódott (nem pre-market)
- Garantált fill — nincs "elmaradt entry" probléma
- A VWAP modul biztosítja, hogy ne entry-zzünk extrém árszinten
- A pipeline 15:45-kor friss árat lát, a MKT order ~15:48-kor megy be → minimális slippage

**VWAP guard:** Ha az aktuális ár > VWAP × 1.02 (2% felett), az entry-t elutasítjuk.

### D3: TP1 — Partial Exit
**Döntés:** TP1 = 0.75× ATR, pozíció 50%-a
**Indoklás:**
- 0.75× ATR intraday reálisan elérhető (1× ATR a napi teljes range átlaga)
- 50% partial exit: profit locking + upside optionality megmarad
- IBKR támogatja a partial bracket-et (OCA group)

**IBKR implementáció:**
```
Parent: BUY 200 shares MKT
  Child 1: SELL 100 shares LMT @ entry + 0.75×ATR  (TP1, 50%)
  Child 2: SELL 200 shares STP @ entry - 1.5×ATR    (SL, full size)
```
Amikor TP1 fill-el (100 shares), a Child 2 STP quantity módosul 200→100.

### D4: Trailing Stop
**Döntés:** IBKR TRAIL + napi script management
**Indoklás:**
- IBKR TRAIL order: real-time védelem, tick-szintű pontosság
- Napi script: ATR-alapú trailing update, OBSIDIAN integráció, max hold tracking

**Trailing mechanizmus:**
```
Entry nap (D+0):
  SL = entry - 1.5× ATR (fix, IBKR STP)
  
D+1 (ha TP1 NEM triggered):
  close_positions.py ellenőrzi az aktuális árat
  Ha ár > entry + 0.3× ATR: SL felhúzás → entry (breakeven)
  
D+1 (ha TP1 triggered, 50% zárva):
  Maradék 50%: IBKR TRAIL order, trailing amount = 1× ATR $-ban
  
D+2 → D+4:
  close_positions.py napi trail update:
  - OBSIDIAN VOLATILE regime → tighter trail (0.75× ATR)
  - OBSIDIAN NORMAL/UNDETERMINED → standard trail (1× ATR)

D+5 (max hold):
  close_positions.py: MOC a maradék pozícióra
```

### D5: VWAP Modul
**Döntés:** VWAP a Phase 6-ba, intraday 5-min bars-ból
**Indoklás:**
- Polygon 5-min aggregates API (Advanced tier: unlimited, real-time)
- VWAP = Σ(Price × Volume) / Σ(Volume) — kumulatív intraday
- Felhasználás: entry quality filter + exit quality (TP1 VWAP közelében jobb fill)

**Polygon API call:**
```
GET /v2/aggs/ticker/{ticker}/range/5/minute/{today}/{today}
```

**VWAP guard logika Phase 6-ban:**
```python
def vwap_entry_check(current_price, vwap, atr):
    """Check if entry price is acceptable relative to VWAP."""
    distance_pct = (current_price - vwap) / vwap * 100
    
    if distance_pct > 2.0:   # >2% above VWAP
        return "REJECT"       # túl drága entry
    elif distance_pct > 1.0:  # 1-2% above VWAP
        return "REDUCE"       # csökkentett méret (50%)
    elif distance_pct < -1.0: # >1% below VWAP
        return "BOOST"        # jó entry, normál vagy emelt méret
    else:
        return "NORMAL"       # VWAP közelében, normál méret
```

### D6: Max Hold Period
**Döntés:** 5 trading day (nem naptári nap)
**Indoklás:**
- A breadth/funda faktorok 1-2 hetes ciklusokat tükröznek
- 5 trading day = ~1 hét — elég a swing mozgáshoz
- A `trading_calendar.py` (BC18-prep) már elérhető a trading day számításhoz
- Earnings before max hold → korai exit (T9 trading calendar integráció)

---

## 3. Új Fájlok / Módosítások

### Új fájlok
| Fájl | Tartalom |
|------|----------|
| `scripts/deploy_intraday.sh` | 15:45 CET cron: Phase 4-6 + submit_orders |
| `src/ifds/phases/vwap.py` | VWAP kalkuláció intraday bars-ból |
| `src/ifds/state/position_tracker.py` | Nyitott pozíciók állapotkezelése (hold day, TP1 status) |

### Módosítandó fájlok
| Fájl | Változás |
|------|----------|
| `scripts/deploy_daily.sh` | `--phases 1-3` flag support |
| `scripts/paper_trading/submit_orders.py` | MKT entry, partial TP1 bracket, TRAIL order |
| `scripts/paper_trading/close_positions.py` | Hold day tracking, trail update, partial exit management |
| `src/ifds/phases/phase6_sizing.py` | VWAP guard, TP1 = 0.75× ATR, position split info |
| `src/ifds/pipeline/runner.py` | `--phases` CLI flag, Phase 4-6 only mode |
| `src/ifds/models/market.py` | Position model: `tp1_qty`, `trail_qty`, `max_hold_days` fields |
| `src/ifds/config/defaults.py` | Új TUNING keys (ld. lent) |
| `src/ifds/sim/broker_sim.py` | Partial exit + trailing stop szimulálás |
| `src/ifds/sim/validator.py` | Multi-day hold, partial exit tracking |

### Új config keys (`defaults.py`)
```python
TUNING = {
    # Swing Trading Hybrid Exit
    "tp1_atr_multiplier": 0.75,       # TP1 = 0.75× ATR (50% exit)
    "tp1_exit_pct": 0.50,             # TP1-nél a pozíció 50%-át zárjuk
    "trailing_stop_atr": 1.0,         # Trailing stop distance = 1× ATR
    "trailing_stop_atr_volatile": 0.75, # OBSIDIAN VOLATILE → tighter
    "breakeven_threshold_atr": 0.3,   # 0.3× ATR profit → SL breakeven-re
    "max_hold_trading_days": 5,       # Max 5 kereskedési nap
    "vwap_reject_pct": 2.0,           # >2% above VWAP → reject entry
    "vwap_reduce_pct": 1.0,           # >1% above VWAP → reduce size
    "vwap_boost_pct": -1.0,           # >1% below VWAP → boost
    "entry_type": "MKT",              # MKT or LMT
}
```

---

## 4. Position Tracker State

Új state fájl: `state/open_positions.json`

```json
{
  "positions": [
    {
      "ticker": "MT",
      "entry_date": "2026-02-19",
      "entry_price": 64.25,
      "total_qty": 89,
      "remaining_qty": 89,
      "tp1_triggered": false,
      "tp1_qty": 44,
      "trail_qty": 45,
      "sl_price": 58.47,
      "tp1_price": 66.16,
      "trail_amount_usd": 2.56,
      "current_trail_stop": 58.47,
      "hold_days": 0,
      "max_hold_days": 5,
      "atr_at_entry": 2.56,
      "vwap_at_entry": 63.90,
      "obsidian_regime": "undetermined",
      "run_id": "run_20260219_154500_abc123"
    }
  ],
  "last_updated": "2026-02-19T15:48:00Z"
}
```

A `close_positions.py` ezt a fájlt olvassa és frissíti minden futtatásnál.

---

## 5. Napi Lifecycle

```
                        22:00 CET (előző este)
                              │
                    ┌─────────▼──────────┐
                    │  Phase 1-3          │
                    │  BMI, Universe,     │
                    │  Sectors            │
                    │  (záróárak)         │
                    └─────────┬──────────┘
                              │ ctx mentés → state/phase13_ctx.json.gz
                              │
                        15:45 CET (másnap)
                              │
                    ┌─────────▼──────────┐
                    │  Phase 4-6          │
                    │  + VWAP modul       │
                    │  (intraday árak)    │
                    └─────────┬──────────┘
                              │ execution_plan.csv
                              │
                        ~15:48 CET
                              │
                    ┌─────────▼──────────┐
                    │  submit_orders.py   │
                    │  MKT buy            │
                    │  + TP1 LMT (50%)    │
                    │  + SL STP (100%)    │
                    └─────────┬──────────┘
                              │
                      Kereskedési nap...
                              │
                    ┌─── TP1 triggered? ──┐
                    │ IGEN                │ NEM
                    ▼                     ▼
              50% zárva              Pozíció nyitva
              maradék 50%:           marad holnapra
              TRAIL order aktív
                    │                     │
                        21:45 CET
                              │
                    ┌─────────▼──────────┐
                    │  close_positions.py │
                    │  - Hold day check   │
                    │  - Breakeven check  │
                    │  - Trail update     │
                    │  - Max hold → MOC   │
                    │  - state update     │
                    └─────────┬──────────┘
                              │
                    Másnap 15:45: ÚJ pipeline +
                    meglévő pozíciók management
```

---

## 6. SimEngine Változások

A `broker_sim.py` és `validator.py` módosítása szükséges:

### broker_sim.py
- `simulate_trade()` → `simulate_swing_trade()`
- Napról napra iterál (max 5 trading day)
- TP1 check: ha high >= tp1_price → 50% exit, P&L regisztrálás
- Trail check: ha TP1 triggered, trailing stop = max(previous_trail, close - trail_atr)
- SL check: ha low <= current_sl → full exit
- Day 5: MOC exit

### validator.py
- `_fetch_bars_for_trades()`: max_hold_days + fill_window padding
- Polygon bars request: 5+ trading day of bars kell trade-enként

### SIM-L2 Mód 1 variáns config
```yaml
variants:
  baseline_swing:
    tp1_atr: 0.75
    tp1_exit_pct: 0.50
    trailing_stop_atr: 1.0
    max_hold_days: 5
  aggressive_swing:
    tp1_atr: 0.5
    tp1_exit_pct: 0.50
    trailing_stop_atr: 0.75
    max_hold_days: 3
  conservative_swing:
    tp1_atr: 1.0
    tp1_exit_pct: 0.50
    trailing_stop_atr: 1.5
    max_hold_days: 7
```

---

## 7. Risk Considerations

| Kockázat | Mitigation |
|----------|-----------|
| Overnight gap | IBKR SL/TRAIL aktív pre/post-market is |
| Mac Mini leáll | IBKR bracket/trail order szerveren él — nem függ a script-től |
| 5 napos hold earnings-be fut | Trading calendar T9: earnings check a position_tracker-ben |
| VWAP torzítás alacsony float-nál | Min volume filter Phase 2-ben már van (500K shares) |
| Partial fill TP1 | IBKR OCA group kezeli: ha TP1 partial fill, SL proportionálisan csökken |
| Túl sok nyitott pozíció | Max 8 pozíció limit + max exposure limit érvényes |

---

## 8. Implementációs Sorrend

| # | Feladat | Dependency | Becsült idő |
|---|---------|-----------|-------------|
| 1 | VWAP modul (`vwap.py`) | Polygon intraday API | 2h |
| 2 | Position Tracker (`position_tracker.py`) | — | 3h |
| 3 | Phase 6 módosítás (TP1 split, VWAP guard) | #1 | 2h |
| 4 | submit_orders.py (MKT + partial bracket) | #2, #3 | 3h |
| 5 | close_positions.py (trail update, hold tracking) | #2 | 3h |
| 6 | deploy_intraday.sh + runner --phases flag | — | 1h |
| 7 | SimEngine swing support (broker_sim, validator) | #1, #2, #3 | 4h |
| 8 | Tesztek | #1-#7 | 3h |
| **Σ** | | | **~21h CC** |

---

## 9. Nyitott kérdések

| # | Kérdés | Státusz |
|---|--------|---------|
| 1 | Phase 1-3 context persistence formátum | LEZÁRVA | JSON + gzip — időtálló, Python-verzió-független, debug-olható. `state/phase13_ctx.json.gz` — ugyanaz a pattern mint Phase 4 snapshot |
| 2 | Phase 2 earnings check a mai napra vonatkozzon? | LEZÁRVA | Igen — a 22:00-ás Phase 2 a másnapi kereskedésre szűr (T+1 nézőpont) |
| 3 | IBKR paper: TRAIL + OCA kombináció | LEZÁRVA | ✅ Támogatott. IBKR szerver-oldali szimuláció. `ib_insync` bracket: parent(transmit=False) + profit_taker(parentId) + trail_stop(parentId, transmit=True). OCA `ocaType=1` (cancel with block). Kódpéldák validálva. |
| 4 | Polygon 5-min bars rate limit | LEZÁRVA | Polygon **Advanced** tier ($199/hó): unlimited API calls, real-time, minute aggregates. Nincs rate limit. |
| 5 | SIM-L1 forward validation swing trade-ekkel | LEZÁRVA | SIM-L1 marad 1 napos (benchmark). Swing trade-ek SIM-L2 Mód 1 variánsokként futnak a márc 2-i comparison run-ban. Két párhuzamos track: SIM-L1 (1-day) + Paper Trading (swing). |

---

## 10. BC Assignment

Ez a fejlesztés **BC20A** (a BC20 SIM-L2 Mód 2 mellé, vagy annak előtte):
- Független a BC17-18 crowdedness munkától
- Független a BC20 SIM-L2 Mód 2-től (de a SimEngine módosításokat közösen használják)
- A Paper Trading infrastruktúra módosítás azonnal élesíthető

Alternatíva: ha a SimEngine módosítás túl nagy, a Paper Trading részt (submit_orders + close_positions + position_tracker) önállóan is be lehet vezetni BC17-18 előtt.
