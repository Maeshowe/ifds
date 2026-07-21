"""FRL-2 batch tests — sanity gate blocks attempts, report is deterministic."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import factors.base as fb  # noqa: E402
import frl_config as cfg  # noqa: E402
import frl_ledger as ledger  # noqa: E402
import frl_report as report  # noqa: E402
import run_frl_batch as batch  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_registry():
    fb.clear_registry()
    yield
    fb.clear_registry()


def _register(name: str, sign: int, compute) -> fb.Factor:
    return fb.register(
        fb.Factor(
            name=name,
            hyp_id="HYP-004",
            data_lane="v1",
            expected_sign=sign,
            compute=compute,
            sanity_panel=fb.linear_sanity_panel("score", sign=1),
            description=f"{name} test factor",
        )
    )


def _returns(days: list[date]) -> pd.DataFrame:
    """Synthetic forward returns — tests must never touch the cache or the API."""
    rows = []
    for day in days:
        for sector in ("Tech", "Health"):
            for i in range(6):
                rows.append(
                    {
                        "date": day,
                        "ticker": f"{sector[:2]}{i}",
                        **{f"fwd_ret_{h}": i * 0.001 * h for h in cfg.IC_HORIZONS},
                    }
                )
    return pd.DataFrame(rows)


_REGISTERED_HYP = """Status: REGISTERED
Updated: 2026-07-21
Data-lane: v1

# HYP-004 — teszt hipotézis

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

Likviditás-nyújtás kompenzációja.

## Várt előjel és horizont

NEGATÍV IC, h=5.

## Ki a vesztes oldal / milyen frikció tartja fenn

Flow-chaser kereslet.

## Költségprofil (várt turnover)

Magas turnover.

## Pre-reg metrika és kill-kritérium

