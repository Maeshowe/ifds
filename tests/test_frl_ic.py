"""FRL-2 IC engine tests — daily IC, Newey-West, era_bar, half-life, cost."""

from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import frl_config as cfg  # noqa: E402
import frl_ic  # noqa: E402


def _panel(
    n_days: int,
    n_per_sector: int = 6,
    sectors=("Tech", "Health"),
    sign: int = 1,
    noise: float = 0.0,
    start: date = date(2026, 5, 18),
) -> pd.DataFrame:
    """Synthetic panel where the forward return is ``sign`` * factor (+ noise)."""
    rows = []
    for d in range(n_days):
        day = start + timedelta(days=d)
        for sector in sectors:
            for i in range(n_per_sector):
                factor = float(i)
                wobble = noise * ((d * 7 + i * 13) % 11 - 5) / 5.0
                rows.append(
                    {
                        "date": day,
                        "ticker": f"{sector[:2]}{i}",
                        "sector": sector,
                        "factor": factor,
                        "fwd_ret_5": sign * factor * 0.01 + wobble,
                    }
                )
    return pd.DataFrame(rows)


class TestDailyIC:
    def test_perfect_positive_relation_gives_ic_one(self):
        ic = frl_ic.daily_ic(_panel(4), "factor", "fwd_ret_5")
        assert len(ic) == 4
        assert all(v == pytest.approx(1.0) for v in ic)

    def test_perfect_negative_relation_gives_ic_minus_one(self):
        ic = frl_ic.daily_ic(_panel(4, sign=-1), "factor", "fwd_ret_5")
        assert all(v == pytest.approx(-1.0) for v in ic)

    def test_no_relation_gives_ic_near_zero(self):
        rows = []
        for d in range(30):
            day = date(2026, 5, 18) + timedelta(days=d)
            for i in range(8):
                rows.append(
                    {
                        "date": day,
                        "ticker": f"T{i}",
                        "sector": "Tech",
                        "factor": float(i),
                        "fwd_ret_5": float((i * 7 + d * 3) % 8) / 100.0,
                    }
                )
        ic = frl_ic.daily_ic(pd.DataFrame(rows), "factor", "fwd_ret_5")
        assert abs(ic.mean()) < 0.35

    def test_sector_neutrality_removes_pure_sector_effect(self):
        """A factor that only separates sectors carries no within-sector signal."""
        rows = []
        for d in range(5):
            day = date(2026, 5, 18) + timedelta(days=d)
            for sector, level in (("Tech", 1.0), ("Health", 0.0)):
                for i in range(6):
                    rows.append(
                        {
                            "date": day,
                            "ticker": f"{sector}{i}",
                            "sector": sector,
                            "factor": level,  # constant inside each sector
                            "fwd_ret_5": level * 0.05,
                        }
                    )
        ic = frl_ic.daily_ic(pd.DataFrame(rows), "factor", "fwd_ret_5")
        assert ic.isna().all(), "constant within-sector factor must not score as IC=1"

    def test_thin_sector_is_dropped(self):
        panel = _panel(2)
        panel = pd.concat(
            [
                panel,
                pd.DataFrame(
                    [
                        {
                            "date": date(2026, 5, 18),
                            "ticker": "X1",
                            "sector": "Energy",
                            "factor": 99.0,
                            "fwd_ret_5": -0.5,
                        },
                        {
                            "date": date(2026, 5, 18),
                            "ticker": "X2",
                            "sector": "Energy",
                            "factor": 98.0,
                            "fwd_ret_5": -0.4,
                        },
                    ]
                ),
            ],
            ignore_index=True,
        )
        report = frl_ic.dropped_sector_report(panel, "factor", "fwd_ret_5")
        first = report[report.date == date(2026, 5, 18)].iloc[0]
        assert first["sectors_dropped"] == 1
        assert first["names_dropped"] == 2
        ic = frl_ic.daily_ic(panel, "factor", "fwd_ret_5")
        assert ic.loc[date(2026, 5, 18)] == pytest.approx(1.0)  # Energy excluded

    def test_missing_data_day_is_nan_not_zero(self):
        panel = _panel(2)
        panel.loc[panel.date == date(2026, 5, 19), "fwd_ret_5"] = float("nan")
        ic = frl_ic.daily_ic(panel, "factor", "fwd_ret_5")
        assert date(2026, 5, 19) not in ic.index or pd.isna(ic.loc[date(2026, 5, 19)])
        assert 0.0 not in set(ic.dropna())


