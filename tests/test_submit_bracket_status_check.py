"""Regression tests for submit_bracket order status verification.

The bug: submit_orders.py logged "Submitted: 8 tickers" but IBKR Orders
tab was empty. Root cause: submit_bracket called ib.placeOrder() but
never checked trade.orderStatus.status, so IBKR silent rejections went
undetected.

The fix: submit_bracket now calls ib.sleep() after placement and then
inspects trade.orderStatus.status for each order. Any status not in
_VALID_ORDER_STATUSES triggers a logger.warning with full details.
"""
from unittest.mock import MagicMock

import pytest


class FakeOrder:
    def __init__(self, order_ref: str = ""):
        self.orderRef = order_ref


class FakeOrderStatus:
    def __init__(self, status: str):
        self.status = status


class FakeLogEntry:
    def __init__(self, time, status: str, message: str):
        self.time = time
        self.status = status
        self.message = message


class FakeTrade:
    def __init__(self, status: str, order_ref: str = "", log_entries=None):
        self.order = FakeOrder(order_ref)
        self.orderStatus = FakeOrderStatus(status)
        self.log = log_entries or []


@pytest.fixture
def fake_ib():
    """Minimal IB mock that returns a fake trade per placeOrder call."""
    ib = MagicMock()
    ib.sleep = MagicMock()  # does nothing — we don't wait in tests
    return ib


@pytest.fixture
def fake_contract():
    c = MagicMock()
    c.symbol = "AAPL"
    return c


class TestSubmitBracketStatusCheck:
    """Verify submit_bracket logs warnings on silent IBKR rejections."""

    def test_all_submitted_no_warning(self, fake_ib, fake_contract, caplog):
        from scripts.paper_trading.lib.orders import submit_bracket

        fake_ib.placeOrder.side_effect = [
            FakeTrade("Submitted", "IFDS_AAPL_A"),
            FakeTrade("PreSubmitted", "IFDS_AAPL_A_TP"),
            FakeTrade("Submitted", "IFDS_AAPL_A_SL"),
        ]
        orders = [MagicMock(), MagicMock(), MagicMock()]

        with caplog.at_level("WARNING", logger="submit"):
            trades = submit_bracket(fake_ib, fake_contract, orders)

        assert len(trades) == 3
        assert fake_ib.placeOrder.call_count == 3
        fake_ib.sleep.assert_called_once_with(1.5)
        # No warnings should be logged
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings == []

    def test_rejected_order_logs_warning(self, fake_ib, fake_contract, caplog):
        """The actual bug: IBKR silently rejects an order → we must warn."""
        from scripts.paper_trading.lib.orders import submit_bracket

        fake_ib.placeOrder.side_effect = [
            FakeTrade("Submitted", "IFDS_AAPL_A"),
            FakeTrade(
                "Cancelled",
                "IFDS_AAPL_A_TP",
                log_entries=[
                    FakeLogEntry(
                        MagicMock(strftime=lambda _: "15:45:12"),
                        "Cancelled",
                        "The price does not conform to the minimum price variation.",
                    )
                ],
            ),
            FakeTrade("Submitted", "IFDS_AAPL_A_SL"),
        ]
        orders = [MagicMock(), MagicMock(), MagicMock()]

        with caplog.at_level("WARNING", logger="submit"):
            submit_bracket(fake_ib, fake_contract, orders)

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        msg = warnings[0].getMessage()
        assert "AAPL" in msg
        assert "REJECTED" in msg
        assert "IFDS_AAPL_A_TP" in msg
        assert "Cancelled" in msg
        assert "minimum price variation" in msg

    def test_inactive_status_logs_warning(self, fake_ib, fake_contract, caplog):
        from scripts.paper_trading.lib.orders import submit_bracket

        fake_ib.placeOrder.side_effect = [FakeTrade("Inactive", "IFDS_AAPL_A")]
        orders = [MagicMock()]

        with caplog.at_level("WARNING", logger="submit"):
            submit_bracket(fake_ib, fake_contract, orders)

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "Inactive" in warnings[0].getMessage()

    def test_all_valid_statuses_no_warning(self, fake_ib, fake_contract, caplog):
        """Every valid status should be accepted without a warning."""
        from scripts.paper_trading.lib.orders import (
            _VALID_ORDER_STATUSES,
            submit_bracket,
        )

        for valid in _VALID_ORDER_STATUSES:
            fake_ib.placeOrder.side_effect = [FakeTrade(valid, f"IFDS_T_{valid}")]
            caplog.clear()
            with caplog.at_level("WARNING", logger="submit"):
                submit_bracket(fake_ib, fake_contract, [MagicMock()])
            warnings = [r for r in caplog.records if r.levelname == "WARNING"]
            assert warnings == [], f"valid status {valid!r} should not warn"

    def test_dry_run_skips_placement(self, fake_ib, fake_contract):
        from scripts.paper_trading.lib.orders import submit_bracket

        trades = submit_bracket(
            fake_ib, fake_contract, [MagicMock(), MagicMock()], dry_run=True
        )
        assert trades == []
        fake_ib.placeOrder.assert_not_called()
        fake_ib.sleep.assert_not_called()


