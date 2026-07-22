"""FRL — deterministic batch report rendering (spec §10).

Pure functions: same input, byte-identical output. No timestamps, no ordering
that depends on dict insertion — the report is golden-file testable, which is how
we keep every number in it sourceable from the batch output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

import frl_config as cfg

# G1/G3: the report may never be read as a gate input or a signal claim.
HEADER_LINE = "Leíró elemzés — Day 63 gate-input NEM (G1/G3)."


def _fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return "n/a"
    if math.isinf(number):
        return "∞" if number > 0 else "−∞"
    return f"{number:.{digits}f}"


@dataclass
class FactorResult:
    """One factor's per-era summaries and its decision."""

    factor: str
    hyp_id: str
    data_lane: str
    expected_sign: int
    horizon: int
    era_summaries: dict[str, dict]
    decision: str
    reasons: tuple[str, ...] = ()
    half_life_days: float = float("nan")
    implied_cost_bps: float = float("nan")
    attempt_id: str = ""
    costed: dict[str, dict] = field(default_factory=dict)  # era -> CostedView dict


@dataclass
class BatchContext:
    """Everything the report needs; assembled by the batch orchestrator."""

    run_date: date
    windows_line: str
    cost_model: dict
    panel_days: dict[str, int]
    missing_days: Sequence[date]
    unexpected_missing: Sequence[date]
    sanity_lines: Sequence[str]
    results: Sequence[FactorResult]
    deflation_rows: Sequence[dict]
    holdout_congestion: int
    parked_retests: Sequence[str] = field(default_factory=tuple)
    unconfirmed: Sequence[dict] = field(default_factory=tuple)
    anomalies: dict = field(default_factory=dict)
    notes: Sequence[str] = field(default_factory=tuple)


