Status: BLOCKED
Updated: 2026-10-19
Note: a design átvizsgálva és ELUTASÍTVA (12 blocker). A biztonságos változat követelménylistája lent; a MOC-ablak guard és a CET-konverzió javítása már bement (`e96e6ed` utáni commit).

# TP1/TP2 ugyanaznapi aukciós kilépés — a design, ami nem élte túl a reviewt

## Mi az indok

`docs/review/2026-10-19-auction-exit-counterfactual.md`: a TP1/TP2 lábakat az
**ugyanaznapi záróaukcióba** terelve a valódi könyvön **+783 $** [+244, +1 460],
23/29 láb javult. Ebből **+536 $ súrlódás-megszűnés** (ismétlődő), **+259 $
óramozgás** (a minta saját árútja, nem él). Tamás jóváhagyta 2026-10-19-én:
„MOO belépő + TP1/TP2 → ugyanaznapi MOC". A MOO fele kész (`e96e6ed`).

## Miért BLOCKED

Egy 50-ágenses adverzariális panel (4 lencse, minden lelet külön cáfoló ágenssel)
**27 leletet igazolt, 12 blockerrel** a javasolt designon. Négyet saját méréssel
is megerősítettem:

### B-1 🔴 A valós tartás 6 session, nem 5 — a design csendben 5-re vitte volna

A 21:40-es job ma **tokent fogyaszt**: `next_action == ACTION_TIME_STOP`, amit az
**előző** nap 22:00-es eod_eval írt. A cron-sorrend (21:40 fogyasztó **előtt**
22:00 termelő) egy session késést ad. Mérve a teljes `state/pending_exits/`-en:

```
119 exit-láb, ebből TIME_STOP 77
days_held eloszlás: {3: 1, 6: 63, 7: 5, 8: 2, 9: 2, 10: 1, 11: 3}
konfigurált swing_time_stop_trading_days = 5 → a VALÓS módusz 6, az 5-en NULLA láb
```

A design élőben számolta volna újra a `days_held >= 5`-öt 21:40-kor → **minden
time stop egy sessionnel korábban zárt volna**. Ez a **tartási horizont**
változtatása, az exit-lábak **65%-án**, **mért előjel nélkül**, egy
végrehajtási-csatorna változtatás belsejébe csempészve. Sem a mérés, sem a
jóváhagyás nem fedi.

### B-2 🔴 Nincs MOC-ablak guard, és a DST-gap hét a ZÁRÁS UTÁN futna

Mérve 2026-10-19 … 12-31 között **7 kereskedési nap**, ahol a 21:40-es slot a
MOC cutoff után van: **okt 26–30** (EU téli idő, US még nyári → 21:40 CET =
16:40 ET, **+40 perc a zárás után**) és **nov 27 / dec 24** (early close,
**+160 perc**).

A design pedig **post-close snapshotból** olvasta volna a `high`-t — ami ilyenkor
a **teljes napi** high → minden pozícióra tüzelt volna, amelynek a napi csúcsa
elérte a szintet. Következmény: végrehajthatatlan MOC + `record_pending_exit_safe`
→ **fantom realizált exitek a pénzügyi ledgerben**, kézzel javíthatóan.

Ma ez a kitettség **korlátozott** (csak előre flagelt TIME_STOP-okra, és a
token-fogyasztás early close-on megvédi); a design **feloldotta volna** a korlátot.

### B-3 🔴 A biztonsági kapum átengedte volna a halott quote-ot

```python
>>> from ib_insync import Ticker; Ticker().high
nan
>>> float("nan") < 100.0     # a kapum: "skip if last < stop_level"
False
```

A `ticker.high`/`ticker.last` **nan** alapértéke mellett a `nan < stop_level`
hamis → a kapu **átengedi**. Plusz a `ticker.high` session-definíciója (IBKR,
akár extended hours) **nem azonos** a Polygon RTH-only napi high-jával, amin a
production `evaluate_position_eod` dolgozik → olyan TP tüzelt volna, amit a
production sosem flagel.

### B-4 🔴 Nincs order-status check az állapot mutálása előtt

