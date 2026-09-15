# IFDS Daily Review — 2026-09-14 (hétfő, Day 82/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR — leállítási feltétel státusza
| | |
|---|---|
| **`cum_30d`** | **−3,38%** (−$3 376,44) — **BREACH** (küszöb −3,0%) |
| Breach kezdete | 2026-09-11 (ma **2. kereskedési nap**) |
| Tegnapi gördülési táblázat szerint | +1. nap: 07-30 ($0,00) kigördül, 0 realizált → **−3,38%** ✓ **pontosan teljesült** |
| **Ma (09-15) kigördül** | 07-31, **+$176,52** → bázis **−$3 552,96 (−3,55%)** |
| **A breach feloldásához a mai realizált kellene** | **> +$552,96** |
| A mai flagek implikált várakozása (09-14 mark) | MANH TP1 ≈ +$48, EQH TIME_STOP ≈ +$75 → **Σ ≈ +$123** → ≈ **−3,43%** |
| **Kapu** | **2026-09-22 — 6 kereskedési nap** (D7: ott döntés) |

A pre-reg irányadó **excess**-triggerek tiszták: `excess_10d_mean` **−0,03%**, `excess_15d_mean` **−0,07%**.
`excess_15d_sum` −1,04% (D4: megfigyelés).

## 1. Fejléc
- **Realized net: $0,00** — **0 exit** (a 09-11-i `next_day_planned` üres volt ✓).
- **Cumulative: −$3 205,51 (−3,21%)** — változatlan.
- **Net Liq: $96 926,78** — napi Δ **+$91,16**.
- **Excess: +0,45%** — **≡ −SPY** (portfolio 0,00% vs SPY −0,45%) — a **§D3/M szélsőérték-eset**:
  0 exit mellett a realized-olvasat mechanikusan az index ellentettje.
- **VIX 16,95 (+7,01%)**, SPY −0,45%.
- **Nyitott pozíciók: 10** — az **éra-rekord kiegyenlítve**.

## 2. Entries (3) — mind a három VISSZALÉPÉS, mind drágábban
| Ticker | Qty | Planned→Fill | Slippage | Előző exit | Visszalépés |
|---|---|---|---|---|---|
| **MANH** | 25 | 201,82 → **207,69** | **+2,91%** 🔴 | 09-09 **MENTAL_SL** @ 205,00 (−$362,11) | **+1,31%** |
| IMAX | 105 | 52,09 → 52,80 | +1,36% | 09-08 TIME_STOP @ 52,66 | +0,26% |
| CRBG | 235 | 34,67 → 34,97 | +0,87% | 09-08 TIME_STOP @ 33,74 | **+3,65%** |

- 🔴 **A MANH +2,91% ÚJ ÉRA-REKORD adverz fill** (előző: FBIN +2,44%, 08-13). Napi átlag **+1,15%**.
- 📌 **A MANH-ot három kereskedési nappal a MENTAL_SL-je után vettük vissza** — az első dokumentált
  **stop-loss → visszalépés** eset a sorozatban (a korábbiak TIME_STOP/TP1 utániak voltak).
- **Visszalépés-sorozat n=12**: 9 drágább / 3 olcsóbb.
- 🔴 **Kitettség: `total_notional` 69,94% — ÚJ ÉRA-REKORD** (előző 63,48%, 08-31).
- 🟡 **Financial Services 24,92%** — **0,08 pp-re a 25%-os figyelmeztetési küszöbtől** (cap 30%);
  a `sector_cap_proximity` flag épp nem tüzelt. *(Emlékeztető §11.18: a Phase 6 cap előretekintő,
  a flag nem — a köztes sávban a korlát már köthet.)*

## 3. 🔴 ÚJ FINDING — a TP1/stop szintek a TERVEZETT árhoz kötöttek, nem a tényleges fillhez
**A MANH már az első napján TP1-flaget kapott** (`next_day_planned: MANH_TP1`). Az ok (verifikálva):

