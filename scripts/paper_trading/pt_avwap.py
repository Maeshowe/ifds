#!/usr/bin/env python3
"""IFDS Paper Trading — AVWAP-based Limit→MKT conversion.

If an entry limit order is unfilled 15 minutes after market open, this script
watches the Anchored VWAP. When price dips below AVWAP and crosses back above,
the limit order is converted to MKT and the bracket is rebuilt with the actual
fill price.

State machine (per ticker):
    IDLE → (T+15 min, unfilled) → WATCHING
    WATCHING → (price <= AVWAP) → DIPPED
    DIPPED → (price > AVWAP) → CONVERTING → DONE

Runs every minute via cron: */1 9-11 * * 1-5 (ET hours, DST-aware)
  CET crontab: */1 15-17 * * 1-5 (CET) or */1 14-16 * * 1-5 (CEST)

clientId: 16 (unique, no collision with submit=10, close=11, eod=12, nuke=13, monitor=15)

Usage:
    python scripts/paper_trading/pt_avwap.py
    python scripts/paper_trading/pt_avwap.py --dry-run    # No IBKR, state transitions only
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pt_avwap")

STATE_DIR = "scripts/paper_trading/logs"
ET = ZoneInfo("America/New_York")

# AVWAP window: market open + 15 min → market open + 2h
AVWAP_DELAY_MINUTES = 15
AVWAP_CUTOFF_HOURS = 2


def send_telegram(message: str) -> None:
    import requests

    token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def load_state(today_str: str) -> dict:
    path = f"{STATE_DIR}/monitor_state_{today_str}.json"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_state(today_str: str, state: dict) -> None:
    path = f"{STATE_DIR}/monitor_state_{today_str}.json"
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def calculate_avwap(ticker: str, market_open_utc: datetime) -> float | None:
    """Calculate Anchored VWAP from Polygon 1-minute bars since market open.

    AVWAP = sum(TP_i * Volume_i) / sum(Volume_i)
    where TP_i = (High_i + Low_i + Close_i) / 3
    """
    from ifds.data.polygon import PolygonClient

    client = PolygonClient(api_key=os.getenv("IFDS_POLYGON_API_KEY"))
    today_str = date.today().strftime("%Y-%m-%d")

    bars = client.get_aggregates(
        ticker, today_str, today_str, timespan="minute", multiplier=1
    )
    if not bars:
        logger.warning(f"{ticker}: No 1-min bars from Polygon")
        return None

    # Filter bars from market open onwards
    open_ts_ms = int(market_open_utc.timestamp() * 1000)
    filtered = [b for b in bars if b.get("t", 0) >= open_ts_ms]

    if not filtered:
        logger.warning(f"{ticker}: No bars since market open")
        return None

    cum_tp_vol = 0.0
    cum_vol = 0.0
    for bar in filtered:
        tp = (bar["h"] + bar["l"] + bar["c"]) / 3
        vol = bar.get("v", 0)
        if vol > 0:
            cum_tp_vol += tp * vol
            cum_vol += vol

    if cum_vol == 0:
        return None

    return cum_tp_vol / cum_vol


def get_last_price(ib, sym: str) -> float | None:
    """Get last traded price via snapshot market data."""
    from ib_insync import Stock

    contract = Stock(sym, "SMART", "USD")
    details = ib.reqContractDetails(contract)
    if not details:
        return None
    ticker = ib.reqMktData(details[0].contract, "", True, False)
    ib.sleep(2)
    price = ticker.last or ticker.close
    ib.cancelMktData(details[0].contract)
    return price if price and price > 0 else None


def is_position_open(ib, sym: str) -> bool:
    """Check if there's an existing IBKR position for this ticker."""
    for pos in ib.positions():
        if pos.contract.symbol == sym and pos.position != 0:
            return True
    return False


def cancel_order_by_ref(ib, order_ref: str) -> bool:
    """Cancel an open order by orderRef. Returns True if found."""
    for order in ib.openOrders():
        if getattr(order, "orderRef", "") == order_ref:
            ib.cancelOrder(order)
            ib.sleep(0.5)
            logger.info(f"Cancelled order: {order_ref} (id={order.orderId})")
            return True
    return False


def cancel_ticker_orders(ib, sym: str) -> int:
    """Cancel all IFDS orders for a ticker. Returns count cancelled."""
    cancelled = 0
    for order in ib.openOrders():
        ref = getattr(order, "orderRef", "")
        if ref.startswith(f"IFDS_{sym}"):
            ib.cancelOrder(order)
            ib.sleep(0.5)
            logger.info(f"Cancelled: {ref} (id={order.orderId})")
            cancelled += 1
    return cancelled


