"""IBKR Paper Trading — Order Creation"""

import asyncio
import logging

# Python 3.14+: event loop must exist before importing ib_insync.
# Mirrors lib/connection.py — this module imports ib_insync at module level,
# so the guard must run here too in case orders is imported before connection.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import LimitOrder, MarketOrder, Stock, StopOrder

logger = logging.getLogger("submit")

# IBKR order status values that indicate a successful placement.
# Any other status (especially "Cancelled", "Inactive", "ApiCancelled") means
# the order was silently rejected by IBKR.
_VALID_ORDER_STATUSES = frozenset(
    {
        "PreSubmitted",
        "Submitted",
        "Filled",
        "PendingSubmit",
        "PendingCancel",
    }
)


def validate_contract(ib, symbol):
    """Validate stock exists in IBKR. Returns contract or None."""
    contract = Stock(symbol, "SMART", "USD")
    details = ib.reqContractDetails(contract)
    if not details:
        return None
    return details[0].contract


def create_day_bracket(
    ib, contract, action, qty, limit_price, tp_price, sl_price, account, tag_suffix=""
):
    """Create a single bracket order: MKT entry + LMT TP + STP SL, all DAY TIF.

    Per BC20A_3 scope: entry is a MarketOrder (immediate fill at open),
    not a LimitOrder. The ``limit_price`` argument is kept for backwards
    compatibility with callers and is used only as a reference price for
    bracket construction — it is NOT applied to the MKT entry order.

    The previous implementation used ``LimitOrder`` with ``algoStrategy='Adaptive'``,
    which IBKR paper accounts silently rejected, resulting in submit_orders.py
    logging "Submitted: N tickers" while the IBKR Orders tab remained empty.

    Returns (entry, tp, sl) order tuple.
    """
    entry_id = ib.client.getReqId()
    tp_id = ib.client.getReqId()
    sl_id = ib.client.getReqId()

    exit_action = "SELL" if action == "BUY" else "BUY"

    entry = MarketOrder(
        action=action,
        totalQuantity=qty,
        orderId=entry_id,
        account=account,
        tif="DAY",
        outsideRth=False,
        orderRef=f"IFDS_{tag_suffix}",
        transmit=False,
    )

    tp = LimitOrder(
        action=exit_action,
        totalQuantity=qty,
        lmtPrice=round(tp_price, 2),
        orderId=tp_id,
        account=account,
        tif="DAY",
        parentId=entry_id,
        orderRef=f"IFDS_{tag_suffix}_TP",
        transmit=False,
    )

    sl = StopOrder(
        action=exit_action,
        totalQuantity=qty,
        stopPrice=round(sl_price, 2),
        orderId=sl_id,
        account=account,
        tif="DAY",
        parentId=entry_id,
        orderRef=f"IFDS_{tag_suffix}_SL",
        transmit=True,  # Last child transmits all
    )

    return entry, tp, sl


def submit_bracket(ib, contract, orders, dry_run=False):
    """Submit bracket order tuple to IBKR and verify status.

    Places each order via ``ib.placeOrder()`` and then waits briefly so
    IBKR can process the event loop and return an initial status. If any
    order's ``trade.orderStatus.status`` is not in ``_VALID_ORDER_STATUSES``
    (i.e. it was rejected, cancelled, or stuck in an error state), a
    WARNING is logged with the full details.

    This prevents the silent-failure case where ``submit_orders.py`` logs
    "Submitted: 8 tickers" but the IBKR Orders tab is empty because every
    order was rejected.
    """
    if dry_run:
        return []

    trades = []
    sym = contract.symbol
    for order in orders:
        trade = ib.placeOrder(contract, order)
        trades.append(trade)

    # Let IBKR process placements and return initial statuses.
    # ib.sleep() pumps the event loop — time.sleep() would block it.
    ib.sleep(1.5)

    for trade in trades:
        order_ref = getattr(trade.order, "orderRef", "") or "<no-ref>"
        status = getattr(trade.orderStatus, "status", "") or "<unknown>"
        if status not in _VALID_ORDER_STATUSES:
            # Silent IBKR rejection — log full details including log entries
            log_entries = [
                f"{le.time.strftime('%H:%M:%S')} {le.status} {le.message}"
                for le in getattr(trade, "log", [])
            ] or ["<no log entries>"]
            logger.warning(
                f"{sym}: order REJECTED or unexpected status — "
                f"orderRef={order_ref} status={status!r} "
                f"log={log_entries}"
            )
        else:
            logger.debug(f"{sym}: order OK — orderRef={order_ref} status={status}")

    return trades


def create_moc_order(qty, account, action="SELL"):
    """Create Market-on-Close order."""
    order = MarketOrder(action, qty)
    order.tif = "DAY"
    order.orderType = "MOC"
    order.account = account
    return order

#: How the entry was routed, for the event log and the daily report.
ROUTE_MOO = "MOO"
ROUTE_MKT_FALLBACK = "MKT_OPEN_FALLBACK"


def create_swing_entry_order(qty, account, ticker, now=None, logger=None):
    """Build the swing entry, preferring the OPENING AUCTION.

    Measured on the swing era (``docs/review/2026-10-19-execution-wall-by-horizon.md``):
    a market order sent after the bell gives up **+60.4 bp**, while an auction
    order gives up **+1.35 bp** — 45x. The entry decision comes from the previous
    close, so routing it into the opening auction executes the SAME decision
    earlier and better; no information is lost and the holding period is unchanged.

    Falls back to today's plain ``MKT``/``DAY`` entry when the opening auction is
    no longer reachable, which is a real risk rather than a theoretical one: the
    US and EU daylight-saving switches are a week apart, and inside that week a
    Budapest cron slot lands an hour later in ET (see ``scripts/crontab.md``
    "DST ÁTMENET FIGYELMEZTETÉS"). Degrading to the status quo is always safe;
    submitting an OPG order after 09:28 ET is not — IBKR rejects it or defers it
    to the next session.

    Returns ``(order, route)`` where ``route`` is :data:`ROUTE_MOO` or
    :data:`ROUTE_MKT_FALLBACK`.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from ifds.utils.calendar import is_before_moo_cutoff

    order = MarketOrder(action="BUY", totalQuantity=qty)
    order.account = account
    order.orderRef = f"IFDS_SWING_{ticker}"

    if is_before_moo_cutoff(now):
        # Market-on-Open is MKT + TIF=OPG (IBKR has no distinct "MOO" type for
        # stocks). outsideRth must stay False: an opening-auction order is RTH by
        # definition, and setting it True has IBKR reject the OPG combination.
        order.tif = "OPG"
        order.outsideRth = False
        return order, ROUTE_MOO

    # --- fallback: today's behaviour, unchanged ---
    # Explicit tif='DAY' short-circuits the IBKR paper-account preset lookup
    # (Order Presets -> Stocks -> Default TIF), which otherwise triggers
    # "Error 10349, Order TIF was set to DAY based on order preset" + a hard
    # Cancel on the swing market-only path. tif='GTC' was tried first (Day 3)
    # and silently failed — GTC is only valid for limit orders.
    order.tif = "DAY"
    order.outsideRth = True
    if logger is not None:
        logger.warning(
            f"{ticker}: the opening auction is no longer reachable (09:28 ET cutoff) — "
            f"falling back to a plain market entry, which the swing-era measurement "
            f"prices at +60.4 bp instead of +1.35 bp. Check the crontab slot against "
            f"the US/EU DST offset."
        )
    return order, ROUTE_MKT_FALLBACK