| | |
|---|---|
| `entry_price` a state-ben | **201,82** — a Phase 6 **tervezett** ára |
| Tényleges MKT fill | **207,69** (+2,91%) |
| `tp1_level` | **212,25** = 201,82 + 1,5 × ATR(6,95) |
| `stop_level` | **187,92** = 201,82 − 2 × ATR |
| MANH 09-14 bar | O 207,71 / **H 212,85** / L 204,00 / C 211,54 → **a high átlépte a TP1-et** |

**A kód** (`submit_orders.py:338–344`): a `SwingPosition` az `entry_price=t["limit_price"]`,
`stop_level=t["stop_loss"]`, `tp1_level=t["take_profit_1"]` mezőket **egyenesen az execution
planből** veszi, miközben a rendelés **MARKET**. **Fill utáni szint-újraszámolás nincs.**

**A geometria torzulása — a mai három belépőn mérve** (tervezett R:R: TP1 +1,5 ATR / stop −2 ATR = **0,75**):

| Ticker | Slippage | TP1-távolság (terv → fill) | Stop-távolság (terv → fill) | **R:R (terv → valós)** |
|---|---|---|---|---|
| **MANH** | +2,91% | +5,17% → **+2,20%** | −6,89% → **−9,52%** | **0,75 → 0,23 (−69%)** |
| IMAX | +1,36% | +4,78% → +3,38% | −6,37% → −7,63% | 0,75 → 0,44 (−41%) |
| CRBG | +0,87% | +3,20% → +2,32% | −4,27% → −5,09% | 0,75 → 0,46 (−39%) |

📌 **Minden adverz fill egyszerre ÖSSZENYOMJA a TP1-távolságot és KITÁGÍTJA a stop-távolságot.**
A CC-éra fillje **~73%-ban adverz** (medián |slippage| ~88 bp) — tehát a hatás **szisztematikus**,
nem egyedi.

