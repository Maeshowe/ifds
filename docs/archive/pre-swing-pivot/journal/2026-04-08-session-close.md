# Session Close — 2026-04-08 (session 9)

## Összefoglaló
P0 root cause megtalálva: a silent "submit says 8, IBKR shows 0" bug oka az `algoStrategy='Adaptive'` a create_day_bracket entry orderen — IBKR paper account csendben elutasítja. Két rétegű fix: detekció (status check) + tényleges gyógyítás (MKT entry, nincs algo).

## Mit csináltunk
1. **Detekciós fix** — `lib/orders.py::submit_bracket`: `ib.sleep(1.5)` a placeOrder után, `trade.orderStatus.status` ellenőrzés minden ordere. Ha nem valid (nem PreSubmitted/Submitted/Filled/Pending*), WARNING log az `orderRef`, `status` és teljes IBKR log entries-szel.
2. **Post-submit verification** — `submit_orders.py`: a loop végén 3s wait, majd `ib.openTrades()` cross-check a `submitted_tickers` ellen. Hiányzó entry order esetén WARNING + `post_submit_missing_orders` event.
3. **Root cause fix** — `lib/orders.py::create_day_bracket`: entry `LimitOrder + algoStrategy='Adaptive'` → tiszta `MarketOrder`. A BC20A_3 scope eredetileg is MKT entry volt (roadmap + backlog + design doc), de a kód sosem lett frissítve. A paper account az Adaptive algót csendben eldobja — sem error, sem log, sem order az Orders tab-ban.
4. **+10 regression teszt** — test_submit_bracket_status_check.py: 5 status check scenario + 5 bracket shape teszt (MarketOrder, nincs algoStrategy/algoParams, nincs lmtPrice, TP/SL gyerekek változatlanok, SELL flip).

## Commit(ok)
- `72d5655` — fix(orders): detect silent IBKR rejections in submit_bracket
- `788cf6d` — fix(orders): switch entry to MarketOrder, remove Adaptive algo (BC20A_3)

## Tesztek
1304 passing (1294 → 1299 → 1304), 0 failure

## Következő lépés
- **Mac Mini `git pull` KÖTELEZŐ holnap 15:45 előtt** — ez az első futás amikor az orderek ténylegesen be fognak érkezni
- Holnapi log review: `POST-SUBMIT VERIFICATION: all N entry orders visible in IBKR openTrades` sort keresni a submit logban
- Ha ismét üres az Orders tab → a status check WARNING megmondja mi a baj (eddig semmi visszajelzés nem volt)

## Blokkolók
Nincs

## Tanulság
**IBKR paper account silent reject**: az Adaptive algoritmust csendben eldobja — sem error, sem log, sem order. A planning doc és az implementáció eltértek (BC20A_3 MKT scope vs LimitOrder+Adaptive kód). Minden ib.placeOrder() után KÖTELEZŐ a `trade.orderStatus.status` ellenőrzés — a silent rejection class of bug-ot másként nem lehet detektálni.
