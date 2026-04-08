"""IBKR Paper Trading — Order Creation"""
import logging

from ib_insync import Stock, LimitOrder, StopOrder, MarketOrder, TagValue

logger = logging.getLogger("submit")

# IBKR order status values that indicate a successful placement.
# Any other status (especially "Cancelled", "Inactive", "ApiCancelled") means
# the order was silently rejected by IBKR.
_VALID_ORDER_STATUSES = frozenset({
    "PreSubmitted",
    "Submitted",
    "Filled",
    "PendingSubmit",
    "PendingCancel",
})


def validate_contract(ib, symbol):
    """Validate stock exists in IBKR. Returns contract or None."""
    contract = Stock(symbol, 'SMART', 'USD')
    details = ib.reqContractDetails(contract)
    if not details:
        return None
    return details[0].contract


def create_day_bracket(ib, contract, action, qty, limit_price, tp_price,
                       sl_price, account, tag_suffix=""):
    """Create a single bracket order: Entry + TP + SL, all DAY TIF.

    Returns (entry, tp, sl) order tuple.
    """
    entry_id = ib.client.getReqId()
    tp_id = ib.client.getReqId()
    sl_id = ib.client.getReqId()

    exit_action = 'SELL' if action == 'BUY' else 'BUY'

    entry = LimitOrder(
        action=action,
        totalQuantity=qty,
        lmtPrice=round(limit_price, 2),
        orderId=entry_id,
        account=account,
        tif='DAY',
        outsideRth=False,
        orderRef=f"IFDS_{tag_suffix}",
        transmit=False,
        algoStrategy='Adaptive',
        algoParams=[TagValue('adaptivePriority', 'Normal')],
    )

    tp = LimitOrder(
        action=exit_action,
        totalQuantity=qty,
        lmtPrice=round(tp_price, 2),
        orderId=tp_id,
        account=account,
        tif='DAY',
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
        tif='DAY',
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
            logger.debug(
                f"{sym}: order OK — orderRef={order_ref} status={status}"
            )

    return trades


def create_moc_order(qty, account, action='SELL'):
    """Create Market-on-Close order."""
    order = MarketOrder(action, qty)
    order.tif = 'DAY'
    order.orderType = 'MOC'
    order.account = account
    return order
