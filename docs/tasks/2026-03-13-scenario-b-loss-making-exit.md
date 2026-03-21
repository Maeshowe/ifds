---
Status: DONE
Updated: 2026-03-21
Note: Implemented — -2.0% threshold, cancel_all_orders + MKT SELL, 5 new tests (987 total)
---

# Feature: Scenario B kiterjesztés — veszteséges pozíció korai zárása 19:00 CET-kor

## Kontextus

A `pt_monitor.py` Scenario B logikája jelenleg csak a **profitable** esetet kezeli:
ha 19:00 CET-kor az ár > entry * 1.005, trail aktivál. Ha a pozíció veszteséges,
semmi nem történik — a pozíció MOC-ra vár.

**Megfigyelt eset (2026-03-12, Day 19):**
- IMAX entry ~$39.78, MOC @$38.24 → **−$303.00**
- 19:00-kor az ár $38.91 volt — korai zárással −$168 lett volna (−$131 saved)

---

## Adat-analízis (2026-03-21, 25 trading day, 119 MOC trade)

### Kérdés 1: 19:00-as ár vs MOC ár — MOC losereknél

| Metrika | Érték |
|---------|-------|
| MOC loss trades összesen | 62 |
| 19:00 close JOBB volt | **44 (71%)** |
| 19:00 close ROSSZABB volt | 18 (29%) |
| Saved (ha 19:00-kor zártunk volna) | +$2,596 |
| Lost (19:00 rosszabb volt) | −$641 |
| **Net impact (csak losereknél)** | **+$1,955** |

### Kérdés 2: 19:00-as ár vs MOC ár — MOC winnereknél

| Metrika | Érték |
|---------|-------|
| MOC winner trades összesen | 57 |
| 19:00 close JOBB volt | 17 (30%) |
| 19:00 close ROSSZABB volt | **40 (70%)** |
| **Net impact (csak winnereknél)** | **−$2,147** |

**Blanket 19:00 close MINDEN MOC trade-re: −$192 net → NEM éri meg.**

### Kérdés 3: Optimális threshold

| Threshold | Trades | Saved | Lost | Net | Win% |
|-----------|--------|-------|------|-----|------|
| −0.50% | 34 | +$717 | −$1,142 | **−$424** | 41% |
| −1.00% | 21 | +$613 | −$710 | **−$96** | 43% |
| −1.50% | 14 | +$573 | −$378 | **+$196** | 50% |
| **−2.00%** | **11** | **+$573** | **−$116** | **+$457** | **64%** |
| −3.00% | 7 | +$417 | −$104 | +$313 | 71% |

### Top esetek ahol 19:00 zárás segített volna

| Date | Ticker | Entry | @19:00 | MOC | Diff |
|------|--------|-------|--------|-----|------|
| 2026-03-18 | ASTS | $95.11 | $95.45 | $90.67 | **+$239** |
| 2026-03-20 | VICR | $187.58 | $173.41 | $164.29 | **+$182** |
| 2026-03-20 | ENB | $54.07 | $54.09 | $53.51 | **+$156** |
| 2026-03-19 | VG | $14.85 | $14.89 | $14.26 | **+$132** |
| 2026-03-12 | IMAX | $39.77 | $38.91 | $38.24 | **+$131** |

### Döntés

**LOSS_THRESHOLD = 0.98 (−2.0%)** — jóváhagyva 2026-03-21.

Indok: −2.0%-nál a win rate 64%-ra ugrik, net impact +$457 (25 nap alapján).
A −0.5% (eredeti javaslat) negatív net impact-ot mutat.

---

## Implementáció

### `pt_monitor.py` — Scenario B loss-making ág

A Scenario B blokk bővítése: ha 19:00 CET-kor a pozíció −2.0%-nál rosszabb,
azonnali MKT SELL az összes SL cancel nélkül (a pozíció teljes qty-ját zárjuk).

```python
SCENARIO_B_LOSS_THRESHOLD = 0.98  # -2.0%

# Scenario B — loss making ág (19:00 CET, price < entry * 0.98)
if current_price < s["entry_price"] * SCENARIO_B_LOSS_THRESHOLD:
    # Cancel ALL open orders for this ticker (SL + TP)
    cancel_all_orders(ib, sym)

    # SELL full position at market
    qty = s["total_qty"]
    contract = Stock(sym, "SMART", "USD")
    ib.qualifyContracts(contract)
    order = MarketOrder("SELL", qty)
    order.tif = "DAY"
    order.orderRef = f"IFDS_{sym}_LOSS_EXIT"
    order.account = ib.managedAccounts()[0]
    ib.placeOrder(contract, order)

    s["trail_active"] = False
    s["scenario_b_eligible"] = False
    s["scenario_b_activated"] = True
    state_changed = True

    msg = (
        f"LOSS EXIT {sym}: Scenario B loss-making close\n"
        f"19:00 CET — position down {((current_price/s['entry_price'])-1)*100:.1f}%\n"
        f"Price: ${current_price:.2f} < threshold: ${s['entry_price']*SCENARIO_B_LOSS_THRESHOLD:.2f}\n"
        f"SELL {qty} shares at MKT"
    )
    logger.warning(msg)
    send_telegram(msg)
```

### Logikai sorrend a Scenario B blokkban

```
19:00 CET check:
  1. Ha profitable (> +0.5%): trail aktiválás (meglévő logika)
  2. Ha loss-making (< -2.0%): MKT SELL, korai zárás (ÚJ)
  3. Egyébként (-2.0% és +0.5% között): skip, MOC-ra vár
```

---

## Tesztelés

1. Unit: Scenario B loss threshold check — price < entry * 0.98 → MKT SELL
2. Unit: price between -2% and +0.5% → no action (MOC wait)
3. Unit: profitable path unchanged (> +0.5% → trail)
4. Unit: cancel_all_orders called before MKT SELL
5. Unit: state fields updated correctly after loss exit
6. Meglévő tesztek: 982 passing — regresszió

---

## Commit üzenet

```
feat(pt_monitor): Scenario B loss-making exit at 19:00 CET

When position is down more than 2% at 19:00 CET, close immediately
via MKT order instead of waiting for MOC. Cancels all open orders
(SL/TP) before selling.

Threshold: -2.0% (SCENARIO_B_LOSS_THRESHOLD = 0.98)
Based on 25-day paper trading analysis: 11 eligible trades,
+$457 net impact, 64% win rate vs MOC.
```

---

## Érintett fájlok

- `scripts/paper_trading/pt_monitor.py` — Scenario B loss-making ág
- `tests/test_pt_monitor_scenario_b.py` — új unit tesztek

---

## Prioritás

**Medium** — BC20 scope. Adatelemzés kész, threshold validálva.
