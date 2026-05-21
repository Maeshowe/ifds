# Post-Submit Stabilizáció — 3 Fix

**Status:** DONE
**Updated:** 2026-04-08
**Priority:** Medium
**Effort:** ~2h CC
**Context:** BC20A deploy után 3 nap instabilitás (ápr 6-8). Az alábbi fixek a MKT entry rendszer stabilizálásához kellenek.

---

## Fix 1: POST-SUBMIT verification false positive

**Probléma:** A `submit_orders.py` POST-SUBMIT VERIFICATION WARNING-ot dob, mert MKT orderek azonnal töltenek → eltűnnek az `openTrades()`-ből. A verification `openTrades()`-ben keresi az entry ordereket orderRef alapján, de a Filled orderek már nincsenek ott.

**Fix:** A verification nézze az `ib.positions()`-t is — ha a ticker megjelent a pozíciók között, az order sikeresen töltött. A WARNING csak akkor jöjjön, ha sem openTrades-ben, sem positions-ben nincs a ticker.

**Érintett fájl:** `scripts/paper_trading/submit_orders.py` — POST-SUBMIT VERIFICATION blokk

**Teszt:** Submit 1 MKT order → nincs WARNING ha fill sikeres.

---

## Fix 2: MKT fill > TP1 eset kezelése

**Probléma:** NSA entry fill $40.45, TP1 $40.00 → a TP1 azonnal triggerelt, az SL Cancelled lett. Ez normális bracket viselkedés, de:
- A monitor_state `tp1_filled: false` marad, mert a fill a submit pillanatában történik, nem a monitor ciklusban
- A monitor ezután phantomként szűri (nincs IBKR pozíció a Bracket A-ra)

**Fix:** A `submit_bracket` után ellenőrizni, hogy a TP gyerek order azonnal Filled lett-e. Ha igen, a monitor_state-be `tp1_filled: true` írása. Vagy: a monitor_state írás előtt `ib.fills()` ellenőrzés.

**Érintett fájlok:** `scripts/paper_trading/submit_orders.py` vagy `scripts/paper_trading/lib/orders.py`

**Teszt:** Mock entry fill > TP1 ár → monitor_state tp1_filled = true.

---

## Fix 3: Phantom filter log noise csökkentése

**Probléma:** A pt_monitor.py 5 percenként logol WARNING-ot minden phantom tickerre. Ápr 8-án 40+ azonos WARNING sor keletkezett. Ez elnyomja a valódi WARNING-okat.

**Fix:** Phantom filter WARNING csak az **első előforduláskor** az adott napon. Utána DEBUG szint. Implementáció: a state-ben `phantom_logged: set()` — ha a ticker már benne van, DEBUG-ra vált.

**Érintett fájl:** `scripts/paper_trading/pt_monitor.py` — phantom filter blokk

**Teszt:** Phantom ticker 2× ciklus → 1 WARNING + 1 DEBUG.

---

## Commit üzenet

```
fix(paper_trading): post-submit MKT stabilization (3 fixes)

1. POST-SUBMIT verification: check ib.positions() alongside openTrades()
   to avoid false WARNING on MKT orders that fill instantly
2. MKT fill > TP1: detect instant TP fill and update monitor_state
3. Phantom filter: log WARNING only once per ticker per day, then DEBUG

Context: BC20A MKT entry deploy caused 3 days of instability (Apr 6-8).
These fixes address the remaining rough edges after the Adaptive algo
removal (788cf6d) and context load fix (fa00a0e).
```
