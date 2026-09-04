# IFDS Daily Review — 2026-09-03 (csütörtök, Day 76/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ Az IBKR MCP connector a session során ki-be kapcsolt — a bróker-oldali kereszt-ellenőrzés
> **ma kimaradt**. Helyette: Mini `reconcile_state` **silent OK** (`state ≡ IBKR`), a `submit`
> és a Phase 6 logok idézve, záró markok **Polygon**-ból.

## 1. Fejléc
- **Realized net: −$23,06** (gross −$22,03, komm. $1,03) — **1 exit**.
- **Cumulative: −$2 265,47 (−2,27%)**.
- **Net Liq: $99 194,15** — napi Δ **+$705,33**, **a legnagyobb egynapos emelkedés a swing-érában**.
- **Excess: −1,07%** (portfolio −0,02% vs SPY **+1,05%**). **MTM: −0,33%** — azonos előjel, 0,74 pp rés.
- **VIX 14,32 (−5,79%)**, SPY **+1,05%** — erős rally, a VIX az éra mélypontja közelében.
- **Nyitott pozíciók: 7** (`reconcile_silent_ok` ✓).

## 2. Exits (1)
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:30 | **AMR** (TP1-maradék) | TIME_STOP | 7 | 219,22 → **215,93** | **−$23,06** (−1,50%) | ≈ **+$99** | **−$122** |

⚠️ **Az AMR egyetlen ülés alatt −7,44%-ot esett** (233,29 → 215,93), **miközben az SPY +1,05%-ot
emelkedett**. Ez a **harmadik $100+ becslési tévedés három ülés alatt**, és **mind a három egyedi
papír-sokkból** jött:

| Nap | Ticker | Papír-mozgás | SPY | Tévedés |
|---|---|---|---|---|
| 09-01 | RGEN | **−6,07%** | −0,69% | **−$282** |
| 09-02 | NWBI | **+2,00%** | +0,44% | **+$226** |
| 09-03 | AMR | **−7,44%** | **+1,05%** | **−$122** |

📌 A „tegnapi záró ≈ mai záró" feltevés **rendszeresen és nagy amplitúdóval bukik** egyedi
papír-mozgáson. A §9 „várt" oszlop **nagyságrend**; ezt innentől a táblázatban is jelölöm.

### ✅ Az AMR TP1-ciklus mérlege (lezárva) — az első, ahol a maradék veszített
| Esemény | Dátum | Összeg |
|---|---|---|
| **TP1** (6 db @ 230,01) | 08-31 | **+$64,57** |
| **TIME_STOP** (7 db @ 215,93) | 09-03 | **−$23,06** |
| **Nettó** | | **+$41,51** |

📌 **A negyedik teljesen lezárt TP1-ciklus — és az első, amelynek a MARADÉK lába veszteséges.**
Mind a négy ciklus **így is pozitív**: IMAX **+$69,48** | DLB **+$95,30** | PSO **+$288,57** |
AMR **+$41,51** → **Σ +$494,86**. ⚠️ **n=4, nem általánosítható (G3)** — de a D6 SIM-napirend
TP1-tételének növekvő inputja: **a TP1-láb mind a négyszer bezsebelte a nyereséget**, a
maradék pedig 3× hozzátett, 1× elvett.

## 3. Entries (0) — verifikált ok
56 ticker a küszöb felett, **0 belépő**. **A `submit` log szerint** az execution plan
**IMAX, FBP, INTA** tickereket tartalmazta — **mind a hármat már tartottuk**:

```
Skipping IMAX / FBP / INTA: already has position or swing state
[SWING] Submitted: 0 tickers — state file untouched (race guard, 8 open)
```

A Phase 6 oldali szűrés (intraday log): `Analyzed: 56 | Passed: 53 | Excluded — sector limit: 5
position limit: 45 risk limit: 0 exposure limit: 0` → **53 − 5 − 45 = 3**, és mind a 3 tartott.

## 4. 🟡 ÚJ FINDING — a szektor-cap MONITOROZÁSI RÉS (kódból verifikálva)
Ma a `sector_cap_proximity` flag **NEM tüzelt** (a legnagyobb szektor Communication Services
**21,86%**, a figyelmeztetési küszöb 25%) — **mégis 5 jelöltet zárt ki a szektor-limit**.

**Az ok a kódban** (`phase6_sizing.py:1581`):
```python
if new_sector_total > sector_cap_usd:
```
A **Phase 6 ellenőrzése ELŐRETEKINTŐ**: a *hozzáadás utáni* szektor-összeget méri a caphez.
A review `sector_cap_proximity` flagje viszont a **jelenlegi** kitettséget nézi.

> 🟡 **Következmény: a flag NÉMA MARADHAT, miközben a cap ténylegesen köt.**
> Ma pontosan ez történt: 0 figyelmeztetés, 5 kizárás. A 09-01-i „a cap köt" finding tehát
> **nem egyszeri állapot** volt — a korlát **azóta is aktív**, csak láthatatlanul.
> **Teendő (kapu UTÁN, D6: prod fagyva):** a napi flag legyen szintén előretekintő, vagy a
> review olvassa be a Phase 6 `excluded_sector_limit` számlálót. **Leíró rögzítés (G3).**

## 5. Nyitott pozíciók (7) — 09-03 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| CRBG | Fin. Services | 32,93 | 34,75 | **+$370,47** |
| RCI | Comm. Services | 36,88 | 38,00 | **+$297,00** |
| FBP | Fin. Services | 27,91 | 28,45 | **+$206,55** |
| NWS | Comm. Services | 34,45 | 34,72 | +$60,82 |
| INTA | Technology | 42,90 | 43,11 | +$21,44 |
| IMAX | Comm. Services | 52,49 | 51,92 | −$47,48 |
| IMVT | Healthcare | 41,49 | 39,12 | **−$262,96** |
| **Σ** | | | | **+$645,85** |