class TestNeweyWest:
    def test_zero_lag_matches_plain_standard_error(self):
        values = [0.1, -0.2, 0.05, 0.3, -0.1, 0.2]
        se = frl_ic.newey_west_se(values, lag=0)
        s = pd.Series(values)
        naive = (s.std(ddof=0)) / math.sqrt(len(s))
        assert se == pytest.approx(naive)

    def test_positive_autocorrelation_widens_the_se(self):
        base = [0.1, 0.12, 0.11, 0.13, 0.1, 0.12, 0.11, 0.13, 0.12, 0.11]
        overlapping = [(base[i] + base[max(0, i - 1)]) / 2 for i in range(len(base))]
        naive = frl_ic.newey_west_se(overlapping, lag=0)
        hac = frl_ic.newey_west_se(overlapping, lag=4)
        assert hac > naive

    def test_short_series_returns_nan(self):
        assert math.isnan(frl_ic.newey_west_se([0.1], lag=4))

    def test_matches_statsmodels_hac(self):
        """Validate the in-house HAC against statsmodels (dev-only reference).

        statsmodels is deliberately NOT a project dependency (Day 63 freeze); the
        batch runs the in-house implementation. This test only guards it.
        """
        sm = pytest.importorskip("statsmodels.api")
        import numpy as np

        rng = np.random.default_rng(42)
        raw = rng.normal(size=60)
        series = [float(raw[i] + 0.7 * raw[i - 1]) for i in range(1, 60)]  # MA(1)

        ours = frl_ic.newey_west_se(series, lag=4)
        y = np.array(series)
        model = sm.OLS(y, np.ones_like(y)).fit(
            cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": False}
        )
        assert ours == pytest.approx(float(model.bse[0]), rel=1e-6)


class TestAggregate:
    def test_summary_fields_on_a_clean_series(self):
        ic = pd.Series([0.05] * 20, index=pd.Index(range(20), name="date"))
        summary = frl_ic.aggregate(ic, horizon=5, era=cfg.ERA_SWING)
        assert summary.n_days == 20
        assert summary.mean_ic == pytest.approx(0.05)
        assert summary.t_eff == pytest.approx(4.0)  # 20 days / h=5
        assert summary.nonoverlap_n == 4

    def test_empty_series_is_inconclusive_not_crash(self):
        summary = frl_ic.aggregate(pd.Series(dtype="float64"), horizon=5, era=cfg.ERA_SWING)
        assert summary.n_days == 0
        assert summary.inconclusive is True

    def test_weak_mean_below_bar_is_flagged_inconclusive(self):
        ic = pd.Series([0.01, -0.02, 0.03, 0.0, 0.01, -0.01, 0.02, 0.0])
        summary = frl_ic.aggregate(ic, horizon=5, era=cfg.ERA_SWING)
        assert summary.inconclusive is True


class TestEraBar:
    def test_bar_never_below_the_floor(self):
        ic = pd.Series([0.001] * 500)  # essentially zero variance -> tiny SE
        assert frl_ic.era_bar(ic, horizon=5) == pytest.approx(cfg.ERA_BAR_FLOOR)

    def test_small_sample_gives_a_higher_bar_than_large_sample(self):
        import numpy as np

        rng = np.random.default_rng(7)
        long_series = pd.Series(rng.normal(0.0, 0.08, 200))
        short_series = long_series.iloc[:20]
        assert frl_ic.era_bar(short_series, 5) > frl_ic.era_bar(long_series, 5)

    def test_bar_converges_toward_the_floor_as_sample_grows(self):
        import numpy as np

        rng = np.random.default_rng(11)
        huge = pd.Series(rng.normal(0.0, 0.05, 5000))
        assert frl_ic.era_bar(huge, 5) < 0.01 + cfg.ERA_BAR_FLOOR


