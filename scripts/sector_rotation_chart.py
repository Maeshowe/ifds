#!/usr/bin/env python3
"""Sector Rotation Chart — Relative Rotation Graph (RRG).

Standalone script that plots 11 GICS sector ETFs on a relative rotation
graph against VTI (total market) benchmark.

Usage:
    python scripts/sector_rotation_chart.py                   # default
    python scripts/sector_rotation_chart.py --trail 8         # longer trail
    python scripts/sector_rotation_chart.py --no-save         # display only
    python scripts/sector_rotation_chart.py --output rrg.png  # custom path
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# .env loader (validate_etf_holdings.py pattern)
# ---------------------------------------------------------------------------
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

from ifds.data.polygon import PolygonClient  # noqa: E402
from ifds.data.cache import FileCache  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SECTORS = [
    {"ticker": "XLE",  "name": "Energy",         "color": "#FF6B35"},
    {"ticker": "XLB",  "name": "Materials",       "color": "#A8DADC"},
    {"ticker": "XLI",  "name": "Industrials",     "color": "#6B9FD4"},
    {"ticker": "XLY",  "name": "Cons. Discr.",    "color": "#F4A261"},
    {"ticker": "XLP",  "name": "Cons. Staples",   "color": "#57CC99"},
    {"ticker": "XLV",  "name": "Health Care",     "color": "#E63946"},
    {"ticker": "XLF",  "name": "Financials",      "color": "#4CC9F0"},
    {"ticker": "XLK",  "name": "Technology",      "color": "#7B2FBE"},
    {"ticker": "XLC",  "name": "Comm. Services",  "color": "#F77F00"},
    {"ticker": "XLU",  "name": "Utilities",       "color": "#90E0EF"},
    {"ticker": "XLRE", "name": "Real Estate",     "color": "#FFBE0B"},
]
BENCHMARK = "VTI"
LOOKBACK = 13  # weeks for RS calculation
MIN_WEEKS_NEEDED = LOOKBACK + 1  # need at least lookback+1 for momentum


def fetch_weekly_closes(client: PolygonClient, ticker: str,
                        from_date: str, to_date: str) -> list[float]:
    """Fetch weekly closing prices for a ticker."""
    bars = client.get_aggregates(
        ticker, from_date=from_date, to_date=to_date,
        timespan="week", multiplier=1,
    )
    if not bars:
        print(f"  WARNING: No data for {ticker}")
        return []
    return [b["c"] for b in bars]


def compute_rs_series(sector_closes: list[float],
                      bench_closes: list[float],
                      lookback: int) -> tuple[list[float], list[float]]:
    """Compute RS-Ratio and RS-Momentum series.

    Returns (rs_ratio, rs_momentum) arrays aligned to the input length,
    with leading NaNs where calculation is not possible.
    """
    n = len(sector_closes)
    rs_ratio = [float("nan")] * n
    rs_momentum = [float("nan")] * n

    for i in range(lookback, n):
        bench_change = (bench_closes[i] - bench_closes[i - lookback]) / bench_closes[i - lookback]
        sector_change = (sector_closes[i] - sector_closes[i - lookback]) / sector_closes[i - lookback]
        rs_ratio[i] = (1 + sector_change) / (1 + bench_change) * 100

    for i in range(lookback + 1, n):
        if not np.isnan(rs_ratio[i]) and not np.isnan(rs_ratio[i - 1]) and rs_ratio[i - 1] != 0:
            rs_momentum[i] = (rs_ratio[i] / rs_ratio[i - 1]) * 100

    return rs_ratio, rs_momentum


def catmull_rom_chain(points: list[tuple[float, float]],
                      tension: float = 0.5,
                      n_seg: int = 12) -> tuple[list[float], list[float]]:
    """Generate a Catmull-Rom spline through a sequence of (x, y) points.

    tension=0.5 matches Chart.js default (0 = Catmull-Rom, 1 = straight).
    """
    if len(points) < 2:
        return [p[0] for p in points], [p[1] for p in points]

    xs, ys = [], []
    # Pad start/end by mirroring
    pts = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t_step in range(n_seg):
            t = t_step / n_seg
            t2 = t * t
            t3 = t2 * t
            s = (1 - tension) / 2
            # Catmull-Rom basis with tension
            x = (s * (-t3 + 2*t2 - t) * p0[0]
                 + (s * (-t3 + t2) + (2*t3 - 3*t2 + 1)) * p1[0]
                 + (s * (t3 - 2*t2 + t) + (-2*t3 + 3*t2)) * p2[0]
                 + s * (t3 - t2) * p3[0])
            y = (s * (-t3 + 2*t2 - t) * p0[1]
                 + (s * (-t3 + t2) + (2*t3 - 3*t2 + 1)) * p1[1]
                 + (s * (t3 - 2*t2 + t) + (-2*t3 + 3*t2)) * p2[1]
                 + s * (t3 - t2) * p3[1])
            xs.append(x)
            ys.append(y)
    # Add last point
    xs.append(points[-1][0])
    ys.append(points[-1][1])
    return xs, ys


def classify_quadrant(rs: float, mom: float) -> str:
    """Classify a point into one of the 4 RRG quadrants."""
    if rs >= 100 and mom >= 100:
        return "LEADING"
    elif rs >= 100 and mom < 100:
        return "WEAKENING"
    elif rs < 100 and mom < 100:
        return "LAGGING"
    else:
        return "IMPROVING"


def plot_rrg(sector_data: list[dict], trail: int, output_path: str | None,
             no_save: bool) -> None:
    """Plot the Relative Rotation Graph."""
    plt.style.use("dark_background")
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))

    # Determine axis limits
    all_rs = []
    all_mom = []
    for s in sector_data:
        all_rs.extend(s["rs_trail"])
        all_mom.extend(s["mom_trail"])
    if not all_rs:
        print("ERROR: No data to plot")
        return

    margin = 1.5
    rs_min = min(min(all_rs), 100) - margin
    rs_max = max(max(all_rs), 100) + margin
    mom_min = min(min(all_mom), 100) - margin
    mom_max = max(max(all_mom), 100) + margin

    # No quadrant fills — dark background only

    # Center lines (dashed)
    ax.axhline(y=100, color="gray", linestyle="--", linewidth=1.0, alpha=0.5)
    ax.axvline(x=100, color="gray", linestyle="--", linewidth=1.0, alpha=0.5)

    # Subtle grid
    ax.grid(True, color="#555", alpha=0.4, linewidth=0.5)
    ax.set_axisbelow(True)

    # Marker sizes: small fixed for prev dots, large for current (like TrendSpider)
    prev_size = 25
    curr_size = 120

    # Plot each sector
    legend_handles = []
    for s in sector_data:
        rs_t = s["rs_trail"]
        mom_t = s["mom_trail"]
        color = s["color"]
        n_pts = len(rs_t)

        # Trail line (smooth Catmull-Rom curve, tension=0.5 like Chart.js)
        if n_pts >= 3:
            pts = list(zip(rs_t, mom_t))
            sx, sy = catmull_rom_chain(pts, tension=0.5, n_seg=12)
            ax.plot(sx, sy, color=color, linewidth=1.5, alpha=0.8)
        else:
            ax.plot(rs_t, mom_t, color=color, linewidth=1.5, alpha=0.8)

        # Previous dots (small, uniform)
        if n_pts > 1:
            ax.scatter(rs_t[:-1], mom_t[:-1], color=color, s=prev_size,
                       alpha=0.7, zorder=3, edgecolors="none")

        # Current point (large)
        ax.scatter(rs_t[-1], mom_t[-1], color=color, s=curr_size, zorder=4,
                   edgecolors="white", linewidth=1.0)

        # Legend handle
        legend_handles.append(
            plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
                       markersize=9, label=s["ticker"])
        )

    # Legend at top
    ax.legend(handles=legend_handles, loc="upper center",
              bbox_to_anchor=(0.5, 1.10), ncol=len(sector_data),
              frameon=False, fontsize=10, handletextpad=0.3, columnspacing=1.2)

    # Quadrant labels in corners (matching TrendSpider colors)
    label_kw = dict(fontsize=13, fontweight="bold", fontstyle="italic", alpha=0.55)
    ax.text(rs_min + 0.4, mom_max - 0.3, "Improving", ha="left", va="top",
            color="#1E90FF", **label_kw)
    ax.text(rs_max - 0.4, mom_max - 0.3, "Leading", ha="right", va="top",
            color="#28A745", **label_kw)
    ax.text(rs_min + 0.4, mom_min + 0.3, "Lagging", ha="left", va="bottom",
            color="#DC3545", **label_kw)
    ax.text(rs_max - 0.4, mom_min + 0.3, "Weakening", ha="right", va="bottom",
            color="#FFC107", **label_kw)

    ax.set_xlim(rs_min, rs_max)
    ax.set_ylim(mom_min, mom_max)
    ax.set_xlabel("Relative Strength (%)", fontsize=12, color="#aaa")
    ax.set_ylabel("RS Momentum", fontsize=12, color="#aaa")
    ax.tick_params(labelsize=10, colors="#999")
    for spine in ax.spines.values():
        spine.set_color("#555")

    fig.subplots_adjust(top=0.88)

    if not no_save:
        out = output_path or f"output/sector_rotation_{date.today().strftime('%Y%m%d')}.png"
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"\nChart saved: {out}")

    if not no_save and output_path is None:
        plt.close(fig)
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sector Rotation Chart (RRG)")
    parser.add_argument("--trail", type=int, default=6, help="Trail length in weeks (default: 6)")
    parser.add_argument("--no-save", action="store_true", help="Display only, don't save PNG")
    parser.add_argument("--output", type=str, default=None, help="Custom output path")
    args = parser.parse_args()

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        print("ERROR: IFDS_POLYGON_API_KEY not set. Source .env first.")
        sys.exit(1)

    cache = FileCache("data/cache")
    client = PolygonClient(api_key=api_key, cache=cache)

    # Need lookback + trail + 1 weeks of data
    weeks_needed = LOOKBACK + args.trail + 2
    to_date = (date.today() - timedelta(days=1)).isoformat()
    from_date = (date.today() - timedelta(weeks=weeks_needed)).isoformat()

    print(f"Fetching weekly bars ({from_date} → {to_date})...")

    # Fetch benchmark
    bench_closes = fetch_weekly_closes(client, BENCHMARK, from_date, to_date)
    if not bench_closes:
        print("ERROR: Could not fetch benchmark (VTI) data")
        sys.exit(1)

    # Fetch sectors and compute RS
    sector_data = []
    quadrants: dict[str, list[str]] = {
        "LEADING": [], "IMPROVING": [], "WEAKENING": [], "LAGGING": [],
    }

    for s in SECTORS:
        closes = fetch_weekly_closes(client, s["ticker"], from_date, to_date)
        if not closes or len(closes) != len(bench_closes):
            print(f"  SKIP {s['ticker']}: length mismatch "
                  f"({len(closes) if closes else 0} vs {len(bench_closes)})")
            continue

        rs_ratio, rs_momentum = compute_rs_series(closes, bench_closes, LOOKBACK)

        # Extract trail (last N valid points)
        valid_pairs = [(r, m) for r, m in zip(rs_ratio, rs_momentum)
                       if not np.isnan(r) and not np.isnan(m)]

        if len(valid_pairs) < 2:
            print(f"  SKIP {s['ticker']}: not enough valid RS data")
            continue

        trail_pairs = valid_pairs[-args.trail:]
        rs_trail = [p[0] for p in trail_pairs]
        mom_trail = [p[1] for p in trail_pairs]

        quadrant = classify_quadrant(rs_trail[-1], mom_trail[-1])
        quadrants[quadrant].append(s["ticker"])

        sector_data.append({
            "ticker": s["ticker"],
            "name": s["name"],
            "color": s["color"],
            "rs_trail": rs_trail,
            "mom_trail": mom_trail,
            "quadrant": quadrant,
        })

    # Terminal summary
    print(f"\n=== Sector Rotation — {date.today().isoformat()} ===")
    for q in ["LEADING", "IMPROVING", "WEAKENING", "LAGGING"]:
        tickers = quadrants[q]
        print(f"{q:12s}: {', '.join(tickers) if tickers else '—'}")

    # Plot
    plot_rrg(sector_data, args.trail, args.output, args.no_save)


if __name__ == "__main__":
    main()
