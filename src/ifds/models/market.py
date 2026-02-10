"""Market data models for IFDS pipeline.

Dataclasses for type-safe data flow between phases.
BC1: Phase 0 models (diagnostics, macro, circuit breaker).
BC2: Phase 1-3 models (BMI, ticker, sector rotation).
BC3: Phase 4-5 models (stock analysis, GEX analysis).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class MarketVolatilityRegime(Enum):
    """VIX-based market volatility classification."""
    LOW = "low"             # VIX <= 15
    NORMAL = "normal"       # 15 < VIX <= 20
    ELEVATED = "elevated"   # 20 < VIX <= 30
    PANIC = "panic"         # 30 < VIX <= 50
    EXTREME = "extreme"     # VIX > 50 — near-halt


class BMIRegime(Enum):
    """Big Money Index regime classification."""
    GREEN = "green"         # BMI <= 25% — aggressive long
    YELLOW = "yellow"       # 25% < BMI < 80% — normal long
    RED = "red"             # BMI >= 80% — short/defensive


class StrategyMode(Enum):
    """Pipeline strategy direction."""
    LONG = "long"
    SHORT = "short"


class APIStatus(Enum):
    """Health check status for an API endpoint."""
    OK = "ok"
    DEGRADED = "degraded"   # Slow but responding
    DOWN = "down"           # Not responding after retries
    SKIPPED = "skipped"     # Not checked (e.g., optional provider)


class GEXRegime(Enum):
    """Gamma Exposure regime classification."""
    POSITIVE = "positive"   # Low volatility, magnet effect
    NEGATIVE = "negative"   # High volatility, unstable
    HIGH_VOL = "high_vol"   # Transition zone


class SectorBMIRegime(Enum):
    """Sector-level BMI classification (per-sector thresholds)."""
    OVERSOLD = "oversold"       # BMI < sector oversold threshold
    NEUTRAL = "neutral"         # Between oversold and overbought
    OVERBOUGHT = "overbought"   # BMI > sector overbought threshold


class MomentumClassification(Enum):
    """Sector momentum ranking classification."""
    LEADER = "leader"       # Top N momentum → +15 bonus
    NEUTRAL = "neutral"     # Middle tier → 0
    LAGGARD = "laggard"     # Bottom N momentum → -20 penalty


class SectorTrend(Enum):
    """Sector price trend relative to SMA20."""
    UP = "up"       # Price > SMA20
    DOWN = "down"   # Price <= SMA20


class DarkPoolSignal(Enum):
    """Dark Pool activity classification."""
    BULLISH = "bullish"     # DP buys > DP sells
    BEARISH = "bearish"     # DP sells > DP buys
    NEUTRAL = "neutral"     # Equal or no data


# ============================================================================
# Phase 0: Diagnostics Models
# ============================================================================

@dataclass
class APIHealthResult:
    """Result of a single API endpoint health check."""
    provider: str           # "polygon", "unusual_whales", "fmp", "fred"
    endpoint: str           # Specific endpoint tested
    status: APIStatus
    response_time_ms: float | None = None
    error: str | None = None
    is_critical: bool = True    # If True, failure → pipeline HALT
    retries_used: int = 0


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for drawdown protection."""
    is_active: bool
    daily_drawdown_pct: float = 0.0
    limit_pct: float = 3.0
    last_check: datetime | None = None
    activated_at: datetime | None = None
    message: str = ""


@dataclass
class MacroRegime:
    """Macro environment assessment from FRED data."""
    # VIX
    vix_value: float
    vix_regime: MarketVolatilityRegime
    vix_multiplier: float       # 1.0 if VIX <= 20, else max(0.25, 1-(VIX-20)*0.02)

    # TNX (10-Year Treasury Yield)
    tnx_value: float
    tnx_sma20: float
    tnx_rate_sensitive: bool    # True if TNX > SMA20 * 1.05

    timestamp: datetime | None = None


@dataclass
class DiagnosticsResult:
    """Combined result of Phase 0: System Diagnostics."""
    api_health: list[APIHealthResult] = field(default_factory=list)
    circuit_breaker: CircuitBreakerState | None = None
    macro: MacroRegime | None = None

    # Overall status
    all_critical_apis_ok: bool = False
    pipeline_can_proceed: bool = False
    halt_reason: str | None = None

    @property
    def uw_available(self) -> bool:
        """Check if Unusual Whales API is available."""
        for h in self.api_health:
            if h.provider == "unusual_whales":
                return h.status == APIStatus.OK
        return False


# ============================================================================
# Phase 1: BMI Market Regime Models
# ============================================================================

@dataclass
class BMIData:
    """Big Money Index calculation result."""
    bmi_value: float                    # Current BMI (SMA25 of daily ratios)
    bmi_regime: BMIRegime               # GREEN / YELLOW / RED
    daily_ratio: float                  # Most recent B/(B+S)*100
    buy_count: int = 0                  # Today's big money buy signals
    sell_count: int = 0                 # Today's big money sell signals
    divergence_detected: bool = False   # Bearish divergence (SPY up, BMI down)
    divergence_type: str | None = None  # "bearish" or None


