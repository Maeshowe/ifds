Status: DONE
Updated: 2026-04-03
Note: BC20A Phase_20A_2 — Position Tracker (~3h CC)
Depends: Phase_20A_1 (VWAP) kész

# BC20A Phase_20A_2 — Position Tracker (State Management)

## Cél

Nyitott swing pozíciók állapotkezelése: hold day tracking, TP1 status,
trail stop állapot, earnings check. Az `open_positions.json` state fájl
a `close_positions.py` és az új pipeline közötti híd.

## Scope

### 1. `src/ifds/state/position_tracker.py` — Új modul

```python
from dataclasses import dataclass, asdict
from datetime import date
import json

@dataclass
class OpenPosition:
    ticker: str
    entry_date: str                # ISO format
    entry_price: float
    total_qty: int
    remaining_qty: int
    tp1_triggered: bool = False
    tp1_qty: int = 0               # Qty that was exited at TP1
    trail_qty: int = 0             # Qty under trail stop
    sl_price: float = 0.0
    tp1_price: float = 0.0
    trail_amount_usd: float = 0.0  # TRAIL order trailing amount ($)
    current_trail_stop: float = 0.0
    hold_days: int = 0             # Trading days since entry
    max_hold_days: int = 5
    atr_at_entry: float = 0.0
    vwap_at_entry: float = 0.0
    obsidian_regime: str = "undetermined"
    run_id: str = ""
    sector: str = ""
    direction: str = "BUY"
    breakeven_triggered: bool = False

class PositionTracker:
    """Manage open swing positions via JSON state file."""
    
    def __init__(self, state_file: str = "state/open_positions.json"):
        self.state_file = state_file
        self.positions: list[OpenPosition] = []
        self._load()
    
    def _load(self) -> None:
        """Load positions from JSON state file."""
    
    def _save(self) -> None:
        """Atomic write positions to JSON state file."""
    
    def add_position(self, pos: OpenPosition) -> None:
        """Add a new position (from submit_orders.py)."""
    
    def remove_position(self, ticker: str) -> OpenPosition | None:
        """Remove a position (full exit). Returns removed pos or None."""
    
    def update_position(self, ticker: str, **kwargs) -> bool:
        """Update fields on existing position. Returns True if found."""
    
    def get_position(self, ticker: str) -> OpenPosition | None:
        """Get position by ticker."""
    
    def get_all(self) -> list[OpenPosition]:
        """Get all open positions."""
    
    def increment_hold_days(self) -> None:
        """Increment hold_days for all positions (called daily by close_positions)."""
    
    def get_expired(self) -> list[OpenPosition]:
        """Get positions that hit max_hold_days."""
    
    def get_earnings_risk(self, earnings_dates: dict[str, str]) -> list[OpenPosition]:
        """Get positions with earnings within 1 trading day."""
    
    @property
    def count(self) -> int:
        return len(self.positions)
```

### 2. State fájl formátum

```json
{
  "positions": [
    {
      "ticker": "CF",
      "entry_date": "2026-04-15",
      "entry_price": 136.45,
      "total_qty": 28,
      "remaining_qty": 28,
      "tp1_triggered": false,
      "tp1_qty": 14,
      "trail_qty": 14,
      "sl_price": 130.50,
      "hold_days": 0,
      "max_hold_days": 5,
      "atr_at_entry": 3.96,
      "sector": "Basic Materials",
      "direction": "BUY"
    }
  ],
  "last_updated": "2026-04-15T15:48:00Z"
}
```

### 3. submit_orders.py integráció (előkészítés)

A `submit_orders.py` a pozíció beküldésekor hívja:

```python
tracker = PositionTracker()
tracker.add_position(OpenPosition(
    ticker=ticker,
    entry_date=date.today().isoformat(),
    entry_price=fill_price,
    total_qty=qty,
    remaining_qty=qty,
    tp1_qty=int(qty * 0.50),
    trail_qty=qty - int(qty * 0.50),
    sl_price=stop_loss,
    tp1_price=tp1_price,
    atr_at_entry=atr,
    ...
))
```

### 4. close_positions.py integráció (előkészítés)

A `close_positions.py` a Position Tracker-ből olvassa a nyitott pozíciókat,
nem az IBKR-ből. Előnyök:
- Tudja a hold_days-t, tp1 státuszt, atr-t
- IBKR reqPositions() csak backup/verification

## Tesztelés

- `test_position_tracker.py`:
  - add + get + count: basic CRUD
  - remove: visszaadja a pozíciót, count csökken
  - update: tp1_triggered=True → mentve
  - increment_hold_days: +1 minden pozícióra
  - get_expired: hold_days >= max_hold_days
  - get_earnings_risk: earnings 1 napon belül
  - _save + _load round-trip: JSON serialization
  - concurrent writes: atomic write → nem korrupt
  - empty state file: graceful load
- `pytest` all green

## Fájlok

| Fájl | Változás |
|------|---------|
| `src/ifds/state/position_tracker.py` | ÚJ |
| `tests/state/test_position_tracker.py` | ÚJ |

## Commit

```
feat(state): add PositionTracker for swing position management

JSON-backed state manager for open swing positions: hold day
tracking, TP1 status, trail stop state, max hold detection,
earnings risk check. Atomic file writes for crash safety.
```
