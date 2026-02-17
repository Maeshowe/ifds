"""IBKR Paper Trading — Order Creation"""
from ib_insync import Stock, LimitOrder, StopOrder, MarketOrder, TagValue


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
    """Submit bracket order tuple to IBKR."""
    if dry_run:
        return []
    trades = []
    for order in orders:
        trade = ib.placeOrder(contract, order)
        trades.append(trade)
    return trades


def create_moc_order(qty, account, action='SELL'):
    """Create Market-on-Close order."""
    order = MarketOrder(action, qty)
    order.tif = 'DAY'
    order.orderType = 'MOC'
    order.account = account
    return order
