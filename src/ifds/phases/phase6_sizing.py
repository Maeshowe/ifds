"""Phase 6: Position Sizing & Risk Management.

Transforms scored candidates into sized positions with:
1. Risk-adjusted position sizing (6 multipliers)
2. Stop-loss / take-profit levels (ATR-based)
3. Freshness Alpha (bonus for new signals)
4. Position limits (max positions, sector diversification, exposure caps)

Formulas:
    BaseRisk = AccountEquity × RiskPerTrade_pct
    AdjustedRisk = BaseRisk × M_total
    M_total = clamp(M_flow × M_insider × M_funda × M_gex × M_vix × M_utility, 0.25, 2.0)
    Quantity = floor(AdjustedRisk / (stop_loss_atr_multiple × ATR14))
"""

import dataclasses
import json
import math
import os
import time
from datetime import date, datetime, timezone

from ifds.config.loader import Config
from ifds.data.signal_dedup import SignalDedup
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    GEXAnalysis,
    MacroRegime,
    MomentumClassification,
    MMSAnalysis,
    Phase6Result,
    PositionSizing,
    SectorBMIRegime,
    SectorScore,
    StockAnalysis,
    StrategyMode,
)

_BASE_SCORE = 50  # Neutral starting point for sub-dimension scores


def run_phase6(config: Config, logger: EventLogger,
               stock_analyses: list[StockAnalysis],
               gex_analyses: list[GEXAnalysis],
               macro: MacroRegime,
               strategy_mode: StrategyMode,
               signal_history_path: str | None = None,
               sector_scores: list[SectorScore] | None = None,
               signal_hash_file: str | None = None,
               mms_analyses: list[MMSAnalysis] | None = None) -> Phase6Result:
    """Run Phase 6: Position Sizing & Risk Management.

    Args:
        config: Pipeline configuration.
        logger: Event logger.
        stock_analyses: Passed stocks from Phase 4.
        gex_analyses: Passed GEX analyses from Phase 5.
        macro: Macro regime (VIX multiplier).
        strategy_mode: LONG or SHORT.
        signal_history_path: Path to signal_history.parquet for freshness alpha.

    Returns:
        Phase6Result with sized positions.
    """
    logger.log(EventType.PHASE_START, Severity.INFO, phase=6,
               message="Phase 6 started: Position Sizing & Risk Management")
    t0 = time.time()

    try:
        # 1. Join stock analyses with GEX analyses by ticker
        candidates = _join_stock_gex(stock_analyses, gex_analyses)

        if not candidates:
            logger.log(EventType.PHASE_COMPLETE, Severity.INFO, phase=6,
                       message="No candidates after stock-GEX join")
            return Phase6Result()

        # 2. Capture original scores BEFORE freshness alpha modifies them
        original_scores = {s.ticker: s.combined_score for s, _ in candidates}

        # 3. Apply freshness alpha (modifies scores before sizing)
        freshness_count, fresh_tickers = _apply_freshness_alpha(
            candidates, config, signal_history_path, logger,
        )

        # 4. Sort by original (pre-freshness) score to preserve ranking
        # Freshness is a multiplier bonus, not a reranking mechanism
        candidates.sort(key=lambda c: original_scores.get(c[0].ticker, c[0].combined_score),
                        reverse=True)

        # 5. Build sector lookup for new PositionSizing fields
        _sector_map = {ss.sector_name: ss for ss in (sector_scores or [])}

        # MMS lookup (BC15)
        _mms_map = {o.ticker: o for o in (mms_analyses or [])}

        # 6. Signal dedup + daily trade limit + position sizing
        dedup = SignalDedup(signal_hash_file) if signal_hash_file else None
        dedup_count = 0

        # Daily trade tracker (BC13)
        daily_trades = _load_daily_counter(
            config.runtime.get("daily_trades_file", "state/daily_trades.json"))
        max_daily_trades = config.runtime.get("max_daily_trades", 20)
        daily_trade_limit_hit = False
        initial_trade_count = daily_trades["count"]

        # Daily notional tracker (BC13)
        daily_notional = _load_daily_counter(
            config.runtime.get("daily_notional_file", "state/daily_notional.json"))
        max_daily_notional = config.runtime.get("max_daily_notional", 200_000)
        max_position_notional = config.runtime.get("max_position_notional", 25_000)
        initial_notional_count = daily_notional["count"]
        daily_trade_excluded = 0
        notional_excluded = 0

        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=6,
                   message=f"[PHASE6] Starting: {len(candidates)} candidates, "
                           f"daily_trades={initial_trade_count}/{max_daily_trades}, "
                           f"daily_notional=${initial_notional_count:.0f}/${max_daily_notional:.0f}")

        raw_positions = []
        sizing_failed_count = 0
        for stock, gex in candidates:
            direction = "BUY" if strategy_mode == StrategyMode.LONG else "SELL_SHORT"
            if dedup and dedup.is_duplicate(stock.ticker, direction):
                dedup_count += 1
                logger.log(EventType.TICKER_FILTERED, Severity.INFO, phase=6,
                           message=f"[DEDUP] Skipping {stock.ticker} — signal already generated today")
                continue

            # Daily trade limit check (BC13) — after dedup, before sizing
            if daily_trades["count"] >= max_daily_trades:
                if not daily_trade_limit_hit:
                    logger.log(EventType.TICKER_FILTERED, Severity.WARNING, phase=6,
                               message=f"[GLOBALGUARD] Daily trade limit reached "
                                       f"({daily_trades['count']}/{max_daily_trades}), skip remaining")
                    daily_trade_limit_hit = True
                daily_trade_excluded += 1
                continue

            pos = _calculate_position(stock, gex, macro, config, strategy_mode,
                                      original_scores, fresh_tickers, _sector_map,
                                      _mms_map)
            if pos is None:
                sizing_failed_count += 1
                if sizing_failed_count <= 5:
                    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=6,
                               message=f"[PHASE6] {stock.ticker}: sizing returned None "
                                       f"(score={stock.combined_score:.1f}, "
                                       f"atr={stock.technical.atr_14:.2f}, "
                                       f"price={stock.technical.price:.2f})")
                continue

            # Notional limit checks (BC13)
            pos_notional = pos.quantity * pos.entry_price

            # Per-position notional cap
            if pos_notional > max_position_notional and pos.entry_price > 0:
                original_notional = pos_notional
                capped_qty = math.floor(max_position_notional / pos.entry_price)
                if capped_qty <= 0:
                    continue
                logger.log(EventType.TICKER_FILTERED, Severity.INFO, phase=6,
                           message=f"[GLOBALGUARD] Position notional capped: {pos.ticker} "
                                   f"${original_notional:.0f} → ${capped_qty * pos.entry_price:.0f}")
                pos = _replace_quantity(pos, capped_qty)
                pos_notional = capped_qty * pos.entry_price

            # Daily notional cap
            if daily_notional["count"] + pos_notional > max_daily_notional:
                logger.log(EventType.TICKER_FILTERED, Severity.WARNING, phase=6,
                           message=f"[GLOBALGUARD] Daily notional limit reached: "
                                   f"${daily_notional['count']:.0f}/${max_daily_notional:.0f}")
                notional_excluded += 1
                continue

            raw_positions.append(pos)
            daily_trades["count"] += 1
            daily_notional["count"] += pos_notional
            if dedup:
                dedup.record(stock.ticker, direction)

        # 7. Apply position limits
        final_positions, limit_counts = _apply_position_limits(
            raw_positions, config, logger,
        )

        # Recalculate daily counters based on final positions (not raw).
        # _apply_position_limits may remove positions (sector, exposure limits),
        # so we must not inflate the daily counters for removed positions.
        daily_trades["count"] = initial_trade_count + len(final_positions)
        daily_notional["count"] = initial_notional_count + sum(
            p.quantity * p.entry_price for p in final_positions)

        # 8. Log each sized position
        for pos in final_positions:
            logger.log(EventType.POSITION_SIZED, Severity.INFO, phase=6,
                       message=f"Sized {pos.ticker}: {pos.quantity} shares @ ${pos.entry_price:.2f}",
                       data={
                           "ticker": pos.ticker,
                           "direction": pos.direction,
                           "quantity": pos.quantity,
                           "entry_price": pos.entry_price,
                           "stop_loss": pos.stop_loss,
                           "risk_usd": round(pos.risk_usd, 2),
                           "multiplier_total": round(pos.multiplier_total, 4),
                       })

        # Save state files
        if dedup:
            dedup.save()
        _save_daily_counter(
            config.runtime.get("daily_trades_file", "state/daily_trades.json"),
            daily_trades)
        _save_daily_counter(
            config.runtime.get("daily_notional_file", "state/daily_notional.json"),
            daily_notional)

        total_risk = sum(p.risk_usd for p in final_positions)
        total_exposure = sum(p.quantity * p.entry_price for p in final_positions)

        elapsed = time.time() - t0
        logger.log(EventType.PHASE_COMPLETE, Severity.INFO, phase=6,
                   message=f"Phase 6 complete: {len(final_positions)} positions sized in {elapsed:.2f}s",
                   data={
                       "positions": len(final_positions),
                       "total_risk_usd": round(total_risk, 2),
                       "total_exposure_usd": round(total_exposure, 2),
                       "freshness_applied": freshness_count,
                   })

        return Phase6Result(
            positions=final_positions,
            excluded_sector_limit=limit_counts["sector"],
            excluded_position_limit=limit_counts["position"],
            excluded_risk_limit=limit_counts["risk"],
            excluded_exposure_limit=limit_counts["exposure"],
            excluded_dedup=dedup_count,
            excluded_daily_trade_limit=daily_trade_excluded,
            excluded_notional_limit=notional_excluded,
            freshness_applied_count=freshness_count,
            total_risk_usd=total_risk,
            total_exposure_usd=total_exposure,
        )

    except Exception as e:
        logger.log(EventType.PHASE_ERROR, Severity.ERROR, phase=6,
                   message=f"Phase 6 error: {e}")
        raise


