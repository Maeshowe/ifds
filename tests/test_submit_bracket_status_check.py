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
