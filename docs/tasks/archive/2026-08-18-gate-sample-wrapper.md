Status: DONE
Updated: 2026-08-18
Note: KÉSZ (13 teszt, n=39 reprodukálva). Hátra: a wrapper PINELÉSE a kapu előtt. A §5.6 mechanizmus-döntés (Tamás, 2026-08-18: WRAPPER) implementációja. A pin c5e9ed0 SÉRTHETETLEN marad; a §5 minta-szűrő külön, önállóan pinelt modulba kerül. Határidő: 2026-09-22 ELŐTT.

# Task — `gate_sample.py`: a §5 minta-definíció pinelt wrappere

## Probléma

A gate-protokoll **§6/2** a kapu-mintát így definiálja: *„entry-alapú clean cut **+ a §5
kizárások**"*. A pinelt `signal_attribution.py` (**`c5e9ed0`**) viszont **kizárólag
adat-elérhetőségi** kizárást ismer (`entry_score` visszanyerhetetlen, hiányzó leg-P&L,
érvénytelen notional) — a **§5 minta-integritási** kizárás (outage-napok, késett exitek)
**nincs benne**.

**A pre-reg a kánon → az eszköz tér el a protokolltól, nem fordítva.**

A 2026-08-18-i leíró futás ezt ad-hoc kerülte meg (a pinelt függvényeket változatlanul hívta,
csak a mintát szűrte előttük). A kapu-futáshoz ez **nem elég**: a minta-szűrő maga is
**auditálható és pinelt** kell legyen, különben „a minta" nem rekonstruálható.

## Döntés (Tamás, 2026-08-18)

**WRAPPER**, nem újra-pinelés. Indoklás: a pin sérthetetlensége a **G1** lényege, és a §6/2
a mintát amúgy is a **protokoll** (nem az eszköz) hatáskörébe teszi.

**Következmény:** ez **NEM** értékelő-motor-módosítás — a `signal_attribution.py` egyetlen
sora sem változik, tehát az ifds-rules „Értékelő-motor fix csak pre-reg szöveghez igazításként"
4 kötelező kísérője **nem alkalmazandó**. Amit viszont teljesíteni kell: a wrapper legyen
**önállóan pinelt**, **read-only**, és **verifikálhatóan azonos** eredményt adjon, mint a
pinelt eszköz, ha a §5-lista üres.

## Megközelítés

Új modul: **`scripts/analysis/gate_sample.py`**

1. **A §5 lista mint befagyasztott adat** — modul-szintű, `frozenset`/tuple konstansok,
   forrás-hivatkozással (gate-protokoll §5.1 / §5.2). Nem konfigurálható futásidőben.
2. **Integritás-önellenőrzés** — a deklarált outage-napok halmaza **egyeznie kell** a
   `state/daily_metrics/`-ből ténylegesen hiányzó trading napokkal. Eltérés → **hangos hiba**,
   nem csendes átengedés. Ez fogja el, ha új outage jön és a lista nem frissül.
3. **Két kizárási kategória, külön riportálva**:
   - `entry_on_outage_day` — belépés outage-napon (**várhatóan no-op**, mert nincs pipeline-esemény;
     defenzív guard, és ha valaha tüzel, az önmagában finding)
   - `outage_delayed_exit` — a §5.2 pozíció-lista (ticker, entry_date) kulcson
4. **A pinelt függvények változatlan hívása** — `load_closed_trades`, `split_samples`,
   `fetch_forward_returns`, `run_attribution`, `render_report` mind a `c5e9ed0`-ból,
   importálva, **nem másolva**.
5. **Pin-verifikáció futásidőben** — a wrapper induláskor ellenőrzi, hogy a
   `signal_attribution.py` a várt pinen áll (`git diff --quiet c5e9ed0 -- <fájl>`); eltérés →
   leáll. Így a „pin nem változhat a futás előtt" (§6/1) **gépileg** kikényszerített.

## Implementációs terv

| # | Lépés |
|---|---|
| 1 | Tesztek először (RED) — `tests/test_gate_sample.py` |
| 2 | `gate_sample.py`: konstansok + `verify_outage_days()` + `apply_s5_exclusions()` |
| 3 | `main()`: pin-check → load → §5 → fetch → attribution → render |
| 4 | Verifikáció: a wrapper reprodukálja a 2026-08-18-i n=39 számokat **bitre** |
| 5 | Üres-§5 ekvivalencia: a wrapper == a pinelt eszköz outputja |

## Tesztelés (kötelező esetek)

- `apply_s5_exclusions` kiveszi a 4 késett exitet, és **pontosan** azokat
- a kizárás **pozíció-kulcsú** (ticker + entry_date): a **másik két PFGC** tétel (06-25, 07-21)
  **bent marad** — ez a legfontosabb regressziós eset
- `verify_outage_days` hibát dob, ha a deklarált lista és a tényleges hiány eltér
- `entry_on_outage_day` a valós adaton **no-op** (0 tétel)
- **üres §5-lista → a wrapper eredménye azonos a pinelt eszközével** (ekvivalencia-teszt)
- a wrapper **nem ír** a trading state-be

## Elfogadási kritérium

A wrapper a jelenlegi adaton **n=39**-et ad, L2 h=5 Spearman **−0,008** CI [−0,323, +0,308] —
azaz a 2026-08-18-i ad-hoc futás számait, immár pinelhető kódban.

## Commit üzenet

```
feat(analysis): gate_sample.py — a §5 minta-definíció pinelt wrappere (§5.6 döntés)
```
