#!/usr/bin/env python3
"""State/IBKR Reconciliation — daily divergence detector.

Runs at 22:15 CET via cron (5 min after the 22:00 EOD eval, before Tamás'
22:30+ review). Compares two source-of-truths:

- ``state/swing_positions.json`` — mental stop / TP1 / TP2 levels per ticker
- IBKR positions (actual holdings)

If they diverge, sends a Telegram WARNING with the two-way diff. Does NOT
auto-fix — the operator decides reconstruction vs nuke.

Day 1 (2026-05-18) example that motivated this script:
  14:42 manual state reset → 15:30 IBKR fills → state empty while
  IBKR holds 3 positions → 22:00 EOD eval would have evaluated on
  empty state (NULL exit logic) without operator intervention.

Usage:
    python scripts/paper_trading/reconcile_state.py
"""

from __future__ import annotations

import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger

    logger = setup_pt_logger("reconcile")
except ModuleNotFoundError:
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("reconcile")

try:
    from lib.event_logger import PTEventLogger

    evt = PTEventLogger()
except ModuleNotFoundError:
    evt = None


# Non-tradable orphans that legitimately stay in IBKR but never enter the
# swing state (e.g. corporate action remnants).
PERMANENT_ORPHANS: frozenset[str] = frozenset({"AVDL.CVR"})


# ---------------------------------------------------------------------------
# Telegram helper
# ---------------------------------------------------------------------------


def send_telegram(message: str) -> None:
    """Send message via Telegram Bot API with CET timestamp header."""
    from lib.telegram_helper import telegram_header
    from lib.telegram_helper import send_telegram as _send

    _send(f"{telegram_header('RECONCILE')}\n{message}")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def compute_divergence(
    state_tickers: set[str],
    ibkr_tickers: set[str],
    permanent_orphans: frozenset[str] = PERMANENT_ORPHANS,
) -> tuple[set[str], set[str]]:
    """Two-way divergence between the swing state and the IBKR holdings.

    Returns ``(in_state_not_ibkr, in_ibkr_not_state)``. The ``ibkr_tickers``
    side is filtered for ``permanent_orphans`` (AVDL.CVR is always benign).
    """
    tradable_ibkr = ibkr_tickers - permanent_orphans
    in_state_not_ibkr = state_tickers - tradable_ibkr
    in_ibkr_not_state = tradable_ibkr - state_tickers
    return in_state_not_ibkr, in_ibkr_not_state


def format_divergence_telegram(
    in_state_not_ibkr: set[str],
    in_ibkr_not_state: set[str],
    today_str: str,
) -> str:
    """Render the WARNING Telegram body for a divergence."""
    lines = [f"⚠️ State/IBKR divergence — {today_str}", ""]
    if in_state_not_ibkr:
        lines.append(f"📋 State has, IBKR doesn't: {sorted(in_state_not_ibkr)}")
    if in_ibkr_not_state:
        lines.append(f"💼 IBKR has, state doesn't: {sorted(in_ibkr_not_state)}")
    lines.append("")
    lines.append("Action: review + decide reconstruction (A) vs nuke (C).")
    lines.append("AVDL.CVR permanent orphan excluded.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# IBKR + state loaders
# ---------------------------------------------------------------------------


def load_state_tickers() -> set[str]:
    """Load the set of tickers currently in ``state/swing_positions.json``."""
    try:
        from ifds.config.loader import Config

        cfg = Config()
        state_file = cfg.tuning.get(
            "swing_positions_state_file",
            "state/swing_positions.json",
        )
    except Exception:
        state_file = "state/swing_positions.json"

    try:
        from ifds.state.swing_positions import load_swing_positions

        return {p.ticker for p in load_swing_positions(state_file)}
    except Exception as exc:
        logger.warning(f"Failed to load swing state: {exc}")
        return set()


def load_ibkr_tickers() -> set[str]:
    """Connect to IBKR (clientId=99) and return the set of non-zero positions."""
    from lib.connection import connect, disconnect

    ib = connect(client_id=99, context_label="reconcile_state.py")
    try:
        ib.sleep(2)
        return {p.contract.symbol for p in ib.positions() if p.position != 0}
    finally:
        disconnect(ib)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    try:
        from lib.trading_day_guard import check_trading_day

        check_trading_day(logger)
    except ModuleNotFoundError:
        pass

    today_str = date.today().strftime("%Y-%m-%d")
    logger.info(f"State/IBKR reconciliation — {today_str}")

    state_tickers = load_state_tickers()
    logger.info(f"State tickers: {sorted(state_tickers)}")

    try:
        ibkr_tickers = load_ibkr_tickers()
    except Exception as exc:
        msg = f"⚠️ Reconcile FAILED — IBKR connection: {exc}"
        logger.error(msg)
        send_telegram(msg)
        if evt:
            evt.log("reconcile", "ibkr_connect_failed", error=str(exc))
        return 1
    logger.info(f"IBKR tickers: {sorted(ibkr_tickers)}")

    in_state_not_ibkr, in_ibkr_not_state = compute_divergence(
        state_tickers,
        ibkr_tickers,
    )

    if not in_state_not_ibkr and not in_ibkr_not_state:
        logger.info("Reconciliation OK — state and IBKR match (silent exit).")
        if evt:
            evt.log(
                "reconcile",
                "no_divergence",
                state_count=len(state_tickers),
                ibkr_count=len(ibkr_tickers),
            )
        return 0

    msg = format_divergence_telegram(in_state_not_ibkr, in_ibkr_not_state, today_str)
    logger.warning(msg)
    send_telegram(msg)
    if evt:
        evt.log(
            "reconcile",
            "divergence_detected",
            in_state_not_ibkr=sorted(in_state_not_ibkr),
            in_ibkr_not_state=sorted(in_ibkr_not_state),
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