def _join_stock_gex(stock_analyses: list[StockAnalysis],
                    gex_analyses: list[GEXAnalysis],
                    ) -> list[tuple[StockAnalysis, GEXAnalysis]]:
    """Inner join stock and GEX analyses by ticker."""
    gex_map = {g.ticker: g for g in gex_analyses}
    result = []
    for stock in stock_analyses:
        gex = gex_map.get(stock.ticker)
        if gex is not None:
            result.append((stock, gex))
    return result


def _apply_freshness_alpha(
    candidates: list[tuple[StockAnalysis, GEXAnalysis]],
    config: Config,
    signal_history_path: str | None,
    logger: EventLogger,
) -> tuple[int, set[str]]:
    """Apply freshness bonus to signals not seen in recent history.

    Returns:
        (count of bonuses applied, set of fresh ticker symbols)
    """
    try:
        import pandas as pd
    except ImportError:
        logger.log(EventType.CONFIG_WARNING, Severity.WARNING, phase=6,
                   message="pandas not installed — skipping freshness alpha")
        return 0, set()

    lookback_days = config.core["freshness_lookback_days"]
    bonus = config.core["freshness_bonus"]
    cutoff = datetime.now(timezone.utc).date()

    # Load existing history
    history_tickers: set[str] = set()
    if signal_history_path:
        try:
            df = pd.read_parquet(signal_history_path)
            if "date" in df.columns and "ticker" in df.columns:
                from datetime import timedelta
                cutoff_date = cutoff - timedelta(days=lookback_days)
                df["date"] = pd.to_datetime(df["date"]).dt.date
                recent = df[df["date"] >= cutoff_date]
                history_tickers = set(recent["ticker"].unique())
        except FileNotFoundError:
            pass  # No history yet — all signals are fresh
        except Exception as e:
            logger.log(EventType.CONFIG_WARNING, Severity.WARNING, phase=6,
                       message=f"Error reading signal history: {e}")

    # Apply freshness bonus
    fresh_count = 0
    fresh_tickers: set[str] = set()
    for stock, _gex in candidates:
        if stock.ticker not in history_tickers:
            original = stock.combined_score
            stock.combined_score = original * bonus
            fresh_tickers.add(stock.ticker)
            fresh_count += 1
            logger.log(EventType.FRESHNESS_BONUS, Severity.DEBUG, phase=6,
                       message=f"Fresh signal: {stock.ticker} (score × {bonus})",
                       data={"ticker": stock.ticker, "bonus": bonus,
                             "original_score": original})

    # Save current signals to history
    if signal_history_path:
        try:
            current_tickers = [s.ticker for s, _ in candidates]
            new_rows = pd.DataFrame({
                "ticker": current_tickers,
                "date": [cutoff] * len(current_tickers),
            })
            try:
                existing = pd.read_parquet(signal_history_path)
                combined = pd.concat([existing, new_rows], ignore_index=True)
            except FileNotFoundError:
                combined = new_rows

            import os
            os.makedirs(os.path.dirname(signal_history_path) or ".", exist_ok=True)
            combined.to_parquet(signal_history_path, index=False)
        except Exception as e:
            logger.log(EventType.CONFIG_WARNING, Severity.WARNING, phase=6,
                       message=f"Error saving signal history: {e}")

    return fresh_count, fresh_tickers


