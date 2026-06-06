#!/usr/bin/env python3
"""Daily-review generator — cross-check (1b) + markdown scaffold (1c).

Connector-INDEPENDENT core of the autonomous review pipeline:

  - ``build_cross_check_flags(review_data, ibkr)`` — the §3 P0 cross-check
    LOGIC as a pure function. The IBKR snapshot is INJECTED (the connector
    feeds it at runtime), so the logic is fully unit-testable offline. These
    are exactly the flags that would auto-catch the Day 13/Day 14 recorder
    incidents (realized P&L gap, state/IBKR divergence, cumulative drift).

  - ``render_review_markdown(review_data, cross_check_flags)`` — turns the 1a
    ``review_data.json`` + cross-check flags into a deterministic review
    markdown scaffold (the Chat §4 structure with the computed data filled in
    + ``<!-- LLM: ... -->`` placeholders for the narrative the 1c LLM layer
    completes).

The thin connector wrapper (fetch the IBKR snapshot live) is layered on
``main()`` separately and is deferred until the IBKR MCP is reachable again.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DATA_DIR = PROJECT_ROOT / "state" / "review_data"
REVIEW_OUT_DIR = PROJECT_ROOT / "docs" / "review"

INITIAL_CAPITAL = 100_000
# Pre-pivot cash carry: the IBKR paper account was reset to ~$100,208 (not
# $100,000.00 flat) at the 2026-05-18 swing pivot. cumulative_pnl.json reset to
# initial_capital=100000 + cumulative=0, but the live account retained ~$208.37
# of pre-pivot residual cash. Adding it to the implied baseline stops the
# cross-check false-flagging the known carry. Verified penny-level in
# docs/analysis/cumulative-drift-investigation-2026-06-08.md (Tamás: option A).
# Can be overridden per-snapshot via ibkr["baseline_offset"].
BASELINE_OFFSET_USD = 208.37
REALIZED_TOL = 1.0  # $ per-day realized gap tolerance
# Tolerance also absorbs slow-growing accrued credit interest (~$13 as of 6/8).
CUMULATIVE_DRIFT_TOL = 50.0  # $ cumulative-vs-NetLiq drift tolerance


# ---------------------------------------------------------------------------
# 1b — cross-check logic (pure; IBKR snapshot injected)
# ---------------------------------------------------------------------------


def build_cross_check_flags(review_data: dict, ibkr: dict) -> list[dict]:
    """Compare the 1a review_data against an IBKR snapshot → P0 flags.

    ``ibkr`` (all keys optional — a missing key skips its check):
      - ``realized_today``: broker realized P&L sum for the day
      - ``position_tickers``: iterable of current IBKR position symbols
      - ``net_liq``: account NetLiquidation
      - ``unrealized``: total unrealized P&L of open positions
      - ``baseline_offset``: pre-pivot cash carry (default BASELINE_OFFSET_USD)

    Returns a list of flag dicts (same shape as the 1a local flags).
    """
    flags: list[dict] = []
    pnl = review_data.get("pnl", {}) or {}

    # P&L tracking gap — recorded realized vs broker realized (Day 13/14 catcher)
    rec_realized = pnl.get("realized_today")
    ibkr_realized = ibkr.get("realized_today")
    if rec_realized is not None and ibkr_realized is not None:
        gap = round(float(rec_realized) - float(ibkr_realized), 2)
        if abs(gap) > REALIZED_TOL:
            flags.append(
                {
                    "flag": "pnl_tracking_gap",
                    "priority": "P0",
                    "detail": f"recorded realized ${rec_realized:+.2f} vs IBKR "
                    f"${float(ibkr_realized):+.2f} (gap ${gap:+.2f})",
                }
            )

    # State / IBKR position divergence
    ibkr_tickers = ibkr.get("position_tickers")
    if ibkr_tickers is not None:
        state_tickers = {
            p.get("ticker") for p in review_data.get("positions", {}).get("detail", [])
        }
        ibkr_set = set(ibkr_tickers)
        in_state_not_ibkr = sorted(state_tickers - ibkr_set)
        in_ibkr_not_state = sorted(ibkr_set - state_tickers)
        if in_state_not_ibkr or in_ibkr_not_state:
            flags.append(
                {
                    "flag": "state_ibkr_divergence",
                    "priority": "P0",
                    "detail": f"in_state_not_ibkr={in_state_not_ibkr} "
                    f"in_ibkr_not_state={in_ibkr_not_state}",
                }
            )

    # Cumulative drift — cumulative vs (NetLiq − initial − baseline_offset − unrealized)
    cum = pnl.get("cumulative")
    net_liq = ibkr.get("net_liq")
    unrealized = ibkr.get("unrealized")
    offset = float(ibkr.get("baseline_offset", BASELINE_OFFSET_USD))
    if cum is not None and net_liq is not None and unrealized is not None:
        implied = float(net_liq) - INITIAL_CAPITAL - offset - float(unrealized)
        drift = round(float(cum) - implied, 2)
        if abs(drift) > CUMULATIVE_DRIFT_TOL:
            flags.append(
                {
                    "flag": "cumulative_drift",
                    "priority": "P0",
                    "detail": f"cumulative ${float(cum):+.2f} vs implied ${implied:+.2f} "
                    f"(NetLiq−{INITIAL_CAPITAL}−offset${offset:.2f}−unrealized) "
                    f"→ drift ${drift:+.2f}",
                }
            )

    return flags


# ---------------------------------------------------------------------------
# 1c — deterministic markdown scaffold
# ---------------------------------------------------------------------------


def _fmt_usd(v) -> str:
    return f"${float(v):+,.2f}" if v is not None else "n/a"


def _priority_rank(p: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "positive": 9}.get(p, 5)


def render_review_markdown(review_data: dict, cross_check_flags: list[dict] | None = None) -> str:
    """Render the deterministic review markdown scaffold from review_data."""
    cross_check_flags = cross_check_flags or []
    all_flags = list(review_data.get("flags", [])) + list(cross_check_flags)
    all_flags.sort(key=lambda f: _priority_rank(f.get("priority", "")))

    date = review_data.get("date", "?")
    dn = review_data.get("day_number", {}) or {}
    nyse = dn.get("nyse_trading")
    pnl = review_data.get("pnl", {}) or {}
    pos = review_data.get("positions", {}) or {}
    exits = review_data.get("exits", {}) or {}

    p0 = [f for f in all_flags if f.get("priority") == "P0"]
    L: list[str] = []

    # --- Header ---
    L.append(f"# IFDS Daily Review — {date} (Day {nyse} Swing Pivot)")
    L.append("")
    L.append(
        f"**Realized today**: {_fmt_usd(pnl.get('realized_today'))} | "
        f"**Cumulative**: {_fmt_usd(pnl.get('cumulative'))} | "
        f"**Open positions**: {pos.get('open_count', 0)}"
    )
    if p0:
        L.append("")
        L.append(f"**⚠️ {len(p0)} P0 finding — lásd §0**")
    L.append("")
    L.append("<!-- LLM: 2-4 kulcs finding bullet (⭐/⚠️) a nap karakteréről -->")
    L.append("")

    # --- CHAT ESCALATION (always present; LLM fills strategic items) ---
    L.append("## ⚠️ CHAT ESCALATION")
    L.append(
        "<!-- LLM: stratégiai ítéletet igénylő finding-ok (több napos P&L-trend, "
        "scoring-minta gyanú, architektúra-javaslat). Ha nincs: 'Nincs stratégiai eszkaláció.' -->"
    )
    L.append("")

    # --- §0 Critical (P0 flags) ---
    if p0:
        L.append("## 0. Kritikus finding (P0)")
        for f in p0:
            who = f.get("ticker") or f.get("sector") or ""
            L.append(f"- **{f['flag']}** {who}: {f.get('detail', '')}")
        L.append("<!-- LLM: P0 ok-elemzés + javasolt akció -->")
        L.append("")

    # --- §1 Trades ---
    L.append("## 1. Trades")
    L.append(
        f"Exits: TP1={exits.get('tp1', 0)} TP2={exits.get('tp2', 0)} "
        f"SL={exits.get('sl', 0)} TRAIL={exits.get('trail', 0)} "
        f"LOSS={exits.get('loss_exit', 0)} MOC={exits.get('moc', 0)}"
    )
    new_e = pos.get("new_entries", [])
    L.append(f"Új entry: {', '.join(new_e) if new_e else 'nincs'}")
    L.append("<!-- LLM: trade-narratíva (entry/exit indok, fill vs terv) -->")
    L.append("")

    # --- §2 EOD State ---
    L.append("## 2. EOD State + outlook")
    L.append("")
    L.append("| Ticker | Sektor | Entry | Qty | days_held (T) | ATR% | next_action |")
    L.append("|--------|--------|-------|-----|---------------|------|-------------|")
    for ep in pos.get("detail", []):
        atrp = f"{ep['atr_pct'] * 100:.1f}%" if ep.get("atr_pct") is not None else "n/a"
        L.append(
            f"| {ep.get('ticker')} | {ep.get('sector', '')} | "
            f"{ep.get('entry_price')} | {ep.get('qty_remaining')} | "
            f"{ep.get('days_held_trading')} | {atrp} | {ep.get('next_action', '')} |"
        )
    L.append("")
    sp = pos.get("sector_pct", {}) or {}
    if sp:
        L.append(
            "**Sektor %**: "
            + " | ".join(f"{k} {v:.1f}%" for k, v in sorted(sp.items(), key=lambda kv: -kv[1]))
        )
    L.append("<!-- LLM: pozíció-narratíva + következő nap outlook -->")
    L.append("")

    # --- §3 Pipeline Log Review ---
    L.append("## 3. Pipeline Log Review")
    L.append("<!-- LLM: pt_submit/close/monitor/reconcile/eod log kulcssorok -->")
    L.append("")

    # --- §4 UW Shadow ---
    uw = review_data.get("uw_shadow", {}) or {}
    L.append("## 4. UW Shadow Log")
    L.append(f"Logged: {uw.get('tickers_logged', 0)} ticker (shadow — nem dönt)")
    L.append("")

    # --- §5 Anomáliák (all flags grouped) ---
    L.append("## 5. Anomáliák / megfigyelések")
    if all_flags:
        for f in all_flags:
            who = f.get("ticker") or f.get("sector") or ""
            L.append(f"- [{f.get('priority')}] **{f['flag']}** {who}: {f.get('detail', '')}")
    else:
        L.append("- Nincs flag (tiszta nap).")
    L.append("")

    # --- §6 Outlook ---
    L.append("## 6. Következő nap outlook")
    nd_flagged = [ep for ep in pos.get("detail", []) if ep.get("next_action") not in (None, "HOLD")]
    if nd_flagged:
        for ep in nd_flagged:
            L.append(
                f"- {ep.get('ticker')}: {ep.get('next_action')} (days_held {ep.get('days_held_trading')})"
            )
    else:
        L.append("- Nincs exit-flag a következő napra.")
    L.append("<!-- LLM: várt exitek + új entry kilátás -->")
    L.append("")

    # --- §7 Files referenced ---
    L.append("## 7. Files referenced")
    L.append(f"- state/review_data/{date}.json (1a aggregátum)")
    L.append(
        "- scripts/paper_trading/logs/cumulative_pnl.json, state/daily_metrics/, "
        "state/swing_positions.json, logs/pt_*_{date}.log"
    )
    L.append("")

    # --- §8 Structural summary ---
    L.append("## 8. Strukturális finding-ek összefoglaló")
    L.append("<!-- LLM: 1-3 strukturális tanulság + a nap karaktere egy mondatban -->")
    L.append("")
    L.append("---")
    L.append(
        f"_Generated by generate_review.py (1c scaffold) from review_data {date}; "
        f"narrative to be completed by CC. Source: 1a aggregate + "
        f"{len(cross_check_flags)} IBKR cross-check flags._"
    )
    return "\n".join(L)


def main() -> None:
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("generate_review")

    parser = argparse.ArgumentParser(description="Daily-review scaffold generator (1c)")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--out", help="output path (default: docs/review/{date}-daily-review.draft.md)"
    )
    args = parser.parse_args()

    data_path = REVIEW_DATA_DIR / f"{args.date}.json"
    review_data = json.loads(data_path.read_text())
    # IBKR cross-check is injected by the connector layer; offline → empty.
    md = render_review_markdown(review_data, cross_check_flags=[])

    out_path = Path(args.out) if args.out else REVIEW_OUT_DIR / f"{args.date}-daily-review.draft.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    logger.info("review draft written: %s", out_path)


if __name__ == "__main__":
    main()
