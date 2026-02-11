"""BC13 Backlog Tests — Survivorship Bias, Telegram Alerts, Max Daily Trades,
Notional Limits.

25+ tests covering all 4 BC13 features.
"""

import json
import os
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, call

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    BMIData,
    BMIRegime,
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis,
    GEXRegime,
    MacroRegime,
    MarketVolatilityRegime,
    Phase1Result,
    Phase2Result,
    Phase4Result,
    Phase5Result,
    Phase6Result,
    PipelineContext,
    PositionSizing,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
    Ticker,
)
from ifds.phases.phase6_sizing import (
    _load_daily_counter,
    _save_daily_counter,
    _replace_quantity,
    run_phase6,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc13")


def _make_stock(ticker="AAPL", price=150.0, atr=3.0, combined=80.0,
                flow_score=10, funda_score=15):
    """Helper to create a StockAnalysis for testing."""
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=atr, trend_pass=True,
        ),
        flow=FlowAnalysis(rvol_score=flow_score),
        fundamental=FundamentalScoring(funda_score=funda_score),
        combined_score=combined,
    )


def _make_gex(ticker="AAPL", call_wall=160.0, put_wall=140.0):
    """Helper to create a GEXAnalysis."""
    return GEXAnalysis(
        ticker=ticker,
        net_gex=1000.0,
        call_wall=call_wall,
        put_wall=put_wall,
        zero_gamma=150.0,
        current_price=150.0,
        gex_regime=GEXRegime.POSITIVE,
        gex_multiplier=1.0,
        data_source="polygon_calculated",
    )


def _make_macro(vix=18.0):
    """Helper to create a MacroRegime."""
    return MacroRegime(
        vix_value=vix,
        vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0,
        tnx_value=4.0,
        tnx_sma20=3.9,
        tnx_rate_sensitive=False,
    )


def _make_position(ticker="AAPL", price=150.0, quantity=22, sector="Technology"):
    """Helper to create a PositionSizing."""
    return PositionSizing(
        ticker=ticker,
        sector=sector,
        direction="BUY",
        entry_price=price,
        quantity=quantity,
        stop_loss=145.0,
        take_profit_1=160.0,
        take_profit_2=165.0,
        risk_usd=500.0,
        combined_score=80.0,
        gex_regime="positive",
        multiplier_total=1.0,
    )


# ============================================================================
# Feature 1: Survivorship Bias Protection
# ============================================================================