def _calculate_multiplier_total(
    stock: StockAnalysis,
    gex: GEXAnalysis,
    macro: MacroRegime,
    config: Config,
) -> tuple[float, dict[str, float]]:
    """Calculate total risk multiplier from 6 factors.

    Returns:
        (clamped M_total, dict of individual multipliers)
    """
    flow_threshold = config.tuning["multiplier_flow_threshold"]
    flow_value = config.tuning["multiplier_flow_value"]
    funda_threshold = config.tuning["multiplier_funda_threshold"]
    funda_value = config.tuning["multiplier_funda_value"]
    utility_threshold = config.tuning["multiplier_utility_threshold"]
    utility_max = config.tuning["multiplier_utility_max"]

    # M_flow: base + rvol_score > threshold
    flow_score = _BASE_SCORE + stock.flow.rvol_score
    m_flow = flow_value if flow_score > flow_threshold else 1.0

    # M_insider: directly from fundamental analysis
    m_insider = stock.fundamental.insider_multiplier

    # M_funda: base + funda_score < threshold → penalize
    funda_score = _BASE_SCORE + stock.fundamental.funda_score
    m_funda = funda_value if funda_score < funda_threshold else 1.0

    # M_gex: from GEX analysis
    m_gex = gex.gex_multiplier

    # M_vix: from macro regime
    m_vix = macro.vix_multiplier

    # M_utility: scaled bonus for high combined scores
    if stock.combined_score > utility_threshold:
        m_utility = min(utility_max,
                        1.0 + (stock.combined_score - utility_threshold) / 100)
    else:
        m_utility = 1.0

    # Total product, clamped to [0.25, 2.0]
    m_total = m_flow * m_insider * m_funda * m_gex * m_vix * m_utility
    m_total = max(0.25, min(2.0, m_total))

    multipliers = {
        "m_flow": m_flow,
        "m_insider": m_insider,
        "m_funda": m_funda,
        "m_gex": m_gex,
        "m_vix": m_vix,
        "m_utility": m_utility,
    }
    return m_total, multipliers