class TestPersistenceAndCost:
    def test_constant_ranking_has_infinite_half_life(self):
        panel = _panel(6)
        assert frl_ic.half_life(panel, "factor") == float("inf")

    def test_shuffled_ranking_has_short_half_life(self):
        rows = []
        for d in range(10):
            day = date(2026, 5, 18) + timedelta(days=d)
            for i in range(8):
                rows.append(
                    {
                        "date": day,
                        "ticker": f"T{i}",
                        "sector": "Tech",
                        "factor": float((i * 5 + d * 3) % 8),
                    }
                )
        hl = frl_ic.half_life(pd.DataFrame(rows), "factor")
        assert hl < 10 or math.isnan(hl)

    def test_decay_diagnostic_scales_inversely_with_half_life(self):
        """The property still holds — but only for the DIAGNOSTIC figure.

        Renamed from implied_turnover_cost_bps on 2026-10-18: this number
        describes a counterfactual strategy that rebalances at the decay scale,
        and feeding it to costed_view is what produced the h/HL artefact.
        """
        fast = frl_ic.decay_implied_cost_bps(5.0, round_trip_cost_bps=95.5)
        slow = frl_ic.decay_implied_cost_bps(50.0, round_trip_cost_bps=95.5)
        assert fast > slow
        assert slow == pytest.approx(252 / 50 * 95.5)

    def test_uses_the_empirical_cost_not_a_3bp_assumption(self):
        import frl_cost

        model = frl_cost.load_cost_model()
        assert (
            frl_cost.round_trip_cost_bps(model) >= 20.0
        ), "3 bp-class cost inputs are forbidden for next-day MKT-open execution"


class TestCostedView:
    def test_gross_minus_cost_is_the_net(self):
        view = frl_ic.costed_view(mean_ic=0.05, sigma_cs=0.04, horizon=5, cost_annual_bps=1000.0)
        assert view.periods_per_year == pytest.approx(252 / 5)
        assert view.gross_annual_bps == pytest.approx(0.05 * 0.04 * (252 / 5) * 10_000)
        assert view.net_annual_bps == pytest.approx(view.gross_annual_bps - 1000.0)

    def test_breakeven_ic_is_the_ic_that_exactly_pays_the_cost(self):
        view = frl_ic.costed_view(0.05, 0.04, 5, cost_annual_bps=1000.0)
        at_breakeven = frl_ic.costed_view(view.breakeven_ic, 0.04, 5, 1000.0)
        assert at_breakeven.net_annual_bps == pytest.approx(0.0, abs=1e-6)

    def test_high_turnover_factor_fails_the_cost_gate(self):
        """The HYP-004 pre-registered (c) branch: gross pass, costed fail."""
        view = frl_ic.costed_view(0.09, 0.05, 5, cost_annual_bps=19_000.0)
        assert view.survives_cost is False
        assert view.breakeven_ic > abs(view.mean_ic)

    def test_sign_of_ic_does_not_change_the_gross_magnitude(self):
        positive = frl_ic.costed_view(0.05, 0.04, 5, 1000.0)
        negative = frl_ic.costed_view(-0.05, 0.04, 5, 1000.0)
        assert positive.gross_annual_bps == pytest.approx(negative.gross_annual_bps)

    def test_cross_sectional_sigma_is_the_mean_daily_dispersion(self):
        panel = pd.DataFrame(
            {
                "date": [date(2026, 6, 1)] * 3 + [date(2026, 6, 2)] * 3,
                "fwd_ret_5": [0.01, 0.02, 0.03, 0.10, 0.20, 0.30],
            }
        )
        sigma = frl_ic.cross_sectional_sigma(panel, "fwd_ret_5")
        expected = (
            pd.Series([0.01, 0.02, 0.03]).std(ddof=1) + pd.Series([0.10, 0.20, 0.30]).std(ddof=1)
        ) / 2
        assert sigma == pytest.approx(expected)

