"""Position Tracker — JSON-backed state manager for open swing positions.

Tracks hold days, TP1 status, trail stop state, max hold detection,
and earnings risk. Uses atomic file writes for crash safety.

State file: ``state/open_positions.json``
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from ifds.utils.io import atomic_write_json


@dataclass
class OpenPosition:
    """A single open swing position."""

    ticker: str
    entry_date: str                     # ISO format (YYYY-MM-DD)
    entry_price: float
    total_qty: int
    remaining_qty: int
    tp1_triggered: bool = False
    tp1_qty: int = 0                    # Qty that was exited at TP1
    trail_qty: int = 0                  # Qty under trail stop
    sl_price: float = 0.0
    tp1_price: float = 0.0
    trail_amount_usd: float = 0.0       # TRAIL order trailing amount ($)
    current_trail_stop: float = 0.0
    hold_days: int = 0                  # Trading days since entry
    max_hold_days: int = 5
    atr_at_entry: float = 0.0
    vwap_at_entry: float = 0.0
    mm_regime: str = "undetermined"
    run_id: str = ""
    sector: str = ""
    direction: str = "BUY"
    breakeven_triggered: bool = False


class PositionTracker:
    """Manage open swing positions via JSON state file.

    All mutations are persisted immediately via atomic write.
    """

    def __init__(self, state_file: str = "state/open_positions.json") -> None:
        self.state_file = state_file
        self.positions: list[OpenPosition] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load positions from JSON state file."""
        path = Path(self.state_file)
        if not path.exists():
            self.positions = []
            return

        try:
            with open(path) as f:
                data = json.load(f)
            self.positions = [
                OpenPosition(**rec)
                for rec in data.get("positions", [])
            ]
        except (json.JSONDecodeError, TypeError, KeyError):
            self.positions = []

    def _save(self) -> None:
        """Atomic write positions to JSON state file."""
        data = {
            "positions": [asdict(p) for p in self.positions],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write_json(self.state_file, data)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_position(self, pos: OpenPosition) -> None:
        """Add a new position. Replaces existing if same ticker."""
        self.positions = [p for p in self.positions if p.ticker != pos.ticker]
        self.positions.append(pos)
        self._save()

    def remove_position(self, ticker: str) -> OpenPosition | None:
        """Remove a position (full exit). Returns removed pos or None."""
        for i, p in enumerate(self.positions):
            if p.ticker == ticker:
                removed = self.positions.pop(i)
                self._save()
                return removed
        return None

    def update_position(self, ticker: str, **kwargs: object) -> bool:
        """Update fields on existing position. Returns True if found."""
        for p in self.positions:
            if p.ticker == ticker:
                for key, value in kwargs.items():
                    if hasattr(p, key):
                        setattr(p, key, value)
                self._save()
                return True
        return False

    def get_position(self, ticker: str) -> OpenPosition | None:
        """Get position by ticker."""
        for p in self.positions:
            if p.ticker == ticker:
                return p
        return None

    def get_all(self) -> list[OpenPosition]:
        """Get all open positions (returns a copy)."""
        return list(self.positions)

    # ------------------------------------------------------------------
    # Daily operations
    # ------------------------------------------------------------------

    def increment_hold_days(self) -> None:
        """Increment hold_days for all positions (called daily)."""
        for p in self.positions:
            p.hold_days += 1
        if self.positions:
            self._save()

    def get_expired(self) -> list[OpenPosition]:
        """Get positions that hit max_hold_days."""
        return [p for p in self.positions if p.hold_days >= p.max_hold_days]

    def get_earnings_risk(
        self,
        earnings_dates: dict[str, str],
    ) -> list[OpenPosition]:
        """Get positions with earnings within 1 trading day.

        Parameters
        ----------
        earnings_dates:
            ``{ticker: "YYYY-MM-DD"}`` of next earnings date.
        """
        today = date.today()
        at_risk: list[OpenPosition] = []
        for p in self.positions:
            earn_str = earnings_dates.get(p.ticker)
            if earn_str is None:
                continue
            try:
                earn_date = date.fromisoformat(earn_str)
            except ValueError:
                continue
            days_until = (earn_date - today).days
            if 0 <= days_until <= 1:
                at_risk.append(p)
        return at_risk

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self.positions)