class TestSurvivorshipBias:
    """Test universe snapshot saving and diff logging."""

    def test_snapshot_saved(self, tmp_path, config, logger):
        """Universe snapshot is saved as JSON."""
        from ifds.phases.phase2_universe import _save_universe_snapshot
        config.runtime["survivorship_snapshot_dir"] = str(tmp_path / "snaps")

        tickers = [
            Ticker(symbol="AAPL", company_name="Apple", sector="Technology",
                   market_cap=3_000_000_000_000, price=150.0, avg_volume=1_000_000),
            Ticker(symbol="MSFT", company_name="Microsoft", sector="Technology",
                   market_cap=2_800_000_000_000, price=380.0, avg_volume=800_000),
        ]
        _save_universe_snapshot(tickers, config, logger)

        today = date.today().isoformat()
        snap_path = tmp_path / "snaps" / f"{today}.json"
        assert snap_path.exists()

        with open(snap_path) as f:
            data = json.load(f)
        assert len(data) == 2
        symbols = {r["symbol"] for r in data}
        assert symbols == {"AAPL", "MSFT"}

    def test_diff_logs_removed(self, tmp_path, config, logger):
        """Removed tickers are logged with [SURVIVORSHIP] WARNING."""
        from ifds.phases.phase2_universe import _save_universe_snapshot
        snap_dir = tmp_path / "snaps"
        config.runtime["survivorship_snapshot_dir"] = str(snap_dir)

        # Create yesterday's snapshot with AAPL + TSLA
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        os.makedirs(snap_dir, exist_ok=True)
        prev_data = [
            {"symbol": "AAPL", "market_cap": 3e12, "sector": "Technology"},
            {"symbol": "TSLA", "market_cap": 800e9, "sector": "Consumer Cyclical"},
        ]
        with open(snap_dir / f"{yesterday}.json", "w") as f:
            json.dump(prev_data, f)

        # Today: only AAPL (TSLA removed)
        tickers = [
            Ticker(symbol="AAPL", company_name="Apple", sector="Technology",
                   market_cap=3_000_000_000_000, price=150.0, avg_volume=1_000_000),
        ]
        _save_universe_snapshot(tickers, config, logger)

        # Check that logger received the survivorship warning
        events = logger.events
        surv_events = [e for e in events if "[SURVIVORSHIP]" in e.get("message", "")]
        assert any("Removed" in e["message"] and "TSLA" in e["message"]
                    for e in surv_events)

    def test_diff_logs_added(self, tmp_path, config, logger):
        """Newly added tickers are logged with [SURVIVORSHIP] INFO."""
        from ifds.phases.phase2_universe import _save_universe_snapshot
        snap_dir = tmp_path / "snaps"
        config.runtime["survivorship_snapshot_dir"] = str(snap_dir)

        # Create yesterday's snapshot with AAPL only
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        os.makedirs(snap_dir, exist_ok=True)
        prev_data = [{"symbol": "AAPL", "market_cap": 3e12, "sector": "Technology"}]
        with open(snap_dir / f"{yesterday}.json", "w") as f:
            json.dump(prev_data, f)

        # Today: AAPL + NVDA (NVDA added)
        tickers = [
            Ticker(symbol="AAPL", company_name="Apple", sector="Technology",
                   market_cap=3_000_000_000_000, price=150.0, avg_volume=1_000_000),
            Ticker(symbol="NVDA", company_name="NVIDIA", sector="Technology",
                   market_cap=2_000_000_000_000, price=875.0, avg_volume=500_000),
        ]
        _save_universe_snapshot(tickers, config, logger)

        events = logger.events
        surv_events = [e for e in events if "[SURVIVORSHIP]" in e.get("message", "")]
        assert any("New" in e["message"] and "NVDA" in e["message"]
                    for e in surv_events)

    def test_unchanged_universe(self, tmp_path, config, logger):
        """Unchanged universe logs [SURVIVORSHIP] Universe unchanged."""
        from ifds.phases.phase2_universe import _save_universe_snapshot
        snap_dir = tmp_path / "snaps"
        config.runtime["survivorship_snapshot_dir"] = str(snap_dir)

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        os.makedirs(snap_dir, exist_ok=True)
        prev_data = [{"symbol": "AAPL", "market_cap": 3e12, "sector": "Technology"}]
        with open(snap_dir / f"{yesterday}.json", "w") as f:
            json.dump(prev_data, f)

        tickers = [
            Ticker(symbol="AAPL", company_name="Apple", sector="Technology",
                   market_cap=3_000_000_000_000, price=150.0, avg_volume=1_000_000),
        ]
        _save_universe_snapshot(tickers, config, logger)

        events = logger.events
        assert any("unchanged" in e.get("message", "").lower() for e in events)

    def test_pruning(self, tmp_path, config, logger):
        """Old snapshots beyond max are pruned."""
        from ifds.phases.phase2_universe import _save_universe_snapshot
        snap_dir = tmp_path / "snaps"
        config.runtime["survivorship_snapshot_dir"] = str(snap_dir)
        config.runtime["survivorship_max_snapshots"] = 3

        os.makedirs(snap_dir, exist_ok=True)

        # Create 5 old snapshot files
        for i in range(5):
            d = date.today() - timedelta(days=i + 1)
            with open(snap_dir / f"{d.isoformat()}.json", "w") as f:
                json.dump([{"symbol": "AAPL", "market_cap": 3e12, "sector": "Tech"}], f)

        tickers = [
            Ticker(symbol="AAPL", company_name="Apple", sector="Technology",
                   market_cap=3_000_000_000_000, price=150.0, avg_volume=1_000_000),
        ]
        _save_universe_snapshot(tickers, config, logger)

        # 6 total snapshots (5 old + today), max 3 → should prune to 3
        remaining = [fn for fn in os.listdir(snap_dir) if fn.endswith(".json")]
        assert len(remaining) == 3

    def test_no_previous_snapshot(self, tmp_path, config, logger):
        """First run with no previous snapshot: no diff logged."""
        from ifds.phases.phase2_universe import _save_universe_snapshot
        snap_dir = tmp_path / "snaps"
        config.runtime["survivorship_snapshot_dir"] = str(snap_dir)

        tickers = [
            Ticker(symbol="AAPL", company_name="Apple", sector="Technology",
                   market_cap=3_000_000_000_000, price=150.0, avg_volume=1_000_000),
        ]
        _save_universe_snapshot(tickers, config, logger)

        events = logger.events
        surv_events = [e for e in events if "[SURVIVORSHIP]" in e.get("message", "")]
        assert len(surv_events) == 0  # No diff — no previous snapshot


