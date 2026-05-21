# BC23 Kiegészítés — Napi Metrika Gyűjtés (Automatikus)

**Status:** DONE
**Updated:** 2026-04-11
**Priority:** P1 — BC23 deploy után, hétfőtől gyűjt
**Effort:** ~1.5h CC
**Depends on:** BC23 Phase 1-4 deploy
**Ref:** docs/planning/bc23-scoring-exit-redesign.md

---

## Kontextus

A BC23 redesign után szükség van egy automatikus napi mérési rendszerre, ami nem a log review része, hanem a pipeline futtatja. A cél: strukturált, géppel olvasható metrikák, amiből a heti és kétheti kiértékelés dolgozik.

## Implementáció

### Új script: `scripts/paper_trading/daily_metrics.py`

A pipeline EOD (22:05) után fut, a `eod_report.py` eredményeire épít. Crontab:

```bash
# 22:10 Budapest — EOD report (22:05) után 5 perccel
10 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/daily_metrics.py
```

**FONTOS:** A crontab módosítás Tamás feladata a Mac Mini-n. CC csak dokumentálja a `docs/deploy/bc23-crontab-changes.md`-ben.

### Bemenetek (read-only)

```
scripts/paper_trading/logs/cumulative_pnl.json   → napi P&L, trade count, exit breakdown
logs/pt_events_YYYY-MM-DD.jsonl                  → fill árak, exit típusok, tickerek
state/phase4_snapshots/YYYY-MM-DD.json.gz        → score-ok, flow al-komponensek
output/execution_plan_run_YYYYMMDD_*.csv          → planned entry árak, risk, multiplierek
```

SPY napi return: Polygon API-ból (`get_aggregates("SPY", today, today)`) vagy az aznapi Phase 0 logból.

### Kimenet

```
state/daily_metrics/YYYY-MM-DD.json
```

Struktúra:

```json
{
  "date": "2026-04-14",
  "day_number": 41,

  "positions": {
    "opened": 4,
    "qualified_above_threshold": 7,
    "threshold": 85,
    "max_allowed": 5
  },

  "market": {
    "spy_return_pct": -0.41,
    "vix_close": 19.06,
    "strategy": "LONG"
  },

  "scoring": {
    "avg_score": 92.3,
    "min_score": 88.5,
    "max_score": 95.0,
    "scores": {
      "PECO": 94.0,
      "FLEX": 93.0,
      "MWA": 92.5,
      "ADC": 91.5
    }
  },

  "execution": {
    "avg_fill_slippage_pct": 0.32,
    "slippage_per_ticker": {
      "PECO": {"planned": 38.33, "filled": 38.06, "slippage_pct": -0.70},
      "FLEX": {"planned": 73.55, "filled": 74.33, "slippage_pct": 1.06}
    },
    "commission_total": 27.25
  },

  "exits": {
    "tp1": 1,
    "tp2": 0,
    "sl": 0,
    "loss_exit": 1,
    "trail": 1,
    "moc": 3
  },

  "pnl": {
    "gross": -486.91,
    "commission": 27.25,
    "net": -514.16,
    "cumulative": -2415.23,
    "cumulative_pct": -2.415
  },

  "excess_return": {
    "portfolio_return_pct": -0.76,
    "spy_return_pct": -0.41,
    "excess_pct": -0.35,
    "note": "excess = portfolio - SPY (beta=1 assumption)"
  },

  "trades": {
    "best": {"ticker": "SBRA", "pnl": 74.0, "pnl_pct": 0.39, "exit_type": "MOC"},
    "worst": {"ticker": "ARM", "pnl": -207.9, "pnl_pct": -4.38, "exit_type": "LOSS_EXIT"},
    "details": [
      {"ticker": "SBRA", "score": 94.5, "entry": 20.38, "exit": 20.46, "pnl": 74.0, "exit_type": "MOC"},
      {"ticker": "ARM", "score": 142.5, "entry": 158.04, "exit": 151.11, "pnl": -207.9, "exit_type": "LOSS_EXIT"}
    ]
  }
}
```

### A slippage számítás

A MKT entry-nél a slippage = (fill - planned) / planned × 100. Az `execution_plan_*.csv`-ből jön a planned entry, a `pt_events` JSONL-ből a fill ár. A join a ticker alapján történik.

```python
# execution plan CSV-ből:
planned = {"PECO": 38.33, "FLEX": 73.55, ...}

# pt_events JSONL order_submitted event-ből:
# (a limit mező a planned entry — a fill ár a trades CSV-ből vagy EOD-ból)

# trades / EOD-ból:
filled = {"PECO": 38.06, "FLEX": 74.33, ...}

slippage = {t: (filled[t] - planned[t]) / planned[t] * 100 for t in planned}
```

### SPY return

```python
from ifds.data.polygon import PolygonClient

polygon = PolygonClient(api_key=...)
today = date.today().isoformat()
yesterday = (date.today() - timedelta(days=1)).isoformat()
bars = polygon.get_aggregates("SPY", yesterday, today)
if bars and len(bars) >= 2:
    spy_return = (bars[-1]["c"] - bars[-2]["c"]) / bars[-2]["c"]
```

Vagy cache-eld az aznapi Phase 0 VIX/macro adatból, ha elérhető.

### A `state/daily_metrics/` mappa

```python
os.makedirs("state/daily_metrics", exist_ok=True)
path = f"state/daily_metrics/{today_str}.json"
```

Nincs rotation, nincs cleanup — az összes napi metrika megmarad (egy fájl ~1KB, 252 kereskedési nap/év = 252KB/év).

## Heti aggregáció (jövőbeli — NEM most implementálandó)

A heti és kétheti kiértékelés manuális (Tamás naptárjában). A `daily_metrics/*.json` fájlokból Tamás vagy a Log Review chat aggregálja a heti metrikákat. Ha a jövőben automatizálni akarjuk → külön task.

## Tesztek

- `test_daily_metrics_output_schema` — a JSON tartalmazza az összes kötelező mezőt
- `test_daily_metrics_no_trades` — ha nincs trade aznap → üres trades, pnl=0
- `test_daily_metrics_spy_return` — SPY return kiszámítása helyes
- `test_daily_metrics_slippage` — slippage = (fill - planned) / planned × 100

## Commit

```
feat(metrics): daily metrics collection — automated walk-forward measurement

New script: daily_metrics.py — runs at 22:10 CEST after EOD report.
Collects: position count, scores, fill slippage, exit breakdown,
P&L (gross/net/excess vs SPY), commission, best/worst trade.

Output: state/daily_metrics/YYYY-MM-DD.json (structured, machine-readable).
This replaces the ad-hoc scoring validation as the primary measurement tool.
Enables weekly/biweekly scoring validation without manual data assembly.

Context: BC23 redesign requires continuous measurement to validate that
the new scoring weights, TP/SL levels, and position limits improve alpha.
```
