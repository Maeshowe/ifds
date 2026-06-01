#!/usr/bin/env python3
"""IBKR Paper Trading — Close positions.

Three modes (Task #4 swing pivot, 2026-05-18):
    --mode=moc         Legacy: MOC SELL all open positions at 21:45 CEST
    --mode=eod_flags   Swing: next-day 15:30 CEST market SELL of HARD/MENTAL/TP/TRAIL flags
    --mode=time_stop   Swing: same-day 21:40 CEST MOC SELL of TIME_STOP flags

Usage:
    python scripts/paper_trading/close_positions.py --mode=eod_flags
    python scripts/paper_trading/close_positions.py --mode=time_stop
    python scripts/paper_trading/close_positions.py            # default: moc (legacy)
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

try:
    from lib.log_setup import setup_pt_logger

    logger = setup_pt_logger("close")
except ModuleNotFoundError:
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("close")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ORDER_SIZE = 500  # IBKR precautionary size limit (Global Configuration/Presets)

# Pending-exit ledger (P0 §0.11 Part A) — anchored to repo root so the 22:10
# recorder (daily_metrics.record_pending_exits) reads the same dir regardless
# of the cron working directory.
PENDING_EXITS_DIR = str(Path(__file__).resolve().parents[2] / "state" / "pending_exits")

try:
    from lib.event_logger import PTEventLogger

    evt = PTEventLogger()
except ModuleNotFoundError:
    evt = None

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def send_telegram(message):
    """Send message via Telegram Bot API with CET timestamp header."""
    from lib.telegram_helper import telegram_header
    from lib.telegram_helper import send_telegram as _send

    _send(f"{telegram_header('CLOSE')}\n{message}")


# ---------------------------------------------------------------------------
# Pending-exit ledger write (P0 §0.11 Part A)
# ---------------------------------------------------------------------------


def record_pending_exit_safe(pos, exit_type: str, qty: int, today_str: str) -> None:
    """Append a pending-exit ledger entry for a submitted swing SELL.

    CRITICAL: fully try/except guarded — a ledger-write failure must NEVER
    block or raise after the actual SELL has been submitted. On failure we
    only ``logger.warning`` and send a best-effort Telegram WARNING.

    For a TP1 partial the ``qty`` passed is the SOLD leg (e.g. 50%); the
    remaining position stays open with ``exit_type=TP1`` recorded for the
    realized sold leg only.
    """
    try:
        from lib.pending_exits import append_pending_exit

        append_pending_exit(
            {
                "ticker": pos.ticker,
                "entry_price": pos.entry_price,
                "entry_date": pos.entry_date,
                "qty": qty,
                "exit_type": exit_type,
                "sector": getattr(pos, "sector", "") or "",
            },
            ledger_dir=PENDING_EXITS_DIR,
            today=today_str,
        )
    except Exception as exc:  # noqa: BLE001 — ledger must never block the SELL
        logger.warning(
            f"pending_exits ledger write failed for {getattr(pos, 'ticker', '?')} "
            f"{exit_type}: {exc}"
        )
        try:
            send_telegram(
                f"⚠️ Ledger write failed: {getattr(pos, 'ticker', '?')} {exit_type} "
                f"— realized P&L tracking may miss this exit (record manually)."
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Net position helper
# ---------------------------------------------------------------------------


def get_net_open_qty(symbol: str, con_id: int, gross_qty: int, todays_fills) -> int:
    """Return safe MOC qty using net BOT-SLD fill calculation.

    Computes today's net position from all executions for this contract:
    net = total_bought - total_sold.  This is suffix-independent and handles
    all exit types (bracket TP/SL, TRAIL, LOSS_EXIT, AVWAP conversions).

    Falls back to gross_qty if no fills found (conservative: close everything).
    Returns 0 if fully closed intraday.
    """
    total_bought = 0
    total_sold = 0
    for fill in todays_fills:
        if fill.contract.conId != con_id:
            continue
        shares = int(fill.execution.shares)
        if fill.execution.side == "BOT":
            total_bought += shares
        elif fill.execution.side == "SLD":
            total_sold += shares

    if total_bought == 0 and total_sold == 0:
        # No fills today for this contract — use gross_qty from positions()
        return gross_qty

    net_position = total_bought - total_sold
    moc_qty = max(0, net_position)

    if moc_qty != gross_qty:
        logger.info(
            f"{symbol}: fills today BOT={total_bought} SLD={total_sold} net={net_position} — "
            f"MOC qty {gross_qty} → {moc_qty}"
        )
    return moc_qty


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_swing_eod_flags(state_file: str, today_str: str) -> None:
    """15:30 CEST next-day exit — Task #4 (HARD_SL/MENTAL_SL/TP1/TP2/TRAIL_SL).

    Reads state/swing_positions.json, finds positions with next_action ∈
    {HARD_SL, MENTAL_SL, TP1, TP2, TRAIL_SL}, submits market SELL orders,
    and updates state (TP1 → partial; others → remove).
    """
    from ifds.state.swing_positions import (
        ACTION_TP1,
        EOD_ACTIONS_NEXT_DAY,
        apply_executed_exit,
        load_swing_positions,
        save_swing_positions,
    )
    from lib.connection import connect, get_account, disconnect
    from ib_insync import MarketOrder, Stock

    positions = load_swing_positions(state_file)
    actionable = [p for p in positions if p.next_action in EOD_ACTIONS_NEXT_DAY]
    if not actionable:
        logger.info("[SWING 15:30 close] No EOD action flags set — nothing to do.")
        return

    ib = connect(client_id=11, context_label="close_positions.py (swing eod_flags)")
    account = get_account(ib)

    new_state = [p for p in positions if p.next_action not in EOD_ACTIONS_NEXT_DAY]
    tp1_sell_pct = 0.50  # mirrored from TUNING — close_positions stays minimal
    submitted: list[tuple[str, str, int]] = []

    for pos in actionable:
        from ifds.state.swing_positions import compute_sell_qty

        qty = compute_sell_qty(pos, pos.next_action, tp1_sell_pct=tp1_sell_pct)
        contract = Stock(pos.ticker, "SMART", "USD")
        ib.qualifyContracts(contract)
        order = MarketOrder(action="SELL", totalQuantity=qty)
        order.account = account
        order.orderRef = f"IFDS_SWING_{pos.ticker}_{pos.next_action}"
        ib.placeOrder(contract, order)
        ib.sleep(1)
        logger.info(f"  {pos.ticker}: {pos.next_action} → SELL {qty} (MKT)")
        if evt:
            evt.log("close", "swing_eod_exit", ticker=pos.ticker, action=pos.next_action, qty=qty)
        submitted.append((pos.ticker, pos.next_action, qty))

        # Ledger the realized exit (sold qty) for the 22:10 P&L recorder.
        record_pending_exit_safe(pos, pos.next_action, qty, today_str)

        if pos.next_action == ACTION_TP1:
            updated = apply_executed_exit(pos, ACTION_TP1, tp1_sell_pct=tp1_sell_pct)
            if updated is not None:
                new_state.append(updated)

    save_swing_positions(state_file, new_state)
    logger.info(f"[SWING 15:30 close] Submitted {len(submitted)} exits | open: {len(new_state)}")

    if submitted:
        lines = [f"📤 IFDS Swing 15:30 Exit — {today_str}"]
        for ticker, action, qty in submitted:
            lines.append(f"  {ticker}: {action} qty {qty}")
        send_telegram("\n".join(lines))

    disconnect(ib)


def run_swing_time_stop(state_file: str, today_str: str) -> None:
    """21:40 CEST same-day TIME_STOP MOC SELL — Task #4."""
    from ifds.state.swing_positions import (
        ACTION_TIME_STOP,
        load_swing_positions,
        save_swing_positions,
    )
    from lib.connection import connect, get_account, disconnect
    from lib.orders import create_moc_order
    from ib_insync import Stock

    positions = load_swing_positions(state_file)
    actionable = [p for p in positions if p.next_action == ACTION_TIME_STOP]
    if not actionable:
        logger.info("[SWING 21:40 close] No TIME_STOP flags — nothing to do.")
        return

    ib = connect(client_id=11, context_label="close_positions.py (swing time_stop)")
    account = get_account(ib)

    new_state = [p for p in positions if p.next_action != ACTION_TIME_STOP]
    submitted: list[tuple[str, int]] = []
    for pos in actionable:
        contract = Stock(pos.ticker, "SMART", "USD")
        ib.qualifyContracts(contract)
        order = create_moc_order(pos.qty_remaining, account, action="SELL")
        order.orderRef = f"IFDS_SWING_{pos.ticker}_TIME_STOP"
        ib.placeOrder(contract, order)
        ib.sleep(1)
        logger.info(f"  {pos.ticker}: TIME_STOP → MOC SELL {pos.qty_remaining}")
        if evt:
            evt.log("close", "swing_time_stop_moc", ticker=pos.ticker, qty=pos.qty_remaining)
        submitted.append((pos.ticker, pos.qty_remaining))

        # Ledger the realized exit for the 22:10 P&L recorder.
        record_pending_exit_safe(pos, "TIME_STOP", pos.qty_remaining, today_str)

    save_swing_positions(state_file, new_state)
    logger.info(f"[SWING 21:40 close] MOC submitted {len(submitted)} | open: {len(new_state)}")

    if submitted:
        lines = [f"🌒 IFDS Swing TIME_STOP MOC — {today_str}"]
        for ticker, qty in submitted:
            lines.append(f"  {ticker}: MOC SELL qty {qty}")
        send_telegram("\n".join(lines))

    disconnect(ib)


