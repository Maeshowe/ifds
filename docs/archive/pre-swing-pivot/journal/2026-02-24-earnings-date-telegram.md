# 2026-02-24 — Earnings Date Column in Telegram Report

**Session:** 2026-02-24, ~08:49–09:45 CET  
**Participants:** Chat (analysis, task design) + CC (implementation)

---

## Kiváltó ok

A 2026-02-23-i pipeline KEP (Korea Electric Power ADR) pozíciót generált, annak ellenére, hogy a részvény 2026-02-24-én (másnap) earnings reportot tett közzé (Bloomberg és Apple Stocks szerint). A Zombie Hunter 7 napos ablakon belül kellett volna kiszűrje — de nem tette.

**Diagnózis:**

A Zombie Hunter a `/stable/earnings-calendar` bulk FMP endpointot használja dátum-range alapon. Ez az endpoint KEP-re `2026-03-10`-et tárolt következő earnings dátumként — míg a valós dátum `2026-02-26` volt (Bloomberg/Apple Stocks). A ticker-specifikus `/stable/earnings?symbol=KEP` endpoint szintén `2026-03-10`-et mutat, tehát az FMP adatminőségi problémája, nem kód bug.

A Zombie Hunter logikája és a 7 napos ablak **helyes volt** — rossz inputot kapott.

---

## Megoldás

Azonnali observability fix: az FMP earnings dátum megjelenítése a Telegram napi reportban minden pozícióhoz. Így manuálisan azonnal látható ha az FMP dátum gyanúsnak tűnik (pl. túl messze van, vagy ADR esetén eltér más forrásoktól).

**Nem változtatja** a Zombie Hunter szűrési logikáját — ez BC18 scope.

---

## Implementáció (CC)

**4 fájl módosítva, 1 új tesztfájl:**

### `src/ifds/data/fmp.py`
- Új metódus: `get_next_earnings_date(ticker: str) -> str | None`
- Endpoint: `/stable/earnings?symbol={ticker}` (ticker-specifikus, nem bulk)
- Logika: legkorábbi jövőbeli dátum ahol `epsActual is None` (prioritás), fallback: bármelyik jövőbeli
- Nincs cache — report generáláskor frissen hívva (max 8 extra hívás)

### `src/ifds/output/telegram.py`
- `_format_exec_table(positions, earnings_map=None)`: opcionális `earnings_map` dict, `EARN` oszlop `MM-DD` formátumban (vagy `N/A`)
- `_format_phases_5_to_6(ctx, config, fmp=None)`: per-ticker earnings lekérdezés, exception-safe
- `_format_success(ctx, duration, config, fmp=None)`: `fmp` paraméter átadása
- `send_daily_report(ctx, config, logger, duration, fmp=None)`: `fmp` paraméter

### `src/ifds/pipeline/runner.py`
- `send_daily_report()` hívásban új `FMPTelegram` client (a korábbi FMP instance-ok ekkorra már zárva)
- `fmp=fmp_telegram` átadás

### `tests/test_earnings_telegram.py` (új)
- 16 teszt: FMP client, exec table, integration, passthrough
- 833 passed total, 0 failure

**Backward compatible:** `fmp=None` esetén régi viselkedés, EARN oszlop nem jelenik meg.

---

## Várható Telegram output holnaptól

```
TICKER   QTY    ENTRY     STOP      TP1      TP2   RISK$  EARN
GE         27 $ 343.22 $ 328.35 $ 363.04 $ 372.95 $  404  04-22
KEP       307 $  22.45 $  21.37 $  23.89 $  24.61 $  333  03-10  ← FMP dátum látható
SKM       194 $  31.17 $  29.11 $  35.00 $  35.30 $  401  03-XX
```

---

## Következő lépések (BC18 scope)

- Ha `EARN dátum <= Today + 7`: WARNING megjelenik a Telegram reportban (piros jelzés)
- Zombie Hunter átválthat ticker-specifikus `/stable/earnings` endpointra a bulk calendar helyett — megbízhatóbb ADR-ekre
- Másodlagos earnings forrás cross-check (Polygon events API) — ha a két forrás eltér, WARNING

---

## Tesztelés (holnap este)

KEP-nél `03-10` jelenik meg → megerősíti az FMP adathiba diagnózist. Ha más ticker is gyanús dátumot mutat, BC18-ban javítjuk a Zombie Hunter input forrását.
