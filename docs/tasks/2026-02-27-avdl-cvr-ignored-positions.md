# Task: AVDL.CVR kizárás az EOD position ellenőrzésből

**Dátum:** 2026-02-27  
**Prioritás:** 🟡 BC17 előtt  
**Fájl:** `scripts/paper_trading/eod_report.py`

---

## Probléma

Az IBKR paper account tartalmaz egy `AVDL.CVR` pozíciót (69 shares, Contingent Value Right),
amelyet paper accounton nem lehet manuálisan törölni. Ez minden este a következő warningot
generálja az EOD logban:

```
WARNING  Still 1 open positions!
WARNING    AVDL.CVR: 69.0 shares
```

Ez zaj — nem hiba, nem actionable. A CVR értéke nem befolyásolja a paper trading P&L mérést
(gross P&L számítása fill árakból történik), de a warning minden napra megjelenik.

---

## Fix

### 1. Konstans definiálása a config szekcióban (~sor 20)

```python
# Positions excluded from EOD clean-state check
# AVDL.CVR: Contingent Value Right — cannot be removed from IBKR paper account
IGNORED_POSITIONS = {"AVDL.CVR"}
```

### 2. Position ellenőrzés frissítése (~sor 300, `main()` függvény)

**Jelenlegi kód:**
```python
positions = [p for p in ib.positions() if p.position != 0]
if positions:
    logger.warning(f"Still {len(positions)} open positions!")
    for p in positions:
        logger.warning(f"  {p.contract.symbol}: {p.position} shares")
```

**Javított kód:**
```python
positions = [
    p for p in ib.positions()
    if p.position != 0 and p.contract.symbol not in IGNORED_POSITIONS
]
ignored = [
    p for p in ib.positions()
    if p.position != 0 and p.contract.symbol in IGNORED_POSITIONS
]
if ignored:
    logger.info(
        f"Ignored positions (known, non-removable): "
        + ", ".join(f"{p.contract.symbol} ({p.position})" for p in ignored)
    )
if positions:
    logger.warning(f"Still {len(positions)} open positions!")
    for p in positions:
        logger.warning(f"  {p.contract.symbol}: {p.position} shares")
```

---

## Viselkedés változás

| | Előtte | Utána |
|---|---|---|
| AVDL.CVR | `WARNING Still 1 open positions!` | `INFO Ignored positions (known, non-removable): AVDL.CVR (69.0)` |
| Valódi nyitott pozíció | `WARNING` | `WARNING` (változatlan) |
| P&L számítás | Nincs hatás | Nincs hatás |

---

## Tesztelés

```bash
# Dry-run — nem kapcsolódik IBKR-hez, CSV-ből olvas
python scripts/paper_trading/eod_report.py --dry-run
```

A dry-run nem teszteli a position logikát (nincs IBKR kapcsolat), ezért:
- Ellenőrizd hogy a konstans a megfelelő helyen van definiálva
- Ellenőrizd hogy a filter logika szintaktikailag helyes
- Következő éles futásnál (holnap 22:05) a logban `INFO Ignored...` kell megjelenjen, `WARNING` helyett

---

## Git commit

```
fix(eod_report): exclude AVDL.CVR from open position warning

AVDL.CVR (Contingent Value Right) cannot be removed from IBKR paper
account. Add IGNORED_POSITIONS constant and filter it from the
clean-state check. Logs as INFO instead of WARNING.
```