def _era_table(results: Sequence[FactorResult]) -> list[str]:
    lines = [
        "| Faktor | h | Éra | napok | T_eff | mean IC | ICIR | NW t | p | éra-bar | verdikt |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for result in sorted(results, key=lambda r: (r.factor, r.horizon)):
        for era in (cfg.ERA_LEGACY, cfg.ERA_SWING):
            summary = result.era_summaries.get(era)
            if not summary:
                continue
            verdict = "inconclusive" if summary.get("inconclusive") else "mérhető"
            lines.append(
                f"| `{result.factor}` | {result.horizon} | {era} | "
                f"{summary.get('n_days', 0)} | {_fmt(summary.get('t_eff'), 1)} | "
                f"{_fmt(summary.get('mean_ic'))} | {_fmt(summary.get('icir'), 2)} | "
                f"{_fmt(summary.get('nw_t'), 2)} | {_fmt(summary.get('p_value'), 3)} | "
                f"{_fmt(summary.get('era_bar'), 4)} | {verdict} |"
            )
    return lines


def _deflation_table(rows: Sequence[dict]) -> list[str]:
    lines = [
        "| Hipotézis | sáv | éra | variánsok | családi p (Šidák) | BH q=0.10 | Bonferroni |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in sorted(rows, key=lambda r: (r["hyp_id"], r["data_lane"], r["era"])):
        lines.append(
            f"| {row['hyp_id']} | {row['data_lane']} | {row['era']} | {row['n_variants']} | "
            f"{_fmt(row['p_family'], 4)} | {'PASS' if row['bh_pass'] else 'fail'} | "
            f"{'PASS' if row['bonferroni_pass'] else 'fail'} |"
        )
    return lines


def build_report(ctx: BatchContext) -> str:
    """Render the weekly batch report as markdown."""
    cost = ctx.cost_model
    cost_note = " ⚠️ kis-n" if cost.get("small_n_warning") else ""
    fallback_note = " (fallback)" if cost.get("fallback_used") else ""

    lines: list[str] = [
        f"# FRL batch — {ctx.run_date.isoformat()}",
        "",
        f"> **{HEADER_LINE}**",
        "",
        "## Ablakok",
        "",
        f"- {ctx.windows_line}",
        "- Panel: " + ", ".join(f"{era} {n} nap" for era, n in sorted(ctx.panel_days.items())),
        f"- Hiányzó nap: {len(ctx.missing_days)} "
        f"(nem várt: {len(ctx.unexpected_missing)}) — soha nem interpolált",
    ]
    if ctx.unexpected_missing:
        lines.append(
            "  - ⚠️ nem dokumentált hiány: "
            + ", ".join(d.isoformat() for d in ctx.unexpected_missing)
        )
    if ctx.anomalies:
        lines.append(
            "- Adat-anomáliák: " + ", ".join(f"{k}={v}" for k, v in sorted(ctx.anomalies.items()))
        )

    lines += [
        "",
        "## Költségmodell (empirikus)",
        "",
        f"- {_fmt(cost.get('cost_bps_per_side'), 1)} bp/oldal{cost_note}{fallback_note} "
        f"(medián), p75 {_fmt(cost.get('p75_bps_per_side'), 1)} bp, n={cost.get('n', 0)}, "
        f"éra={cost.get('era', '—')}",
        f"- Forrás: `{cost.get('source', '—')}`",
        "",
        "## Sanity-kapu",
        "",
    ]
    lines += [f"- {line}" for line in ctx.sanity_lines] or ["- (nincs faktor)"]

    lines += ["", "## IC — éra-bontásban (G5: pooled nézet nincs)", ""]
    lines += _era_table(ctx.results)

    lines += ["", "## Multiplicitás-defláció (a teljes ledger-történeten)", ""]
    lines += _deflation_table(ctx.deflation_rows)

    lines += [
        "",
        "## Perzisztencia és forgási költség",
        "",
        "| Faktor | half-life (nap) | implikált éves költség (bp) |",
        "|---|---|---|",
    ]
    for result in sorted({r.factor: r for r in ctx.results}.values(), key=lambda r: r.factor):
        lines.append(
            f"| `{result.factor}` | {_fmt(result.half_life_days, 1)} | "
            f"{_fmt(result.implied_cost_bps, 0)} |"
        )

    lines += [
        "",
        "## Bruttó vs költséggel terhelt IC (§5.3 cost-kapu)",
        "",
        "> Feltevés (az egyetlen): egy dollár-semleges, normalizált faktor-súlyú "
        "portfólió horizontonként ≈ `IC × σ_cs` hozamot termel (Grinold-közelítés). "
        "A per-oldal költség és a forgás **empirikus**.",
        "",
        "| Faktor | h | Éra | mean IC | σ_cs | bruttó bp/év | költség bp/év | **nettó bp/év** | breakeven IC |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for result in sorted(ctx.results, key=lambda r: (r.factor, r.horizon)):
        for era in (cfg.ERA_LEGACY, cfg.ERA_SWING):
            view = result.costed.get(era)
            if not view:
                continue
            net = view.get("net_annual_bps")
            mark = "" if (net is not None and net > 0) else " ❌"
            lines.append(
                f"| `{result.factor}` | {result.horizon} | {era} | "
                f"{_fmt(view.get('mean_ic'))} | {_fmt(view.get('sigma_cs'), 4)} | "
                f"{_fmt(view.get('gross_annual_bps'), 0)} | "
                f"{_fmt(view.get('cost_annual_bps'), 0)} | "
                f"**{_fmt(net, 0)}**{mark} | {_fmt(view.get('breakeven_ic'), 4)} |"
            )

    lines += [
        "",
        "## Döntések",
        "",
        "> A batch verdiktje **auto** (mechanikusan triggerelt pre-reg kritérium), "
        "`human_confirmed: false`-szal születik. A döntés Tamásé (spec §10) — "
        "a megerősítés vagy felülírás explicit művelet.",
        "",
    ]
    for result in sorted(ctx.results, key=lambda r: (r.factor, r.horizon)):
        reason = "; ".join(result.reasons) if result.reasons else "—"
        lines.append(
            f"- **{result.decision}** (auto) — `{result.factor}` h={result.horizon} "
            f"({result.hyp_id}, {result.data_lane}, attempt {result.attempt_id or '—'}): {reason}"
        )

    lines += ["", "### Megerősítésre váró döntések", ""]
    if ctx.unconfirmed:
        lines.append("| Attempt | Hipotézis | Variáns | Auto-verdikt | Zárva |")
        lines.append("|---|---|---|---|---|")
        for entry in sorted(ctx.unconfirmed, key=lambda e: e.get("attempt_id", "")):
            lines.append(
                f"| {entry.get('attempt_id', '?')} | {entry.get('hyp_id', '?')} | "
                f"`{entry.get('variant', '?')}` | {entry.get('decision', '?')} | "
                f"{entry.get('closed_at', '—')} |"
            )
        lines.append("")
        lines.append(
            f"**{len(ctx.unconfirmed)} döntés vár emberi megerősítésre.** "
            "Megerősítés: `frl_ledger.confirm_decision(attempt_id, by=..., note=...)`; "
            "felülírás: ugyanaz `decision=` paraméterrel (az auto-verdikt "
            "`auto_decision`-ként megmarad)."
        )
    else:
        lines.append("- Nincs megerősítésre váró döntés. ✅")

    lines += [
        "",
        "## Holdout",
        "",
        f"- Az aktuális holdout-ablakot eddig {ctx.holdout_congestion} hipotézis érintette"
        + (
            " — ≥3, a következő PROMOTE a következő gördülésig vár (§7)."
            if ctx.holdout_congestion >= 3
            else "."
        ),
    ]
    if ctx.parked_retests:
        lines.append("- Auto-retest esedékes: " + ", ".join(ctx.parked_retests))

    if ctx.notes:
        lines += ["", "## Megjegyzések", ""] + [f"- {n}" for n in ctx.notes]

    lines.append("")
    return "\n".join(lines)
