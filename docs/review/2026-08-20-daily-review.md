# IFDS Daily Review — 2026-08-20 (csütörtök, Day 66/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett; IBKR MCP kereszt-ellenőrzés lefutott.

## 1. Fejléc
- **Realized net: $0,00** — **0 exit**, ahogy a 08-19-i §8 előre jelezte. **Cumulative változatlan:
  −$738,18 (−0,74%)**.
- **Net Liq: $98 629,14** — napi Δ **−$312,74** (08-19: $98 941,88).
- **Excess: +0,84%** — `daily_metrics::excess_return` (portfolio **0,00%** vs SPY −0,84%).
  🔴 **Ez a §D3/M szélsőérték-eset, élesben**: az `excess` ma **pontosan `−SPY`** (§6).
  **MTM-olvasat: +0,52%** — ugyanaz az előjel, de **0,32 pp-tal kisebb**.
- **VIX 15,99 (+7,39%)** — risk-off nap (SPY +0,21% → **−0,84%**).
- **Nyitott pozíciók: 9** (7-ről; `swing_positions` ≡ IBKR ✓, `reconcile_silent_ok`).

## 2. Exits (0)
Nincs végrehajtott exit. **Ma beállított flagek: 4** → holnap (§8).

## 3. Entries (2) — `daily_metrics::execution`
| Ticker | Qty | Planned→Fill | Slippage | Komm. (IBKR) |
|---|---|---|---|---|
| PSO | 530 | 16,06 → **16,07** | +0,06% (adverz) | $2,65 |
| FMS | 288 | 23,84 → **23,68** | **−0,67%** (**kedvező**) | $1,44 |

**Qty-súlyozott átlag: −0,20%** — a **CC-éra első kedvező napi átlaga**. Belépő-jelöltek top-3:
DLB 90,3 | **PSO 86,1** | **FMS 83,7**; 76 ticker a küszöb felett, 2 belépő.

**Bróker-verifikáció** (`get_account_trades`): PSO BUY 530 @ 16,07 13:31:14Z; FMS BUY 288 @ 23,68
13:31:10Z; **0 SELL** ✓ Együttes komm. **$4,09**.

## 4. Nyitott pozíciók (9) — 08-20 **záró** mark (IBKR `get_account_positions`)
| Ticker | Bázis | Záró | Unrealized | Napi Δ |
|---|---|---|---|---|
| DLB | 61,96 | 64,19 | **+$209,56** | **+$140,06** |
| IMAX | 52,76 | 52,74 | −$1,88 | −$85,36 |
| PSO | 16,08 | 16,07 | −$2,65 | −$2,65 (ma nyílt) |
| FMS | 23,69 | 23,43 | −$73,44 | −$73,44 (ma nyílt) |
| SN | 187,64 | 179,98 | −$183,88 | −$30,24 |
| ZBRA | 379,73 | 360,52 | −$192,10 | **+$58,70** |
| BANC | 19,77 | 18,65 | −$299,94 | −$78,01 |
| FBIN | 50,07 | 45,01 | −$379,75 | −$111,00 |
| EQH | 53,03 | 48,31 | **−$481,42** | −$168,30 |
| **Σ** | | | **−$1 405,50** | **−$350,24** |

A könyv **−$1 052,56 → −$1 405,50** (**−$352,94**). A **DLB** a legjobb tétel (+$209,56) — két nappal
a §3-ban mért **−$79,22 self-reentry súrlódás** után. Az **EQH** a legrosszabb és tovább mélyül.

**⚠️ Kitettség-ugrás**: `total_notional` **32,94% → 48,32%** egyetlen nap alatt (7 → 9 tétel).
Limit-sértés **nincs** (`max_concurrent` 12; legnagyobb szektor **Communication Services 13,12%**
vs 30%-os cap). Új szektor: **Healthcare** (FMS). Megfigyelés-tárgy, nem anomália.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 13:31 submit (PSO, FMS), 21:40 time_stop (nincs flag),
  22:11 eod (`Trades: 0`), metrics, review_data.
