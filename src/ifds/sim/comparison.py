"""Statistical comparison between simulation variants.

Uses paired t-test on per-trade P&L to determine significance.
scipy is a mandatory dependency — no fallback.
"""

from scipy.stats import ttest_rel

from ifds.sim.models import ComparisonReport, SimVariant, VariantDelta

MIN_PAIRED_TRADES = 30  # Minimum for valid p-value


def compare_variants(variants: list[SimVariant]) -> ComparisonReport:
    """Compare first variant (baseline) against all others.

    Args:
        variants: List of SimVariant with trades/summary populated.
                  First element is baseline, rest are challengers.

    Returns:
        ComparisonReport with deltas and p-values.
    """
    if not variants:
        return ComparisonReport()

    baseline = variants[0]
    challengers = variants[1:]

    deltas = []
    for challenger in challengers:
        delta = _compute_delta(baseline, challenger)
        deltas.append(delta)

    return ComparisonReport(
        baseline=baseline,
        challengers=challengers,
        deltas=deltas,
    )


def _compute_delta(baseline: SimVariant, challenger: SimVariant) -> VariantDelta:
    """Compute delta metrics between baseline and challenger."""
    bs = baseline.summary
    cs = challenger.summary

    delta = VariantDelta(
        challenger_name=challenger.name,
        pnl_delta=cs.total_pnl - bs.total_pnl,
        win_rate_leg1_delta=cs.leg1_win_rate - bs.leg1_win_rate,
        win_rate_leg2_delta=cs.leg2_win_rate - bs.leg2_win_rate,
        avg_pnl_delta=cs.avg_pnl_per_trade - bs.avg_pnl_per_trade,
        avg_holding_days_delta=cs.avg_holding_days - bs.avg_holding_days,
        fill_rate_delta=cs.fill_rate - bs.fill_rate,
    )

    # Paired t-test on per-trade P&L
    baseline_pnls, challenger_pnls = _pair_trade_pnls(baseline, challenger)
    delta.paired_trade_count = len(baseline_pnls)

    if len(baseline_pnls) < MIN_PAIRED_TRADES:
        delta.insufficient_data = True
    else:
        try:
            _, p_value = ttest_rel(baseline_pnls, challenger_pnls)
            delta.p_value = round(p_value, 6)
            delta.is_significant = bool(p_value < 0.05)
        except Exception:
            delta.insufficient_data = True

    return delta


def _pair_trade_pnls(baseline: SimVariant,
                     challenger: SimVariant) -> tuple[list[float], list[float]]:
    """Extract paired P&L values (same ticker, same date).

    Only includes trades where both variants had a fill.
    """
    # Build lookup: (ticker, run_date) -> pnl for baseline
    baseline_map: dict[tuple[str, str], float] = {}
    for t in baseline.trades:
        if t.filled:
            key = (t.ticker, t.run_date.isoformat() if t.run_date else "")
            baseline_map[key] = t.total_pnl

    baseline_pnls = []
    challenger_pnls = []

    for t in challenger.trades:
        if t.filled:
            key = (t.ticker, t.run_date.isoformat() if t.run_date else "")
            if key in baseline_map:
                baseline_pnls.append(baseline_map[key])
                challenger_pnls.append(t.total_pnl)

    return baseline_pnls, challenger_pnls
