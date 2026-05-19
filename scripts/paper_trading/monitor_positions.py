#!/usr/bin/env python3
"""IFDS Paper Trading — Leftover position monitor (swing-aware).

Runs at 10:10 CET via cron (after the Sunday 22:00 macro pipeline; before
the 14:30 Phase 4-6 cron). Distinguishes between:

- TRUE LEFTOVERS — IBKR-ben van pozíció, DE NEM swing carry-over ÉS NEM
  permanent orphan (pl. AVDL.CVR). Ez WARNING-ot küld, manual zárás kell.
- SWING CARRY-OVER — IBKR-ben van ÉS swing_positions.json-ben is. Ez a
  swing arch normál működése (3-5 nap hold), NEM hibajelzés.
- PERMANENT ORPHAN — non-tradable ".CVR" tickers, sose kerülnek a swing-be.

Hallgat (no Telegram) ha mind csak swing carry-over + orphan; csak akkor
küld Telegram-ot, ha valódi leftover van. Verbose mode-ban (IFDS_LEFTOVER_VERBOSE)
mindig küld egy reggeli heartbeat-et.

Usage:
    python scripts/paper_trading/monitor_positions.py
"""
from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("monitor_positions")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger('monitor_positions')

try:
    from lib.event_logger import PTEventLogger
    evt = PTEventLogger()
except ModuleNotFoundError:
    evt = None

# Non-tradable orphans that legitimately stay in IBKR but never enter the
# swing state (e.g. corporate action remnants). Treat as ignored.
PERMANENT_ORPHANS: frozenset[str] = frozenset({"AVDL.CVR"})


def send_telegram(message: str) -> None:
    """Send message via Telegram Bot API with CET timestamp header."""
    from lib.telegram_helper import telegram_header
    from lib.telegram_helper import send_telegram as _send
    _send(f"{telegram_header('LEFTOVER')}\n{message}")


def load_swing_state_tickers() -> set[str]:
    """Return the set of tickers currently in state/swing_positions.json.

    Returns empty set if the state file is missing or malformed — in which
    case every IBKR position will be treated as a candidate leftover and the
    operator can decide.
    """
    try:
        from ifds.config.loader import Config
        from ifds.state.swing_positions import load_swing_positions
        cfg = Config()
        state_file = cfg.tuning.get(
            "swing_positions_state_file", "state/swing_positions.json",
        )
    except Exception:
        state_file = "state/swing_positions.json"

    try:
        from ifds.state.swing_positions import load_swing_positions
        positions = load_swing_positions(state_file)
        return {p.ticker for p in positions}
    except Exception as exc:
        logger.warning(f"Failed to load swing state: {exc}")
        return set()


def classify_positions(
    ibkr_tickers: set[str],
    swing_tickers: set[str],
) -> tuple[set[str], set[str], set[str]]:
    """Split IBKR positions into (true_leftovers, swing_carry_over, permanent_orphans).

    Pure function — easy to unit test against IBKR mocks.
    """
    permanent = ibkr_tickers & PERMANENT_ORPHANS
    tradable = ibkr_tickers - PERMANENT_ORPHANS
    swing_carry_over = tradable & swing_tickers
    true_leftovers = tradable - swing_tickers
    return true_leftovers, swing_carry_over, permanent


def main() -> None:
    try:
        from lib.trading_day_guard import check_trading_day
        check_trading_day(logger)
    except ModuleNotFoundError:
        pass
    from lib.connection import connect, disconnect

    today_str = date.today().strftime("%Y-%m-%d")
    logger.info(f"Leftover position monitor — {today_str}")

    swing_tickers = load_swing_state_tickers()
    logger.info(
        f"Swing state: {sorted(swing_tickers) if swing_tickers else 'empty'}"
    )

    ib = connect(client_id=14)
    ib.sleep(3)

    # All IBKR positions (including ignored ones like .CVR — classified later).
    raw_positions = [p for p in ib.positions() if p.position != 0]
    ibkr_qty = {p.contract.symbol: int(p.position) for p in raw_positions}
    ibkr_tickers = set(ibkr_qty.keys())

    true_leftovers, swing_carry_over, permanent_orphans = classify_positions(
        ibkr_tickers, swing_tickers,
    )

    logger.info(
        f"Classification — true_leftovers: {sorted(true_leftovers)} | "
        f"swing_carry_over: {sorted(swing_carry_over)} | "
        f"permanent_orphans: {sorted(permanent_orphans)}"
    )

    verbose = bool(os.getenv("IFDS_LEFTOVER_VERBOSE", "").lower() in ("1", "true", "yes"))

    if true_leftovers:
        lines = [f"⚠️ TRUE LEFTOVER POSITIONS — {today_str}"]
        for sym in sorted(true_leftovers):
            lines.append(f"  {sym}: {ibkr_qty[sym]:+d} shares (NOT in swing state)")
        if swing_carry_over:
            lines.append(
                f"\nSwing carry-over (NORMAL, ignored): {sorted(swing_carry_over)}"
            )
        if permanent_orphans:
            lines.append(
                f"Permanent orphans (ignored): {sorted(permanent_orphans)}"
            )
        lines.append("\nAction: nuke.py before market open or manual close in IBKR.")
        msg = "\n".join(lines)
        logger.warning(msg)
        send_telegram(msg)
        if evt:
            evt.log(
                "monitor_positions", "true_leftover_found",
                tickers=sorted(true_leftovers),
                count=len(true_leftovers),
                swing_carry_over=sorted(swing_carry_over),
            )
    else:
        logger.info("No true leftovers — swing carry-over is normal.")
        if evt:
            evt.log(
                "monitor_positions", "no_true_leftover",
                swing_carry_over=sorted(swing_carry_over),
                permanent_orphans=sorted(permanent_orphans),
            )
        if verbose:
            lines = [f"✓ Morning leftover check — {today_str}"]
            if swing_carry_over:
                lines.append(
                    f"  Swing carry-over (NORMAL): {sorted(swing_carry_over)}"
                )
            if permanent_orphans:
                lines.append(
                    f"  Permanent orphans (ignored): {sorted(permanent_orphans)}"
                )
            lines.append("  No true leftovers detected.")
            send_telegram("\n".join(lines))

    disconnect(ib)


if __name__ == "__main__":
    main()
