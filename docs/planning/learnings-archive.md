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

## AVWAP fallback MKT opció (idea, 2026-03-24)

NOG + EFXT unfill eset (Day 27): limit nem teljesült, AVWAP dip+cross sem triggerelt (ár végig AVWAP felett).
2/4 ticker maradt WATCHING → 0 fill. **Potenciális javítás:** ha az AVWAP window végéig (11:30 ET)
nem volt dip+cross, fallback MKT conversion. Kockázat: rosszabb entry-k, ha az ár az AVWAP felett
van de nem igazán erős. Döntés: egyelőre hagyjuk, 30+ nap adat kell a fill rate statisztikához.
Ha a fill rate tartósan <60%, érdemes bekapcsolni.

## STATUS.md — egyetlen igazságforrás Chat/CC/Cowork szinkronhoz (decision, 2026-03-28)

Chat, CC, és Cowork (claude.ai Projects) egyetlen fájlból olvassa a projekt
aktuális állapotát: `docs/STATUS.md`. Chat frissíti session végén (in-place),
CC frissíti `/wrap-up`-kor, Cowork csatolja egyszer.
Motivation: `development-backlog-YYYY-MM-DD.md` pattern stale snapshot-okat
halmozott fel; `CLAUDE.md` Aktuális Kontextus CC írta de Chat döntések nem
jelentek meg benne azonnal.
`CLAUDE.md` ettől stabil referencia marad (ritkán változik) — nem frissítjük
minden session végén.
