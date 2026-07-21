"""FRL-1 loader tests — cross-section panel, era labelling, gaps, validation.

Covers the five mandatory FRL-0 gate consequences (gate report:
docs/tasks/2026-07-21-frl-scan-matrix-loader.md §Eredmény):
  1. tech_filter rows -> NaN score, never 0
  2. era column mandatory, pooled score factor forbidden
  3. JSONL is not a score validator in the swing era
  4. return matrix from grouped-daily bars
  5. (reported downstream) EWMA smoothing note
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import frl_config as cfg  # noqa: E402
import frl_cost  # noqa: E402
import frl_loader as loader  # noqa: E402
import frl_returns  # noqa: E402

_HEADER = (
    "Ticker,Status,Reason,Total_Score,Flow_Score,Funda_Score,Tech_Score,Strategy,"
    "Sector_ETF,Sector_BMI,Sector_Regime,Price,ATR,Sector_Name\n"
)


def _write_scan(dirpath: Path, day: str, rows: list[str]) -> None:
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / f"full_scan_matrix_{day}.csv").write_text(_HEADER + "".join(rows))


def _row(ticker: str, status: str, reason: str, score: float, sector: str = "Tech") -> str:
    return (
        f"{ticker},{status},{reason},{score},50,50,10,LONG,XLK,55.0,BULLISH,"
        f"100.0,2.5,{sector}\n"
    )


# ---------------------------------------------------------------------------
# 1. tech_filter -> NaN (the dp_pct structural-zero error class)
# ---------------------------------------------------------------------------


class TestTechFilterIsNaN:
    def test_tech_filter_rows_have_nan_score_not_zero(self, tmp_path):
        _write_scan(
            tmp_path,
            "2026-07-20",
            [
                _row("AAA", "ACCEPTED", "", 60.5),
                _row("BBB", "REJECTED", "swing_score", -12.3),
                _row("CCC", "REJECTED", "Tech Filter (Price < SMA200)", 0.0),
            ],
        )
        df = loader.load_cross_section(date(2026, 7, 20), scan_dir=tmp_path)

        ccc = df.loc[df.ticker == "CCC", "score"].iloc[0]
        assert pd.isna(ccc), "tech_filter row must be NaN, never a 0.0 factor value"
        assert df.loc[df.ticker == "BBB", "score"].iloc[0] == -12.3
        assert df["scored"].tolist() == [True, True, False]

    def test_zero_score_outside_tech_filter_is_kept_and_flagged(self, tmp_path):
        """A genuine 0.0 swing score is a real observation — keep it, but flag it."""
        _write_scan(
            tmp_path,
            "2026-07-20",
            [
                _row("AAA", "REJECTED", "swing_score", 0.0),
                _row("CCC", "REJECTED", "Tech Filter (Price < SMA200)", 0.0),
            ],
        )
        df = loader.load_cross_section(date(2026, 7, 20), scan_dir=tmp_path)
        assert df.loc[df.ticker == "AAA", "score"].iloc[0] == 0.0
        assert df.attrs["anomalies"]["zero_score_not_tech_filter"] == 1


# ---------------------------------------------------------------------------
# 2. Era labelling
# ---------------------------------------------------------------------------


class TestEraLabelling:
    @pytest.mark.parametrize(
        "day,expected",
        [
            (date(2026, 2, 11), cfg.ERA_LEGACY),
            (date(2026, 5, 15), cfg.ERA_LEGACY),
            (date(2026, 5, 16), None),
            (date(2026, 5, 18), cfg.ERA_SWING),
            (date(2026, 7, 20), cfg.ERA_SWING),
        ],
    )
    def test_era_boundaries(self, day, expected):
        assert cfg.era_of(day) == expected

    def test_era_column_present_on_both_sides(self, tmp_path):
        _write_scan(tmp_path, "2026-05-15", [_row("AAA", "ACCEPTED", "", 82.0)])
        _write_scan(tmp_path, "2026-05-18", [_row("AAA", "ACCEPTED", "", 61.42)])
        legacy = loader.load_cross_section(date(2026, 5, 15), scan_dir=tmp_path)
        swing = loader.load_cross_section(date(2026, 5, 18), scan_dir=tmp_path)
        assert legacy["era"].unique().tolist() == [cfg.ERA_LEGACY]
        assert swing["era"].unique().tolist() == [cfg.ERA_SWING]

    def test_pooled_score_factor_is_rejected(self, tmp_path):
        """Scale-incompatible eras must not be pooled on a score-derived factor (G5)."""
        _write_scan(tmp_path, "2026-05-15", [_row("AAA", "ACCEPTED", "", 82.0)])
        _write_scan(tmp_path, "2026-05-18", [_row("AAA", "ACCEPTED", "", 61.42)])
        panel = loader.load_panel(date(2026, 5, 15), date(2026, 5, 18), scan_dir=tmp_path)
        with pytest.raises(ValueError, match="pooled"):
            loader.require_single_era(panel.frame, factor_col="score")

    def test_single_era_passes_the_guard(self, tmp_path):
        _write_scan(tmp_path, "2026-05-18", [_row("AAA", "ACCEPTED", "", 61.42)])
        panel = loader.load_panel(date(2026, 5, 18), date(2026, 5, 18), scan_dir=tmp_path)
        loader.require_single_era(panel.frame, factor_col="score")  # must not raise


# ---------------------------------------------------------------------------
# 3. Panel gaps — missing, never interpolated
# ---------------------------------------------------------------------------


class TestPanelGaps:
    def test_missing_day_is_reported_not_interpolated(self, tmp_path):
        _write_scan(tmp_path, "2026-07-13", [_row("AAA", "ACCEPTED", "", 60.0)])
        _write_scan(tmp_path, "2026-07-15", [_row("AAA", "ACCEPTED", "", 62.0)])
        panel = loader.load_panel(date(2026, 7, 13), date(2026, 7, 15), scan_dir=tmp_path)

        assert panel.missing_days == [date(2026, 7, 14)]
        assert sorted(panel.frame["date"].unique()) == [date(2026, 7, 13), date(2026, 7, 15)]
        assert len(panel.frame) == 2  # no synthetic row for the gap day

    def test_weekend_and_holiday_are_not_missing_days(self, tmp_path):
        # 2026-07-17 Fri, 2026-07-20 Mon — the weekend must not count as a gap.
        _write_scan(tmp_path, "2026-07-17", [_row("AAA", "ACCEPTED", "", 60.0)])
        _write_scan(tmp_path, "2026-07-20", [_row("AAA", "ACCEPTED", "", 61.0)])
        panel = loader.load_panel(date(2026, 7, 17), date(2026, 7, 20), scan_dir=tmp_path)
        assert panel.missing_days == []

    def test_known_gap_is_flagged_separately(self, tmp_path):
        _write_scan(tmp_path, "2026-06-26", [_row("AAA", "ACCEPTED", "", 60.0)])
        _write_scan(tmp_path, "2026-07-07", [_row("AAA", "ACCEPTED", "", 60.0)])
        panel = loader.load_panel(date(2026, 6, 26), date(2026, 7, 7), scan_dir=tmp_path)
        assert panel.missing_days  # the outage days are missing
        assert all(cfg.is_known_gap(d) for d in panel.missing_days)
        assert panel.unexpected_missing == []


# ---------------------------------------------------------------------------
# 4. JSONL validator — era dependent (FRL-0 consequence #3)
# ---------------------------------------------------------------------------


class TestEventLogValidator:
    def _write_events(self, dirpath: Path, day: str, scored: dict[str, float]) -> None:
        dirpath.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(
                {
                    "event_type": "TICKER_SCORED",
                    "data": {"ticker": t, "combined_score": s},
                }
            )
            for t, s in scored.items()
        ]
        (dirpath / f"ifds_run_{day.replace('-', '')}_220000.jsonl").write_text(
            "\n".join(lines) + "\n"
        )

    def test_legacy_era_compares_scores(self, tmp_path):
        scan, logs = tmp_path / "out", tmp_path / "logs"
        _write_scan(scan, "2026-04-15", [_row("AAA", "ACCEPTED", "", 82.0)])
        self._write_events(logs, "2026-04-15", {"AAA": 82.0})
        rep = loader.validate_with_events(date(2026, 4, 15), scan_dir=scan, log_dir=logs)
        assert rep.score_comparable is True
        assert rep.score_mismatches == 0

    def test_legacy_era_detects_score_mismatch(self, tmp_path):
        scan, logs = tmp_path / "out", tmp_path / "logs"
        _write_scan(scan, "2026-04-15", [_row("AAA", "ACCEPTED", "", 82.0)])
        self._write_events(logs, "2026-04-15", {"AAA": 71.0})
        rep = loader.validate_with_events(date(2026, 4, 15), scan_dir=scan, log_dir=logs)
        assert rep.score_mismatches == 1

    def test_swing_era_never_compares_scores(self, tmp_path):
        """The JSONL logs the pre-rescore legacy composite — comparing would
        false-alarm on every swing day."""
        scan, logs = tmp_path / "out", tmp_path / "logs"
        _write_scan(scan, "2026-07-14", [_row("AAA", "ACCEPTED", "", -12.34)])
        self._write_events(logs, "2026-07-14", {"AAA": 88.0})
        rep = loader.validate_with_events(date(2026, 7, 14), scan_dir=scan, log_dir=logs)
        assert rep.score_comparable is False
        assert rep.score_mismatches == 0
        assert rep.ok is True

    def test_swing_era_flags_ticker_not_in_scan_matrix(self, tmp_path):
        scan, logs = tmp_path / "out", tmp_path / "logs"
        _write_scan(scan, "2026-07-14", [_row("AAA", "ACCEPTED", "", -12.34)])
        self._write_events(logs, "2026-07-14", {"AAA": 88.0, "ZZZ": 90.0})
        rep = loader.validate_with_events(date(2026, 7, 14), scan_dir=scan, log_dir=logs)
        assert rep.events_not_in_scan == ["ZZZ"]
        assert rep.ok is False


# ---------------------------------------------------------------------------
# 5. Forward return matrix
# ---------------------------------------------------------------------------


class TestForwardReturns:
    def test_forward_return_horizon_uses_trading_days(self):
        # 2026-07-13..17 Mon-Fri, 2026-07-20 Mon — h=1 from Friday crosses the weekend.
        closes = pd.DataFrame(
            {"AAA": [100.0, 110.0, 121.0]},
            index=[date(2026, 7, 17), date(2026, 7, 20), date(2026, 7, 21)],
        )
        fwd = frl_returns.forward_returns(closes, horizons=(1, 2))
        r1 = fwd[(fwd.date == date(2026, 7, 17)) & (fwd.ticker == "AAA")]["fwd_ret_1"].iloc[0]
        r2 = fwd[(fwd.date == date(2026, 7, 17)) & (fwd.ticker == "AAA")]["fwd_ret_2"].iloc[0]
        assert r1 == pytest.approx(0.10)
        assert r2 == pytest.approx(0.21)

    def test_tail_horizons_are_nan_not_dropped(self):
        closes = pd.DataFrame(
            {"AAA": [100.0, 110.0]},
            index=[date(2026, 7, 20), date(2026, 7, 21)],
        )
        fwd = frl_returns.forward_returns(closes, horizons=(1, 5))
        last = fwd[fwd.date == date(2026, 7, 21)].iloc[0]
        assert pd.isna(last["fwd_ret_1"])
        assert pd.isna(fwd[fwd.date == date(2026, 7, 20)].iloc[0]["fwd_ret_5"])

    def test_grouped_daily_rows_become_a_close_matrix(self):
        rows = {
            date(2026, 7, 20): [{"T": "AAA", "c": 10.0}, {"T": "BBB", "c": 20.0}],
            date(2026, 7, 21): [{"T": "AAA", "c": 11.0}],
        }
        closes = frl_returns.closes_from_grouped(rows, tickers=["AAA", "BBB"])
        assert closes.loc[date(2026, 7, 20), "BBB"] == 20.0
        assert pd.isna(closes.loc[date(2026, 7, 21), "BBB"])  # no bar -> NaN, not ffill


# ---------------------------------------------------------------------------
# 6. Cost model (spec §5.3, R1#3)
# ---------------------------------------------------------------------------


class TestCostModel:
    def _metrics(self, dirpath: Path, day: str, slips: dict[str, float]) -> None:
        dirpath.mkdir(parents=True, exist_ok=True)
        payload = {
            "date": day,
            "execution": {
                "slippage_per_ticker": {
                    t: {"planned": 100.0, "filled": 100.0 * (1 + p / 100), "slippage_pct": p,
                        "qty": 10}
                    for t, p in slips.items()
                }
            },
        }
        (dirpath / f"{day}.json").write_text(json.dumps(payload))

    def test_uses_absolute_slippage_median_and_p75(self, tmp_path):
        # Signed prints (+1.0 / -1.0) must not cancel out — |slippage| is the estimator.
        self._metrics(tmp_path, "2026-06-01", {"AAA": 1.0, "BBB": -1.0, "CCC": 0.5, "DDD": 2.0})
        model = frl_cost.build_cost_model(metrics_dir=tmp_path, era=cfg.ERA_SWING)
        assert model["n"] == 4
        assert model["median_bps_per_side"] == pytest.approx(100.0)  # |0.5,1,1,2| -> 1.0%
        assert model["p75_bps_per_side"] >= model["median_bps_per_side"]
        assert model["cost_bps_per_side"] == model["median_bps_per_side"]

    def test_small_sample_carries_a_warning(self, tmp_path):
        self._metrics(tmp_path, "2026-06-01", {"AAA": 1.0})
        model = frl_cost.build_cost_model(metrics_dir=tmp_path, era=cfg.ERA_SWING)
        assert model["small_n_warning"] is True

    def test_empty_sample_falls_back_to_75bp(self, tmp_path):
        model = frl_cost.build_cost_model(metrics_dir=tmp_path, era=cfg.ERA_SWING)
        assert model["n"] == 0
        assert model["cost_bps_per_side"] == cfg.FALLBACK_COST_BPS_PER_SIDE
        assert model["small_n_warning"] is True

    def test_era_filter_excludes_legacy_fills(self, tmp_path):
        self._metrics(tmp_path, "2026-04-20", {"OLD": 0.1})  # legacy LMT-era fill
        self._metrics(tmp_path, "2026-06-01", {"NEW": 1.0})
        model = frl_cost.build_cost_model(metrics_dir=tmp_path, era=cfg.ERA_SWING)
        assert model["n"] == 1
        assert model["median_bps_per_side"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# 7. Golden file — the real 2026-07-20 production scan matrix
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (cfg.SCAN_MATRIX_DIR / "full_scan_matrix_2026-07-20.csv").exists(),
    reason="production scan matrix not present in this checkout",
)
class TestGoldenProductionFile:
    def test_2026_07_20_shape_and_nan_policy(self):
        df = loader.load_cross_section(date(2026, 7, 20))
        assert len(df) == 433
        assert (df.status == "ACCEPTED").sum() == 7
        assert df["score"].isna().sum() == 176  # the tech_filter block
        assert df["scored"].sum() == 257
        assert df["era"].unique().tolist() == [cfg.ERA_SWING]
        scored = df[df.scored]
        assert (scored.score > 0).sum() == 115  # gate report figure
        assert (scored.score < 0).sum() == 142
