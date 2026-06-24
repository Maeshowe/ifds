# Kickoff — next IFDS session

Folytatás a 2026-06-24 handoff után (`docs/handoff/2026-06-24-session-close-handoff.md`).

**Állapot:** UW-GEX flip végrehajtva (Polygon-only GEX él a Mini-n), UW = nulla
döntési hatás, a közös UW-sub 07-04-én meghal és az IFDS bizonyítottan biztonságos
ellene. Freeze Day 63-ig. 1969 passing.

**Az EGYETLEN nyitott IFDS-tétel — flip post-verify:**
A 06-24 14:30 CEST intraday run UTÁN, a Mini-n:
1. `grep -c "greek-exposure" logs/cron_intraday_20260624_*.log` → 0 (UW már nem hívódik)
2. `.venv/bin/python scripts/analysis/gex_live_onoff_diff.py` → VERDICT: PASS
3. Phase 5 normál ticker-szám, M_gex=1.0, regime+exclusion az invariáns baseline-nal egyező
→ majd **04-risks §11.6 flip-lezárás** ("flip executed + post-verified 06-24").

**07-04 előtt (Tamás, kódmunka nélkül):** `IFDS_UW_API_KEY` eltávolítása a Mini prod
`.env`-ből → tiszta zárás (a dead-UW health-check zaj megszűnik). Lásd a de-scope dok
"07-04 deadline" szekcióját. Nem kötelező (graceful), de a tiszta lépés.

**Következő CC-munka (freeze-safe):** `signal_attribution` data-loader wiring — a spec
§6.1-ben pinned a 3 invariáns. Day-63 előkészítés.

**Kontextus:** a héten drawdown (cumulative 1716 → 555); a napi review-k tárgya, nem
a flip-ügy. MID UW-decommission = MID CC dolga, nincs IFDS-teendő.