class TestCreateDayBracketEntryType:
    """Regression tests for BC20A_3 MKT entry requirement.

    The previous implementation used LimitOrder with Adaptive algo, which
    IBKR paper accounts silently rejected. Entry must now be MarketOrder
    with no algoStrategy / algoParams.
    """

    def _make_ib(self):
        ib = MagicMock()
        # getReqId returns monotonically increasing IDs
        counter = {"n": 1000}

        def next_id():
            counter["n"] += 1
            return counter["n"]

        ib.client.getReqId.side_effect = next_id
        return ib

    def test_entry_is_market_order(self):
        from ib_insync import MarketOrder

        from scripts.paper_trading.lib.orders import create_day_bracket

        ib = self._make_ib()
        contract = MagicMock(symbol="AAPL")
        entry, tp, sl = create_day_bracket(
            ib, contract, action="BUY", qty=100,
            limit_price=150.25, tp_price=155.00, sl_price=145.00,
            account="DUH118657", tag_suffix="AAPL_A",
        )
        assert isinstance(entry, MarketOrder)
        assert entry.action == "BUY"
        assert entry.totalQuantity == 100
        assert entry.tif == "DAY"
        assert entry.orderRef == "IFDS_AAPL_A"
        assert entry.transmit is False

    def test_entry_has_no_adaptive_algo(self):
        """BC20A_3 requires no algoStrategy — paper account rejects Adaptive."""
        from scripts.paper_trading.lib.orders import create_day_bracket

        ib = self._make_ib()
        contract = MagicMock(symbol="AAPL")
        entry, _, _ = create_day_bracket(
            ib, contract, action="BUY", qty=100,
            limit_price=150.25, tp_price=155.00, sl_price=145.00,
            account="DUH118657", tag_suffix="AAPL_A",
        )
        # ib_insync Order defaults algoStrategy to empty string, not None
        assert not getattr(entry, "algoStrategy", ""), (
            "Entry order must not use an IBKR algoStrategy "
            "(paper accounts silently reject Adaptive)"
        )
        assert not getattr(entry, "algoParams", None), (
            "Entry order must not carry algoParams"
        )

    def test_entry_has_no_lmt_price(self):
        """MarketOrder must leave lmtPrice at IBKR's UNSET sentinel."""
        import sys

        from scripts.paper_trading.lib.orders import create_day_bracket

        ib = self._make_ib()
        contract = MagicMock(symbol="AAPL")
        entry, _, _ = create_day_bracket(
            ib, contract, action="BUY", qty=100,
            limit_price=150.25, tp_price=155.00, sl_price=145.00,
            account="DUH118657", tag_suffix="AAPL_A",
        )
        # ib_insync uses sys.float_info.max as the "unset" sentinel
        # for numeric Order fields. A real lmtPrice would be much smaller.
        lmt = getattr(entry, "lmtPrice", 0)
        assert lmt == sys.float_info.max or lmt == 0, (
            f"MarketOrder should leave lmtPrice unset, got {lmt}"
        )

    def test_bracket_children_unchanged(self):
        """TP must be LimitOrder, SL must be StopOrder, both DAY TIF."""
        from ib_insync import LimitOrder, StopOrder

        from scripts.paper_trading.lib.orders import create_day_bracket

        ib = self._make_ib()
        contract = MagicMock(symbol="AAPL")
        entry, tp, sl = create_day_bracket(
            ib, contract, action="BUY", qty=100,
            limit_price=150.25, tp_price=155.00, sl_price=145.00,
            account="DUH118657", tag_suffix="AAPL_A",
        )
        assert isinstance(tp, LimitOrder)
        assert tp.action == "SELL"
        assert tp.lmtPrice == 155.00
        assert tp.parentId == entry.orderId
        assert tp.transmit is False

        assert isinstance(sl, StopOrder)
        assert sl.action == "SELL"
        assert sl.auxPrice == 145.00
        assert sl.parentId == entry.orderId
        assert sl.transmit is True  # Last child transmits all

    def test_sell_action_flips_exits_to_buy(self):
        from scripts.paper_trading.lib.orders import create_day_bracket

        ib = self._make_ib()
        contract = MagicMock(symbol="AAPL")
        entry, tp, sl = create_day_bracket(
            ib, contract, action="SELL", qty=50,
            limit_price=150.00, tp_price=145.00, sl_price=155.00,
            account="DUH118657", tag_suffix="AAPL_A",
        )
        assert entry.action == "SELL"
        assert tp.action == "BUY"
        assert sl.action == "BUY"
