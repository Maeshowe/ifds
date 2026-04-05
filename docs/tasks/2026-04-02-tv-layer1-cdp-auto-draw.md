Status: OPEN
Updated: 2026-04-03
Note: TV-SYNC Layer 1 — CDP auto-draw (~6-8h CC)

# TV-SYNC Layer 1 — Pozíció vizualizáció TradingView-on (CDP auto-draw)

## Cél

A napi pipeline és submit_orders.py után automatikusan rajzolni a TradingView
Desktop chartra az aktuális pozíciók szintjeit. IBKR egyidejű használat nélkül
követhető, hogy a trade-k hogyan mennek.

## Háttér — Az IBKR egyfelhasználós probléma

Az IBKR Gateway egyszerre csak egy klienst szolgál ki. A paper trading scriptek
(submit=10, avwap=16, monitor=15, close=11, eod=12) percenként használják,
így az IBKR TWS/Gateway-t nem lehet megnyitni a pozíciók követésére.

A TradingView Desktop (Electron app) CDP-n keresztül (Chrome DevTools Protocol,
port 9222) programozottan vezérelhető: watchlist, rajzolás, szimbólumváltás.

## Adatforrás

**Elsődleges:** `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json`

Ez a VALÓS állapot (nem az execution plan!):
- `entry_price` — AVWAP-korrigált ha `avwap_converted: true`
- `tp1_price`, `tp2_price` — AVWAP után újraszámolt
- `stop_loss`, `sl_distance` — VIX-capped (pt_avwap.py)
- `trail_active`, `trail_sl_current`, `trail_high` — trailing stop state
- `scenario_b_activated` — 19:00 CET döntés megtörtént-e
- `total_qty`, `qty_b` — bracket A/B méretezés
- `avwap_state`, `avwap_last` — AVWAP konverzió állapot

**Másodlagos:** `output/execution_plan_run_YYYYMMDD_*.csv`
- `instrument_id`, `limit_price`, `stop_loss`, `take_profit_1`, `take_profit_2`
- `score`, `sector`, `gex_regime`, `multiplier_total`
- Felhasználás: ha monitor_state még nem létezik (submit előtt)

## Scope

### 1. `scripts/tradingview/tv_sync.py` — Fő script

Python CDP kliens ami a TradingView Desktop-ot vezérli:

```python
"""IFDS TradingView Sync — draw position levels on TradingView Desktop.

Reads monitor_state.json and draws entry/TP/SL levels on TradingView charts.
TradingView Desktop must be running with --remote-debugging-port=9222.

Usage:
    python scripts/tradingview/tv_sync.py              # Sync all positions
    python scripts/tradingview/tv_sync.py --dry-run    # Print what would be drawn
    python scripts/tradingview/tv_sync.py --clear      # Remove IFDS drawings
"""
```

**CDP kommunikáció:**
- websocket csatlakozás `ws://localhost:9222` (standard CDP)
- A `tradingview-mcp` repo `src/` kódjából portolható a connection logic
- Fő CDP módszerek: `Runtime.evaluate()` JS injection a TV Electron ablakba

**Művelet per ticker:**

```python
for ticker, state in monitor_state.items():
    # 1. Watchlist-re adás
    add_to_watchlist(cdp, ticker)
    
    # 2. Szimbólum váltás
    set_symbol(cdp, ticker)
    sleep(1)  # chart betöltés
    
    # 3. Meglévő IFDS rajzok törlése (tag alapján)
    clear_ifds_drawings(cdp, tag="IFDS")
    
    # 4. Entry marker
    if state.get("avwap_converted"):
        draw_horizontal_line(cdp, state["entry_price"], 
            color="orange", style="dashed", text=f"AVWAP Entry ${state['entry_price']:.2f}")
    else:
        draw_horizontal_line(cdp, state["entry_price"],
            color="blue", style="solid", text=f"Limit Entry ${state['entry_price']:.2f}")
    
    # 5. TP1 / TP2
    draw_horizontal_line(cdp, state["tp1_price"],
        color="green", style="dashed", text=f"TP1 ${state['tp1_price']:.2f}")
    draw_horizontal_line(cdp, state["tp2_price"],
        color="green", style="dotted", text=f"TP2 ${state['tp2_price']:.2f}")
    
    # 6. Stop Loss (VIX-capped)
    draw_horizontal_line(cdp, state["stop_loss"],
        color="red", style="solid", text=f"SL ${state['stop_loss']:.2f}")
    
    # 7. Trail SL (ha aktív)
    if state.get("trail_active"):
        draw_horizontal_line(cdp, state["trail_sl_current"],
            color="orange", style="dashed",
            text=f"Trail SL ${state['trail_sl_current']:.2f} ({state['trail_scope']})")
        # Trail high marker
        draw_horizontal_line(cdp, state["trail_high"],
            color="gray", style="dotted", text=f"Trail High ${state['trail_high']:.2f}")
```

### 2. CDP helper modul — `scripts/tradingview/lib/cdp_client.py`

