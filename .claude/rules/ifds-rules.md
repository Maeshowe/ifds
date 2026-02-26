# IFDS — Permanent Rules (CC mindig olvassa)

Ezek a szabályok a CONDUCTOR learnings-ből kerültek ide (2026-02-26 migráció).
Forrás: `.conductor/memory/project.db` — learnings tábla.

---

## IBKR Paper Trading — ClientId collision (rule, 2026-02-21)

Minden script KÖTELEZŐEN egyedi clientId-t használ:
- submit_orders.py → clientId=10
- close_positions.py → clientId=11
- eod_report.py → clientId=12
- nuke.py → clientId=13

Ugyanaz a clientId session takeover-t okoz — az előző connection csendben ledobódik.
Mindig `ib.sleep(2-3)` kell connect után a pozíció/order szinkronhoz.

---

## Phase 6 Scoring — Freshness Alpha mutation guard (correction, 2026-02-09)

`phase6_sizing.py`: az `original_scores` dict-et BEFORE kell rögzíteni,
mielőtt a `_apply_freshness_alpha` mutálja a `combined_score`-t.
`fresh_tickers` típusa: `set[str]` (NEM `dict[str, float]`).
`_calculate_position` mindkét paramétert külön kapja: `original_scores` + `fresh_tickers`.

---

## Testing — AsyncMock warning (correction, 2026-02-21)

Ha sync kódút tesztelünk, ami NEM hívja az async függvényt:
`patch` hívásban `new=MagicMock()` — NEM `AsyncMock`.
AsyncMock nem-awaited coroutine-t hoz létre → RuntimeWarning.
scipy paired t-test azonos különbségekkel: precision loss → adj slight noise.

---

## FileCache TTL (correction, beépített BC18-prep)

A FileCache TTL check mindig frissnek mutatott stale adatot — proper expiry check kell.
Javítva BC18-prep-ben.