A csendben elutasított MOC után az állapot „eladva", a broker long. És egy **TP1
részleges** eladást **egyetlen reconciler sem tud észlelni**: mindhárom
ticker-**halmazt** hasonlít, soha nem mennyiséget. Vagyis egy félméretű pozíció
**tartósan láthatatlan**.

Ráadásul a TP1 mennyiség-formulám (`floor(qty_remaining * 0.5)`) **eltér** a
productiontól: `compute_sell_qty` = `max(1, floor(qty * 0.5))` — az **eredeti**
`qty` fele, nem a maradék fele.

## Amit a review nyomán MÁR megjavítottam (külön commit)

| | |
|---|---|
| **MOC-ablak guard** | `ifds.utils.calendar.is_before_moc_cutoff()` — exchange-kalendárból és `America/New_York`-ban, `MOC_SUBMISSION_LEAD = 10 min` (early close-on is helyes, mert lead-time és nem óraidő). A 21:40-es job most **megtagadja** a feladást és **nem** nyúl az állapothoz. Guard-only: csak megakadályozhat egy ordert, soha nem okozhat egyet. |
| **`get_market_close_time_cet`** | a hard-kódolt `ET + 6h` („DST offsets cancel") helyett valódi zóna-konverzió. A DST-gap héten a régi 22:00-t adott a valódi **21:00** helyett — és az egyetlen hívója épp azt dönti el, hogy egy MOC már késő-e. |

## A biztonságos változat követelménylistája (ha egyszer megépül)

1. **A TIME_STOP marad token-fogyasztó.** `next_action == ACTION_TIME_STOP`, élő
   `days_held` újraszámítás **TILOS**. A 6-vs-5 késés külön, külön jóváhagyott
   változás, saját előtte/utána méréssel.
2. **MOC-ablak guard** az egész passzra (megvan).
3. **Láb-szintű idempotencia** a `pending_exits` ledger kulcson
   (`make_key(ticker, exit_type, today)`) — kézi újrafuttatás ne adjon el újra.
4. **Cross-leg fall-through tilalom**: egy TP1 után a maradékot **ugyanabban a
   sessionben** nem szabad time-stoppolni (a production prioritás a TP1-et a
   TIME_STOP fölé teszi).
5. **NaN-biztos quote guard**: `math.isfinite()` ellenőrzés a `high`/`last`-ra,
   és a session-definíció egyeztetése a Polygon RTH high-jal (vagy
   `reqHistoricalData` 5-perces RTH bar-okból számolt high).
6. **Order-status check az állapot mutálása ELŐTT**, a házszabály valid-státusz
   halmaza ellen, és **mennyiség-szintű** reconcile (a mai három reconciler
   halmaz-alapú → félméretű pozíciót nem lát).
7. **`compute_sell_qty` újrahasználata**, nem új formula.
8. **IBKR qty cross-check** a feladás előtt (a 2026-05-23-i reconcile-before-decide
   védelem megkerülése tilos).
9. **A költségmodell exit-klasszifikációja**: a `frl_fills.NEXT_DAY_MARKET`
   tartalmazza a TP1/TP2-t → az **átállítás után** az aukciós fillt a **nyitóhoz**
   árazná, azaz **engedékeny** irányba. Az átállítással egy commitban javítandó.
10. **Nincs élő smoke** → a kereskedés újraindításának első napján kötelező
    ellenőrzés, a MOO belépővel együtt.

## Cost/benefit, amiért ez nem sürgős

A megszerezhető **ismétlődő** rész **+536 $ / 88 nap ≈ 6 $/nap**. Ezzel szemben
tíz követelmény egy élő pénzügyi exit-úton, egy olyan rendszerben, ahol a
kereskedés áll és a jelcsalád megerősített null. A MOO belépő (már kész) a
falat 0,1428 → 0,0615-re viszi; ez a tétel 0,0327-re — **hasznos, de nem ez a
szűk keresztmetszet**.

## Referencia

- Mérés: `docs/review/2026-10-19-auction-exit-counterfactual.md`
- Fal: `docs/review/2026-10-19-execution-wall-by-horizon.md`
- Panel: 50 ágens, 4 lencse, 27 igazolt lelet / 12 blocker (2026-10-19)
