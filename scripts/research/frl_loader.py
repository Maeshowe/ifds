"""FRL — cross-section loader (full_scan_matrix CSV + JSONL validation layer).

Read-only research tooling; touches no production path. Spec §4, and the FRL-0
gate report (``docs/tasks/2026-07-21-frl-scan-matrix-loader.md`` §Eredmény), whose
verified findings are encoded here:

* ``Total_Score`` is the canonical score column, era-dependent in meaning:
  legacy = legacy composite (0..108, .0/.5 grid), swing = EWMA(5)-smoothed
  ``S_j = 100*(PCR_pct - OTM_pct) + sector_adj`` (-125..+107, continuous).
* Rows rejected by the SMA200 tech filter were never scored — their 0.0 is a
  default, not a factor value. They load as **NaN**. On all four sampled days the
  zero-score set was exactly the tech-filter set; treating them as 0 would be the
  third occurrence of the dp_pct structural-zero error class.
* The JSONL ``TICKER_SCORED`` event logs the *pre-rescore legacy composite* on a
  biased subset, so score comparison is valid in the legacy era only.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

import frl_config as cfg

_TECH_FILTER_PREFIX = "Tech Filter"

_COLUMNS: dict[str, str] = {
    "Ticker": "ticker",
    "Status": "status",
    "Reason": "reason",
    "Total_Score": "score",
    "Flow_Score": "flow_score",
    "Funda_Score": "funda_score",
    "Tech_Score": "tech_score",
    "Sector_Name": "sector",
    "Sector_ETF": "sector_etf",
    "Price": "price",
    "ATR": "atr",
}

_NUMERIC = ("score", "flow_score", "funda_score", "tech_score", "price", "atr")


def scan_matrix_path(day: date, scan_dir: Path | None = None) -> Path:
    """Path of the daily scan matrix CSV for ``day``."""
    base = Path(scan_dir) if scan_dir is not None else cfg.SCAN_MATRIX_DIR
    return base / f"full_scan_matrix_{day.isoformat()}.csv"


def load_cross_section(day: date, scan_dir: Path | None = None) -> pd.DataFrame:
    """Load one day's scored cross-section.

    Returns a frame with a ``score`` column that is NaN wherever scoring never
    ran (tech-filter rejects), a boolean ``scored`` column, and an ``era`` label.
    ``frame.attrs["anomalies"]`` reports data-health counters for the batch report.

    Raises:
        FileNotFoundError: if the day's scan matrix is absent.
        ValueError: if the day falls outside both eras (spec §5.2 G5).
    """
    path = scan_matrix_path(day, scan_dir)
    if not path.exists():
        raise FileNotFoundError(f"scan matrix missing: {path}")

    era = cfg.era_of(day)
    if era is None:
        raise ValueError(f"{day} belongs to no FRL era (see frl_config.era_of)")

    raw = pd.read_csv(path)
    missing_cols = set(_COLUMNS) - set(raw.columns)
    if missing_cols:
        raise ValueError(f"{path.name}: missing columns {sorted(missing_cols)}")

    df = raw[list(_COLUMNS)].rename(columns=_COLUMNS).copy()
    df["reason"] = df["reason"].fillna("")
    for col in _NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    is_tech_filter = df["reason"].str.startswith(_TECH_FILTER_PREFIX)
    zero_elsewhere = int(((df["score"] == 0) & ~is_tech_filter).sum())
    tech_filter_nonzero = int(((df["score"] != 0) & is_tech_filter).sum())

    # The dp_pct-class guard: never let an unscored row enter the panel as 0.0.
    #
    # The condition is `score == 0`, NOT the Reason string. The scan writer
    # OVERWRITES Reason with "Sector VETO (...)" whenever the sector is vetoed
    # (execution_plan.py), which masks the real exclusion reason — 6179 legacy
    # rows are tech-filter drop-outs wearing a VETO label. A reason-based rule
    # would let every one of them into the panel as a 0.0 factor value.
    #
    # `score == 0` is safe as the unscored marker: across all 102 production days
    # no ACCEPTED row carries 0.0 and the smallest genuine |score| is 0.01, so an
    # exact zero is always the dataclass default of a ticker that never reached
    # scoring. A vetoed row that WAS scored keeps its value — the veto is a
    # portfolio decision, not a missing measurement.
    unscored = is_tech_filter | (df["score"] == 0)
    df.loc[unscored, "score"] = float("nan")
    df["scored"] = ~unscored
    df["era"] = era
    df["date"] = day
    df = df[
        [
            "date",
            "ticker",
            "sector",
            "sector_etf",
            "status",
            "reason",
            "score",
            "scored",
            "era",
            "flow_score",
            "funda_score",
            "tech_score",
            "price",
            "atr",
        ]
    ].reset_index(drop=True)

    df.attrs["anomalies"] = {
        # Unscored rows whose Reason does NOT say tech filter — almost always a
        # Sector VETO label masking the real reason. Reported, not hidden.
        "unscored_masked_by_reason": zero_elsewhere,
        "tech_filter_with_nonzero_score": tech_filter_nonzero,
    }
    return df


@dataclass(frozen=True)
class PanelResult:
    """Multi-day panel plus its coverage bookkeeping (gaps are never filled)."""

    frame: pd.DataFrame
    days: list[date]
    missing_days: list[date] = field(default_factory=list)
    unexpected_missing: list[date] = field(default_factory=list)
    anomalies: dict[str, int] = field(default_factory=dict)

    @property
    def coverage(self) -> float:
        total = len(self.days) + len(self.missing_days)
        return len(self.days) / total if total else 0.0


def load_panel(start: date, end: date, scan_dir: Path | None = None) -> PanelResult:
    """Load the cross-section panel for every NYSE trading day in [start, end].

    Missing days are reported, never interpolated (spec §4.5). Days inside a
    documented gap (Mini outage, power outage) are separated from unexpected
    ones, because only the latter warrant investigation.
    """
    from ifds.utils.trading_calendar import trading_days_between

    frames: list[pd.DataFrame] = []
    loaded: list[date] = []
    missing: list[date] = []
    anomalies: dict[str, int] = {}

    for day in trading_days_between(start, end):
        if cfg.era_of(day) is None:
            continue
        try:
            df = load_cross_section(day, scan_dir)
        except FileNotFoundError:
            missing.append(day)
            continue
        for key, value in df.attrs.get("anomalies", {}).items():
            anomalies[key] = anomalies.get(key, 0) + value
        frames.append(df)
        loaded.append(day)

    frame = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=["date", "ticker", "sector", "score", "scored", "era"])
    )
    unexpected = [d for d in missing if not cfg.is_known_gap(d)]
    return PanelResult(
        frame=frame,
        days=loaded,
        missing_days=missing,
        unexpected_missing=unexpected,
        anomalies=anomalies,
    )


def require_single_era(frame: pd.DataFrame, factor_col: str) -> str:
    """Guard against pooling score-derived factors across eras (spec §5.2 G5).

    The legacy composite (0..108, .0/.5 grid) and the swing S_j (-125..+107,
    continuous) are different quantities on incompatible scales; a pooled IC over
    both is meaningless. OHLCV-derived factors are era-agnostic and may bypass
    this guard.

    Raises:
        ValueError: if the frame spans more than one era.
    """
    eras = sorted(set(frame["era"].dropna().unique()))
    if len(eras) > 1:
        raise ValueError(
            f"factor '{factor_col}' cannot be pooled across eras {eras} — the score "
            "scales are incompatible (G5). Run the IC per era and report both."
        )
    return eras[0] if eras else ""


@dataclass(frozen=True)
class ValidationReport:
    """Result of cross-checking a scan matrix against the run's JSONL events."""

    day: date
    era: str
    n_scan: int
    n_events: int
    score_comparable: bool
    score_mismatches: int
    events_not_in_scan: list[str]

    @property
    def ok(self) -> bool:
        return not self.events_not_in_scan and self.score_mismatches == 0

    def summary(self) -> str:
        mode = "score+coverage" if self.score_comparable else "coverage-only (swing era)"
        return (
            f"{self.day} [{self.era}] {mode}: scan={self.n_scan} events={self.n_events} "
            f"mismatch={self.score_mismatches} orphan_events={len(self.events_not_in_scan)}"
        )


