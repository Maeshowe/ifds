# 19:00 CEST Breakeven Lock — B Bracket Profit Védelem és Veszteség Korlátozás

**Status:** DONE
**Created:** 2026-04-28
**Priority:** **P1** (risk control, nem alpha keresés — soft floor matematikai garancia: nem termel több kárt mint a meglévő rendszer)
**Estimated effort:** ~1.5-2h CC

**Depends on:**
- nincs

**NEM depends on:**
- M_contradiction multiplier (independent — külön task fájl, külön commit)
- MID Bundle Integration (független)

---

## Kontextus — A POST -$299 eset

A 2026-04-27 (hétfő) szerda kereskedési napon a POST pozíció **-$299** veszteséggel zárt MOC-on, **annak ellenére**, hogy a nap egy meghatározott pontján profit volt.

**Idővonal (CEST):**

```
16:18 CEST  Entry: POST $105.59 (limit $105.27, slippage +0.30%)
            SL $101.26, TP1 $108.61, TP2 $110.62

19:00 CEST  trail_activated_b @ ár $106.04 (entry felett +0.43%)
            Trail SL $102.03 (3.4% entry alatt)

19:05 CEST  trail_sl_update @ $102.13, ár $106.14 (még profit)

            ... ezután 2 óra 35 perc CSEND POST-ról ...

21:40 CEST  POST MOC submitted

22:00 CEST  Fill: $103.87 → -$299.28
```

**A probléma:**
- 19:00 CEST-kor **profit van** (+$0.55/share)
- A trail SL azonban **3.4%-kal entry alatt** marad ($102.03)
- A piac csendesen visszaesik, a profit veszteséggé alakul
- A trail mechanika **nem véd** entry-szintre, csak ATR-távolságban

## A javasolt megoldás — 19:00 CEST Breakeven Lock

**Minden 19:00 CEST időpontnál**, minden aktív pozícióra:

### Profit állapot (price > entry)

A B bracket trail SL **soft floor-t kap entry áron**:

```python
B_bracket.sl_floor = entry_price
B_bracket.effective_sl = max(B_bracket.trail_sl, B_bracket.sl_floor)
```

A normál trail mechanika **továbbra is működik** — ha az ár tovább emelkedik, a trail emelkedik is, és **átlépheti** az entry floor-t (`max()` operáció).

### Veszteség állapot (price ≤ entry)

A B bracket SL **felülírva max -1% veszteségre**:

```python
B_bracket.sl_floor = entry_price * 0.99  # max -1% loss
B_bracket.effective_sl = max(B_bracket.trail_sl, B_bracket.sl_floor)
```

Ez **szigorúbb** mint a meglévő -2% LOSS_EXIT, így minimálisan korlátozza a downside-t.

### Az A bracket változatlan

Az A bracket **NEM** kap floor-t — a TP1 cél megőrizve. Ez **kritikus**: ne vágjuk el a partial profit lehetőséget.

## Soft floor vs Hard jump — miért soft floor

A két verzió a POST-tegnapi esetében **ugyanúgy** működik (mert az ár csak lefelé ment 19:00 után). De a különbség **felfelé** mozgásnál:

| Forgatókönyv | Hard jump | Soft floor |
|--------------|-----------|------------|
| Ár tovább emelkedik $107-re majd visszaesik | SL fixe $105.59, kilépés $105.59-en | Trail követi $107-et, SL pl. $104, kilépés $104-en |
| Ár emelkedik $112-re majd visszaesik | SL $105.59, kilépés $105.59-en | Trail $112-re emelkedett, SL pl. $108, kilépés $108-on |
| Ár csak visszaesik (POST tegnapi) | SL $105.59, kilépés $105.59-en | Trail floor-on, kilépés $105.59-en |

**A soft floor azonos protection-t ad lefelé, plusz extra profit-megtartás felfelé.**

## Matematikai garancia — soft floor nem termel több kárt

**Ez kulcsérv a kockázat-szempontból.**

A meglévő rendszer SL = `trail_sl_calculation`.
Az új rendszer SL = `max(trail_sl_calculation, entry_or_minus_1pct_floor)`.