🟢 **A könyv −$82,83 → +$645,85** (**+$728,68 egyetlen nap alatt**) — **5/7 pozitív**, és a
**swing-éra egyik legerősebb könyv-napja**. Három tétel adta a javulás nagy részét
(CRBG, RCI, FBP). Az **IMVT** magányosan romlik (−$262,96, negyedik napja a legrosszabb).

## 6. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:31 submit (0 tétel), 21:40 time_stop
  (AMR MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,29%** ✓ | `excess_15d_mean` **−0,10%** ✓ | **`cum_30d` −2,37%** ✓
  ⚠️ **A `10d_mean` érdemben romlott** (−0,10% → −0,29%) a mai **−1,07%**-os excess-nap miatt.
  Bőven a küszöb felett, de **a sorozat megfordult**.
  ⚠️ `excess_10d_sum` **−2,90%** és `excess_15d_sum` −1,44% BREACH — **D4: megfigyelés**.
- 📌 **`cum_30d` −2,30% → −2,37%** (küszöbig $626,91). **A holnapi gördülés erősen kedvező**:
  a **07-23-i nap gördül ki, ami −$531,32** volt.

## 7. Anomáliák (új/változott/lezárt)
- **🟡 Szektor-cap monitorozási rés** (§4) — **kódból verifikálva**, új finding.
- **📌 A becslési módszer harmadik egymást követő bukása** (§2) — mind egyedi papír-sokk.
- **📌 A `10d_mean` megfordult** (−0,10% → −0,29%) — az egyetlen napi −1,07%-os excess miatt.
  Ez a mai nap **§D3/M-tiszta esete**: ~nulla realizált (−0,02%) egy **+1,05%-os rally-napon**
  → az `excess` gyakorlatilag **`−SPY`**. **Volt exit** (AMR), de olyan kicsi (−$23,06 ≈ −0,02%),
  hogy a mező viselkedése a 0-exites esettel azonos.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (normál ablak, §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TIME_STOP:1, TP1:2}` ≡ a **mai** RCI/CRBG/FBP flagek), `commission_total`
  csak exit-láb, `entry_price=planned`, `reconcile` csak ticker-halmaz, **FileVault**,
  **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 8. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-ciklusok (teljesen lezárt)** — **n=4, mind pozitív**: IMAX +$69,48 | DLB +$95,30 |
  PSO +$288,57 | **AMR +$41,51**. **Σ +$494,86.** Az AMR az első, ahol a **maradék** veszített.
- **Pozitív realizált nap** — 25/68 (ma nem).
- **Next-day MKT fill slippage** — CC-éra n=40, változatlan (ma 0 belépő).
- **Szektor-koncentráció** — Comm. Services **21,86%** (legnagyobb); a **cap mégis kizárt 5-öt** (§4).
- **Kitettség** — 48,03%.
- **Rally/risk-off aszimmetria** — **erős rally-nap** (SPY +1,05%), realized szerint **−1,07% lemaradás**
  — a sorozat legnagyobb egynapos lemaradása. Sorozat: **13** rally-lemaradás vs 12 eső-napi
  felülteljesítés.
- **Ellentétes-előjelű nap** — 14/54 (ma nem; mindkettő negatív).
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **TP-hit / pozitív-exit**: **0/1**. **Várt-vs-tény**: **−$122** (§2).

## 9. Ma (péntek, 09-04) — várt + feltevés *(nagyságrend, nem előrejelzés)*
**Három exit — a hét legsűrűbb napja**:

| Idő | Ticker | Típus | Qty | Bázis / 09-03 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **RCI** | **TP1** (264→132) | 132 | 36,88 / 38,00 | **≈ +$148** |
| 15:30 | **CRBG** | **TP1** (203→101) | 101 | 32,93 / 34,75 | **≈ +$184** |
| 21:40 | **FBP** | TIME_STOP | 379 | 27,91 / 28,45 | **≈ +$207** |
| **Σ** | | | | | **≈ +$539** |

📌 **Mind a három POZITÍV lenne** — ez a swing-éra első ilyen napja. Ha teljesül:
cumulative −$2 265,47 → **~−$1 726**. **De**: az elmúlt három ülés becslési hibája
$282 / $226 / $122 volt — **ez nagyságrend**.
📌 Az **FBP** a **kapuig hátralévő** időszak egyik legnagyobb tétele (379 db, $10 771 notional).

- **Fókuszlista**: (1) a három exit; (2) a **`cum_30d`** (−2,37%, a gördülés ma kedvező);
  (3) a **10d_mean** megfordulása (−0,29%); (4) a **W36 heti zárás**; (5) az IMVT (−$262,96).

## 10. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 12 kereskedési nap.**

## 11. A nap egy mondatban
Egy **+1,05%-os rally-napon** a realizált gyakorlatilag nulla maradt (−$23,06, az **AMR egy ülés
alatt −7,44%-ot esett**, $122-vel a becslésem alatt) — így a realized-olvasat **−1,07%-os
lemaradást** mért, a sorozat legnagyobbját —, **miközben a nyitott könyv $728,68-at javult**
(−$82,83 → **+$645,85**, 5/7 pozitív, a swing-éra egyik legerősebb könyv-napja); mellékesen
lezárult a **negyedik TP1-ciklus** (AMR +$41,51, mind a négy pozitív, Σ +$494,86), és
**kódból verifikáltam egy monitorozási rést**: a Phase 6 szektor-check előretekintő, a napi
flag viszont nem — így a cap **némán is köthet**, ahogy ma 5 jelöltnél tette.
