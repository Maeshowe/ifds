Status: OPEN
Updated: 2026-10-23
Note: A Stocks Advanced → Starter leminősítés ($170/hó) másik feltétele. A 10-26→10-30 hét NEM használható tesztre: a DST-ráhagyás, ami biztonságossá teszi, pont az, ami használhatatlanná teszi. Első informatív nap: 2026-11-02. A Mini-crontab telepítése KÜLÖN jóváhagyást igényel.

# A 22:xx lánc +30 perc — a késleltetett feed előfeltétele

## 1. Probléma

Egy 15 perces késleltetésű csomagon a T időpontban olvasott adat a **T−15** szalagot
tükrözi. Teljes napi barhoz a szalag kell:

| adat | szükséges szalag | legkorábbi biztonságos olvasás |
|---|---|---|
| részvény napi bar | 16:00 ET-ig | **16:15 ET** |
| I:VIX napi bar | 16:15 ET-ig (elszámolás) | **16:30 ET** |

A mai lánc 22:00–22:20 Budapest = **16:00–16:20 ET** (téli időszámításban), azaz a
részvény-oldalon 0–20 perc, a VIX-en **negatív** ráhagyás.

## 2. Miért +30 és nem +20

| | +20 perc | +30 perc |
|---|---|---|
| `pt_monitor` (lánc eleje, legkevesebb ráhagyás) | 16:20 ET → **5 perc** | 16:30 ET → **15 perc** |
| `daily_metrics` | 16:30 ET → **0 perc** a VIX-re | 16:40 ET → **10 perc** |

A tíz extra perc nem kerül semmibe, a nulla-ráhagyásos eset pedig **csendben** bukik
(nem hibát ad, hanem csonka bart). A kötő korlát a **Stocks** oldal: a `pt_monitor`
per-ticker OHLC-je van a lánc elején. *(Az I:VIX nem sizingol: a tervezett Indices-lépés
LEMONDÁS, nem leminősítés — az EOD-only Basic-et semmilyen cron-idő nem menti meg; a VIX
forrása az FMP lesz, lásd a külön taskot.)*

## 3. Az új slotok

Mind a hat sor **egyszerre** mozog, a relatív sorrend változatlan. A `crontab.md:121`
kötött sorrendet rögzít: *„Az eod_report-nak EZUTÁN kell futnia"*.

| job | mai | új | ET (téli) |
|---|---|---|---|
| `pt_monitor --mode=eod_eval` | 22:00 | **22:30** | 16:30 |
| `daily_metrics.py` | 22:10 | **22:40** | 16:40 |
| `eod_report.py` | 22:11 | **22:41** | 16:41 |
| `reconcile_state.py` | 22:15 | **22:45** | 16:45 |
| `generate_review_data.py` | 22:20 | **22:50** | 16:50 |
| `events_to_sqlite.py` | 22:45 | **23:15** | 17:15 |

**Ütközés-ellenőrzés:** mind a 25 telepített sorral összevetve — ütközésmentes.

## 4. ⚠️ A tesztablak kérdése

**A 2026-10-26 → 10-30 hét NEM használható.** Az EU 10-25-én vált téli időre, az USA
11-01-én: abban a héten 22:10 Budapest = **17:10 ET**, egy teljes extra órányi
ráhagyással. A lánc ott akkor is átmenne, **ha a védelem nem működik**.

> A ráhagyás, ami biztonságossá teszi a hetet, pontosan az, ami használhatatlanná teszi
> tesztnek.

**Első informatív hétköznap: 2026-11-02.**

Amit viszont a hét alatt meg LEHET csinálni: a cron-tolás **telepítése** (kockázatmentes,
mert több a ráhagyás), hogy 11-02-re már a tolt lánc fusson, és az legyen az első
valódi próba.

## 5. Implementációs terv

1. `scripts/crontab.md` — a hat sor + a hozzájuk tartozó ET-kommentek átírása.
2. **A Mini telepített crontabja** — `crontab -l > backup`, majd a hat sor cseréje.
   ⚠️ **Ez production-változtatás, külön jóváhagyással.** A repo-oldali doksi és a
   telepített crontab nem csúszhat szét (ma egyeznek, ellenőrizve).
3. `pt_monitor.py:354` — a Telegram-szövegben szereplő időpont együtt mozogjon
   (a tesztje `test_pt_monitor_reconcile.py:296` zöld marad akkor is, ha nem — ezért
   kézzel ellenőrizendő).

## 6. Tesztelés

- A `crontab.md` és a telepített crontab **bájtra egyező** hat sora (diff a telepítés után).
- 2026-11-02: az első tolt futás logja — a `daily_metrics` SPY és VIX mezője kitöltve,
  `data_quality` nélkül.
- A §5.3-as Telegram-szöveg kézi ellenőrzése.

## 7. Commit üzenet

```
chore(cron): a 22:xx lánc +30 perc — a késleltetett feed előfeltétele

Egy 15 perces késleltetésű csomagon a T-ben olvasott adat a T-15 szalagot tükrözi;
teljes napi barhoz a részvény-szalag 16:00 ET-ig, a VIX-elszámolás 16:15 ET-ig kell.
A mai 22:00-22:20 Budapest (16:00-16:20 ET) ebből 0-20 percet hagy, a VIX-en
negatívat. +20 perc a pt_monitornak 5 percet adna, a daily_metrics VIX-ágának nullát;
+30 perc 15-öt, illetve 10-et. A nulla-ráhagyásos eset csendben bukik, nem hangosan.

Mind a hat sor egyszerre mozog, a crontab.md:121 kötött sorrendje megmarad; mind a 25
telepített sorral ütközésmentes.

A 2026-10-26..10-30 hét NEM tesztablak: az EU 10-25-én vált, az USA 11-01-én, tehát
ott 22:10 Budapest 17:10 ET, egy extra órányi ráhagyással — a lánc akkor is átmenne,
ha a védelem nem működik. Első informatív nap: 2026-11-02.
```
