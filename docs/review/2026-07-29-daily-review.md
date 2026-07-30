# IFDS Daily Review — 2026-07-29 (szerda, Day 50/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott (mind a 4 exit fill verifikálva).
> ⚠️ A §4 markok a 07-30 pre-market IBKR-snapshotból (a `daily_pnl` ~0 → gyakorlatilag a 07-29-i záró
> szintek). Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 50/63** (NYSE-count). ⚠️ `cumulative_trading_days=43` (gap: outage-napok).
- **Realized net: +$359,68** (4 exit, komm. $4,36). **Cumulative: +$170,93 (+0,171%)** — **a kumulatív
  POZITÍVBA fordult**, először a 07-21-i +$107,62 óta (a 07-23-i −$531 exit sodorta negatívba).
- **Net Liq: $100 455,17** — `daily_equity.json`; **napi Δ: −$596,58** (07-28: $101 051,75).
  ⚠️ **A NetLiq CSÖKKENT a +$359,68 realizált mellett** — a maradó könyv unrealizedje esett többet
  (WAB és ROIV, lásd §4/§6).
- **Excess: +1,90%** — `daily_metrics::excess_return` (portfolio **+0,36%** vs SPY **−1,54%**).
  **Risk-off nap** (VIX 20,22, **+11,04%**) — a könyv érdemben felülteljesített.
- **Nyitott pozíciók: 5** (`swing_positions` ≡ IBKR 5 ✓) — 6-ról, a 4 exit és 1 belépő nettójában.

## 2. Exits (4) — típus: `pending_exits`; realized: IBKR `get_account_trades` (mind verifikálva)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | 07-28 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30 | USFD | TP1 | 28 | 94,30 → 100,34 | **+$169,24** (+6,41%) | ~+$202 | −$33 |
| 15:30 | MLI | TP1 | 46 | 64,48 → 65,02 | **+$24,65** (+0,83%) | ~+$94 | **−$69** |
| 21:59 | PFGC | TIME_STOP (MOC) | 30 | 110,47 → 116,65 | **+$185,32** (+5,59%) | ~+$153 | **+$32** |
| 21:59 | EQH | TIME_STOP (MOC) | 126 | 48,58 → 48,42 | **−$19,53** (−0,32%) | ~+$104 | **−$124** |

**Összeg +$359,68** (= a `cumulative` Δ ✓). **Várt ~+$553 → tény +$359,68 (−$193, −35%)** — a sorozat
eddigi legnagyobb elmaradása, és az ok azonosítható: a becslés feltevése „holnapi ár ≈ mai mark" volt,
de **07-29 risk-off nap lett** (SPY −1,54%). Az MLI és az EQH visszaadta a 07-28-i emelkedést a fill előtt.
A PFGC ellenben **felülmúlta** (+$32) — napközben tovább emelkedett. 3 pozitív / 1 negatív exit.

## 3. Entries (1) — `pt_events` 15:31 + IBKR
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| CTAS | Industrials | 28 | 214,90 → **214,88** | **−0,01%** | 202,62 / 224,11 / 233,32 |

A sorozat **legkisebb slippage-e** (1 bázispont, kedvező irányban), IBKRATS-en.

## 4. Nyitott pozíciók (5)
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| USFD | 4 | 102,35 | **+$226,58** | 12,21% | HOLD (TP1 után maradó 28) |
| CTAS | 0 | 216,53 | +$45,20 | 6,42% | HOLD |
| MLI | 2 | 65,40 | +$43,20 | 8,04% | HOLD (TP1 után maradó 46) |
| WAB | 2 | 292,00 | **−$226,75** | 2,08% | HOLD |
| ROIV | 2 | 32,87 | **−$400,76** | **0,49%** ⚠️ | HOLD (lásd §6) |

**Total unrealized: −$312,53** (IBKR) — a 07-28-i +$634,39-ról fordult meg; a két negatív (ROIV, WAB)
együtt −$627,51. Gross position value $23 048,42; notional **32,27% → 23,32%** equity (a legkönnyebb könyv
a swing-érában). **Holnapra nincs exit-flag.**

## 5. Ops-checklist
- ✓ **Reconcile 5/5 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 15:30 close (USFD+MLI TP1), 15:31 submit (CTAS), 21:40 time_stop (PFGC+EQH MOC),
  22:00 eod_eval (0 új flag), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (5) normál.
- ✓ **`pt_events` tiszta** (11 sor, nincs teszt-szennyezés).
- ✓ **STOP-triggerek: ✓ nincs breach** (mind a pre-reg ablak kiértékelve).
- ✓ **v2 enrichment sink**: `226/131` ≡ scan-matrix **226/131** — pontos egyezés.
- ✓ **IBKR MCP** helyreállt (a 07-28-i részleges kiesés után mindhárom végpont működik).