@dataclass
class Phase1Result:
    """Output of Phase 1: Market Regime determination."""
    bmi: BMIData
    strategy_mode: StrategyMode         # LONG or SHORT
    ticker_count_for_bmi: int = 0       # How many tickers used for BMI calc
    sector_bmi_values: dict[str, float] = field(default_factory=dict)  # ETF → BMI%


# ============================================================================
# Phase 2: Universe Building Models
# ============================================================================

@dataclass
class Ticker:
    """A screened stock from FMP with basic fundamentals."""
    symbol: str
    company_name: str = ""
    sector: str = ""
    market_cap: float = 0.0
    price: float = 0.0
    avg_volume: float = 0.0
    has_options: bool = False
    is_etf: bool = False

    # Zombie-specific fields (SHORT universe)
    debt_equity: float | None = None
    net_margin: float | None = None
    interest_coverage: float | None = None


@dataclass
class Phase2Result:
    """Output of Phase 2: Universe Building."""
    tickers: list[Ticker] = field(default_factory=list)
    total_screened: int = 0
    earnings_excluded: list[str] = field(default_factory=list)
    strategy_mode: StrategyMode = StrategyMode.LONG


# ============================================================================
# Phase 3: Sector Rotation Models
# ============================================================================

@dataclass
class SectorScore:
    """Analysis result for a single sector ETF."""
    etf: str                            # e.g. "XLK"
    sector_name: str                    # e.g. "Technology"
    momentum_5d: float = 0.0           # 5-day relative performance %
    trend: SectorTrend = SectorTrend.UP
    rank: int = 0                       # 1 = highest momentum
    classification: MomentumClassification = MomentumClassification.NEUTRAL
    sector_bmi: float | None = None     # Sector-level BMI (if calculated)
    sector_bmi_regime: SectorBMIRegime = SectorBMIRegime.NEUTRAL
    vetoed: bool = False                # True if sector is vetoed
    veto_reason: str | None = None
    score_adjustment: int = 0           # +15 Leader, -20 Laggard, etc.


@dataclass
class Phase3Result:
    """Output of Phase 3: Sector Rotation."""
    sector_scores: list[SectorScore] = field(default_factory=list)
    vetoed_sectors: list[str] = field(default_factory=list)   # ETF symbols
    active_sectors: list[str] = field(default_factory=list)   # Non-vetoed ETFs
    rate_sensitive_penalty: bool = False  # True if TNX rate sensitivity active


# ============================================================================
# Phase 4: Individual Stock Analysis Models
# ============================================================================

@dataclass
class TechnicalAnalysis:
    """Technical indicator results for a ticker."""
    price: float
    sma_200: float
    sma_20: float
    rsi_14: float
    atr_14: float
    trend_pass: bool            # Price > SMA200 (LONG) or Price < SMA200 (SHORT)
    rsi_score: int = 0          # RSI ideal zone: +30 inner, +15 outer, 0 outside
    sma_50: float = 0.0
    sma50_bonus: int = 0        # +30 if price > SMA50
    rs_vs_spy: float | None = None  # ticker - SPY 3-month return
    rs_spy_score: int = 0       # +40 if outperforming SPY


@dataclass
class FlowAnalysis:
    """Flow (VPA + Dark Pool) analysis for a ticker."""
    volume_today: float = 0.0
    volume_sma_20: float = 0.0
    rvol: float = 1.0                          # volume_today / volume_sma_20
    rvol_score: int = 0                        # -10 to +15 (+ squat bar bonus)
    spread_today: float = 0.0                  # High - Low
    spread_sma_10: float = 0.0
    spread_ratio: float = 1.0                  # spread_today / spread_sma_10
    squat_bar: bool = False                    # RVOL > 2.0 AND SpreadRatio < 0.9
    squat_bar_bonus: int = 0                   # +10 if squat bar detected
    dark_pool_pct: float = 0.0                 # DP volume / total volume
    dark_pool_signal: DarkPoolSignal | None = None
    dp_pct_score: int = 0                        # +10 or +15 based on dp_pct
    pcr: float | None = None                      # Put/Call Ratio
    pcr_score: int = 0                            # +15 bullish, -10 bearish
    otm_call_ratio: float | None = None           # OTM calls / total calls
    otm_score: int = 0                            # +10 if > 40%
    block_trade_count: int = 0                    # $500K+ trades
    block_trade_score: int = 0                    # +10 or +15
    vwap: float = 0.0                             # Volume-weighted average price
    buy_pressure_score: int = 0                   # buy pressure + VWAP signal


@dataclass
class FundamentalScoring:
    """Fundamental metrics and scores for a ticker."""
    revenue_growth_yoy: float | None = None
    eps_growth_yoy: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    debt_equity: float | None = None
    interest_coverage: float | None = None
    insider_score: int = 0              # Sum of (buys - sells) in last 30d
    insider_multiplier: float = 1.0     # 0.75, 1.0, or 1.25
    funda_score: int = 0                # Sum of all fundamental score components
    shark_detected: bool = False        # Insider cluster buying detected
    inst_ownership_trend: str = "unknown"   # "increasing", "decreasing", "stable", "unknown"
    inst_ownership_score: int = 0           # +10 increasing, -5 decreasing