def _read_ticker_scored(day: date, log_dir: Path | None = None) -> dict[str, float | None]:
    base = Path(log_dir) if log_dir is not None else cfg.EVENT_LOG_DIR
    scored: dict[str, float | None] = {}
    for path in sorted(base.glob(f"ifds_run_{day:%Y%m%d}_*.jsonl")):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or "TICKER_SCORED" not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event_type") != "TICKER_SCORED":
                    continue
                data = event.get("data") or {}
                ticker = data.get("ticker")
                if ticker:
                    scored[ticker] = data.get("combined_score")
    return scored


def validate_with_events(
    day: date,
    scan_dir: Path | None = None,
    log_dir: Path | None = None,
) -> ValidationReport:
    """Cross-check the scan matrix against the run's TICKER_SCORED events.

    Era-dependent by necessity (FRL-0 finding): in the swing era the event logs
    the pre-rescore *legacy* composite on a biased subset, so only ticker
    coverage is checked. Comparing scores there would false-alarm every day.
    """
    df = load_cross_section(day, scan_dir)
    era = df["era"].iloc[0] if len(df) else cfg.era_of(day) or ""
    events = _read_ticker_scored(day, log_dir)

    scan_scores = dict(zip(df["ticker"], df["score"]))
    orphans = sorted(t for t in events if t not in scan_scores)

    comparable = era == cfg.ERA_LEGACY
    mismatches = 0
    if comparable:
        for ticker, value in events.items():
            expected = scan_scores.get(ticker)
            if expected is None or value is None or pd.isna(expected):
                continue
            if abs(float(value) - float(expected)) > 0.01:
                mismatches += 1

    return ValidationReport(
        day=day,
        era=era,
        n_scan=len(df),
        n_events=len(events),
        score_comparable=comparable,
        score_mismatches=mismatches,
        events_not_in_scan=orphans,
    )


def available_days(scan_dir: Path | None = None) -> list[date]:
    """Every date for which a scan matrix exists, ascending."""
    base = Path(scan_dir) if scan_dir is not None else cfg.SCAN_MATRIX_DIR
    days: list[date] = []
    for path in base.glob("full_scan_matrix_*.csv"):
        try:
            days.append(date.fromisoformat(path.stem.replace("full_scan_matrix_", "")))
        except ValueError:
            continue
    return sorted(days)


def write_panel_csv(panel: PanelResult, out_path: Path) -> Path:
    """Write a panel to CSV (diagnostics; the batch keeps parquet in cache)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.frame.to_csv(out_path, index=False, quoting=csv.QUOTE_MINIMAL)
    return out_path