A `tradingview-mcp` repo CDP logikáját portoljuk Python-ba:

```python
class CDPClient:
    """Chrome DevTools Protocol client for TradingView Desktop."""
    
    def __init__(self, host="localhost", port=9222):
        self.ws_url = self._get_ws_url(host, port)
        self.ws = None
        self._msg_id = 0
    
    def connect(self) -> None:
        """Connect to TradingView via CDP websocket."""
    
    def evaluate(self, expression: str) -> dict:
        """Execute JavaScript in TradingView context."""
    
    def disconnect(self) -> None:
        """Close websocket connection."""
```

A TradingView belső API-ja (amit az MCP is használ):
```javascript
// Szimbólum váltás
TradingView.activeChart().setSymbol("AAPL")

// Rajzolás (horizontal line)
TradingView.activeChart().createShape(
    {time: Math.floor(Date.now()/1000), price: 155.00},
    {shape: "horizontal_line", lock: true, disableSelection: false,
     overrides: {linecolor: "#00FF00", linestyle: 2, linewidth: 1,
                 showLabel: true, text: "TP1 $155.00"}}
)

// Watchlist
// TradingView.activeChart() → watchlist API via ui_evaluate
```

### 3. Logging integráció (log infrastruktúra modernizáció)

A tv_sync.py a többi PT scripthez hasonlóan a közös log infrastruktúrát használja:

```python
# log_setup.py — napi rotáció (logs/pt_tv_sync_YYYY-MM-DD.log)
from lib.log_setup import setup_pt_logger
logger = setup_pt_logger("tv_sync")

# event_logger.py — üzleti event-ek a közös JSONL-be
from lib.event_logger import PTEventLogger
events = PTEventLogger()
```

**Event típusok a pt_events JSONL-ben:**

| Event | Mikor | Adat |
|-------|-------|------|
| `tv_sync_started` | Script indul | tickers, mode (sync/update) |
| `tv_sync_ticker` | Ticker rajzolva | ticker, entry, tp1, tp2, sl, avwap_state, trail_active |
| `tv_sync_completed` | Sync kész | tickers_count, errors_count, duration_sec |
| `tv_sync_failed` | CDP hiba | error_message |

### 4. Cron integráció (Mac Mini)

A script belül kezeli a napi log rotációt (`logs/pt_tv_sync_YYYY-MM-DD.log`),
a cron csak stderr-t naplózza biztonsági mentésként:

```bash
# 15:40 CET — submit_orders (15:35) után, monitor_state kész
40 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tradingview/tv_sync.py 2>> logs/cron_errors.log

# 19:10 CET — Scenario B döntés (19:00) után, frissített szintek
10 19 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tradingview/tv_sync.py --update 2>> logs/cron_errors.log
```

### 5. Telegram integráció

Sync eredmény küldése Telegram-ra:
```
TV SYNC | 2026-04-15 15:40 CET
✅ 5 ticker szinkronizálva: TECK, PNW, EMN, CENX, DBRG
📊 TECK: AVWAP entry $53.24, Trail aktív $52.99
📊 PNW: Limit entry $100.75, Scenario B pending
⚠️ DBRG: AVWAP FAILED, eredeti szintek
```

## Előfeltétel

- TradingView Desktop telepítve Mac Mini-re
- TradingView fizetős előfizetés (real-time data)
- TradingView debug módban indítva: `--remote-debugging-port=9222`
- Python `websocket-client` csomag (pip install)
- Log infrastruktúra modernizáció KÉSZ (`log_setup.py`, `event_logger.py`)
- Lásd: `docs/guides/tradingview-setup.md` (infrastruktúra útmutató)

## Tesztelés

- `test_tv_sync.py`:
  - monitor_state parsing: normál, AVWAP-converted, trail_active
  - Dry-run mód: szintek listája stdout-ra, nincs CDP hívás
  - Üres monitor_state → no crash, "No positions" log
  - CDP connection failure → graceful exit + Telegram alert
  - 19:10-es update mód: csak változott szintek frissítése
- Manuális teszt: TV-n vizuálisan ellenőrizni a szinteket

## Fájlok

| Fájl | Leírás |
|------|--------|
| `scripts/tradingview/__init__.py` | ÚJ csomag |
| `scripts/tradingview/tv_sync.py` | ÚJ — fő sync script |
| `scripts/tradingview/lib/__init__.py` | ÚJ |
| `scripts/tradingview/lib/cdp_client.py` | ÚJ — CDP kommunikáció |
| `scripts/tradingview/lib/drawings.py` | ÚJ — rajzolási helper-ek |
| `tests/tradingview/test_tv_sync.py` | ÚJ |

## Commit

```
feat(tradingview): add CDP position sync for TradingView Desktop

Reads monitor_state.json and draws entry/TP/SL/trail levels on
TradingView charts via Chrome DevTools Protocol (port 9222).
Runs at 15:40 and 19:10 CET. Supports AVWAP-adjusted entries,
VIX-capped SL, and trailing stop visualization.
```