# ============================================================================
# Feature 2: Telegram Daily Report
# ============================================================================

def _make_ctx(positions=None):
    """Helper to build a minimal PipelineContext for telegram tests."""
    macro = MacroRegime(
        vix_value=18.5,
        vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0,
        tnx_value=4.2,
        tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )
    bmi = BMIData(
        bmi_value=45.0,
        bmi_regime=BMIRegime.GREEN,
        daily_ratio=48.0,
        buy_count=120,
        sell_count=130,
    )
    phase1 = Phase1Result(
        bmi=bmi,
        strategy_mode=StrategyMode.LONG,
        ticker_count_for_bmi=11000,
    )
    phase2 = Phase2Result(
        tickers=[Ticker(symbol="AAPL"), Ticker(symbol="MSFT")],
        total_screened=900,
        earnings_excluded=["GOOG", "AMZN"],
    )
    ctx = PipelineContext(
        run_id="test-run",
        macro=macro,
        bmi_value=45.0,
        bmi_regime=BMIRegime.GREEN,
        strategy_mode=StrategyMode.LONG,
        phase1=phase1,
        phase2=phase2,
    )
    if positions is not None:
        ctx.phase4 = Phase4Result(analyzed=[], passed=[])
        ctx.phase5 = Phase5Result(analyzed=[], passed=[])
        ctx.phase6 = Phase6Result(positions=positions)
    return ctx