@dataclass
class StockAnalysis:
    """Complete analysis result for a single ticker."""
    ticker: str
    sector: str
    technical: TechnicalAnalysis
    flow: FlowAnalysis
    fundamental: FundamentalScoring
    combined_score: float = 0.0         # Weighted: 0.4*flow + 0.3*funda + 0.3*tech + sector_adj
    sector_adjustment: int = 0          # From Phase 3 (Leader +15, Laggard -20, etc.)
    excluded: bool = False
    exclusion_reason: str | None = None  # "tech_filter", "min_score", "clipping"
    shark_detected: bool = False


@dataclass
class Phase4Result:
    """Output of Phase 4: Individual Stock Analysis."""
    analyzed: list[StockAnalysis] = field(default_factory=list)
    passed: list[StockAnalysis] = field(default_factory=list)   # score >= 70, not clipped
    excluded_count: int = 0
    clipped_count: int = 0              # Crowded trades (score > 90, base score before freshness)
    tech_filter_count: int = 0          # Failed SMA200 trend filter
    min_score_count: int = 0            # Score < 70


# ============================================================================
# Phase 5: GEX Analysis Models
# ============================================================================

@dataclass
class GEXAnalysis:
    """GEX regime analysis for a ticker."""
    ticker: str
    net_gex: float = 0.0
    call_wall: float = 0.0
    put_wall: float = 0.0
    zero_gamma: float = 0.0
    current_price: float = 0.0
    gex_regime: GEXRegime = GEXRegime.POSITIVE
    gex_multiplier: float = 1.0         # 1.0 / 0.5 / 0.6
    excluded: bool = False              # True if NEGATIVE in LONG mode
    exclusion_reason: str | None = None
    data_source: str = ""               # "unusual_whales" or "polygon_calculated"


@dataclass
class Phase5Result:
    """Output of Phase 5: GEX Analysis."""
    analyzed: list[GEXAnalysis] = field(default_factory=list)
    passed: list[GEXAnalysis] = field(default_factory=list)
    excluded_count: int = 0
    negative_regime_count: int = 0


# ============================================================================
# Phase 6: Position Sizing Models
# ============================================================================

@dataclass
class PositionSizing:
    """Position sizing result for a single ticker."""
    ticker: str
    sector: str
    direction: str               # "BUY" or "SELL_SHORT"
    entry_price: float
    quantity: int                # floor(adjusted_risk / stop_distance)
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_usd: float
    combined_score: float
    gex_regime: str              # GEXRegime.value
    multiplier_total: float
    m_flow: float = 1.0
    m_insider: float = 1.0
    m_funda: float = 1.0
    m_gex: float = 1.0
    m_vix: float = 1.0
    m_utility: float = 1.0
    scale_out_price: float = 0.0
    scale_out_pct: float = 0.33
    is_fresh: bool = False
    original_score: float = 0.0
    sector_etf: str = ""
    sector_bmi: float | None = None
    sector_regime: str = ""
    is_mean_reversion: bool = False
    shark_detected: bool = False


@dataclass
class Phase6Result:
    """Output of Phase 6: Position Sizing & Risk Management."""
    positions: list[PositionSizing] = field(default_factory=list)
    excluded_sector_limit: int = 0
    excluded_position_limit: int = 0
    excluded_risk_limit: int = 0
    excluded_exposure_limit: int = 0
    excluded_dedup: int = 0
    freshness_applied_count: int = 0
    total_risk_usd: float = 0.0
    total_exposure_usd: float = 0.0


# ============================================================================
# Pipeline Context (passed between phases)
# ============================================================================

@dataclass
class PipelineContext:
    """Shared context passed through all pipeline phases.

    Each phase reads from and writes to this context.
    """
    # Phase 0 output
    diagnostics: DiagnosticsResult | None = None
    macro: MacroRegime | None = None
    uw_available: bool = False

    # Phase 1 output
    phase1: Phase1Result | None = None
    strategy_mode: StrategyMode | None = None
    bmi_regime: BMIRegime | None = None
    bmi_value: float | None = None
    sector_bmi_values: dict[str, float] = field(default_factory=dict)

    # Phase 2 output
    phase2: Phase2Result | None = None
    universe: list[Ticker] = field(default_factory=list)

    # Phase 3 output
    phase3: Phase3Result | None = None
    sector_scores: list[SectorScore] = field(default_factory=list)
    vetoed_sectors: list[str] = field(default_factory=list)

    # Phase 4 output
    phase4: Phase4Result | None = None
    stock_analyses: list[StockAnalysis] = field(default_factory=list)

    # Phase 5 output
    phase5: Phase5Result | None = None
    gex_analyses: list[GEXAnalysis] = field(default_factory=list)

    # Phase 6 output
    phase6: Phase6Result | None = None
    positions: list[PositionSizing] = field(default_factory=list)
    execution_plan_path: str | None = None

    # Metadata
    run_id: str = ""
    started_at: datetime | None = None
    config_snapshot: dict = field(default_factory=dict)
