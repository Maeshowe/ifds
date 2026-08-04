# IFDS Daily Review — 2026-08-03 (hétfő, Day 53/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.
> ⚠️ **A §4 markok a 08-04 pre-market IBKR-snapshotból**: 5 tételnél a `daily_pnl ≈ 0` → ezek a 08-03-i
> záró szintek; a **CTAS** és a **TTWO** viszont pre-market mozgást mutat (lásd §6).

## 🔴 A nap főcíme: a STOP-trigger monitor ELSŐ BREACH-e

```
STOP-triggerek: ⚠️ BREACH — excess_10d_sum -2.2% < -1.0%, excess_15d_sum -2.2% < -1.0%
```

**Ez nem halt-döntés** — a monitor jelez, a leállítás Tamás-döntés (human-in-the-loop). A teljes kép §6.

## 1. Fejléc
- **Day 53/63** (NYSE-count). ⚠️ `cumulative_trading_days=46`.
- **Realized net: $0,00** (0 végrehajtott exit). **Cumulative: +$347,45 (+0,347%)** — változatlan, pozitívban.
- **Net Liq: $100 471,02** — `daily_equity.json`; **napi Δ: +$304,88** (07-31: $100 166,14).
  *(IBKR 08-04 pre-market: $100 468,40.)*
- **Excess: −1,42%** — `daily_metrics::excess_return` (portfolio **0,00%** vs SPY **+1,42%**).
  **Második egymást követő rally-nap 0 realizált exittel** → a realized-only mező mechanikusan `−SPY`-t ad
  (D3-kaveát). Ez a breach közvetlen kiváltója (§6).
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR 7 ✓).

## 2. Exits (0)
Nincs végrehajtott exit. **Ma beállított flagek**: **ROIV, WAB, MLI — mind TIME_STOP** (mindhárom day-5
max_hold) → **ma (08-04) 21:40 MOC**. Ez a pénteki review §8 előrejelzésének pontos beteljesülése.

## 3. Entries (0)
Nincs mai belépő (`new_entries=[]`; submit `existing_skip`: ROIV/MLI/SAIC). A slippage-sorozat n=12 marad.

## 4. Nyitott pozíciók (7)
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| SAIC | 1 | 120,12 | +$149,30 | 10,07% | HOLD |
| MLI | **5** | 66,55 | +$96,10 | 9,63% | **TIME_STOP** (ma 21:40) |
| DE | 2 | 605,06 | +$65,70 | 4,68% | HOLD |
| TTWO | 1 | 245,54* | +$2,64 | 4,30% | HOLD |
| WAB | **5** | 296,47 | −$132,88 | 3,55% | **TIME_STOP** (ma 21:40) |
| ROIV | **5** | 33,32 | −$332,36 | 1,83% | **TIME_STOP** (ma 21:40) |
| CTAS | 3 | 200,70* | **−$398,04** | **−0,96%** ⚠️ | HOLD (lásd §6) |

`*` = pre-market mozgással. **Total unrealized: −$549,54** (−$789,66-ról **javult**). Gross position value
$38 352,70; notional 38,88%. A három TIME_STOP ma zár → a könyv jelentősen könnyül.

## 5. Ops-checklist
- ✓ **Reconcile 7/7 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Cron-lánc**: 15:31 submit (0 új), 22:00 eod_eval (**3 TIME_STOP flag**), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (7) normál.
- ✓ **`pt_events` tiszta** (9 sor).
- 🔴 **STOP-triggerek: ⚠️ BREACH** — `excess_10d_sum −2,21%` és `excess_15d_sum −2,21%` a −1,0% küszöb alatt.
  **A `mean` olvasat NEM breach-el** (−0,22% / −0,15%). Részletes elemzés: §6/P1.
- ✓ **v2 enrichment sink**: `226/125` ≡ scan-matrix **226/125** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)

### 🔴 P1 (ÚJ) — STOP-trigger BREACH a `sum` olvasaton; a D4 döntés anyagivá vált

| Olvasat | Érték | Küszöb | Státusz |
|---|---|---|---|
| `excess_10d_**mean**` | **−0,22%** | −1,0% | ✓ (messze) |
| `excess_10d_**sum**` | **−2,21%** | −1,0% | 🔴 **BREACH** |
| `excess_15d_**mean**` | −0,15% | −1,0% | ✓ |
| `excess_15d_**sum**` | −2,21% | −1,0% | 🔴 **BREACH** |
| `cum_30d` | −0,42% | −3,0% | ✓ (messze) |
| MTM-diagnosztika (10d átlag) | −0,23% | — | ≈ egyezik a realized `mean`-nel |