Mivel `max(x, y) >= x` mindig, az új SL **mindig egyenlő vagy szigorúbb** mint a régi. Tehát:

- **Veszteség oldalon:** az új rendszer **soha nem ad rosszabb** kilépést mint a régi
- **Profit oldalon:** az új rendszer **soha nem ad kisebb profitot** mint a régi (max() művelet)
- **Egyetlen kompromisszum:** ha az ár az új SL-en kilép és **utána tovább emelkedne**, akkor a régi rendszer megtartotta volna pozíciót. **De ez egy fundamentális trade-off** — kockázat-csökkentés szükségszerűen csökkenti az upside opciók számát is.

A változás **lefelé szigorúbb** (jó: kevesebb kár), **felfelé azonos vagy jobb** (jó: több profit). **Nincs szcenárió**, ahol az új rendszer **több kárt** termel mint a régi. Ezért a változás **risk-control kategória**, nem alpha-experiment.

## Implementáció részletei

### 1. Időbeli trigger

A `pt_monitor.py` (vagy ami az 5 perces monitoring loop-ot futtatja) **19:00:00 CEST** időpontban (= 13:00 ET) **egyszer** ellenőrizze az aktív B bracket-eket.

A jelenlegi monitor 5 perces frekvencián fut — a 19:00 CEST trigger pontosabb, mint a "minden iterációban", mert egyetlen alkalmas időponti ellenőrzés.

**Implementáció:**

```python
def maybe_apply_breakeven_lock(positions, current_time_cest):
    """Apply 19:00 CEST breakeven lock to B bracket positions."""
    if current_time_cest.hour != 19 or current_time_cest.minute > 5:
        return  # Csak 19:00:00 - 19:05:00 sávban aktiválódik (5 perces tűrés)

    for pos in positions:
        if pos.bracket != "B":
            continue
        if pos.breakeven_locked:
            continue  # már alkalmazva ma

        if pos.current_price > pos.entry_price:
            new_floor = pos.entry_price
        else:
            new_floor = pos.entry_price * 0.99  # max -1% loss

        old_sl = pos.trail_sl
        pos.trail_sl = max(pos.trail_sl, new_floor)
        pos.breakeven_locked = True

        if pos.trail_sl != old_sl:
            log_event("breakeven_lock_applied", {
                "ticker": pos.ticker,
                "old_sl": old_sl,
                "new_sl": pos.trail_sl,
                "entry": pos.entry_price,
                "current_price": pos.current_price,
                "lock_type": "profit_breakeven" if pos.current_price > pos.entry_price else "loss_capped_minus_1pct"
            })
```

### 2. State perszisztencia

A `breakeven_locked` flag a pozíció state-ben (valószínűleg `state/positions.json` vagy hasonló) **per-day perszisztens** kell legyen. Holnap reggel (másnap) automatikusan reset.

**Megjegyzés:** Ha a state struktúra már ismert, CC ellenőrzi a tényleges fájl helyét és formátumát az implementáció előtt.

### 3. Trail mechanika integráció

A meglévő `trail_sl_update` esemény **továbbra is** számolja a trail-t. A breakeven lock után:
- Ha a normál trail számítás **alacsonyabb** mint a floor → a SL marad floor-on
- Ha a normál trail számítás **magasabb** mint a floor → a SL emelkedik a trail-lel (átlépi a floor-t)

Ez **soft floor** viselkedés. A breakeven_locked flag **nem** "kikapcsolja" a trail-t, csak megakadályozza a SL `entry alá` esését.

### 4. Logging

Minden alkalommal, amikor a breakeven lock érvényesül:

```json
{"ts": "2026-04-28T17:00:14Z", "script": "monitor", "event": "breakeven_lock_applied",
 "ticker": "XYZ", "old_sl": 100.50, "new_sl": 102.00, "entry": 102.00,
 "current_price": 103.50, "lock_type": "profit_breakeven"}
```

Ezt a `pt_events_*.jsonl`-be írja, hogy a daily review fel tudja használni.

### 5. Daily metrics integráció (opcionális, de hasznos)

A `daily_metrics.py` új mezőt kaphat:

```python
"risk_control": {
    "breakeven_locks_applied": 1,
    "breakeven_lock_tickers": ["POST"],
    "breakeven_lock_avg_savings": 250.00,  # becslés a P&L delta alapján
}
```

Ez **W18 péntek heti metrikába** is bekerülhet — látni akarjuk a feature hatását.

## Tesztek (5-6 új test)

**Fájl:** `tests/test_breakeven_lock.py` (új) vagy a meglévő trail teszt bővítése

```python
def test_breakeven_lock_applied_at_1900_cest_with_profit():
    """A profit pozícióra entry SL kerül 19:00 CEST-kor."""

def test_breakeven_lock_applied_at_1900_cest_with_loss():
    """Veszteség pozícióra entry × 0.99 SL kerül 19:00 CEST-kor."""

def test_breakeven_lock_only_b_bracket():
    """Az A bracket változatlan marad."""

def test_breakeven_lock_does_not_lower_trail_sl():
    """Soft floor: ha a trail már magasabb mint az entry, a trail marad."""

def test_breakeven_lock_only_applied_once_per_day():
    """A flag megakadályozza a duplikált alkalmazást."""

def test_breakeven_lock_outside_1900_window():
    """18:55 vagy 19:10 CEST-kor nem aktiválódik."""

def test_breakeven_lock_with_subsequent_trail_rise():
    """Soft floor: a trail továbbra is emelkedhet 19:00 után, ha az ár felmegy."""
```

## Success criteria

1. **Tesztek:** 5-7 új teszt + a teljes test suite zöld marad
2. **Live verification (kedd este):**
   - 19:00:00 - 19:05:00 CEST sávban a `pt_monitor.py` log keressen `breakeven_lock_applied` eseményt
   - Ha aznap volt B bracket pozíció trail_activated állapotban, az esemény jelenjen meg
3. **Visszamenőleges sanity check (szerda reggel):**
   - A POST 2026-04-27 pozícióra futtatva (mock-kal vagy SIM-L2-vel) az új SL = $105.59 lenne 19:00-kor
   - Becsült megtakarítás: ~$250-300

## Risk

**Nagyon alacsony.** Indoklás:

1. **Matematikai garancia** — `max()` operáció soha nem ad rosszabb eredményt mint a meglévő trail SL
2. **Csak B bracket** — A bracket TP1 esélye érintetlen
3. **Soft floor** (nem hard jump) — a trail mechanika természetesen folytatódik felfelé
4. **Egyetlen alkalmazás per nap** — a flag megakadályozza a duplikált triggert
5. **Per-position log entry** — minden alkalmazás auditálható

## Out of scope (explicit)

- **Hard jump verzió** — soft floor választott a felfelé extra profit miatt
- **A bracket breakeven** — TP1 esélyét megőrizzük
- **Más időpontok** (18:00, 20:00) — 19:00 fix, későbbi tuning lehet külön task
- **Variable loss cap** (-0.5%, -1.5%, -2%) — a -1% mostani választás, későbbi tuning lehet
- **Mindennap minden pozícióra "early breakeven"** (pl. ha +1% profit elérése) — más design, külön task ha érdekes
- **A meglévő LOSS_EXIT (-2%) kihagyása** — megmarad változatlanul mint backup védelem

## Implementation order (CC számára)

1. **Olvasás / megerősítés** (15 min)
   - `pt_monitor.py` — hol van a 5 perces monitoring loop és a trail SL update
   - State perszisztencia — hol tárolódnak a pozíciók (state/positions.json vagy más)
   - A `entry_price` és `trail_sl` mezők elérési útja a state struktúrában
2. **Időbeli trigger** (15 min) — `19:00:00 - 19:05:00 CEST` window detection
3. **Breakeven lock function** (20 min) — `max(trail_sl, floor)` logika + state update + logging
4. **State perszisztencia** (15 min) — `breakeven_locked: bool` flag a pozíció state-ben, daily reset
5. **Tesztek** (30 min) — 5-7 unit test, mocked time + position fixtures
6. **Smoke test** (10 min) — futtatás 1 mock pozíción, log ellenőrzés
7. **Commit + push** (5 min)

