# IFDS Daily Review — 2026-09-17 (csütörtök, Day 85/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.
> ℹ️ **Késve készült** (2026-09-19) — a **09-18-i review + a W38 heti zárás** hátra van.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR
| | |
|---|---|
| **`cum_30d`** | **−4,62%** (−$4 616,73) — **BREACH**, **5. kereskedési nap**, tovább romlik |
| Breach-sorozat | −3,38% → −3,38% → −3,45% → −4,26% → **−4,62%** |
| Gördülés a kapuig (0 realizált) | 09-18 **−4,71%** · 09-21 **−4,21%** · **09-22 (KAPU) −4,33%** |
| **A kapu napján** | **BREACH marad** — a küszöbhöz ~**+$1 330** kumulatív javulás kellene 3 nap alatt |

⚠️ `excess_10d_sum` −1,73% és `excess_15d_sum` −1,99% **visszament BREACH-re** — **D4: megfigyelés**.
🟢 A pre-reg **irányadó** triggerek tiszták: `excess_10d_mean` **−0,17%**, `excess_15d_mean` **−0,13%**.

**Kapu: 2026-09-22 — 2 kereskedési nap.**

## 1. Fejléc
- **Realized net: −$383,59** (gross −$381,22, komm. $2,37) — **2 exit**.
- **Cumulative: −$4 294,30 (−4,29%)** — új mélypont.
- **Net Liq: $96 107,05** — napi Δ **−$212,68**.
- **Excess: −1,52%** (portfolio −0,38% vs SPY **+1,13%**) — **a swing-éra legnagyobb egynapos
  lemaradása** a realized-olvasat szerint.
- **VIX 15,46 (−12,70%)**, SPY **+1,13%** — erős rally.
- **Nyitott pozíciók: 7**; kitettség **45,74% → 50,46%**.

## 2. Exits (2)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:23 | **YPF** | **TRAIL_SL** | 51 | 54,20 → 54,06 | **−$7,19** (−0,26%) | ≈ +$22 | −$29 |
| 19:59:32 | **RCI** | TIME_STOP | 220 | 36,84 → **35,13** | **−$376,40** (−4,64%) | ≈ −$205 | **−$171** |
| **Σ** | | | | | **−$383,59** | ≈ −$182 | **−$202** |

📌 **Az első TRAIL_SL exit a review-időszakban** — és **enyhe veszteséggel** zárt.
⚠️ **A §11.17 defekt 4. esete**: a kanonikus típus **TRAIL_SL**, a `trades.details.exit_type`
mégis **„TP1"** (fill 13:30:23Z, normál ablak). Az `exits` blokk helyesen `trail: 1`.

### 🔴 HARMADIK lezárt visszalépési ciklus — mind a három NEGATÍV
| Ticker | 1. ciklus | Visszalépés | 2. ciklus | **Összesen** |
|---|---|---|---|---|
| ELVN | −$197,89 | 09-10 (**−0,47%, olcsóbb**) | −$430,15 | −$628,04 |
| FBP | +$227,10 | 09-08 (+0,70%, drágább) | −$373,22 | −$146,12 |
| **RCI** | **+$123,55** | **09-09 (−0,05%, olcsóbb)** | **−$376,40** | **−$252,85** |

📌 **Mind a három második ciklus veszteséges — függetlenül attól, hogy a visszalépés olcsóbb
vagy drágább volt.** **n=3, nem általánosítható (G3)**, de a D6 SIM-napirend visszalépés-tételének
legerősebb inputja eddig.

## 3. 🔎 §11.20-KÖVETÉS — a trail HELYES, de a „breakeven" NEM
A 09-16-i review-ban jeleztem, hogy megnézem a trail-szint horgonyzását. **Eredmény
(`swing_manager.py:158–163`):**

```python
trail_amount = pos.atr_at_entry * cfg["trailing_stop_atr"]
trail_stop   = round(price - trail_amount, 2)      # ← AZ ÉLŐ ÁR
```
✅ **A trailing stop az élő árhoz kötött — HELYES, a §11.20 nem érinti.** Ez magyarázza, hogy a
YPF TRAIL_SL csak −$7,19-et hozott, nem egy torzított szintről.

🔴 **A breakeven viszont IGEN** (`swing_manager.py:140–155`):
```python
be_threshold = pos.entry_price + pos.atr_at_entry * cfg["breakeven_threshold_atr"]
...  price=pos.entry_price   # az SL-t az entry_price-ra emeli
```
Mivel az `entry_price` a **tervezett** ár, a „breakeven" stop **nem a valós belépőre** kerül.
**Adverz fill esetén a „breakeven" a valós belépő ALATT van** — egy „breakeven" stop-out tehát
**veszteséget** realizálna. Példa: **MANH** tervezett 201,82 vs valós fill 207,69 → a „breakeven"
SL **−2,83%**-kal a valós belépő alatt.

**A §11.20 pontosított hatóköre (4 szint-mechanizmusból 3 érintett):**
| Mechanizmus | Horgony | Státusz |
|---|---|---|
| TP1-szint | tervezett ár | 🔴 érintett (élesben igazolva: MANH, 09-15) |
| Stop-szint | tervezett ár | 🔴 érintett |
| **Breakeven SL** | **tervezett ár** | 🔴 **érintett — ÚJ (ma verifikálva)** |
| Trailing stop | **élő ár** | ✅ **helyes** |

