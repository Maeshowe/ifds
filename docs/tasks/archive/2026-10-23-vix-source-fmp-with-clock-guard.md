Status: DONE
Updated: 2026-10-23
Note: Implementálva 2026-10-23. Phase 0 + daily_metrics + a VIX-backfill script mind FMP ^VIX-re állítva, óra-guarddal (VIX_FINALITY_CUTOFF_ET=16:30). A guard visszavezetéssel verifikálva. ⚠️ MARADT két Polygon I:VIX hívóhely: pt_monitor.py:497 (trading-guarded, ma dormant) — RESTART-CHECKLIST tétel. Mellékhaszon: a backfill script most a 95 hibás historikus vix_close javítására is használható. +28 teszt.

# VIX — forrás FMP ^VIX-re, kötelező óra-guarddal

## 1. Probléma — nem a szolgáltató, az ÓRA

A `daily_metrics` 22:10 Budapestkor fut = **16:10 ET**, azaz **öt perccel a 16:15 ET-i
VIX-elszámolás ELŐTT**, az év ~50 hetében. A rögzített érték ezért nem a végleges zárás.

**Mérve a production adatokon (2026-04-29 … 2026-10-22, n=113):**

| | |
|---|---|
| egyezés a hivatalos CBOE zárással (FRED VIXCLS) | **18/113 = 15,9%** |
| átlagos hiba | +0,0074 |
| maximum abszolút hiba | **1,10** (2026-07-09: 16,94 rögzítve vs 15,84 hivatalos) |

Vagyis a $49/hó Indices sor nyolc hónapja egy nem-végleges értéket vesz fel.

## 2. Mit mér a három forrás — saját mérés, 2026-10-23

| dátum | Polygon I:VIX | FMP ^VIX | FRED VIXCLS |
|---|---:|---:|---:|
| 10-15 … 10-22 (6 lezárt nap) | **mind a három centre azonos** | | |
| 10-23 (élő, nem végleges) | 20,51 | **20,10** | — (még nincs) |

**Két következtetés:**

1. Lezárt napon a forrás **nem számít** — mindhárom a hivatalos CBOE zárást adja.
2. A **nem végleges** napon az FMP is élő, mutáló bart ad (20,10 vs a Polygon 20,51-e).
   Az FMP EOD-végpontja tehát **nem** „csak zárás" — guard nélküli váltás Polygonról
   FMP-re **ugyanazt a hibát reprodukálná**.

A FRED egy napot késik (ma a legfrissebb értéke 10-22), de **centre pontos**.

## 3. Miért lemondás és nem leminősítés

Az `I:VIX` az **egyetlen** index-ticker a kódbázisban (4/4 élő hívóhely). A Massive saját
KB-je szerint a VIX fizetős Indices szinthez kötött, tehát az Indices Basic ($0) **nem**
szolgálná ki. Ugyanaz a megtakarítás, nincs fenntartandó halott csomag.

## 4. Implementációs terv

### 4.1 `src/ifds/data/fmp.py` — két új metódus

- `get_index_quote(symbol)` → `/stable/quote?symbol=^VIX`, a `price` mező (mérve 6-29 s friss).
- `get_index_eod(symbol, from_date, to_date)` → `/stable/historical-price-eod/full`.

Élő séma-verifikáció a commit ELŐTT (ház-szabály), mint a 2026-10-23-i funda-javításnál.

### 4.2 `scripts/paper_trading/daily_metrics.py`

`_fetch_vix_from_polygon` → `_fetch_vix_from_fmp`, **véglegességi guarddal**:

```
a nap N zárása CSAK AKKOR fogadható el, ha now_ET >= 16:30
  (16:15 elszámolás + feed-latencia)
különben: vix_close = kimarad + data_quality ok
```

Fallback-lánc: **FMP EOD (guardolt) → FRED VIXCLS (T+1, centre pontos) → a Phase 0
rögzített értéke**. A hardcode-olt 20.0 **nem** kerül a kutatási adatfolyamba.

### 4.3 Phase 0 (`phase0_diagnostics.py`)

A lánc ma `Polygon I:VIX → FRED VIXCLS → 20.0` (mérve: 287 Mini-futásból 237-ben
Polygon, 0 FRED, 0 default). A Polygon-ág helyére **FMP quote** kerül; a FRED marad
a második lépcsőnek. A 20.0-s default marad, de a logja WARNING (már az).

> ⚠️ `docs/API_STACK.md:72-74` az ellenkezőjét állítja („a VIX elsődlegesen FRED-ből jön") —
> **a doksi elavult**, javítandó ugyanebben a változtatásban.

## 5. Tesztelés

Hermetikus, injektált kliensekkel:

- `now_ET < 16:30` → a mai zárás **nem** fogadható el, akkor sem, ha a végpont ad bart;
- `now_ET >= 16:30` + van bar → elfogadva;
- nincs bar → FRED-fallback, és a visszaadott érték a FRED-é;
- se FMP, se FRED → kimarad + `data_quality`, **nem** 20.0;
- a guard **nem** használ `== 0`-t, és az időzóna UTC/ET-horgonyú (a meglévő
  `test_timestamp_timezone.py` AST-guardja érvényes rá).

## 6. Commit üzenet

```
fix(vix): forrás FMP ^VIX-re, kötelező véglegességi guarddal

A rögzített vix_close 113 napból 18-on (15,9%) egyezett a hivatalos CBOE zárással,
max. 1,10 hibával. Az ok nem a szolgáltató, hanem az óra: a daily_metrics 16:10
ET-kor fut, öt perccel a 16:15-ös VIX-elszámolás ELŐTT.

Mérve: lezárt napon a Polygon, az FMP és a FRED centre azonos; a nem végleges napon
az FMP is élő, mutáló bart ad (10-23: FMP 20,10 vs Polygon 20,51) — tehát a
forrásváltás önmagában NEM javítja a hibát, az óra-guard igen.

Ezzel az Indices Starter sor ($49/hó) lemondható: az I:VIX az egyetlen index-ticker,
és a Massive KB szerint a Basic nem szolgálja ki.
```
