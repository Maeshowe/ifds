# IFDS Daily Review — 2026-08-06 (csütörtök, Day 56/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett.
> ✅ **Az IBKR MCP helyreállt** (a tegnapi kiesés után, a review ELŐTT ellenőrizve) — mindhárom végpont
> él, a teljes v6 §3 kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 56/63** (NYSE-count). ⚠️ `cumulative_trading_days=49`.
- **Realized net: −$493,70** (2 exit, komm. $2,26). **Cumulative: −$79,98 (−0,08%)** — a tegnapi rekord
  **+$413,72-ról negatívba fordult**; a két mental-stop egyetlen nap alatt elvitte a teljes pozitívumot.
- **Net Liq: $100 471,62** — `daily_equity.json`; **napi Δ: +$118,59** (08-05: $100 353,03).
  ⚠️ Fordított előjel a szokásoshoz képest: **negatív realizált mellett EMELKEDŐ NetLiq** — a két
  veszteséges tétel kikerült a könyvből, a maradék javult.
- **Excess: −0,33%** — `daily_metrics::excess_return` (portfolio **−0,49%** vs SPY −0,16%).
  Enyhén eső tape (VIX 15,25, −3,54%); a lemaradás a két realizált veszteségből jön.
- **Nyitott pozíciók: 6** (`swing_positions` ≡ IBKR 6 ✓, `reconcile::no_divergence`).

## 2. Exits (2) — típus: `state/pending_exits/` (KANONIKUS); realized: IBKR `get_account_trades`
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | 08-05 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30 | CTAS | **MENTAL_SL** | 28 | 214,96 → 202,81 | **−$340,08** (−5,65%) | ~−$345 | **+$5** |
| 15:30 | TTWO | **MENTAL_SL** | 28 | 245,49 → 240,00 | **−$153,62** (−2,23%) | ~−$293 | **+$139** |

**Összeg −$493,70** (= a `cumulative` Δ ✓). **Várt ~−$638 → tény −$493,70: +$144 (+23%)**.
A **CTAS becslése gyakorlatilag pontos** (+$5); a **TTWO jelentősen jobban zárt**, mert a fill **240,00**
a 234,99-es stop **fölött** történt — a mental-stop a 22:00-s záráskor értékel, de a végrehajtás másnap
15:30 MKT, így a közbeni visszapattanás javít. **Ez a mental-stop architektúra strukturális jellemzője**,
nem hiba (a stop nem védett szint, hanem kilépési jelzés).

> ⚠️ **Adatminőség — az ismert `exit_type` hiba megerősítve:** a `daily_metrics::trades::details`
> **mindkét exitre `TP1`-et ír**, holott a `pending_exits` (a v6 §3 szerinti **kanonikus** forrás)
> helyesen **MENTAL_SL**-t. Ez a v6-ban dokumentált, ismert defekt (fill-timestamp-alapú besorolás) —
> a review a kanonikus forrást használja. Nem új anomália, de **élő megerősítés** arról, hogy a mező
> a P1-fixig megbízhatatlan.

## 3. Entries (1) — `pt_events` 15:31 + IBKR
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| GTES | Industrials | 134 | 29,30 → **29,53** | **+0,78%** | 26,69 / 31,25 / 33,21 |

Két lábon telt (100 @ ARCA + 34 @ NYSE), komm. $1,00.
**Ez a GTES második ciklusa** — az első 07-17→07-27 (TIME_STOP, −$29,31). **8 trading nap rés**
(07-28..08-05 egyszer sem jelölt GTES-t) → **friss jel, NEM self-reentry** (mint a JAZZ tegnap).

## 4. Nyitott pozíciók (6) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| SAIC | 4 | 124,60 | **+$179,35** | 13,30% | HOLD |
| DE | **5** | 613,71 | +$152,20 | 6,02% | **TIME_STOP** (holnap 21:40) |
| VLTO | 1 | 97,67 | +$36,24 | 7,55% | HOLD |
| GTES | 0 | 28,84 | −$93,46 | 7,45% | HOLD |
| JAZZ | 1 | 258,58 | −$120,35 | 4,80% | HOLD |
| SSNC | 1 | 79,55 | **−$192,75** | 4,85% | HOLD |

**Total unrealized: −$38,77** — gyakorlatilag nulla, és **jelentős javulás** a könyv összetételében
(a két legrosszabb tétel realizálódott). Notional **38,14% → 29,12%**. **Nincs kritikusan szűk buffer**
(a legszűkebb JAZZ 4,80%) — ez a legkiegyensúlyozottabb könyv hetek óta.

## 5. Ops-checklist
- ✓ **Reconcile 6/6 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 15:30 close (2 MENTAL_SL), 15:31 submit (GTES), 22:00 eod_eval (DE TIME_STOP flag),
  22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (6) normál.
- ✓ **`pt_events` tiszta** (9 sor).
- ⚠️ **STOP-triggerek** (D4: a **`mean` az irányadó**): `excess_10d_mean` **−0,37%** vs −1,0% → **✓ nincs
  halt-feltétel**. A `sum` megfigyelésként breach-el (−3,72%). **A `cum_30d` tovább romlik** — §6.