def _calculate_position(
    stock: StockAnalysis,
    gex: GEXAnalysis,
    macro: MacroRegime,
    config: Config,
    strategy_mode: StrategyMode,
    original_scores: dict[str, float] | None = None,
    fresh_tickers: set[str] | None = None,
    sector_map: dict[str, SectorScore] | None = None,
    mms_map: dict[str, MMSAnalysis] | None = None,
) -> PositionSizing | None:
    """Calculate position sizing for a single candidate.

    Returns None if ATR is zero or quantity would be zero.
    """
    atr = stock.technical.atr_14
    entry = stock.technical.price
    sl_mult = config.core["stop_loss_atr_multiple"]

    # Guard: cannot size without valid volatility data
    # Use "not (x > 0)" to catch NaN (NaN comparisons always return False)
    if not (atr > 0) or not (entry > 0):
        return None

    # Risk calculation
    account_equity = config.runtime["account_equity"]
    risk_pct = config.runtime["risk_per_trade_pct"]
    base_risk = account_equity * risk_pct / 100  # e.g., $500

    m_total, multipliers = _calculate_multiplier_total(stock, gex, macro, config)
    adjusted_risk = base_risk * m_total

    # Stop distance and quantity
    stop_distance = sl_mult * atr
    quantity = math.floor(adjusted_risk / stop_distance)

    # Fat finger protection: NaN/Inf/negative guards + quantity caps
    if math.isnan(quantity) or math.isinf(quantity) or quantity < 0:
        return None
    if math.isnan(entry) or math.isinf(entry) or entry <= 0:
        return None
    max_qty = config.runtime.get("max_order_quantity", 5000)
    quantity = min(quantity, max_qty)
    max_single = config.runtime.get("max_single_ticker_exposure", 20000)
    if entry > 0:
        max_value_qty = int(max_single / entry)
        quantity = min(quantity, max_value_qty)

    if quantity <= 0:
        return None

    # Stop loss
    if strategy_mode == StrategyMode.LONG:
        stop_loss = entry - stop_distance
    else:
        stop_loss = entry + stop_distance

    # Take Profit 1: use call_wall if valid, else ATR-based
    tp1_atr = config.core["tp1_atr_multiple"] * atr
    if strategy_mode == StrategyMode.LONG:
        if gex.call_wall > 0 and gex.call_wall > entry:
            tp1 = gex.call_wall
        else:
            tp1 = entry + tp1_atr
    else:
        if gex.put_wall > 0 and gex.put_wall < entry:
            tp1 = gex.put_wall
        else:
            tp1 = entry - tp1_atr

    # Take Profit 2: always ATR-based
    tp2_atr = config.core["tp2_atr_multiple"] * atr
    if strategy_mode == StrategyMode.LONG:
        tp2 = entry + tp2_atr
        # TP2 must be more favorable than TP1 for LONG (higher)
        if tp2 <= tp1:
            tp2 = tp1 + atr
    else:
        tp2 = entry - tp2_atr
        # TP2 must be more favorable than TP1 for SHORT (lower)
        if tp2 >= tp1:
            tp2 = tp1 - atr

    # Scale-out price
    scale_atr = config.core["scale_out_atr_multiple"] * atr
    if strategy_mode == StrategyMode.LONG:
        scale_out_price = entry + scale_atr
    else:
        scale_out_price = entry - scale_atr

    direction = "BUY" if strategy_mode == StrategyMode.LONG else "SELL_SHORT"

    # Freshness audit trail: original_score captured BEFORE freshness mutation
    _orig = original_scores or {}
    _fresh = fresh_tickers or set()
    original_score = _orig.get(stock.ticker, stock.combined_score)
    is_fresh = stock.ticker in _fresh

    # Sector context for monitoring CSVs
    _ss = (sector_map or {}).get(stock.sector)
    sector_etf = _ss.etf if _ss else ""
    sector_bmi = _ss.sector_bmi if _ss else None
    sector_regime = _ss.sector_bmi_regime.value if _ss else ""
    is_mean_reversion = (
        _ss is not None
        and _ss.classification == MomentumClassification.LAGGARD
        and _ss.sector_bmi_regime == SectorBMIRegime.OVERSOLD
    )

    # MMS context (BC15)
    _mms = (mms_map or {}).get(stock.ticker)
    mm_regime = _mms.mm_regime.value if _mms else ""
    unusualness_score = _mms.unusualness_score if _mms else 0.0

    return PositionSizing(
        ticker=stock.ticker,
        sector=stock.sector,
        direction=direction,
        entry_price=entry,
        quantity=quantity,
        stop_loss=round(stop_loss, 2),
        take_profit_1=round(tp1, 2),
        take_profit_2=round(tp2, 2),
        risk_usd=adjusted_risk,
        combined_score=stock.combined_score,
        gex_regime=gex.gex_regime.value,
        multiplier_total=m_total,
        m_flow=multipliers["m_flow"],
        m_insider=multipliers["m_insider"],
        m_funda=multipliers["m_funda"],
        m_gex=multipliers["m_gex"],
        m_vix=multipliers["m_vix"],
        m_utility=multipliers["m_utility"],
        scale_out_price=round(scale_out_price, 2),
        scale_out_pct=config.core["scale_out_pct"],
        is_fresh=is_fresh,
        original_score=original_score,
        sector_etf=sector_etf,
        sector_bmi=sector_bmi,
        sector_regime=sector_regime,
        is_mean_reversion=is_mean_reversion,
        shark_detected=stock.shark_detected,
        mm_regime=mm_regime,
        unusualness_score=unusualness_score,
    )


