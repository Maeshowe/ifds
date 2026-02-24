"""Tests for earnings date column in Telegram execution table.

Covers:
- FMPClient.get_next_earnings_date()
- _format_exec_table() with earnings_map
- _format_phases_5_to_6() earnings lookup integration
- send_daily_report() fmp parameter passthrough
- Phase 2 earnings breakdown in Telegram (bulk vs ticker-specific)
"""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from ifds.output.telegram import (
    _format_exec_table, _format_phases_0_to_4, _format_phases_5_to_6,
)


# ---------------------------------------------------------------------------
# Minimal PositionSizing stub for table tests
# ---------------------------------------------------------------------------
@dataclass
class _Pos:
    ticker: str = "AAPL"
    quantity: int = 10
    entry_price: float = 150.0
    stop_loss: float = 145.0
    take_profit_1: float = 160.0
    take_profit_2: float = 170.0
    risk_usd: float = 50.0


# =========================================================================
# FMPClient.get_next_earnings_date
# =========================================================================
class TestGetNextEarningsDate:
    """Test FMPClient.get_next_earnings_date()."""

    def test_returns_earliest_upcoming(self):
        """Picks the earliest future date where epsActual is None."""
        from ifds.data.fmp import FMPClient

        client = FMPClient.__new__(FMPClient)
        client._api_key = "test"

        api_response = [
            {"date": "2026-01-15", "epsActual": 2.5},
            {"date": "2026-04-22", "epsActual": None},
            {"date": "2026-07-20", "epsActual": None},
        ]

        with patch.object(client, "_get", return_value=api_response), \
             patch("ifds.data.fmp.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2026-02-24"
            result = client.get_next_earnings_date("AAPL")

        assert result == "2026-04-22"

    def test_fallback_when_all_have_eps_actual(self):
        """Falls back to earliest date >= today even with epsActual set."""
        from ifds.data.fmp import FMPClient

        client = FMPClient.__new__(FMPClient)
        client._api_key = "test"

        api_response = [
            {"date": "2026-01-15", "epsActual": 2.5},
            {"date": "2026-04-22", "epsActual": 3.0},
        ]

        with patch.object(client, "_get", return_value=api_response), \
             patch("ifds.data.fmp.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2026-02-24"
            result = client.get_next_earnings_date("AAPL")

        assert result == "2026-04-22"

    def test_returns_none_when_no_future_dates(self):
        """Returns None when all dates are in the past."""
        from ifds.data.fmp import FMPClient

        client = FMPClient.__new__(FMPClient)
        client._api_key = "test"

        api_response = [
            {"date": "2025-10-22", "epsActual": 2.0},
            {"date": "2026-01-15", "epsActual": 2.5},
        ]

        with patch.object(client, "_get", return_value=api_response), \
             patch("ifds.data.fmp.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2026-02-24"
            result = client.get_next_earnings_date("AAPL")

        assert result is None

    def test_returns_none_on_empty_response(self):
        """Returns None when API returns empty list."""
        from ifds.data.fmp import FMPClient

        client = FMPClient.__new__(FMPClient)
        client._api_key = "test"

        with patch.object(client, "_get", return_value=[]):
            result = client.get_next_earnings_date("AAPL")

        assert result is None

    def test_returns_none_on_none_response(self):
        """Returns None when API returns None."""
        from ifds.data.fmp import FMPClient

        client = FMPClient.__new__(FMPClient)
        client._api_key = "test"

        with patch.object(client, "_get", return_value=None):
            result = client.get_next_earnings_date("AAPL")

        assert result is None


# =========================================================================
# _format_exec_table
# =========================================================================
class TestExecTableEarnings:
    """Test _format_exec_table with earnings_map."""

    def test_no_earnings_map_no_earn_column(self):
        """Default: no EARN column."""
        result = _format_exec_table([_Pos()])
        assert "EARN" not in result

    def test_earnings_map_shows_earn_column(self):
        """With earnings_map, EARN header and dates appear."""
        positions = [_Pos(ticker="GE"), _Pos(ticker="LMT")]
        earnings = {"GE": "2026-04-22", "LMT": "2026-04-25"}
        result = _format_exec_table(positions, earnings_map=earnings)
        assert "EARN" in result
        assert "04-22" in result
        assert "04-25" in result

    def test_earnings_map_none_value_shows_na(self):
        """Ticker with None earnings shows N/A."""
        positions = [_Pos(ticker="KEP")]
        earnings = {"KEP": None}
        result = _format_exec_table(positions, earnings_map=earnings)
        assert "N/A" in result

    def test_earnings_map_missing_ticker_shows_na(self):
        """Ticker not in earnings_map shows N/A."""
        positions = [_Pos(ticker="XYZ")]
        earnings = {}
        result = _format_exec_table(positions, earnings_map=earnings)
        assert "N/A" in result

    def test_backward_compat_none_earnings_map(self):
        """earnings_map=None produces same output as no arg."""
        positions = [_Pos()]
        result_default = _format_exec_table(positions)
        result_none = _format_exec_table(positions, earnings_map=None)
        assert result_default == result_none

    def test_pre_tags_present(self):
        """Output wrapped in <pre> tags."""
        result = _format_exec_table([_Pos()], earnings_map={"AAPL": "2026-04-22"})
        assert result.startswith("<pre>")
        assert result.endswith("</pre>")


# =========================================================================
# _format_phases_5_to_6 — earnings integration
# =========================================================================
class TestPhasesEarningsIntegration:
    """Test _format_phases_5_to_6 with fmp parameter."""

    def _make_ctx(self):
        """Minimal PipelineContext with phase6 positions."""
        from ifds.models.market import (
            PipelineContext, Phase5Result, Phase6Result, PositionSizing,
        )

        pos = PositionSizing(
            ticker="GE", sector="Industrials", direction="BUY",
            entry_price=343.22, quantity=27, stop_loss=328.35,
            take_profit_1=363.04, take_profit_2=372.95,
            risk_usd=404.0, combined_score=85.0,
            gex_regime="POSITIVE", multiplier_total=1.2,
        )
        ctx = PipelineContext(
            run_id="test", started_at=None,
            phase5=Phase5Result(analyzed=[], passed=[], negative_regime_count=0),
            phase6=Phase6Result(
                positions=[pos],
                total_risk_usd=404.0,
                total_exposure_usd=9267.0,
                excluded_sector_limit=0,
                excluded_position_limit=0,
                excluded_risk_limit=0,
                excluded_exposure_limit=0,
                freshness_applied_count=0,
            ),
        )
        return ctx

    def _make_config(self):
        """Minimal Config mock."""
        config = MagicMock()
        config.tuning = {"obsidian_enabled": False}
        return config

    def test_with_fmp_earn_column_appears(self):
        """When fmp provided, EARN column with date appears."""
        ctx = self._make_ctx()
        config = self._make_config()
        fmp = MagicMock()
        fmp.get_next_earnings_date.return_value = "2026-04-22"

        result = _format_phases_5_to_6(ctx, config, fmp=fmp)
        assert "EARN" in result
        assert "04-22" in result
        fmp.get_next_earnings_date.assert_called_once_with("GE")

    def test_without_fmp_no_earn_column(self):
        """When fmp=None, no EARN column."""
        ctx = self._make_ctx()
        config = self._make_config()

        result = _format_phases_5_to_6(ctx, config)
        assert "EARN" not in result

    def test_fmp_exception_shows_na(self):
        """If fmp.get_next_earnings_date raises, ticker gets N/A."""
        ctx = self._make_ctx()
        config = self._make_config()
        fmp = MagicMock()
        fmp.get_next_earnings_date.side_effect = Exception("API error")

        result = _format_phases_5_to_6(ctx, config, fmp=fmp)
        assert "EARN" in result
        assert "N/A" in result


# =========================================================================
# send_daily_report — fmp passthrough
# =========================================================================
class TestSendDailyReportFmpParam:
    """Test send_daily_report passes fmp through the format chain."""

    def test_fmp_none_backward_compat(self):
        """send_daily_report without fmp param still works."""
        from ifds.output.telegram import send_daily_report

        config = MagicMock()
        config.runtime = {}
        logger = MagicMock()

        # No telegram credentials → returns False (disabled)
        result = send_daily_report(MagicMock(), config, logger, 10.0)
        assert result is False

    def test_fmp_passed_through(self):
        """fmp parameter reaches _format_exec_table."""
        from ifds.output.telegram import send_daily_report
        from ifds.models.market import (
            PipelineContext, Phase5Result, Phase6Result, PositionSizing,
        )

        pos = PositionSizing(
            ticker="T", sector="Telecom", direction="BUY",
            entry_price=28.0, quantity=100, stop_loss=27.0,
            take_profit_1=29.0, take_profit_2=30.0,
            risk_usd=100.0, combined_score=80.0,
            gex_regime="POSITIVE", multiplier_total=1.0,
        )
        ctx = PipelineContext(
            run_id="test", started_at=None,
            phase5=Phase5Result(analyzed=[], passed=[], negative_regime_count=0),
            phase6=Phase6Result(
                positions=[pos],
                total_risk_usd=100.0,
                total_exposure_usd=2800.0,
                excluded_sector_limit=0,
                excluded_position_limit=0,
                excluded_risk_limit=0,
                excluded_exposure_limit=0,
                freshness_applied_count=0,
            ),
        )

        config = MagicMock()
        config.runtime = {
            "telegram_bot_token": "fake-token",
            "telegram_chat_id": "fake-chat",
            "telegram_timeout": 1,
        }
        config.tuning = {"obsidian_enabled": False}
        logger = MagicMock()

        fmp = MagicMock()
        fmp.get_next_earnings_date.return_value = "2026-04-23"

        with patch("ifds.output.telegram._send_message", return_value=True):
            result = send_daily_report(ctx, config, logger, 5.0, fmp=fmp)

        assert result is True
        fmp.get_next_earnings_date.assert_called_once_with("T")


# =========================================================================
# Telegram Phase 2 earnings breakdown
# =========================================================================
class TestPhase2EarningsBreakdown:
    """Test Telegram Phase 2 shows bulk/ticker-specific breakdown."""

    def _make_ctx(self, bulk=10, ticker_specific=2, total_excluded=12):
        from ifds.models.market import PipelineContext, Phase2Result, Ticker
        excluded = [f"T{i}" for i in range(total_excluded)]
        tickers = [Ticker(symbol="AAPL"), Ticker(symbol="NVDA")]
        phase2 = Phase2Result(
            tickers=tickers,
            total_screened=100,
            earnings_excluded=excluded,
            bulk_excluded_count=bulk,
            ticker_specific_excluded_count=ticker_specific,
        )
        ctx = PipelineContext(run_id="test", started_at=None, phase2=phase2)
        return ctx

    def _make_config(self):
        config = MagicMock()
        config.tuning = {}
        return config

    def test_breakdown_shown_when_ticker_specific_positive(self):
        """When ticker-specific > 0, breakdown shown in parentheses."""
        ctx = self._make_ctx(bulk=10, ticker_specific=2, total_excluded=12)
        config = self._make_config()
        result = _format_phases_0_to_4(ctx, 5.0, config)
        assert "Earnings excluded: 12 (bulk=10, ticker-specific=2)" in result

    def test_no_breakdown_when_ticker_specific_zero(self):
        """When ticker-specific == 0, no parentheses shown."""
        ctx = self._make_ctx(bulk=10, ticker_specific=0, total_excluded=10)
        config = self._make_config()
        result = _format_phases_0_to_4(ctx, 5.0, config)
        assert "Earnings excluded: 10" in result
        assert "bulk=" not in result
        assert "ticker-specific=" not in result

    def test_zero_excluded_no_breakdown(self):
        """When no exclusions at all, just shows 0."""
        ctx = self._make_ctx(bulk=0, ticker_specific=0, total_excluded=0)
        config = self._make_config()
        result = _format_phases_0_to_4(ctx, 5.0, config)
        assert "Earnings excluded: 0" in result
        assert "bulk=" not in result