- ✓ **v2 enrichment sink**: `380/240` ≡ scan-matrix **380/240** — pontos egyezés (második nap friss contexttel).
- ✓ **IBKR MCP** helyreállt — a review előtt ellenőrizve, mindhárom végpont él.

## 6. Anomáliák (új/változott/lezárt)
- **✅ LEZÁRVA — CTAS/TTWO mental-stop végrehajtva.** A hetek óta figyelt két szűk tétel kikerült a
  könyvből (−$493,70 együtt). **A mechanizmus végig szabályosan működött**: flag a 22:00-s evalban →
  végrehajtás másnap 15:30. A CTAS a belépés (07-29) óta végig veszteséges volt, a TTWO 07-31 óta.
- **⚠️ Változott — a `cum_30d` NÉGY NAPJA egyirányúan romlik** (megfigyelés, D4 szerint nincs halt):
  | Nap | `10d_mean` | `cum_30d` |
  |---|---|---|
  | 08-03 | −0,22% | −0,42% |
  | 08-04 | −0,38% | −1,08% |
  | 08-05 | −0,27% | −1,32% |
  | **08-06** | **−0,37%** | **−1,81%** |
  A `cum_30d` a **−3,0%-os küszöb 60%-ánál** jár, és a romlás **monoton**. A `mean` oldalazik
  (−0,22…−0,38%), a küszöbtől 2,7×. **A 30-napos ág a követendő** — ha tartja az ütemet (~−0,45%/nap),
  a küszöböt ~2-3 hét alatt elérheti. Nem előrejelzés, trajektória-rögzítés.
- **📌 Megfigyelés — a mental-stop fill a stop FÖLÖTT is telhet.** A TTWO 240,00-en telt a 234,99-es
  stop helyett (+$139 a becsléshez képest). A mental-stop **nem védett szint**: a 22:00-s eval jelez,
  a végrehajtás másnap 15:30 MKT-n történik → a közbeni mozgás **mindkét irányba** hat. A CTAS-nál
  ez ~nulla volt (+$5), a TTWO-nál +$139. **Day 63-input** a stop-hatékonyság értékeléséhez.
- **Ismert, nyitott** (nem ismételve): `exit_type` mező hibás (§2, élő megerősítés), entry_price=planned
  (§11.10 — a GTES-nél ma is: tervezett 29,30 vs fill 29,53, a stop a tervezettből számolva),
  FileVault (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=16** (+GTES +0,78%, adverz). **|medián| 0,94%**; előjeles átlag
  **+0,28%** (11 adverz / 5 kedvező). *(FRL `cost_model.json` input.)*
- **Self-reentry** — **n=2, változatlan**. A GTES (8 napos rés) és a JAZZ (6 napos rés) **nem** tartozik
  ide — mindkettő friss jel alapján, nem kényszerű round-trip. **A megkülönböztetés következetes.**
- **Rally/risk-off aszimmetria** — ma enyhén eső nap (SPY −0,16%), a könyv **alulteljesített** (−0,33%),
  de ez a **realizált veszteségekből** jön, nem mark-mozgásból. A sorozat állása változatlan
  (4 rally-lemaradás vs 4 risk-off felülteljesítés).
- **TP-hit / pozitív-exit**: ma 2 exit, **0 pozitív** (mindkettő mental-stop). Ez az első nap, amikor
  a mental-stop érdemi veszteséget realizált.
- **Outage-késleltetett exit** — n=3, változatlan.
- **Várt-vs-tény pontosság**: ma **+$144 / +23%**. A becslés **aszimmetrikusan pontos**: a CTAS-nál +$5
  (0,1%), a TTWO-nál +$139 (47%) — a különbség a fill-időzítésből (§6).

## 8. Holnap (péntek, 08-07) — várt + feltevés
- **DE TIME_STOP** 21:40 MOC (10) — `várt` ≈ **+$152** (feltevés: pénteki close ≈ mai mark 613,71;
  IBKR-bázis 598,49). A day-5 max_hold zárja; **a könyv legnagyobb nyertes tétele**.
- **Péntek → heti zárás (W32)**: `weekly_metrics.py` + Telegram.
- **Fókuszlista**: (1) a DE exit várt-vs-tény; (2) a `cum_30d` trajektóriája (−1,81%, monoton romlás);
  (3) a három friss belépő (SSNC −$193, JAZZ −$120, GTES −$93) — mindhárom víz alatt;
  (4) a heti zárás (W32) képe; (5) **kapu: Day 63 ~08-17 — 6 trading nap**.

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
A két hetek óta figyelt szűk tétel (CTAS, TTWO) mental-stopon kiszállt −$493,70-tel, ami a kumulatívot
rekordról (+$413,72) negatívba fordította (−$79,98) — de a könyv ezzel kitisztult (unrealized ~0, nincs
szűk buffer), miközben a `cum_30d` negyedik napja monoton romlik (−1,81%, a küszöb 60%-a).