- ✓ **`reconcile_silent_ok`** — state ≡ IBKR, 0 divergencia. Bróker: 0 SELL ✓ ≡ realized $0,00.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó): `excess_10d_mean` **+0,04%** →
  **ELŐSZÖR POZITÍV**, és **6× javult sorban** (−0,36% → −0,17% → −0,01% → **+0,04%**).
  🟢 `excess_10d_sum` szintén **pozitív** (+0,41%) — a BREACH-ről tegnap jött le.
  ⚠️ `excess_15d_sum` **romlott**: −3,70% → **−4,76%** (BREACH). Ok: a 15 napos ablak **még tartja**
  a 08-13 (−$409) és 08-14 (−$237) napokat, amelyek a 10 naposból már kiestek.
  **D4: a `sum` megfigyelés, nem trigger.** `cum_30d` −1,28% ✓
- ℹ️ **`Day 66/63`** — számláló-artefakt (a periódus 08-17-én lezárult), kapu **2026-09-22**.

## 6. Anomáliák (új/változott/lezárt)
- **🔴 A §D3/M SZÉLSŐÉRTÉK-ESET MA ELŐSZÖR ÁLL FENN ÉLESBEN — pontosan a tegnap jelzett módon.**
  0 exit mellett `portfolio_return_pct ≡ 0,00%`, tehát **`excess = −SPY` = +0,84%**. A rendszer
  ma **„+0,84% felülteljesítést" könyvel**, miközben a **nyitott könyv −$352,94-et vesztett** és a
  **NetLiq −$312,74-gyel esett**. A MTM-olvasat **+0,52%** — ugyanaz az előjel (mert az index még
  nagyobbat esett), de a rés **0,32 pp**.
  📌 **Ez nem hiba, hanem a mező dokumentált korlátja** (§D3/M). A pre-reg mező **marad az
  irányadó** (D3). Frissített számok: **0-realizált nap 20/57 (35,1%)**; ellentétes előjelű
  **12/45**. **A kapu-riportban a 0-exites napok hozzájárulását külön ki kell mutatni.**
- **🟡 P2 (ÚJ, PONTOSÍTOTT DEFEKT) — a `swing_state.exits_today` MEZŐ FÉLREVEZETŐEN VAN ELNEVEZVE.**
  Nem a napi exiteket tartalmazza, hanem a **ma beállított flageket a HOLNAPI végrehajtásra** —
  azaz a `next_day_planned` tükörképét. **12/12 napon ellenőrizve** (08-04 → 08-20), kivétel nélkül:
  | Nap | `exits_today` | `next_day_planned` | tényleges exit |
  |---|---|---|---|
  | 08-19 | `{}` | — | **ADT** |
  | 08-20 | `{TIME_STOP:2, MENTAL_SL:1, TP1:1}` | 4 flag | **nincs** |
  A tegnapi review ezt még csak „inkonzisztens"-ként jelezte; **most a szemantika azonosítva**.
  **Ez KÜLÖN defekt** a már ismert `exit_type`-tól. **Hatás: display-only.**
  ✅ **A kaput NEM érinti**: a `signal_attribution` **2. invariánsa** kimondja, hogy az `exit_type`
  **kizárólag** a `state/pending_exits/`-ből jön — ezt a mezőt a betöltő **nem olvassa**.
  Javítás: **kapu utáni** cleanup (átnevezés `exit_flags_set_today`-re).
- **🟡 P3 (ÚJ) — a `commission_total` csak az EXIT-lábat számolja.** Ma **$0,00**-t jelent,
  miközben a bróker a 2 belépőn **$4,09**-et számított fel.
  ✅ **NEM P&L-hiba**: az IBKR a belépő-jutalékot a **költségbázisba** építi — verifikálva a DLB-n
  (`average_price` 61,96064 vs fill 61,95 → 0,01064 × 94 = **$1,00**, pontosan a belépő-komm.).
  A realizált P&L tehát **mindkét lábra nettó**, a `cumulative` helyes. Csak a **napi jutalék-adat**
  alulmutat. Kapu utáni riport-tétel.
