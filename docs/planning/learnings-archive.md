# IFDS — Learnings Archive

CONDUCTOR `project.db`-ből exportálva 2026-02-26-án (migráció).
Operatív szabályok: `.claude/rules/ifds-rules.md`

---

## BC14 állapot (discovery, 2026-02-11)

BC10: scoring calibration, BC11: circuit breakers + robustness,
BC12: signal dedup + monitoring CSV + async phases,
BC13: survivorship bias, telegram alerts, daily trade limits, notional caps,
BC14: sector breadth analysis (7 regimes, divergence detection, FMP ETF holdings).
636 tests. Breadth adj isolated from ticker scores — crowding stable at 43.

## BC18-prep tanulságok (discovery, 2026-02-21)

Trading calendar: `pandas_market_calendars` opcionális, weekday-only fallback-kel.
Danger zone filter: bottom-10% performers kizárása universe-ből.
FileCache TTL broken volt — mindig stale adatot adott vissza.

## BC19 SIM-L2 Mode 1 (discovery, 2026-02-21)

Parameter sweep engine Phase 4 snapshot persistence-szel.
Paired t-test comparison (scipy). SimVariant config overrides: tuning dict patches-ként.
Phase 4 snapshots: `output/snapshots/YYYY-MM-DD.json`.

## BC18 scope döntés (discovery, 2026-02-21)

IBKR Connection Hardening (retry 3x, 5s/15s timeout, Telegram alert) → BC18-ba kerül.
BC25 Auto Execution bővítve long-running mode-dal.

## Paper Trading PnL tracking (discovery, 2026-02-21)

`cumulative_pnl.json` vs IBKR Realized PnL eltérés: nuke.py előző nap záróárral számol,
nem tényleges fill árral. OBSIDIAN aktiválás NEM dátumfüggő: store entry count >= 21/ticker.
