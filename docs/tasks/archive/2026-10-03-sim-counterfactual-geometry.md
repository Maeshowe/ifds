Status: DONE
Updated: 2026-10-03
Note: EREDMÉNY — a javítás hozadéka −$8 (CI [−707,+649]); a geometria NEM okozta a veszteséget. A hipotézisem megbukott. Riport: docs/review/2026-10-03-sim1-counterfactual-geometry.md. D6 SIM-napirend 1. tétel, a kapu-futás UTÁN. Read-only mérés: nem ír `state/`-be, nem módosít kereskedési logikát, nem kapu-input (G1 — a kapu 2026-10-03-án lezárult, ez post-gate leíró mérés).

# SIM-1 — a §11.20 exit-geometria ellenpróbája a 88 nap valós filljein

## 1. A kérdés

A kumulatív **−$6 460,95** (88 kereskedési nap) mekkora részét okozta a §11.20 defekt,
és mennyi marad a stratégiára?

A stratégia **soha, egyetlen napon sem** futott helyes exit-geometriával: a TP1, a stop és a
breakeven mind a **tervezett** árhoz volt horgonyozva, miközben a belépő MARKET volt, és a fillek
~73%-a adverz. Ezért a veszteség-rekord **önmagában még nem érvényes bizonyíték** a jel ellen —
ez a mérés hivatott eldönteni, hogy javítható defektről vagy valódi negatív edge-ről van-e szó.

**A döntési szerepe:** ez a szám dönti el, melyik §3-utat érdemes választani —
„folytatás más feltételekkel" vs. „keret-revízió új pre-reggel". Lásd a 2026-10-03-i
javaslat-választ és `docs/decisions/2026-10-03-gate-run-outcome.md`.

## 2. Megközelítés — ugyanaz a kód, más horgony

A kulcs-felismerés: **`src/ifds/state/swing_positions.py::evaluate_position_eod()` pure
függvény** (nincs IBKR, nincs Telegram, nincs state-írás). Tehát az ellenpróba **a termelési
exit-logikával** futtatható, csak más `SwingPosition`-horgonnyal:

| Konfiguráció | `entry_price` | `stop/tp1/tp2_level` |
|---|---|---|
| **A — faktuális** | tervezett (plan `limit_price`) | plan `stop_loss` / `take_profit_1` / `take_profit_2` |
| **B — ellenpróba** | **valós fill** | fillből újraszámolva, **ugyanazokkal az ATR-multiplikátorokkal** |

Ezzel **nem írok újra exit-szabályt** → nincs esély rá, hogy a szimulátorom eltérjen a
termeléstől. Ez a konstrukció a mérés egész hitelességének az alapja.

### 2.1 Az ATR egzaktan visszafejthető a planből

TP1 = entry + 1,5·ATR, stop = entry − 2,0·ATR, TP2 = entry + 3,0·ATR — mindhárom ugyanazt az
ATR-t adja (verifikálva: MANH 6,953, IMAX 1,66). Tehát az ATR nem becsült, hanem **rekonstruált**.

### 2.2 Adatforrások

| Mennyiség | Forrás |
|---|---|
| Zárt pozíciók (leg-szint) | `state/pending_exits/*.json` (bróker-autoritatív ledger) |
| Tervezett ár + szintek | `output/execution_plan_run_YYYYMMDD_*.csv` |
| **Valós fill** | `state/daily_metrics/{entry_date}.json` → `execution.slippage_per_ticker[T].filled` |
| Tényleges realizált P&L | `state/daily_metrics/{exit_date}.json` → `trades.details[]` |
| Napi OHLC | `research/cache/api/polygon/grouped_daily/{date}/ALL.json` |

### 2.3 Végrehajtási modell

- `EOD_ACTIONS_NEXT_DAY` (HARD_SL/MENTAL_SL/TP1/TP2/TRAIL_SL) → **következő nap `open`**
  (termelés: `close_positions.py` 15:30 CEST = 09:30 ET).
- `TIME_STOP` → **aznapi `close`** (termelés: 21:40 MOC).
- A kiértékelés a **belépés napján indul** (a termelés is így tesz — MANH 09-14-én, a belépés
  napján kapott TP1-flaget).
- TP1 = `qty × 0,50` (`compute_sell_qty`), minden más exit a maradék.

## 3. A hitelességi kapu (KÖTELEZŐ, az eredmény előtt)

**Az A konfigurációnak reprodukálnia kell a valóságot.** A riport a counterfactual delta ELŐTT
közli:
1. exit-típus egyezési arány (A-sim vs. ledger `exit_type`),
2. exit-dátum egyezés,
3. a P&L-eltérés eloszlása (medián, p90).

Ha az A-sim nem reprodukálja a tényeket, a **B-szám nem közölhető** — akkor a szimulátor
hibás, nem a termelés. Ez a §„Értékelő-motor" szabály szellemében: a mérőeszköz hitelességét
előbb kell bizonyítani, mint az eredményt felhasználni.

## 4. Kizárások (előre rögzítve, a futás előtt)

1. **Nincs fill-rekord** → kizárva. 13 pozíció (2026-05-22 … 2026-06-03), ahol a
   `slippage_per_ticker` mező még nem létezett. Fill nélkül nincs ellenpróba — ez nem
   szelekció, hanem adathiány.
2. **Nincs teljes bar-lefedettség** a tartási ablakra → kizárva, felsorolva.
3. **Nincs leg-szintű realizált P&L** → a *validáció* alól kizárva (a B-sim futhat).

A kizárások száma és oka a riportban tételesen szerepel.

## 5. Implementációs terv

- [x] `grouped_daily` backfill 2026-07-25 → 2026-10-02 (~49 nap, 1 cache-elt hívás/nap)
- [x] `tests/test_counterfactual_geometry.py` — TDD (RED) a sim-harness tiszta egységeire
- [x] `scripts/analysis/counterfactual_geometry.py` — loader + bars + A/B sim + riport
- [x] Hitelességi kapu futtatása (3. szekció) — ha bukik, STOP és diagnózis
- [x] Riport `docs/review/2026-10-03-sim1-counterfactual-geometry.md` (NEM `docs/analysis/` —
      az gitignore-olt ÉS a `--delete` sync-halmazban van)
- [x] `04-risks` §11.20 kiegészítése a mért számmal

## 6. Keretezés (G1/G3)

- A kapu-futás **2026-10-03-án lezárult** (`docs/decisions/2026-10-03-gate-run-outcome.md`),
  tehát a G3 jel-érvényességi nyelvi tilalom **feloldódott**.
- Ez a mérés **post-gate, leíró** — a kapu mintájába vagy küszöbeibe **visszamenőleg nem
  számít be**, és a §3 küszöbök **nem módosíthatók** a fényében (pre-reg = kánon).
- Bármely jövőbeli élő periódus **új pre-regisztrációt** kíván; ez a szám annak *inputja*,
  nem a korábbi kapu utólagos átértékelése.

## 7. Commit üzenet

```
feat(analysis): SIM-1 — a §11.20 exit-geometria ellenpróbája a valós filleken

A termelési evaluate_position_eod() pure függvényt futtatja két horgonnyal
(A: tervezett ár = ahogy élesben futott, B: valós fill = ahogy futnia kellett
volna), ugyanazokkal az ATR-multiplikátorokkal. Előbb hitelességi kapu: az
A-sim reprodukálja-e a ledger tényleges exitjeit.
```