Spearman IC h=5.
"""


def _registry(tmp_path: Path, status: str = "REGISTERED") -> Path:
    """A minimal hypothesis registry so the hypothesis-first gate lets us run."""
    directory = tmp_path / "hypotheses"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "HYP-004-test.md").write_text(
        _REGISTERED_HYP.replace("Status: REGISTERED", f"Status: {status}")
    )
    return directory


def _scan_files(scan_dir: Path, days: list[date]) -> None:
    header = (
        "Ticker,Status,Reason,Total_Score,Flow_Score,Funda_Score,Tech_Score,Strategy,"
        "Sector_ETF,Sector_BMI,Sector_Regime,Price,ATR,Sector_Name\n"
    )
    scan_dir.mkdir(parents=True, exist_ok=True)
    for day in days:
        rows = []
        for sector in ("Tech", "Health"):
            for i in range(6):
                rows.append(
                    f"{sector[:2]}{i},ACCEPTED,,{i * 5}.0,50,50,10,LONG,XLK,55.0,"
                    f"BULLISH,100.0,2.5,{sector}\n"
                )
        (scan_dir / f"full_scan_matrix_{day.isoformat()}.csv").write_text(header + "".join(rows))


class TestSanityGateBlocksAttempts:
    def test_failing_sanity_writes_no_ledger_row(self, tmp_path, monkeypatch):
        """R1#6: a bugged factor must not spend an attempt — or a holdout touch."""
        _register("flipped", 1, lambda panel: -panel["score"])

        scan_dir = tmp_path / "output"
        days = [date(2026, 5, 18) + timedelta(days=i) for i in range(3)]
        _scan_files(scan_dir, days)
        monkeypatch.setattr(cfg, "SCAN_MATRIX_DIR", scan_dir)
        monkeypatch.setattr("frl_loader.cfg.SCAN_MATRIX_DIR", scan_dir)

        ledger_path = tmp_path / "ledger.jsonl"
        text = batch.run_batch(
            run_date=date(2026, 7, 20),
            ledger_path=ledger_path,
            runs_dir=tmp_path / "runs",
            returns_frame=_returns(days),
            hypothesis_dir=_registry(tmp_path),
        )

        assert "SANITY_FAIL flipped" in text
        assert ledger.read_ledger(ledger_path) == [], "no attempt row for a failed sanity"

    def test_passing_factor_is_listed_as_pass(self, tmp_path, monkeypatch):
        _register("clean", 1, lambda panel: panel["score"])
        scan_dir = tmp_path / "output"
        _scan_files(scan_dir, [date(2026, 5, 18)])
        monkeypatch.setattr("frl_loader.cfg.SCAN_MATRIX_DIR", scan_dir)

        text = batch.run_batch(
            run_date=date(2026, 7, 20),
            ledger_path=tmp_path / "ledger.jsonl",
            runs_dir=tmp_path / "runs",
            returns_frame=_returns([date(2026, 5, 18)]),
            hypothesis_dir=_registry(tmp_path),
        )
        assert "PASS clean" in text

    def test_dry_run_writes_nothing(self, tmp_path, monkeypatch):
        _register("clean", 1, lambda panel: panel["score"])
        scan_dir = tmp_path / "output"
        _scan_files(scan_dir, [date(2026, 5, 18)])
        monkeypatch.setattr("frl_loader.cfg.SCAN_MATRIX_DIR", scan_dir)

        ledger_path = tmp_path / "ledger.jsonl"
        runs_dir = tmp_path / "runs"
        batch.run_batch(
            run_date=date(2026, 7, 20),
            dry_run=True,
            ledger_path=ledger_path,
            runs_dir=runs_dir,
            returns_frame=_returns([date(2026, 5, 18)]),
            hypothesis_dir=_registry(tmp_path),
        )
        assert not ledger_path.exists()
        assert not runs_dir.exists()

    def test_draft_hypothesis_blocks_the_attempt(self, tmp_path, monkeypatch):
        """Hypothesis-first: a factor whose hypothesis is still DRAFT never runs."""
        _register("clean", 1, lambda panel: panel["score"])
        scan_dir = tmp_path / "output"
        _scan_files(scan_dir, [date(2026, 5, 18)])
        monkeypatch.setattr("frl_loader.cfg.SCAN_MATRIX_DIR", scan_dir)

        ledger_path = tmp_path / "ledger.jsonl"
        text = batch.run_batch(
            run_date=date(2026, 7, 20),
            ledger_path=ledger_path,
            runs_dir=tmp_path / "runs",
            returns_frame=_returns([date(2026, 5, 18)]),
            hypothesis_dir=_registry(tmp_path, status="DRAFT"),
        )
        assert "BLOCKED clean" in text
        assert "PASS clean" in text, "sanity passed; only the registry gate blocked it"
        assert ledger.read_ledger(ledger_path) == []

    def test_missing_hypothesis_file_blocks_the_attempt(self, tmp_path, monkeypatch):
        _register("clean", 1, lambda panel: panel["score"])
        scan_dir = tmp_path / "output"
        _scan_files(scan_dir, [date(2026, 5, 18)])
        monkeypatch.setattr("frl_loader.cfg.SCAN_MATRIX_DIR", scan_dir)

        empty_registry = tmp_path / "empty"
        empty_registry.mkdir()
        ledger_path = tmp_path / "ledger.jsonl"
        text = batch.run_batch(
            run_date=date(2026, 7, 20),
            ledger_path=ledger_path,
            runs_dir=tmp_path / "runs",
            returns_frame=_returns([date(2026, 5, 18)]),
            hypothesis_dir=empty_registry,
        )
        assert "BLOCKED clean" in text
        assert ledger.read_ledger(ledger_path) == []

    def test_injected_returns_bypass_cache_and_api(self, tmp_path, monkeypatch):
        """Guard: a test run must never read the parquet cache or call Polygon."""
        _register("clean", 1, lambda panel: panel["score"])
        scan_dir = tmp_path / "output"
        _scan_files(scan_dir, [date(2026, 5, 18)])
        monkeypatch.setattr("frl_loader.cfg.SCAN_MATRIX_DIR", scan_dir)

        def _boom(*args, **kwargs):
            raise AssertionError("batch reached for cached/live returns despite injection")

        monkeypatch.setattr("frl_returns.load_cached_returns", _boom)
        monkeypatch.setattr(batch, "_polygon_client", _boom)

        batch.run_batch(
            run_date=date(2026, 7, 20),
            ledger_path=tmp_path / "ledger.jsonl",
            runs_dir=tmp_path / "runs",
            returns_frame=_returns([date(2026, 5, 18)]),
            hypothesis_dir=_registry(tmp_path),
        )


