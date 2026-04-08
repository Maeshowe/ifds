# IFDS — Permanent Rules (CC mindig olvassa)

Ezek a szabályok a CONDUCTOR learnings-ből kerültek ide (2026-02-26 migráció).
Forrás: `.conductor/memory/project.db` — learnings tábla.

---

## IBKR Paper Account — Adaptive algo silent reject (rule, 2026-04-08)

Az IBKR paper account (DUH118657) csendben elutasítja az `algoStrategy='Adaptive'`
(vagy bármilyen algo) ordereket. **Nincs error, nincs log entry, nincs bejegyzés
az Orders tab-ban, és `ib.placeOrder()` normálisan tér vissza.** Ezért a submit
script tud "Submitted: 8 tickers"-t logolni, miközben 0 order van az IBKR-ben.

**Szabályok:**

1. Paper account entry order → `MarketOrder` (vagy `LimitOrder`) **algoStrategy NÉLKÜL**.
   SOHA ne használj `algoStrategy='Adaptive'`-t paper accounton.

2. Minden `ib.placeOrder()` után KÖTELEZŐ `ib.sleep(~1-2s)` + `trade.orderStatus.status`
   ellenőrzés. Valid státuszok:
   `{PreSubmitted, Submitted, Filled, PendingSubmit, PendingCancel}`.
   Bármi más (`Cancelled`, `Inactive`, `ApiCancelled` stb.) silent rejection
   → WARNING log az `orderRef` + teljes `trade.log` entries-szel.

3. Bracket submit után post-submit verification: `ib.openTrades()` cross-check
   a várt `orderRef` halmaz ellen. Hiányzó entry = silent reject.

**Referencia:** `72d5655` (status check), `788cf6d` (MarketOrder switch),
`tests/test_submit_bracket_status_check.py` (10 regression teszt),
`scripts/paper_trading/lib/orders.py::create_day_bracket` + `submit_bracket`.

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

---

## Cron env isolation — test fixture env var kontroll (rule, 2026-03-02)

A `deploy_daily.sh` `source .env`-vel betölti a prod env-et (`IFDS_ASYNC_ENABLED`, `IFDS_UW_API_KEY` stb.)
a pytest pre-flight ELŐTT. Minden test config fixture-nek KÖTELEZŐEN explicit kell kezelnie
az összes viselkedés-módosító env var-t:
1. Sync fixture-ökben: `monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")`
2. Async fixture-ökben: `monkeypatch.delenv("IFDS_UW_API_KEY", raising=False)` ha a teszt nem számít UW client-re

ÚJ fixture írásakor mindig ellenőrizd: milyen env var-ok változtatják meg a kódútat?

---

## CC session kontextus: journal + STATUS.md (rule, 2026-03-28)

`session-start.sh` (UserPromptSubmit hook) minden CC promptnál betölti:
1. `docs/journal/` utolsó 2 entry — narratív kontextus (mi történt)
2. `docs/STATUS.md` — aktuális projekt állapot (élő, mindig friss)

`CLAUDE.md` Aktuális Kontextus szekció stabil referencia (ritkán változik) —
NEM frissítjük `/wrap-up`-kor. `docs/STATUS.md` az egyetlen dinamikus állapotfájl.
`/wrap-up` → `docs/STATUS.md` in-place frissítés (nem új fájl, nem CLAUDE.md).

---

## Git push policy (rule, 2026-02-26)

CC commitol, Tamás pusholja. Push csak explicit jóváhagyással.
