#!/usr/bin/env python3
"""IBKR Paper Trading — Close remaining positions at market close (MOC).

Runs at 21:45 CET (15:45 ET) — 5 min before NYSE MOC deadline.
Submits Market-on-Close SELL orders for any open positions.

Usage:
    python scripts/paper_trading/close_positions.py
"""
import os
from datetime import date

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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger('close')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ORDER_SIZE = 500  # IBKR precautionary size limit (Global Configuration/Presets)

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
        if fill.execution.side == 'BOT':
            total_bought += shares
        elif fill.execution.side == 'SLD':
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


def main():
    try:
        from lib.trading_day_guard import check_trading_day
        check_trading_day(logger)
    except ModuleNotFoundError:
        pass

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

    today_str = date.today().strftime('%Y-%m-%d')

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
        ExecutionFilter(time=date.today().strftime('%Y%m%d') + ' 00:00:00')
    )

    # Get open positions (long and short, skip non-tradable)
    positions = [p for p in ib.positions()
                 if p.position != 0
                 and '.CVR' not in p.contract.symbol
                 and p.contract.secType == 'STK']

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
        contract = Stock(conId=con_id, exchange='SMART')
        ib.qualifyContracts(contract)

        action = 'SELL' if pos.position > 0 else 'BUY'
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
                    evt.log("close", "moc_submitted", ticker=sym, qty=leg_qty, action=action, leg=leg, total_legs=total_legs)
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

        lines = [f"🔔 PAPER TRADING MOC — {today_str}",
                 f"Closing {len(ticker_totals)} positions at market close:"]
        for sym, (total_qty, action) in ticker_totals.items():
            lines.append(f"{sym}: {action} {total_qty} shares")
        send_telegram("\n".join(lines))

    disconnect(ib)


if __name__ == '__main__':
    main()
