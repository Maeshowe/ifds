# BC23 Cleanup — 3 Bug Fix

**Status:** DONE
**Updated:** 2026-04-14
**Priority:** P2 — nem blokkoló, de idegesítő
**Effort:** ~1.5h CC

---

## Bug 1: nuke.py NameError (_log_path)

**Fájl:** scripts/paper_trading/nuke.py
**Fix:** _log_path változó definiálása a main() elején
**Teszt:** nuke.py --dry-run nem dob NameError-t

## Bug 2: FRED API HALT-olja a Phase 1-3-at

**Fájl:** src/ifds/data/fred.py vagy src/ifds/phases/phase0_diagnostics.py
**Fix:** FRED is_critical=False — pipeline ne HALT-oljon FRED nélkül (TNX Polygon fallback)
**Teszt:** test_pipeline_continues_without_fred

## Bug 3: LION/SDRL/DELL/DOCN phantom 22:00 után

**Fájl:** scripts/paper_trading/pt_monitor.py
**Fix:** Vizsgálat honnan jön a LION/SDRL state (nem a monitor_state fájlokból). Valószínű: ib.executions() cache vagy tp1_was_filled() dátumszűrés bug 22:00 UTC után.
**Teszt:** 22:00 utáni monitor ciklus → nincs LION/SDRL event

## Commit

fix(cleanup): nuke.py log_path, FRED optional, phantom investigation
