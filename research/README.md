# `research/` — Factor Research Loop (FRL) state

**Why this is a new top-level directory.** `sync_from_mini.sh` mirrors
`data/ logs/ output/ state/ scripts/paper_trading/logs/ docs/analysis/` from the
Mini in **`--delete` mode**. Anything the FRL wrote into those trees would be
deleted by the next sync. `research/` is deliberately outside that set
(spec §4.3). The FRL runs on the **MacBook**; it never writes to the Mini.

## Layout

| Path | Git | Content |
|---|---|---|
| `attempt_ledger.jsonl` | tracked | append-only, one line per tested variant (spec §6). Every variant is written with `decision: PENDING` **before** the test runs (G4). |
| `cost_model.json` | tracked | empirical per-side cost, median/p75 of \|entry slippage\| (spec §5.3) |
| `runs/YYYY-MM-DD/` | tracked | weekly batch outputs — IC tables, report.md |
| `cache/` | **ignored** | Polygon return-matrix parquet; rebuildable from the API |

## Governance reminder

Every output here is **descriptive, forever** (G1). The Day 63/126 gate's only
input is `signal_attribution.py` (pinned `c5e9ed0`) — a positive FRL result is
just as inadmissible to the gate as a negative one. Reports carry the mandatory
header line: *"Leíró elemzés — Day 63 gate-input NEM (G1/G3)."*

Spec: `docs/design/2026-07-21-factor-research-loop-spec.md`
Tracker: `docs/design/frl/TRACKER.md`
