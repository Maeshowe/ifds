# QA Feedback — Circuit Breaker Design Decision

**Date:** 2026-02-26
**From:** Chat (Orchestrator)
**To:** QA Layer
**Re:** `2026-02-26-pipeline-output.md` Finding PT1 — Circuit breaker non-halt

---

## Visszajelzés

A PT1 finding helyes — a circuit breaker valóban nem haltol, és a CRITICAL besorolás indokolt.

**Az eredeti design döntés kontextusa:**

A "warn but continue" viselkedés szándékos volt a paper trading fázisban. Indok: ha reggel manuálisan futtatjuk a scriptet és pontosan tudjuk mi történt (pl. előző nap nagy veszteség), nem akarjuk hogy a script megakadályozza a futást visszajelzés nélkül.

**Elfogadott implementáció:**

A nyers `sys.exit(1)` helyett az `--override-circuit-breaker` flag megközelítés:

```python
if cb_alert and not args.override_cb:
    logger.error("Circuit breaker triggered. Use --override-circuit-breaker to proceed.")
    sys.exit(1)
```

Ez megőrzi a biztonságot (alapból haltol) miközben lehetővé teszi a tudatos manuális override-ot.

**CC task scope:** `submit_orders.py` — `--override-circuit-breaker` flag hozzáadása + `sys.exit(1)` ha flag nincs megadva.

---

## QA-nak: Következő audit validálja

- ☐ `submit_orders.py` circuit breaker `sys.exit(1)` OR `--override-circuit-breaker` implementálva
- ☐ Teszt: circuit breaker trigger → exit(1) flag nélkül
- ☐ Teszt: circuit breaker trigger → folytatódik `--override-circuit-breaker` flaggel