def wait_for_fill(ib, trade, timeout: int = 30) -> float | None:
    """Wait for a trade to fill. Returns fill price or None on timeout."""
    for _ in range(timeout):
        ib.sleep(1)
        if trade.orderStatus.status == "Filled":
            return trade.orderStatus.avgFillPrice
    return None


def get_vix_adaptive_sl_distance(fill_price: float, original_sl_distance: float,
                                  vix: float | None, atr: float | None = None) -> tuple[float, str]:
    """Calculate VIX-adaptive SL distance.

    Args:
        fill_price: Actual fill price of the MKT order.
        original_sl_distance: Original SL distance (1.5 × ATR).
        vix: Current VIX value, or None if unavailable.
        atr: ATR value for VIX > 30 ATR reduction, optional.

    Returns:
        (capped_distance, cap_label) — the applied distance and a human-readable label.
    """
    if vix is None or vix < 20:
        return original_sl_distance, "no_cap"

    sl_distance = original_sl_distance

    if vix < 25:
        max_pct = 0.020   # 2.0%
        cap_label = f"VIX={vix:.1f}→2.0%_cap"
    elif vix < 30:
        max_pct = 0.015   # 1.5%
        cap_label = f"VIX={vix:.1f}→1.5%_cap"
    else:
        max_pct = 0.010   # 1.0%
        cap_label = f"VIX={vix:.1f}→1.0%_cap"
        if atr is not None:
            sl_distance = min(sl_distance, 1.0 * atr)

    pct_cap = fill_price * max_pct
    capped = min(sl_distance, pct_cap)
    return capped, cap_label


def _fetch_vix_for_avwap() -> float | None:
    """Fetch current VIX from FRED (VIXCLS). Returns None on error."""
    try:
        from ifds.data.fred import FREDClient
        fred = FREDClient(api_key=os.getenv("IFDS_FRED_API_KEY", ""))
        observations = fred.get_vix(limit=5)
        fred.close()
        if not observations:
            return None
        for obs in observations:
            val = obs.get("value")
            if val and val != ".":
                return float(val)
    except Exception as e:
        logger.warning(f"VIX fetch failed: {e}")
    return None