class TestTelegramDailyReport:
    """Test unified Telegram daily report."""

    def test_disabled_no_token(self, config, logger):
        """Returns False when no token configured."""
        from ifds.output.telegram import send_daily_report
        config.runtime["telegram_bot_token"] = None
        config.runtime["telegram_chat_id"] = None

        ctx = _make_ctx(positions=[_make_position()])
        result = send_daily_report(ctx, config, logger, 12.3)
        assert result is False

    def test_disabled_no_chat_id(self, config, logger):
        """Returns False when token set but no chat_id."""
        from ifds.output.telegram import send_daily_report
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = None

        ctx = _make_ctx(positions=[_make_position()])
        result = send_daily_report(ctx, config, logger, 12.3)
        assert result is False

    def test_sends_with_zero_positions(self, config, logger):
        """Always sends even with 0 positions (health report)."""
        from ifds.output.telegram import send_daily_report
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = "456"

        ctx = _make_ctx(positions=[])
        with patch("ifds.output.telegram.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            result = send_daily_report(ctx, config, logger, 5.0)

        assert result is True
        text = mock_post.call_args[1]["json"]["text"]
        assert "No positions today" in text

    @patch("ifds.output.telegram.requests.post")
    def test_successful_send(self, mock_post, config, logger):
        """Sends unified message with all phases."""
        from ifds.output.telegram import send_daily_report
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = "456"

        mock_post.return_value = MagicMock()

        positions = [_make_position(), _make_position(ticker="MSFT", sector="Technology")]
        ctx = _make_ctx(positions=positions)
        result = send_daily_report(ctx, config, logger, 42.5)

        assert result is True
        # May send 1 or 2 messages depending on size
        assert mock_post.call_count >= 1
        first_call = mock_post.call_args_list[0]
        args, kwargs = first_call
        assert "api.telegram.org" in args[0]
        assert kwargs["json"]["chat_id"] == "456"
        assert kwargs["json"]["parse_mode"] == "HTML"
        text = kwargs["json"]["text"]
        assert "IFDS Daily Report" in text
        assert "42.5s" in text
        assert "[ 0/6 ]" in text
        assert "[ 1/6 ]" in text

    @patch("ifds.output.telegram.requests.post", side_effect=Exception("Network error"))
    def test_failure_returns_false(self, mock_post, config, logger):
        """Returns False on network failure."""
        from ifds.output.telegram import send_daily_report
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = "456"

        ctx = _make_ctx(positions=[_make_position()])
        result = send_daily_report(ctx, config, logger, 10.0)
        assert result is False

    def test_format_success_content(self, config):
        """Format includes all phase headers and HTML tags."""
        from ifds.output.telegram import _format_success
        positions = [_make_position(), _make_position(ticker="MSFT", sector="Technology")]
        ctx = _make_ctx(positions=positions)
        part1, part2 = _format_success(ctx, 33.7, config)

        # Part 1 has Phase 0-4
        assert "IFDS Daily Report" in part1
        assert "33.7s" in part1
        assert "GREEN" in part1
        assert "LONG" in part1
        assert "[ 0/6 ]" in part1
        assert "[ 1/6 ]" in part1
        assert "[ 2/6 ]" in part1
        assert "VIX=18.50" in part1
        assert "Screened: 900" in part1
        assert "Passed: 2" in part1

        # Exec table in part2 or combined
        full = part1 + part2
        assert "[ 5/6 ]" in full
        assert "[ 6/6 ]" in full
        assert "AAPL" in full
        assert "MSFT" in full
        assert "<pre>" in full

    def test_format_html_parse_mode(self, config, logger):
        """Verify HTML parse_mode is used instead of Markdown."""
        from ifds.output.telegram import send_daily_report
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = "456"

        ctx = _make_ctx(positions=[_make_position()])
        with patch("ifds.output.telegram.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            send_daily_report(ctx, config, logger, 5.0)

        for c in mock_post.call_args_list:
            assert c[1]["json"]["parse_mode"] == "HTML"

    def test_format_phase_structure(self, config):
        """All 7 phase headers appear in the formatted output."""
        from ifds.output.telegram import _format_success
        ctx = _make_ctx(positions=[_make_position()])
        part1, part2 = _format_success(ctx, 10.0, config)
        full = part1 + part2
        for i in range(7):
            assert f"[ {i}/6 ]" in full

    @patch("ifds.output.telegram.requests.post")
    def test_failure_report(self, mock_post, config, logger):
        """Failure report sends error message with HTML."""
        from ifds.output.telegram import send_failure_report
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = "456"

        mock_post.return_value = MagicMock()

        result = send_failure_report("Connection refused", config, logger, 2.5)
        assert result is True
        kwargs = mock_post.call_args[1]
        assert kwargs["json"]["parse_mode"] == "HTML"
        text = kwargs["json"]["text"]
        assert "FAILED" in text
        assert "Connection refused" in text
        assert "2.5s" in text

    @patch("ifds.output.telegram.requests.post")
    def test_message_splitting(self, mock_post, config, logger):
        """Long messages are split into 2 sends."""
        from ifds.output.telegram import send_daily_report, _MAX_MSG_LEN
        config.runtime["telegram_bot_token"] = "123:ABC"
        config.runtime["telegram_chat_id"] = "456"
        mock_post.return_value = MagicMock()

        # Create many positions to push message over 4096
        positions = [
            _make_position(ticker=f"T{i:03d}", price=100.0 + i)
            for i in range(60)
        ]
        ctx = _make_ctx(positions=positions)
        result = send_daily_report(ctx, config, logger, 99.0)

        assert result is True
        # Should have sent 2 messages (Phase 0-4 + Phase 5-6)
        assert mock_post.call_count == 2
        text1 = mock_post.call_args_list[0][1]["json"]["text"]
        text2 = mock_post.call_args_list[1][1]["json"]["text"]
        assert "[ 0/6 ]" in text1
        assert "[ 6/6 ]" in text2


# ============================================================================
# Feature 3: Max Daily Trades
# ============================================================================

class TestDailyTradeCounter:
    """Test daily trade state file loading and saving."""

    def test_load_no_file(self, tmp_path):
        """Missing file returns today with count=0."""
        result = _load_daily_counter(str(tmp_path / "nonexistent.json"))
        assert result["date"] == date.today().isoformat()
        assert result["count"] == 0

    def test_load_today(self, tmp_path):
        """Today's file returns stored count."""
        state_file = tmp_path / "trades.json"
        state_file.write_text(json.dumps({
            "date": date.today().isoformat(),
            "count": 5,
        }))
        result = _load_daily_counter(str(state_file))
        assert result["count"] == 5

    def test_load_old_date_resets(self, tmp_path):
        """Yesterday's file resets to count=0."""
        state_file = tmp_path / "trades.json"
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state_file.write_text(json.dumps({"date": yesterday, "count": 15}))
        result = _load_daily_counter(str(state_file))
        assert result["count"] == 0
        assert result["date"] == date.today().isoformat()

    def test_load_corrupt_json(self, tmp_path):
        """Corrupt JSON returns fresh counter."""
        state_file = tmp_path / "trades.json"
        state_file.write_text("{bad json")
        result = _load_daily_counter(str(state_file))
        assert result["count"] == 0

    def test_save_and_reload(self, tmp_path):
        """Save writes valid JSON that loads back correctly."""
        state_file = tmp_path / "trades.json"
        counter = {"date": date.today().isoformat(), "count": 7}
        _save_daily_counter(str(state_file), counter)

        assert state_file.exists()
        result = _load_daily_counter(str(state_file))
        assert result["count"] == 7

    def test_save_creates_dirs(self, tmp_path):
        """Save creates parent directories if needed."""
        state_file = tmp_path / "sub" / "dir" / "trades.json"
        counter = {"date": date.today().isoformat(), "count": 3}
        _save_daily_counter(str(state_file), counter)
        assert state_file.exists()


class TestMaxDailyTrades:
    """Test daily trade limit enforcement in Phase 6."""

    def test_daily_limit_enforced(self, config, logger, tmp_path):
        """Candidates beyond max_daily_trades are skipped."""
        config.runtime["max_daily_trades"] = 2
        config.runtime["max_positions"] = 20
        config.runtime["max_daily_notional"] = 10_000_000
        config.runtime["max_position_notional"] = 1_000_000

        # Create state file with 2 trades already today
        trades_file = tmp_path / "daily_trades.json"
        trades_file.write_text(json.dumps({
            "date": date.today().isoformat(),
            "count": 2,
        }))
        config.runtime["daily_trades_file"] = str(trades_file)
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")

        stocks = [_make_stock(f"T{i}", combined=90.0 - i) for i in range(3)]
        gex_list = [_make_gex(f"T{i}") for i in range(3)]

        result = run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        # All 3 should be excluded by daily limit
        assert result.excluded_daily_trade_limit == 3
        assert len(result.positions) == 0

    def test_daily_limit_partial(self, config, logger, tmp_path):
        """Some candidates pass before limit is hit."""
        config.runtime["max_daily_trades"] = 2
        config.runtime["max_positions"] = 20
        config.runtime["max_daily_notional"] = 10_000_000
        config.runtime["max_position_notional"] = 1_000_000

        trades_file = tmp_path / "daily_trades.json"
        # Start with 0 trades today
        config.runtime["daily_trades_file"] = str(trades_file)
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")

        stocks = [_make_stock(f"T{i}", combined=90.0 - i) for i in range(5)]
        gex_list = [_make_gex(f"T{i}") for i in range(5)]

        result = run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        # 2 pass, 3 excluded by daily limit
        assert len(result.positions) == 2
        assert result.excluded_daily_trade_limit == 3


# ============================================================================
# Feature 4: Notional Limits
# ============================================================================

class TestNotionalLimits:
    """Test per-position and daily notional limit enforcement."""

    def test_position_notional_capped(self, config, logger, tmp_path):
        """Position with notional > max_position_notional has quantity reduced."""
        config.runtime["max_daily_trades"] = 100
        config.runtime["max_daily_notional"] = 10_000_000
        config.runtime["max_position_notional"] = 3_000  # $3K cap
        config.runtime["max_positions"] = 20
        config.runtime["daily_trades_file"] = str(tmp_path / "trades.json")
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")

        # Stock at $150, normal sizing would give ~22 shares ($3300 > $3K)
        stocks = [_make_stock("AAPL", price=150.0, combined=80.0)]
        gex_list = [_make_gex("AAPL")]

        result = run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        if result.positions:
            pos = result.positions[0]
            assert pos.quantity * pos.entry_price <= 3_000

    def test_daily_notional_cap(self, config, logger, tmp_path):
        """Positions exceeding daily notional total are skipped."""
        config.runtime["max_daily_trades"] = 100
        config.runtime["max_daily_notional"] = 5_000  # Very low daily limit
        config.runtime["max_position_notional"] = 50_000
        config.runtime["max_positions"] = 20
        config.runtime["daily_trades_file"] = str(tmp_path / "trades.json")
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")

        # Multiple stocks — each ~$3K notional, so 2nd one should exceed $5K daily
        stocks = [_make_stock(f"T{i}", price=150.0, combined=90.0 - i) for i in range(3)]
        gex_list = [_make_gex(f"T{i}") for i in range(3)]

        result = run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        # Some positions should be excluded by daily notional
        assert result.excluded_notional_limit >= 1

    def test_daily_notional_persisted(self, config, logger, tmp_path):
        """Daily notional counter is saved after Phase 6."""
        config.runtime["max_daily_trades"] = 100
        config.runtime["max_daily_notional"] = 10_000_000
        config.runtime["max_position_notional"] = 1_000_000
        config.runtime["max_positions"] = 20
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")
        config.runtime["daily_trades_file"] = str(tmp_path / "trades.json")

        stocks = [_make_stock("AAPL", combined=80.0)]
        gex_list = [_make_gex("AAPL")]

        run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        # Notional file should now exist with today's data
        notional_path = tmp_path / "notional.json"
        assert notional_path.exists()
        data = json.loads(notional_path.read_text())
        assert data["date"] == date.today().isoformat()
        assert data["count"] > 0  # At least one position's notional recorded


# ============================================================================
# Replace Quantity Helper
# ============================================================================

class TestReplaceQuantity:
    """Test PositionSizing quantity replacement."""

    def test_replace_quantity_preserves_fields(self):
        """All fields except quantity are preserved."""
        pos = _make_position(ticker="NVDA", price=875.0, quantity=50)
        new_pos = _replace_quantity(pos, 10)

        assert new_pos.quantity == 10
        assert new_pos.ticker == "NVDA"
        assert new_pos.entry_price == 875.0
        assert new_pos.sector == "Technology"
        assert new_pos.direction == "BUY"
        assert new_pos.stop_loss == pos.stop_loss
        assert new_pos.take_profit_1 == pos.take_profit_1

    def test_replace_quantity_different_value(self):
        """Quantity is actually changed."""
        pos = _make_position(quantity=100)
        new_pos = _replace_quantity(pos, 25)
        assert new_pos.quantity == 25
        assert pos.quantity == 100  # Original unchanged


# ============================================================================
# Phase6Result Model Extensions
# ============================================================================

class TestPhase6ResultFields:
    """Test new Phase6Result fields for BC13."""

    def test_default_values(self):
        """New fields default to 0."""
        result = Phase6Result()
        assert result.excluded_daily_trade_limit == 0
        assert result.excluded_notional_limit == 0

    def test_fields_set(self):
        """New fields can be set."""
        result = Phase6Result(
            excluded_daily_trade_limit=5,
            excluded_notional_limit=3,
        )
        assert result.excluded_daily_trade_limit == 5
        assert result.excluded_notional_limit == 3


# ============================================================================
# Integration: GLOBALGUARD logging
# ============================================================================

class TestGlobalGuardLogging:
    """Test [GLOBALGUARD] logging for trade and notional limits."""

    def test_daily_trade_limit_log(self, config, logger, tmp_path):
        """[GLOBALGUARD] Daily trade limit message is logged."""
        config.runtime["max_daily_trades"] = 1
        config.runtime["max_daily_notional"] = 10_000_000
        config.runtime["max_position_notional"] = 1_000_000
        config.runtime["max_positions"] = 20
        config.runtime["daily_trades_file"] = str(tmp_path / "trades.json")
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")

        stocks = [_make_stock(f"T{i}", combined=90.0 - i) for i in range(3)]
        gex_list = [_make_gex(f"T{i}") for i in range(3)]

        run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        events = logger.events
        globalguard = [e for e in events
                       if "[GLOBALGUARD]" in e.get("message", "")
                       and "Daily trade limit" in e.get("message", "")]
        assert len(globalguard) >= 1

    def test_position_notional_cap_log(self, config, logger, tmp_path):
        """[GLOBALGUARD] Position notional capped message is logged."""
        config.runtime["max_daily_trades"] = 100
        config.runtime["max_daily_notional"] = 10_000_000
        config.runtime["max_position_notional"] = 1_000  # Very low → force cap
        config.runtime["max_positions"] = 20
        config.runtime["daily_trades_file"] = str(tmp_path / "trades.json")
        config.runtime["daily_notional_file"] = str(tmp_path / "notional.json")

        stocks = [_make_stock("AAPL", price=150.0, combined=80.0)]
        gex_list = [_make_gex("AAPL")]

        run_phase6(
            config, logger, stocks, gex_list,
            _make_macro(), StrategyMode.LONG,
        )

        events = logger.events
        cap_events = [e for e in events
                      if "[GLOBALGUARD]" in e.get("message", "")
                      and "notional capped" in e.get("message", "").lower()]
        assert len(cap_events) >= 1