## 4. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Megjegyzés |
|---|---|---|---|---|
| **EQH** | 141 | 53,88 → **54,96** | **+2,00%** (adverz) | **Visszalépés** (09-15 TIME_STOP @ 53,95 → **+1,87%** drágábban) |
| NWSA | 263 | 30,19 → **30,13** | −0,20% (kedvező) | *(A 09-11-én zárt NWS **másik részvényosztálya**, nem ugyanaz az instrumentum.)* |

📌 Az **EQH +2,00%** a CC-éra 2. legnagyobb adverz fillje (rekord: MANH +2,91%).
**Visszalépés-sorozat n=13** (10 drágább / 3 olcsóbb).

## 5. Nyitott pozíciók (7) — 09-17 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| MANH (TP1 után) | Technology | 207,82 | 210,82 | **+$39,00** |
| NWSA | Comm. Services | 30,13 | 30,18 | +$13,15 |
| CRBG | Fin. Services | 34,97 | 34,88 | −$21,15 |
| IMAX | Comm. Services | 52,80 | 51,83 | −$101,60 |
| TS | Basic Materials | 57,39 | 56,52 | −$119,19 |
| EQH | Fin. Services | 54,96 | 54,04 | −$129,72 |
| **OGE** | Utilities | 47,37 | 46,30 | **−$248,24** |
| **Σ** | | | | **−$567,75** |

A könyv **−$696,88 → −$567,75**; **2/7 pozitív**. Az **OGE ma TIME_STOP-on zár** (≈ −$248).

## 6. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:30 eod_flags (YPF TRAIL_SL), 15:31 submit (EQH, NWSA),
  21:40 time_stop (RCI MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −4,62%, BREACH, 5. nap.
- ⚠️ **A becslés 5. napja alulbecsüli a veszteséget** (ma −$202; az RCI egyedül −$171).

## 7. Anomáliák
- **🔴 A `cum_30d` a kapu napján is BREACH lesz** a gördülés szerint (§0).
- **🔴 Harmadik lezárt visszalépési ciklus, mind a három negatív** (§2).
- **🔎 §11.20 hatókör pontosítva**: a **breakeven is érintett** (új), a **trail nem** (§3).
- **⚠️ A §11.17 defekt 4. esete** (TRAIL_SL → „TP1").
- **✅ VÁLTOZATLAN**: `swing_state.exits_today`, `commission_total` csak exit-láb,
  `reconcile` csak ticker-halmaz, szektor-cap rés (§11.18), TP1 utáni max_hold-túlfutás,
  **FileVault**, **sync-rés**, **§5.1/§5.2 döntések**.

## 8. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Visszalépés exit után** — **n=13** (10 drágább / 3 olcsóbb); **3 teljes ciklus lezárva,
  mind negatív** (Σ **−$1 027,01**).
- **TRAIL_SL** — **n=1** (YPF −$7,19), az első a review-időszakban.
- **TP1 (teljes swing-éra)** — n=25, ebből 3 negatív. **MENTAL_SL** — n=8.
- **Next-day MKT fill slippage** — CC-éra **n=53** (+EQH **+2,00%**, +NWSA −0,20%):
  **39 adverz / 14 kedvező** (73,6%).
- **Kitettség** — 50,46%.
- **Pozitív realizált nap** — 28/77 (ma nem).
- **Rally/risk-off aszimmetria** — **erős rally-nap** (SPY +1,13%), realized szerint **−1,52%
  lemaradás — a sorozat legnagyobbja**. Sorozat: **15** rally-lemaradás vs 15 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **0/2**. **Várt-vs-tény**: **−$202**.

## 9. Másnap (péntek, 09-18) — a flag szerint
**Egy TIME_STOP 21:40 MOC**: **OGE** 232, bázis 47,37 / 09-17 záró 46,30 → **≈ −$248**.
*(A 09-18-i tényleges nap külön review tárgya — a `daily_equity` szerint a NetLiq
**$95 885,19**-re esett, azaz további −$221,86.)*

## 10. Freeze-sor
🔓 Freeze feloldva 08-17 — **D6: prod FAGYVA 2026-09-22-ig**; **D7: a breach nem indok
paraméter-változtatásra.** G1/G3–G7 élnek. Ma **nem történt** production-kód változás.

## 11. A nap egy mondatban
Egy **+1,13%-os rally-napon** a portfólió −0,38%-ot realizált (**−$383,59**, döntően az RCI
−$376,40-os max_hold-exitjéből), ami a realized-olvasat szerint **−1,52%-os lemaradás — a
swing-éra legnagyobbja**; ezzel **lezárult a harmadik visszalépési ciklus is, és mind a három
negatív** (Σ −$1 027) — miközben a `cum_30d` **−4,62%-ra romlott, ötödik napja BREACH-ben**, és
a megígért §11.20-követés egy **új érintett mechanizmust** hozott: a **„breakeven" stop a
tervezett árhoz kötött**, tehát adverz fill esetén **nem breakeven, hanem veszteség** — a
trailing stop viszont **helyesen** az élő árhoz igazodik.