⚠️ **Ez a régóta ismert `entry_price=planned` defekt (§11.10) ÚJ olvasata.** Eddig **kozmetikainak**
kezeltük (*„a könyvelést NEM érinti — broker-realized"*) — **a könyvelésre ez igaz is marad**.
**A kereskedési geometriára viszont NEM kozmetikai**: a TP1/stop szintek a tervezett árhoz kötődnek,
így a **tényleges** kockázat/hozam arány a slippage-dzsel arányosan romlik.
📌 **Valószínű eredet (nem verifikált):** az execution plan még `order_type: LIMIT`-et ír (a
09-01-i CSV-ben látható), a swing pivot viszont **MKT belépőre** váltott — a szintek egy olyan árhoz
maradtak horgonyozva, ami már nem a belépő.
✅ **Kapu-hatás: a minta-definíciót nem érinti** (a `signal_attribution` belépési S_j-t és
bróker-realizáltat használ). **A kereskedési viselkedést igen → D6 SIM-napirend tétel, KAPU UTÁN**
(a prod fagyva 09-22-ig; **a breach sem indok** a módosításra, D7).

## 4. Nyitott pozíciók (10) — 09-14 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| YPF (TP1 után) | Energy | 54,21 | 56,33 | **+$108,12** |
| MANH | Technology | 207,69 | 211,54 | +$96,25 |
| EQH | Fin. Services | 53,12 | 53,67 | +$75,16 |
| IMAX | Comm. Services | 52,80 | 53,43 | +$66,40 |
| RCI | Comm. Services | 36,83 | 36,65 | −$39,60 |
| CRBG | Fin. Services | 34,97 | 34,80 | −$39,95 |
| FBP | Fin. Services | 28,72 | 28,15 | −$188,15 |
| OGE | Utilities | 47,37 | 46,23 | −$264,48 |
| ELVN | Healthcare | 57,57 | 54,43 | −$273,18 |
| TS | Basic Materials | 57,39 | 55,14 | **−$308,25** |
| **Σ** | | | | **−$767,67** |

A könyv **−$852,10 → −$767,67** (+$84,43), **4/10 pozitív**. A friss **TS** (09-11) már −3,9%-on.

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:31 submit (3 tétel), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −3,38%, BREACH, 2. nap.
- ✓ Irányadó excess-triggerek tiszták.
- 🔴 **Kitettség-rekord 69,94%** · 🟡 Financial Services 24,92% (a flag-küszöb alatt 0,08 pp-vel).

## 6. Anomáliák
- **🔴 A TP1/stop szintek a tervezett árhoz kötöttek** (§3) — **új, kódból verifikált** finding;
  a §11.10 defekt **viselkedési** következménye. Kapu után, SIM-ben.
- **🔴 MANH +2,91% — éra-rekord fill** (§2).
- **📌 Első stop-loss → visszalépés** (MANH, 3 nappal a MENTAL_SL után).
- **✅ VÁLTOZATLAN**: `exit_type` defekt (§11.17), `swing_state.exits_today`, `commission_total`,
  szektor-cap rés (§11.18), TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**, **§5.1/§5.2**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Visszalépés exit után** — **n=12**: 9 drágább / 3 olcsóbb; ma **első stop-loss utáni** eset.
- **Next-day MKT fill slippage** — CC-éra **n=51** (+MANH **+2,91%**, +IMAX +1,36%, +CRBG +0,87%):
  **38 adverz / 13 kedvező** (74,5%).
- **Kitettség** — **69,94%, éra-rekord**; 10 nyitott tétel (rekord kiegyenlítve).
- **TP1-ciklusok (lezárt)** — n=6, mind pozitív, Σ +$850,84. **MENTAL_SL** — n=7.
- **Pozitív realizált nap** — 27/74 (ma 0 exit).
- **Rally/risk-off aszimmetria** — eső nap, 0 exit → +0,45% (a §D3/M artefakt tiszta esete).

## 8. Ma (kedd, 09-15) — várt + feltevés *(nagyságrend, nem előrejelzés)*
| Idő | Ticker | Típus | Qty | Bázis / 09-14 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **MANH** | **TP1** (25→~12) | ~12–13 | 207,69 / 211,54 | **≈ +$48** |
| 21:40 | EQH | TIME_STOP | 136 | 53,12 / 53,67 | ≈ +$75 |
| **Σ** | | | | | **≈ +$123** |

📌 **A MANH TP1 a §3 finding élő esete**: a tervezett geometria szerint +1,5 ATR, a valós fillhez
mérve csak **+2,20%** a TP1 — a nyitás körüli árfolyam dönti el, pozitív vagy negatív lesz-e.
- **Fókuszlista**: (1) **D7-sor** (`cum_30d`, feloldáshoz > +$552,96 kellene); (2) a MANH TP1;
  (3) a **69,94%-os kitettség**; (4) a Financial Services 24,92%.

## 9. Freeze-sor
🔓 Freeze feloldva 08-17 — **D6: a production konfiguráció FAGYVA 2026-09-22-ig**; **D7: a breach
nem indok paraméter-változtatásra.** G1/G3–G7 élnek. Ma **nem történt** production-kód változás.
**A kapuig 6 kereskedési nap.**

## 10. A nap egy mondatban
Nulla exites nap, a `cum_30d` **pontosan a tegnapi táblázat szerint −3,38%-on, BREACH-ben** maradt
(2. nap) — miközben a rendszer **három visszalépést** vett (köztük a 3 napja stop-loss-on zárt MANH-ot,
**+2,91%-os éra-rekord fillel**), a kitettség **69,94%-os rekordra** nőtt, és a MANH első napi TP1-flagje
egy **kódból verifikált geometriai torzulást** hozott felszínre: **a TP1/stop szintek a tervezett
árhoz kötöttek, nem a fillhez** — így a MANH valós kockázat/hozam aránya **0,75 helyett 0,23**.