def main():
    parser = argparse.ArgumentParser(description="IFDS Paper Trading — Close Positions")
    parser.add_argument(
        "--mode",
        choices=["moc", "eod_flags", "time_stop"],
        default="moc",
        help="moc: legacy 21:45 MOC close all | eod_flags: 15:30 next-day swing exits | time_stop: 21:40 same-day TIME_STOP MOC",
    )
    args, _ = parser.parse_known_args()

    try:
        from lib.trading_day_guard import check_trading_day

        check_trading_day(logger)
    except ModuleNotFoundError:
        pass

    today_str = date.today().strftime("%Y-%m-%d")

    if args.mode in ("eod_flags", "time_stop"):
        try:
            from ifds.config.loader import Config as _IFDSConfig

            _cfg = _IFDSConfig()
            state_file = _cfg.tuning.get(
                "swing_positions_state_file",
                "state/swing_positions.json",
            )
        except Exception:
            state_file = "state/swing_positions.json"

        if args.mode == "eod_flags":
            run_swing_eod_flags(state_file, today_str)
        else:
            run_swing_time_stop(state_file, today_str)
        return

    # Early close detection
    try:
        from ifds.utils.calendar import is_early_close, get_market_close_time_cet

        if is_early_close():
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo

            close_cet = get_market_close_time_cet()
            now_cet = _dt.now(ZoneInfo("Europe/Budapest")).time()
            if close_cet and now_cet > close_cet:
                logger.error(f"EARLY CLOSE DAY — market closed at {close_cet} CET!")
                send_telegram(f"EARLY CLOSE — piac {close_cet}-kor zárt, MOC túl késő!")
                sys.exit(1)
            logger.info(f"Early close day — market closes at {close_cet} CET")
    except ImportError:
        pass

    from lib.connection import connect, get_account, disconnect
    from lib.orders import create_moc_order

    ib = connect(client_id=11)
    ib.sleep(3)  # Initial sync
    # Force fresh position data: reqPositions ensures intraday TP/SL fills are reflected
    ib.reqPositions()
    ib.sleep(5)  # Wait for IBKR to push updated positions (total: 8s)

    logger.info(f"MOC Close — {today_str}")
    account = get_account(ib)

    from ib_insync import Stock, ExecutionFilter

    # Cancel ALL open orders to prevent late fills after MOC cutoff.
    # Covers: IFDS_ bracket orders + residual split-leg orders without IFDS_ tag
    # (e.g. partial entry fills leaving orphaned SL/TP2 from OCA groups).
    # Safe on paper account (DUH118657) where only IFDS orders exist.
    open_orders = ib.openOrders()
    if open_orders:
        for order in open_orders:
            ib.cancelOrder(order)
        ib.sleep(2)
        logger.info(f"Cancelled {len(open_orders)} open orders before MOC")
    else:
        logger.info("No open orders to cancel")

    # Fetch today's executions once for bracket fill detection (used by get_net_open_qty)
    todays_fills = ib.reqExecutions(
        ExecutionFilter(time=date.today().strftime("%Y%m%d") + " 00:00:00")
    )

    # Get open positions (long and short, skip non-tradable)
    positions = [
        p
        for p in ib.positions()
        if p.position != 0 and ".CVR" not in p.contract.symbol and p.contract.secType == "STK"
    ]

    if not positions:
        logger.info("No positions to close")
        disconnect(ib)
        return

    moc_submitted = []

    for pos in positions:
        sym = pos.contract.symbol
        con_id = pos.contract.conId

        # Compute net open qty after intraday bracket TP/SL fills
        gross_qty = int(abs(pos.position))
        net_qty = get_net_open_qty(sym, con_id, gross_qty, todays_fills)

        if net_qty == 0:
            logger.info(f"{sym}: SKIP — already closed (intraday TP/SL)")
            if evt:
                evt.log("close", "position_skipped", ticker=sym, reason="fully_closed_intraday")
            continue

        if net_qty != gross_qty:
            logger.info(f"{sym}: qty adjusted {gross_qty} → {net_qty} (intraday partial fill)")
            if evt:
                evt.log("close", "qty_adjusted", ticker=sym, gross_qty=gross_qty, net_qty=net_qty)

        # Create fresh contract with SMART routing (avoids Error 10311)
        contract = Stock(conId=con_id, exchange="SMART")
        ib.qualifyContracts(contract)

        action = "SELL" if pos.position > 0 else "BUY"
        qty = net_qty

        if qty <= MAX_ORDER_SIZE:
            order = create_moc_order(qty, account, action=action)
            ib.placeOrder(contract, order)
            moc_submitted.append((sym, qty, action))
            logger.info(f"{sym}: MOC {action} {qty} shares")
            if evt:
                evt.log("close", "moc_submitted", ticker=sym, qty=qty, action=action)
        else:
            # Split into multiple legs to stay under IBKR size limit
            remaining = qty
            leg = 1
            total_legs = -(-qty // MAX_ORDER_SIZE)  # ceil division
            while remaining > 0:
                leg_qty = min(remaining, MAX_ORDER_SIZE)
                order = create_moc_order(leg_qty, account, action=action)
                ib.placeOrder(contract, order)
                moc_submitted.append((sym, leg_qty, action))
                logger.info(f"{sym}: MOC {action} {leg_qty} shares (leg {leg}/{total_legs})")
                if evt:
                    evt.log(
                        "close",
                        "moc_submitted",
                        ticker=sym,
                        qty=leg_qty,
                        action=action,
                        leg=leg,
                        total_legs=total_legs,
                    )
                remaining -= leg_qty
                leg += 1

    ib.sleep(1)  # Let orders propagate

    logger.info(f"MOC submitted: {len(moc_submitted)} positions")

    # Telegram notification — aggregate split legs per ticker
    if moc_submitted:
        ticker_totals = {}
        for sym, leg_qty, action in moc_submitted:
            if sym not in ticker_totals:
                ticker_totals[sym] = (0, action)
            ticker_totals[sym] = (ticker_totals[sym][0] + leg_qty, action)

        lines = [
            f"🔔 PAPER TRADING MOC — {today_str}",
            f"Closing {len(ticker_totals)} positions at market close:",
        ]
        for sym, (total_qty, action) in ticker_totals.items():
            lines.append(f"{sym}: {action} {total_qty} shares")
        send_telegram("\n".join(lines))

    disconnect(ib)


if __name__ == "__main__":
    main()
