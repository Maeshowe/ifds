# Session Close — 2026-04-15 (session 12)

## Összefoglaló
BC23 cleanup — 3 bug fix: nuke.py NameError, FRED is_critical=False (Polygon fallback), tp1_was_filled dátum post-filter (phantom LION/SDRL/DELL/DOCN). 1335 passing.

## Mit csináltunk
1. **Bug 1 — nuke.py `_log_path`**: Path definiálása main() elején (`Path("logs") / f"pt_nuke_{today}.log"`).
2. **Bug 2 — FRED HALT**: `FREDClient.check_health(is_critical=False)`. VIX-nek Polygon I:VIX primary source, TNX-nek Polygon ticker fallback, 2s10s shadow-only.
3. **Bug 3 — phantom 22:00 után**: `tp1_was_filled()` most `execution.time.date() == today` post-filter az IBKR stale cache ellen. LION/SDRL/DELL/DOCN fillek korábbi napokról már nem triggerelnek.
4. **+7 regression teszt** — test_bc23_cleanup.py. Autouse fixture `ensure_event_loop` az ib_insync import miatt.

## Commit(ok)
- `1bffb57` — fix(cleanup): nuke.py log_path, FRED optional, phantom date guard

## Tesztek
1335 passing (1328 + 7), 0 failure

## Következő lépés
- Mac Mini git pull (fent van a megoldás az ütközésre — `mv task-local.md`)
- Péntek ápr 17 piaczárás után: első `weekly_metrics.py` futtatás

## Blokkolók
Nincs

## Tanulság
**IBKR ExecutionFilter nem szigorú**: az `ExecutionFilter(time=...)` nem garantáltan szűri ki a régebbi executionöket. Ha stale végrehajtások jönnek ugyanazzal az orderRef-fel (pl. újra submit másnap), phantom fill detektálás lesz. Minden `reqExecutions` eredménynél `execution.time.date() == today` post-filter kell.