def convert_to_market(ib, sym: str, s: dict) -> bool:
    """Cancel limit orders, place MKT, rebuild bracket with fill price.

    Returns True on success.
    """
    from ib_insync import MarketOrder, Stock
    from lib.connection import get_account
    from lib.orders import create_day_bracket, submit_bracket

    # Cancel all existing orders for this ticker
    cancelled = cancel_ticker_orders(ib, sym)
    logger.info(f"{sym}: Cancelled {cancelled} existing orders")
    ib.sleep(1)

    # Place MKT order
    contract = Stock(sym, "SMART", "USD")
    ib.qualifyContracts(contract)
    account = get_account(ib)

    mkt_order = MarketOrder("BUY", s["total_qty"])
    mkt_order.tif = "DAY"
    mkt_order.orderRef = f"IFDS_{sym}_AVWAP"
    mkt_order.account = account
    trade = ib.placeOrder(contract, mkt_order)

    fill_price = wait_for_fill(ib, trade, timeout=30)
    if fill_price is None:
        logger.warning(f"{sym}: MKT fill timeout — skip bracket rebuild")
        return False

    # Fetch VIX for adaptive SL cap
    vix = _fetch_vix_for_avwap()
    atr = s.get("atr")

    # Bracket rebuild with VIX-adaptive SL
    original_sl_distance = s["sl_distance"]
    tp1_distance = s["tp1_price"] - s["entry_price"]
    tp2_distance = s["tp2_price"] - s["entry_price"]

    capped_sl_distance, cap_label = get_vix_adaptive_sl_distance(
        fill_price, original_sl_distance, vix, atr
    )

    new_sl = round(fill_price - capped_sl_distance, 2)
    new_tp1 = round(fill_price + tp1_distance, 2)
    new_tp2 = round(fill_price + tp2_distance, 2)

    qty_tp1 = s["total_qty"] - s["qty_b"]
    qty_tp2 = s["qty_b"]

    contract_qual = Stock(sym, "SMART", "USD")
    ib.qualifyContracts(contract_qual)

    bracket_a = create_day_bracket(
        ib, contract_qual, "BUY", qty_tp1,
        fill_price, new_tp1, new_sl, account,
        tag_suffix=f"{sym}_AVWAP_A",
    )
    submit_bracket(ib, contract_qual, bracket_a)

    bracket_b = create_day_bracket(
        ib, contract_qual, "BUY", qty_tp2,
        fill_price, new_tp2, new_sl, account,
        tag_suffix=f"{sym}_AVWAP_B",
    )
    submit_bracket(ib, contract_qual, bracket_b)

    # Update monitor state — capped sl_distance for consistent trail behavior
    s["entry_price"] = fill_price
    s["tp1_price"] = new_tp1
    s["tp2_price"] = new_tp2
    s["stop_loss"] = new_sl
    s["sl_distance"] = capped_sl_distance
    s["vix_at_avwap"] = vix

    vix_info = f"VIX: {vix:.1f} | SL cap: {cap_label}" if vix is not None else "VIX: N/A"
    msg = (
        f"AVWAP {sym}: Limit->MKT conversion\n"
        f"Fill @ ${fill_price:.2f}\n"
        f"{vix_info}\n"
        f"New SL: ${new_sl:.2f} (distance: ${capped_sl_distance:.2f}) | "
        f"TP1: ${new_tp1:.2f} | TP2: ${new_tp2:.2f}\n"
        f"AVWAP: ${s.get('avwap_last', 0):.2f}"
    )
    logger.info(msg)
    send_telegram(msg)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="AVWAP Limit->MKT monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="No IBKR connection, log state transitions only")
    args = parser.parse_args()

    # Time window check (ET-aware)
    now_et = datetime.now(ET)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    avwap_start = market_open + timedelta(minutes=AVWAP_DELAY_MINUTES)
    avwap_cutoff = market_open + timedelta(hours=AVWAP_CUTOFF_HOURS)

    if not (avwap_start <= now_et <= avwap_cutoff):
        logger.info(
            f"Outside AVWAP window ({avwap_start.strftime('%H:%M')}-"
            f"{avwap_cutoff.strftime('%H:%M')} ET). Exiting."
        )
        return

    today_str = date.today().strftime("%Y-%m-%d")
    state = load_state(today_str)
    if not state:
        logger.info("No monitor state — nothing to watch.")
        return

    # Filter: only tickers not yet AVWAP-converted, not already filled
    watching = [
        sym for sym, s in state.items()
        if not s.get("avwap_converted", False)
        and not s.get("tp1_filled", False)
        and s.get("avwap_state", "IDLE") in ("IDLE", "WATCHING", "DIPPED")
    ]

    if not watching:
        logger.info("No tickers need AVWAP monitoring.")
        return

    logger.info(f"AVWAP candidates: {watching}")

    # Market open in UTC for Polygon bar filtering
    market_open_utc = market_open.astimezone(ZoneInfo("UTC"))

    if args.dry_run:
        logger.info("[DRY RUN] — No IBKR connection")
        for sym in watching:
            s = state[sym]
            avwap = calculate_avwap(sym, market_open_utc)
            if avwap is None:
                continue
            s["avwap_last"] = round(avwap, 4)
            logger.info(f"  {sym}: AVWAP=${avwap:.4f}, state={s.get('avwap_state', 'IDLE')}")
            # Can't check IBKR price in dry run
            if s.get("avwap_state", "IDLE") == "IDLE":
                s["avwap_state"] = "WATCHING"
        save_state(today_str, state)
        return

    # Live mode
    from lib.connection import connect, disconnect

    ib = connect(client_id=16)
    ib.sleep(2)

    state_changed = False

    for sym in watching:
        s = state[sym]

        # IDLE → WATCHING: check if position already exists (limit filled normally)
        if s.get("avwap_state", "IDLE") == "IDLE":
            if is_position_open(ib, sym):
                logger.info(f"{sym}: Position already open — skip AVWAP")
                s["avwap_converted"] = True
                state_changed = True
                continue
            s["avwap_state"] = "WATCHING"
            state_changed = True

        # Calculate AVWAP from Polygon 1-min bars
        avwap = calculate_avwap(sym, market_open_utc)
        if avwap is None:
            continue

        s["avwap_last"] = round(avwap, 4)
        current_price = get_last_price(ib, sym)
        if current_price is None:
            logger.warning(f"{sym}: Cannot get price")
            continue

        logger.info(
            f"{sym}: price=${current_price:.2f} AVWAP=${avwap:.4f} "
            f"state={s['avwap_state']}"
        )

        # WATCHING → DIPPED
        if s["avwap_state"] == "WATCHING" and current_price <= avwap:
            s["avwap_state"] = "DIPPED"
            s["avwap_dipped"] = True
            state_changed = True
            logger.info(f"{sym}: Price dipped below AVWAP — state=DIPPED")

        # DIPPED → CONVERTING: price crossed back above AVWAP
        if s["avwap_state"] == "DIPPED" and current_price > avwap:
            logger.info(f"{sym}: Price crossed above AVWAP — converting to MKT")
            success = convert_to_market(ib, sym, s)
            if success:
                s["avwap_state"] = "DONE"
                s["avwap_converted"] = True
            else:
                s["avwap_state"] = "FAILED"
            state_changed = True

    if state_changed:
        save_state(today_str, state)

    disconnect(ib)


if __name__ == "__main__":
    main()