def _apply_position_limits(
    positions: list[PositionSizing],
    config: Config,
    logger: EventLogger,
) -> tuple[list[PositionSizing], dict[str, int]]:
    """Apply position limits in priority order.

    Positions are expected to be sorted by combined_score descending.
    Limits applied:
        1. max_positions — total portfolio limit
        2. max_positions_per_sector — sector diversification
        3. max_single_position_risk_pct — per-position risk cap
        4. max_gross_exposure — total $ exposure
        5. max_single_ticker_exposure — per-ticker $ exposure (reduce quantity)

    Returns:
        (accepted positions, counts of exclusions by reason)
    """
    max_positions = config.runtime["max_positions"]
    max_per_sector = config.tuning["max_positions_per_sector"]
    max_risk_pct = config.runtime["max_single_position_risk_pct"]
    max_gross = config.runtime["max_gross_exposure"]
    max_ticker = config.runtime["max_single_ticker_exposure"]
    account_equity = config.runtime["account_equity"]

    max_risk_usd = account_equity * max_risk_pct / 100

    accepted: list[PositionSizing] = []
    sector_counts: dict[str, int] = {}
    running_exposure = 0.0
    counts = {"sector": 0, "position": 0, "risk": 0, "exposure": 0}

    for pos in positions:
        # 1. Max positions
        if len(accepted) >= max_positions:
            counts["position"] += 1
            continue

        # 2. Sector diversification
        sector_count = sector_counts.get(pos.sector, 0)
        if sector_count >= max_per_sector:
            counts["sector"] += 1
            logger.log(EventType.TICKER_FILTERED, Severity.DEBUG, phase=6,
                       message=f"{pos.ticker} excluded: sector limit ({pos.sector})",
                       data={"ticker": pos.ticker, "reason": "sector_limit"})
            continue

        # 3. Single position risk cap
        if pos.risk_usd > max_risk_usd:
            counts["risk"] += 1
            logger.log(EventType.TICKER_FILTERED, Severity.DEBUG, phase=6,
                       message=f"{pos.ticker} excluded: risk ${pos.risk_usd:.0f} > cap ${max_risk_usd:.0f}",
                       data={"ticker": pos.ticker, "reason": "risk_limit"})
            continue

        # 4. Gross exposure check
        ticker_exposure = pos.quantity * pos.entry_price
        if running_exposure + ticker_exposure > max_gross:
            counts["exposure"] += 1
            logger.log(EventType.TICKER_FILTERED, Severity.DEBUG, phase=6,
                       message=f"[GLOBALGUARD] {pos.ticker} removed: gross exposure "
                               f"${running_exposure + ticker_exposure:.0f} > ${max_gross:.0f}",
                       data={"ticker": pos.ticker, "reason": "exposure_limit"})
            continue

        # 5. Single ticker exposure — reduce quantity if needed
        if ticker_exposure > max_ticker:
            reduced_qty = math.floor(max_ticker / pos.entry_price)
            if reduced_qty <= 0:
                counts["exposure"] += 1
                continue
            logger.log(EventType.TICKER_FILTERED, Severity.DEBUG, phase=6,
                       message=f"[GLOBALGUARD] {pos.ticker} reduced: exposure "
                               f"${ticker_exposure:.0f} > ${max_ticker:.0f}",
                       data={"ticker": pos.ticker, "reason": "ticker_exposure_reduced"})
            pos = dataclasses.replace(pos, quantity=reduced_qty)
            ticker_exposure = reduced_qty * pos.entry_price

        accepted.append(pos)
        sector_counts[pos.sector] = sector_count + 1
        running_exposure += ticker_exposure

    return accepted, counts


def _load_daily_counter(file_path: str) -> dict:
    """Load a daily counter from JSON state file.

    Format: {"date": "YYYY-MM-DD", "count": <number>}
    Resets to 0 if the date doesn't match today.
    """
    today = date.today().isoformat()
    try:
        with open(file_path) as f:
            data = json.load(f)
        if data.get("date") == today:
            return {"date": today, "count": data.get("count", 0)}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return {"date": today, "count": 0}


def _save_daily_counter(file_path: str, counter: dict) -> None:
    """Save a daily counter to JSON state file."""
    try:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(counter, f)
    except OSError:
        pass


def _replace_quantity(pos: PositionSizing, new_qty: int) -> PositionSizing:
    """Create a copy of PositionSizing with an updated quantity."""
    return dataclasses.replace(pos, quantity=new_qty)