class TestAsTradedCost:
    """The cost the engine charges must describe the strategy that RAN.

    Domain error found 2026-10-18: cost was charged at the DECAY frequency
    (252/half_life) while alpha was credited at the REBALANCE frequency (252/h),
    so ``breakeven_ic`` scaled as h/HL and could be driven anywhere. Flow got 3.79
    (the formula charging 12.5 round trips inside a 5-day hold); Funda got 0.0017
    (h/HL = 0.006, the most degenerate cell in the table).

    The fix is a SIMPLIFICATION, not a new model. The system traded a FIXED hold
    with a MOC time stop: it re-formed the book every h days regardless of how
    persistent the factor was. Half-life is therefore not the right quantity for
    the realised cost, and it drops out entirely:

        cost_as_traded = (252/h) * 2c          -> one number, HL-free
        breakeven_ic   = 2c / (sigma_cs(h) * 1e4)

    An earlier proposed fix discounted cost by the un-traded fraction
    (1 - 2^(-h/HL)). Three independent derivations refuted it: the GROSS term
    already presumes the full book is re-formed every h days, so discounting only
    the cost manufactures a free lunch — the same error mirrored.

    Pre-reg source: FRL spec §5.3 (half-life is a REPORT field confronted with the
    empirical friction, never the rebalance frequency) + this module's own
    docstring ("one round trip per half-life (THE HORIZON ...)"), which only holds
    at h = HL. Task: docs/tasks/2026-10-18-breakeven-turnover-domain-fix.md
    """

    # The measured ROUND TRIP, not a per-side figure doubled. Since 2026-10-19
    # the two sides are measured separately (entry +40.3 against the open, exit
    # +23.2 against what the order type promised) and added — pre-reg D-C1.
    RT = 63.52

    def test_cost_is_set_by_the_rebalance_schedule_alone(self):
        assert frl_ic.as_traded_cost_bps(5, self.RT) == pytest.approx(252 / 5 * self.RT)

    def test_half_life_does_not_enter_the_as_traded_cost(self):
        """The signature property: a 0.4-day factor and an 800-day factor traded on
        the same fixed 5-day hold pay exactly the same, because the book is fully
        re-formed either way."""
        assert frl_ic.as_traded_cost_bps(5, self.RT) == frl_ic.as_traded_cost_bps(5, self.RT)
        # and the function simply has no half-life parameter to pass
        import inspect
        assert "half_life" not in inspect.signature(frl_ic.as_traded_cost_bps).parameters

    def test_a_longer_hold_costs_proportionally_less(self):
        assert frl_ic.as_traded_cost_bps(10, self.RT) == pytest.approx(
            frl_ic.as_traded_cost_bps(5, self.RT) / 2
        )

    @pytest.mark.parametrize("bad", [0, -5])
    def test_a_degenerate_horizon_yields_nan(self, bad):
        assert math.isnan(frl_ic.as_traded_cost_bps(bad, self.RT))

    def test_every_factor_shares_one_breakeven_at_a_given_horizon(self):
        """0.106 at h=5, round trip 63.5 bp, sigma=0.06 — for Flow, Tech,
        aggregate and Funda alike. The old 2200x spread between them was the h/HL
        artefact; the drop from 0.278 is the two-sided estimator (pre-reg D-C1)."""
        sigma, h = 0.06, 5
        be = frl_ic.costed_view(0.0, sigma, h, frl_ic.as_traded_cost_bps(h, self.RT)).breakeven_ic
        assert be == pytest.approx(self.RT / (sigma * 1e4), rel=1e-6)
        assert be == pytest.approx(0.1059, abs=0.002)

    def test_breakeven_is_linear_in_cost_and_falls_as_one_over_root_h(self):
        """The two real levers, correctly scaled: cost is LINEAR (the strong one),
        horizon only helps as 1/sqrt(h) because sigma_cs grows as sqrt(h)."""
        sigma5 = 0.06
        def be(h, c):
            s = sigma5 * math.sqrt(h / 5)
            return frl_ic.costed_view(0.0, s, h, frl_ic.as_traded_cost_bps(h, c)).breakeven_ic
        assert be(5, 2 * self.RT) == pytest.approx(2 * be(5, self.RT), rel=1e-6)
        assert be(20, self.RT) == pytest.approx(be(5, self.RT) / 2, rel=1e-6)

    def test_the_decay_figure_survives_as_a_labelled_diagnostic(self):
        """Spec §5.3 wants half-life reported ("Riport-mező"), so it stays — but as
        an explicitly counterfactual number, never as the gate input."""
        d = frl_ic.decay_implied_cost_bps(9.9, self.RT)
        assert d == pytest.approx(252 / 9.9 * self.RT, rel=1e-6)
        assert "counterfactual" in frl_ic.decay_implied_cost_bps.__doc__.lower()

    def test_the_decay_figure_cannot_reach_the_gate(self):
        """Guard against the artefact returning silently via a future refactor.

        Checked on SOURCE at both ends: costed_view must not take a half-life,
        and the batch must feed it the as-traded cost.
        """
        import inspect

        gate = inspect.getsource(frl_ic.costed_view)
        assert "half_life" not in gate, "costed_view must not see a half-life"

        # The batch may COMPUTE the decay figure (spec §5.3 wants it reported); what
        # it must never do is feed it to costed_view. Check the actual call arguments.
        import re

        batch = (Path(frl_ic.__file__).parent / "run_frl_batch.py").read_text()
        assert "as_traded_cost_bps" in batch, "the batch must use the as-traded cost"
        calls = re.findall(r"costed_view\((.*?)\)", batch, re.S)
        assert calls, "expected at least one costed_view call site to check"
        for args in calls:
            assert "decay" not in args, (
                f"the decay diagnostic reached a costed_view call: {args.strip()[:120]}"
            )
            assert "half_life" not in args, (
                f"a half-life reached a costed_view call: {args.strip()[:120]}"
            )