**A verdikt NEM stabil az olvasat szerint** — pontosan ezért számol a monitor mindkettőt (a `D4` kétértelműség
a kapu-protokollban **2026-07-25-én, ELŐRE rögzítve**: *„a monitor, amely csendben választ egy olvasatot,
elfedhet egy breach-et"*).

**A breach anatómiája** (a 10 napos ablak):
- A −2,21%-os összeg **három 0-realizált-exites napból** jön: 07-24 (−0,10%), **07-30 (−1,68%)**,
  **08-03 (−1,42%)** = **−3,20%**. E három nélkül az összeg **+0,99%** lenne.
- Ezeken a napokon `portfolio_return_pct = 0,00%` → `excess = −SPY` **mechanikusan** (D3-kaveát).
- ⚠️ **DE a mark-to-market diagnosztika NEM menti fel**: 10 napos MTM-átlag **−0,23%** ≈ a realized
  `mean` −0,22%. **A lemaradás tehát VALÓS** (~−2,2% 10 nap alatt, mindkét mérésben), nem tisztán
  mérési artifact. A D3 szerinti „ellentétes irány" eset **nem** áll fenn — a két olvasat egyetért.

**Kontextus a józansági ellenőrzéshez** (tényszerű, nem érv): a cumulative **+$347,45 (pozitív)**, a
30-napos kumulatív **−0,42%** a −3,0%-os küszöb töredéke, a NetLiq **$100 471** a $100k induló fölött.

**Amit CC javasol — és a fegyelmi kaveát, amit ki kell mondani:**
A pre-reg szöveg (`2026-05-14 §3.14`) szó szerint: *„10 napi excess vs SPY **átlag** < −1,0%"*. Az
**„átlag" = mean**, tehát a **szöveghez igazodó olvasat a `mean`** → e szerint **nincs halt-feltétel**.
⚠️ **Ezt a döntést azonban az adat MEGTEKINTÉSE UTÁN hozzuk meg** — ami a ház-szabály
(`ifds-rules.md`: *„Értékelő-motor fix csak pre-reg szöveghez igazításként"*) hatálya alá esik.
A szabály szerint ez **akkor és csak akkor** legitim, ha a döntés **a pre-reg szöveghez** igazít, nem az
eredmény felé. Itt ez teljesül (az „átlag" szó a kánon), **de a kísérőket meg kell adni**:
1. **Pre-reg forrás**: `2026-05-14 §3.14`, „10 napi excess vs SPY átlag"; a D4-kétértelműség
   **előre rögzítve** a kapu-protokoll §2-ben (2026-07-25), a breach előtt.
2. **Érzékenység**: a `mean` olvasat mellett a jelenlegi érték −0,22% vs −1,0% → **a verdikt stabil**
   (a küszöb ~4,5×-e a mért értéknek). A `sum` olvasat mellett breach. **A két olvasat különbözik**,
   ezért a döntés érdemi.
3. **Regressziós védelem**: a monitor **mindkettőt riportálja tovább**; a `sum` nem tűnik el, csak a
   halt-jelzés kötődik a `mean`-hez.
4. **Nincs újrafuttatás verdiktért** — a monitor determinisztikus, egyetlen futás.

**→ TAMÁS-DÖNTÉS (D4 lezárása): a `mean` vagy a `sum` az irányadó?** CC-ajánlás: **`mean`** (a pre-reg
szöveg szerint), a `sum` **megfigyelésként** marad. **Halt-javaslat: NINCS** — de a döntés a tiéd.

### ⚠️ P2 (ÚJ) — CTAS a stop ALATT (pre-market), HOLD státusszal
A 08-03-i eval **HOLD**-ot adott (a záró ~204,01 a 202,62-es stop **fölött**, buffer ~0,68%). A **08-04
pre-market** viszont **200,70** — a stop **alatt 1,92 dollárral** (−0,96%). Unrealized **−$398,04**, a könyv
legmélyebb tétele; harmadik egymást követő romló nap. **Ha ma is a stop alatt zár, MENTAL_SL várható a
22:00 evalban** — ez a 07-20-i USFD / 07-29-i ROIV osztály harmadik esete.

- **Ismert, nyitott** (nem ismételve): entry_price=planned (§11.10), FileVault (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=12, ma nem nőtt** (0 belépő). |medián| ~0,98%, torzítás ~0.
- **Self-reentry** — n=2, mindkettő zárt (lásd 07-31 §6). Nincs új eset.
- **Major risk-off excess** — ma nem risk-off (SPY +1,42%). **⚠️ ÚJ, a tükörkép erősödik:** a könyv
  **három egymást követő rally-napon maradt le** (07-30 −1,68%, 07-31 −0,54%, 08-03 −1,42%), miközben
  risk-off napon konzisztensen felülteljesített (07-17 +0,99%, 07-23 +0,70%, 07-29 +1,90%).
  **Ez a low-beta karakter tényszerű megnyilvánulása** — Day 63 előtt következtetés nincs, de a sorozat
  mindkét oldala már érdemi (3 vs 3).
- **TP-hit / pozitív-exit**: ma 0 exit.
- **Outage-késleltetett exit** — n=3, változatlan.
- **Várt-vs-tény**: ma nem mérhető (0 exit volt tervezve ✓).

## 8. Ma (kedd, 08-04) — várt + feltevés
**Három TIME_STOP 21:40 MOC** (mind day-5 max_hold; feltevés: keddi close ≈ hétfői mark):
- **MLI** (46) — `várt` ≈ **+$96** (mark 66,55; bázis 64,461)
- **WAB** (21) — `várt` ≈ **−$133** (mark 296,47; bázis 302,798)
- **ROIV** (152) — `várt` ≈ **−$332** (mark 33,32; bázis 35,507)

Együtt `várt` ≈ **−$369** → a cumulative +$347,45 → **~−$22** (a nulla közelébe). ⚠️ A ROIV a legnagyobb
tétel; a becslés érzékeny a mai mozgására.

- **Fókuszlista**: (1) **D4-döntés** (a breach kezelése); (2) **CTAS** — stop alatt, MENTAL_SL?;
  (3) a 3 TIME_STOP várt-vs-tény; (4) a könyv 7→4 tételre könnyül; (5) **kapu: Day 63 ~08-17 — 9 trading nap**.

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** A D4-döntés **nem paraméter-változtatás**, hanem a pre-reg
szöveg értelmezésének rögzítése (§6/P1). Freeze él Day 63-ig.

## 10. A nap egy mondatban
Csendes hétfő (0 exit, 0 belépő) három day-5 TIME_STOP flaggel, de a **STOP-trigger monitor először jelzett
breach-et** a `sum` olvasaton (−2,21%) — miközben a szó szerinti „átlag" olvasaton nincs breach (−0,22%),
a cumulative pozitív, és a CTAS pre-marketben a stopja alá csúszott.