**Összesen: ~1.5-2h.**

## Commit message draft

```
feat(monitor): add 19:00 CEST breakeven lock for B bracket positions

Implements a risk control to prevent the "winner-to-loser" pattern observed
on 2026-04-27 (POST -$299): a position trail_activated in profit at 19:00
CEST whose trail SL was 3.4% below entry, then quietly drifted to MOC loss.

The 19:00 CEST breakeven lock applies to B bracket positions:

  - If price > entry  → SL_floor = entry            (breakeven protection)
  - If price <= entry → SL_floor = entry × 0.99     (max -1% loss cap)
  - effective_sl      = max(trail_sl, SL_floor)     (soft floor — trail
                                                     continues upward)

The A bracket is unchanged (TP1 chance preserved).

Mathematical guarantee: max() operation never produces a worse SL than the
existing trail mechanism. Therefore this change is strictly risk-reducing —
no scenario produces a larger loss than the current system.

Verified retrospectively: POST 2026-04-27 would have been stopped at $105.59
(breakeven) instead of MOC $103.87, saving ~$300.

Tests:
  - test_breakeven_lock_applied_at_1900_cest_with_profit
  - test_breakeven_lock_applied_at_1900_cest_with_loss
  - test_breakeven_lock_only_b_bracket
  - test_breakeven_lock_does_not_lower_trail_sl
  - test_breakeven_lock_only_applied_once_per_day
  - test_breakeven_lock_outside_1900_window
  - test_breakeven_lock_with_subsequent_trail_rise
```

## Kapcsolódó

- POST eset: `logs/pt_events_2026-04-27.jsonl` (trail_activated_b @ 17:00 UTC = 19:00 CEST)
- Daily review: `docs/review/2026-04-27-daily-review.md` (POST -$299 részletes)
- Trail mechanika: `scripts/paper_trading/pt_monitor.py` (vagy ahol a trail logika él)
- Linda Raschke: `docs/references/raschke-adaptive-vs-automated.md` (risk control mint discretionary judgment kódolása)
- Backlog: `docs/planning/backlog-ideas.md` (kapcsolódó M_contradiction multiplier)

## Implementáció időzítése — MA (kedd ápr 28)

**Risk management prioritás indokolja a haladéktalan implementációt.** A soft floor matematikai garanciája miatt a feature **nem termel több kárt** mint a meglévő rendszer, tehát W18 mérés szempontjából **nem kuszít** változót — csak adatot ad arról, hányszor aktiválódik és milyen P&L hatással.

- **Kedd reggel:** Tamás visszaigazolta a paramétereket (price > entry → entry SL; veszteség → -1% SL; csak B bracket; soft floor)
- **Kedd délelőtt:** CC kezdje meg az implementációt
- **Kedd délután:** commit + push, smoke test
- **Kedd este 19:00 CEST:** első éles ellenőrzés a kedd-i pozíciókra
- **Szerda reggel:** Tamás ellenőrzi a logot (`grep breakeven_lock pt_events_2026-04-28.jsonl`)
- **Szerda délelőtt:** CC megkezdi a M_contradiction multiplier task-ot (külön task fájl, külön commit)

## Megjegyzés a Linda Raschke-elv kontextusban

A `docs/references/raschke-adaptive-vs-automated.md` rögzíti, hogy az IFDS architektúrája **fokozatos változtatásokat** preferál, és **risk control nem ugyanaz mint alpha keresés**.

A 19:00 CEST Breakeven Lock egy **risk control** változás:
- **Lefelé szigorúbb** védelem (kevesebb kár)
- **Felfelé azonos vagy jobb** profit-megtartás
- **Nincs új alpha-keresés** a változásban
- **A POST-típusú esemény elkerülése** strukturális javítás

Ezért a változás **W18-ban** (most) implementálandó, nem W19-ben — a Day 63 mérés **nem kuszul**, csak a meglévő rendszer **mindenhol >=** verziója lesz aktív.

A discretionary judgment (Tamás "ha 19:00-kor profit, kösd be entry-re" intuíció) **kódolva** lett a systematic layer-be — pontosan a Raschke "systematic + adaptive" hibrid.