class TestReportRendering:
    def _ctx(self, **overrides) -> report.BatchContext:
        base = dict(
            run_date=date(2026, 7, 24),
            windows_line="dev 2026-05-18..2026-06-15 | purge ... | holdout ...",
            cost_model={
                "cost_bps_per_side": 95.5,
                "p75_bps_per_side": 137.0,
                "n": 28,
                "era": "swing",
                "small_n_warning": True,
                "fallback_used": False,
                "source": "state/daily_metrics/*.json::execution.slippage_per_ticker",
            },
            panel_days={"swing": 25, "legacy": 66},
            missing_days=[date(2026, 6, 29)],
            unexpected_missing=[],
            sanity_lines=["PASS reversal: ic=+0.980 expected_sign=+1"],
            results=[
                report.FactorResult(
                    factor="reversal",
                    hyp_id="HYP-004",
                    data_lane="v1",
                    expected_sign=-1,
                    horizon=5,
                    era_summaries={
                        "swing": {
                            "n_days": 25,
                            "t_eff": 5.0,
                            "mean_ic": -0.031,
                            "icir": -0.4,
                            "nw_t": -1.2,
                            "p_value": 0.28,
                            "era_bar": 0.06,
                            "inconclusive": True,
                        },
                    },
                    decision="KILL",
                    reasons=("swing era inconclusive",),
                    half_life_days=8.0,
                    implied_cost_bps=6017.0,
                    attempt_id="A-0001",
                )
            ],
            deflation_rows=[
                {
                    "hyp_id": "HYP-004",
                    "data_lane": "v1",
                    "era": "swing",
                    "n_variants": 4,
                    "p_family": 0.62,
                    "bh_pass": False,
                    "bonferroni_alpha": 0.1,
                    "bonferroni_pass": False,
                }
            ],
            holdout_congestion=0,
        )
        base.update(overrides)
        return report.BatchContext(**base)

    def test_mandatory_governance_header_is_present(self):
        text = report.build_report(self._ctx())
        assert report.HEADER_LINE in text
        assert "Day 63 gate-input NEM (G1/G3)" in text

    def test_report_is_deterministic(self):
        assert report.build_report(self._ctx()) == report.build_report(self._ctx())

    def test_inconclusive_is_stated_explicitly(self):
        assert "inconclusive" in report.build_report(self._ctx())

    def test_empirical_cost_is_shown_with_small_n_warning(self):
        text = report.build_report(self._ctx())
        assert "95.5 bp/oldal ⚠️ kis-n" in text
        assert "n=28" in text

    def test_unexpected_missing_days_are_escalated(self):
        text = report.build_report(self._ctx(unexpected_missing=[date(2026, 7, 2)]))
        assert "⚠️ nem dokumentált hiány" in text
        assert "2026-07-02" in text

    def test_holdout_congestion_governor_is_announced(self):
        text = report.build_report(self._ctx(holdout_congestion=3))
        assert "következő gördülésig vár" in text

    def test_ewma_caveat_is_carried_into_the_report(self):
        text = report.build_report(self._ctx(notes=("A swing score EWMA(5)-simított",)))
        assert "EWMA(5)-simított" in text

    def test_no_pooled_era_row_is_emitted(self):
        text = report.build_report(self._ctx())
        assert "| pooled |" not in text
