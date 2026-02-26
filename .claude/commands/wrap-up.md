End the current CONDUCTOR session.

## Ha a user megadott summary-t a $ARGUMENTS-ben:
```bash
python -m conductor wrap-up --summary "$ARGUMENTS" --project-dir .
```

## Ha $ARGUMENTS üres:
NE kérdezd meg a user-t! Generáld magad az összefoglalót a session-ből:
- Mit csináltunk (feature-ök, fix-ek)
- Hány teszt fut (ha volt teszt futtatás)
- Commit hash (ha volt commit)
- Mi a következő lépés

Formátum: egy tömör, 1-2 mondatos összefoglaló. Példa:
"BC16 complete: Phase 1 async (282s→17s), factor volatility framework, SIM-L1 engine. 752 tests. Next: BC17 March 4."

Aztán futtasd:
```bash
python -m conductor wrap-up --summary "<generált összefoglaló>" --project-dir .
```

## Output feldolgozás
Parse the JSON output and present:
- **Session closed** — ID, duration
- **Summary** — amit mentettünk
- **Tasks snapshot** — open/done/blocked
- **Decisions snapshot** — active count

Ha nincs aktív session, jelezd a user-nek.