## 6. Anomáliák (új/változott/lezárt)
- **⚠️ P2 (ÚJ) — ROIV stop-buffer 0,49%, mégis HOLD.** A mark 32,87 a 32,71-es stop **fölött 16 centtel**;
  az unrealized −$400,76 (−7,4%), a könyv legmélyebb tétele. A 22:00 eval **HOLD**-ot adott, tehát a
  Polygon-close a szint fölött volt. **Ez ugyanaz az osztály, mint a 07-20-i USFD-eset** (ott a −0,05%-os
  határeset forrás-timing artifactnak bizonyult, és másnap MENTAL_SL-t kapott). **Holnapi watch: ha a ROIV
  a 32,71 alá zár, MENTAL_SL várható; ha alá megy és mégis HOLD marad, P1-re emelendő.**
- **⚠️ Változott — WAB fordulat.** +$39,59 → **−$226,75** két nap alatt (302,80 → 292,00, −3,6%);
  stop-buffer 2,08%. Nincs flag, de a második legszűkebb. Megfigyelés.
- **✅ LEZÁRVA — PFGC self-reentry, az első teljesen mérhető eset** (a sorozat n=2 első zárása).
  A max_hold 07-20-án kiléptette (109,18), a jel 07-21-én visszaengedte (110,42; round-trip súrlódás
  ~**−$74**). A visszalépett 60 db teljes realizált eredménye: TP1 30 @ 114,07 (**+$107,92**) +
  TIME_STOP 30 @ 116,65 (**+$185,32**) = **+$293,24**. Tényszerű összegzés: a kényszerű round-trip
  ~$74-be került, a visszalépett pozíció ennek ~4×-esét hozta. **Egyetlen eset (n=1 zárt) — nem
  általánosítható**, Day 63-input marad.
- **Ismert, nyitott** (nem ismételve): entry_price=planned (§11.10), FileVault (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=9** (+CTAS −0,01%). **|medián| = 1,00% (100 bp) — n=5/8/9 mellett
  VÁLTOZATLAN**; előjeles átlag **+0,26%**; **6 adverz / 3 kedvező**. *(FRL `cost_model.json` input.)*
- **Self-reentry** — n=2, ebből **1 teljesen zárt** (PFGC, +$293,24 a visszalépett lábon, ~$74 round-trip
  súrlódás mellett); USFD részben realizált (TP1 +$169,24), maradó 28 db +$226,58 unrealized.
- **Major risk-off excess** — **ma hozzáadva** (SPY −1,54%): portfolio +0,36%, **excess +1,90%**.
  A könyv risk-off napon eddig **konzisztensen** felülteljesített (07-17 +0,99%, 07-23 +0,70%, ma +1,90%).
- **TP-hit / pozitív-exit**: ma **4 exit, 3 pozitív** (75%) — 2 TP1 (USFD +6,41%, MLI +0,83%),
  1 TIME_STOP pozitív (PFGC +5,59%), 1 negatív (EQH −0,32%).
- **Outage-késleltetett exit** — n=3, változatlan.
- **Várt-vs-tény pontosság**: ma **−$193 / −35%** — a sorozat legnagyobb elmaradása (ok: risk-off nap
  a „mark ≈ holnapi ár" feltevés ellenében). Tanulság a becsléshez: **több-exites napon a hiba is halmozódik**.

## 8. Holnap (csütörtök, 07-30) — várt + feltevés
- **Nincs ütemezett exit-flag** (`next_day_planned` üres) — csendes nap várható, hacsak a csütörtöki
  eval új flaget nem tesz.
- **Fókuszlista**: (1) **ROIV** — a 0,49%-os stop-buffer az egyetlen éles tétel; (2) WAB (2,08% buffer,
  −$227); (3) a könyv könnyű (23,32% notional) → új belépő valószínű; (4) a cumulative pozitívban
  (+$170,93) — tartható-e; (5) kapu-menetrend: **Day 63 ~08-17** (freeze-feloldás + első leíró futás).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
Risk-off nap (SPY −1,54%, VIX +11%) négy exittel: a kumulatív **pozitívba fordult** (+$170,93) a
+$359,68 realizálttal, de a becslést −35%-kal alulmúlta (az MLI/EQH visszaadta a mark-nyereséget),
és a NetLiq a maradó könyv (ROIV, WAB) romlása miatt csökkent — a ROIV stop-buffere 0,49%.