- **✅ VÁLTOZATLAN**: `entry_price=planned` (§11.10), `uw_shadow` üresen ír (UW kivezetve),
  **FileVault** (parkolva), **`docs/analysis/` sync-rés** (a kapu előtt zárandó).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **CC-éra n=28** (+PSO +0,06%, +FMS −0,67%): **20 adverz / 8 kedvező**.
  **Teljes swing-éra n=54**: 36 adverz / 18 kedvező. *(A címke-korrekció a 08-19-i §6-ban.)*
  📌 Az **FMS −0,67%** a CC-éra **4.** legkedvezőbb fillje (rekord: DE −2,06% 07-30, USFD −1,89%
  07-23, GTES −1,00% 07-17) — de a napi **qty-súlyozott átlag (−0,20%)** a **CC-éra első kedvező
  napi átlaga**.
- **Self-reentry** — n=3 változatlan. A **DLB** (a 3., mért súrlódású eset) ma **+$209,56**-on áll.
- **„Rés utáni visszalépés"** — n=2 lezárt, **1 nyitva**: **EQH −$481,42** (08-19: −$313,12 →
  **tovább mélyült**, 4. egymást követő napon). **Holnap MENTAL_SL-en zárhat** (§8).
- **Outage-késleltetett exit** — n=4. **„Stop-közeli"** — n=5. Mindkettő változatlan.
- **Rally/risk-off aszimmetria** — ma eső nap, realized szerint +0,84% felülteljesítés.
  ⚠️ **Ez a sorozat mai eleme a §D3/M-artefakt tiszta esete** (0 exit) — a sorozat **e naptól
  külön jelölendő**. Sorozat (realized-olvasat): 7 rally-lemaradás vs **8** eső-napi felülteljesítés,
  **ebből 4 nulla-exites** (azaz mechanikus).
- **TP-hit / pozitív-exit**: ma nem mérhető (0 exit volt tervezve ✓ — a becslés **pontos** volt).

## 8. Holnap (péntek, 08-21) — várt + feltevés
**Négy exit-flag — a swing-éra egyik legsűrűbb exit-napja** (feltevés: pénteki ár ≈ mai záró):

| Idő | Ticker | Típus | Qty | Mai záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **EQH** | **MENTAL_SL** | 102 | 48,31 | **≈ −$481** |
| 15:30 | **DLB** | **TP1** (50%) | 94 → 47 | 64,19 | **≈ +$105** |
| 21:40 | SN | TIME_STOP | 24 | 179,98 | ≈ −$184 |
| 21:40 | FBIN | TIME_STOP | 75 | 45,01 | ≈ −$380 |
| **Σ** | | | | | **≈ −$940** |

Ha teljesül: cumulative **−$738,18 → ~−$1 678**. A könyv **9 → 5,5 tételre** csökken.

- 📌 **A DLB TP1 lenne a self-reentry-ciklus első pozitív realizálása** — a −$79,22 súrlódás után.
- 📌 **Az EQH MENTAL_SL a „rés utáni visszalépés" 3. esetének lezárása** lenne, és a
  sorozatot **3/3 negatívra** állítaná (JAZZ −$251, GTES −$266, EQH ≈ −$481).
- ⚠️ **A becslés bizonytalansága ezen a héten kétszer is $100+ volt** (08-18 tételenként
  ellentétes irányban, 08-19 +$132) — a fenti Σ **nagyságrendi**, nem előrejelzés.
- **Fókuszlista**: (1) a 4 exit végrehajtása; (2) az **EQH** és a sorozat lezárása; (3) a **DLB TP1**;
  (4) a STOP-`mean` (+0,04%) és a `15d_sum` (−4,76%) széttartása; (5) **W34 heti zárás**
  (`weekly_metrics.py`) — péntek.

## 9. Freeze-sor
🔓 A parameter freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció
FAGYVA marad 2026-09-22-ig** (kétsávos: a revíziók a SIM-L2 / Mode 2 re-score infrán).
A **G1/G3–G7 guardrailek változatlanul élnek**. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Nulla exit mellett a rendszer **„+0,84% felülteljesítést" könyvelt egy olyan napon, amikor a
nyitott könyv $353-at vesztett** — a §D3/M szélsőérték-esete pontosan úgy állt elő, ahogy tegnap
jeleztem —, miközben a kitettség egy nap alatt 33%-ról **48%-ra ugrott**, a STOP-`mean` **először
lett pozitív** (+0,04%), és holnapra **négy exit-flag** áll, köztük a „rés utáni visszalépés"
harmadik esetének (EQH, −$481) várható lezárása.
