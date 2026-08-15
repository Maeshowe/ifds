# IFDS Daily Review — 2026-08-14 (péntek, Day 62/63 NYSE-count) + W33 heti zárás

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 62/63** (NYSE-count). ⚠️ `cumulative_trading_days=54`. **A kapu az utolsó előtti napja.**
- **Realized net: −$236,60** (1 exit, komm. $1,10). **Cumulative: −$449,88 (−0,45%)**.
- **Net Liq: $99 963,29** — `daily_equity.json`; **napi Δ: −$146,55** (08-13: $100 109,84).
  Ismét **$100k alatt** (harmadszor: 07-20, 08-12, ma).
- **Excess: −0,04%** — `daily_metrics::excess_return` (portfolio −0,24% vs SPY −0,20%).
  Gyakorlatilag **együtt mozgott a piaccal** (VIX 14,24, a periódus mélypontja).
- **Nyitott pozíciók: 6** (`swing_positions` ≡ IBKR 6 ✓, `reconcile::no_divergence`).

## 2. Exits (1) — típus: `pending_exits`; realized: `daily_metrics::trades::details` (broker-lánc)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | 08-13 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59 | GTES | TIME_STOP (MOC) | 134 | 29,55 → 27,78 | **−$236,60** | ~−$250 | **+$13** |

Pontos becslés (5%). A day-5 max_hold zárta.

## 3. Entries (1) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| EQH | Financial Services | 102 | 52,80 → **53,02** | +0,42% | 49,40 / 55,35 / 57,90 |

⚠️ **Az EQH is „rés utáni visszalépés"** — a harmadik ilyen eset (§6).

## 4. Nyitott pozíciók (6) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| DLB | 4 | 62,39 | **+$59,16** | 6,92% | HOLD |
| EQH | 0 | 53,09 | +$6,14 | 6,95% | HOLD |
| ADT | 3 | 7,49 | −$12,05 | 5,61% | HOLD |
| SN | 1 | 185,10 | −$61,00 | 7,18% | HOLD |
| STE | 4 | 233,28 | −$114,28 | 4,26% | HOLD |
| FBIN | 1 | 47,84 | −$167,50 | 7,59% | HOLD |

**Total unrealized: −$289,53** (a 08-12-i −$960,92 mélypontról jelentősen javult). Notional 31,05%.
**Hétfőre nincs exit-flag.**

## 5. Ops-checklist
- ✓ **Reconcile 6/6 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 10:10 monitor (tiszta), 15:31 submit (EQH), 21:40 time_stop (GTES MOC),
  22:00 eod_eval (0 új flag), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (6) normál.
- ✓ **`pt_events` tiszta** (7 sor).
- ⚠️ **STOP-triggerek** (D4: `mean` az irányadó): `excess_10d_mean` **−0,46%** vs −1,0% → **✓ nincs halt**.
  **A tegnapi szorulás enyhült**: −0,62% → −0,46%, a távolság **1,6× → 2,2×**. `cum_30d` −1,34% (javult).
  MTM (−0,45%) ≈ realized `mean` (−0,46%) — **továbbra is egyeznek**.
- ✓ **v2 enrichment sink**: `766/533` ≡ scan-matrix **766/533** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)
- **📌 ÚJ, MARKÁNS MINTÁZAT — a „rés utáni visszalépés" mind a három esetben MAGASABB áron történt,
  és a két lezárt eset nettó negatív:**
  | Ticker | #1 ciklus | #1 realizált | #2 belépő | vs #1 exit-ár | #2 realizált | **Nettó** |
  |---|---|---|---|---|---|---|
  | JAZZ | 07-20→07-28 | +$156,34 | 08-05 @ 264,00 | **+2,8%** | −$407,36 | **−$251,02** |
  | GTES | 07-17→07-27 | −$29,31 | 08-06 @ 29,55 | **+11,3%** | −$236,60 | **−$265,91** |
  | EQH | 07-21→07-29 | −$19,53 | 08-14 @ 53,02 | **+9,5%** | *nyitva* | — |
  **Mindhárom visszalépés az előző exit-ár FÖLÖTT történt** (+2,8% … +11,3%), és **mindkét lezárt eset
  #2 ciklusa rosszabb, mint a #1**. **n=2 lezárt — NEM általánosítható**, de a mintázat konzisztens és
  mechanizmusa plauzibilis (a jel egy emelkedés után kvalifikál újra, tehát drágábban lép be).
  **Day 63-input.** ⚠️ Ez **NEM** a self-reentry sorozat (n=2, kényszerű azonnali round-trip) — külön
  megfigyelés, réssel.
- **✅ Enyhült — a STOP-trigger szorulás** (§5): a tegnapi 1,6×-ről 2,2×-re. A mai −0,04%-os excess
  (gyakorlatilag semleges) nem terhelte tovább az ablakot.
- **Ismert, nyitott** (nem ismételve): `exit_type` mező hibás, entry_price=planned (§11.10),
  **FileVault** (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=22** (+EQH +0,42%). |medián| ~0,89%; előjeles átlag +0,37%
  (15 adverz / 7 kedvező). *(FRL `cost_model.json` input.)*
- **Self-reentry** (kényszerű, azonnali) — **n=2**, változatlan (PFGC, USFD; mindkettő nyereséges volt).
- **„Rés utáni visszalépés"** — **n=2 lezárt** (JAZZ −$251,02, GTES −$265,91 nettó), **1 nyitva** (EQH).
  **Mindkét lezárt eset negatív; mindhárom belépő magasabb áron, mint az előző exit.** (§6)
- **„Stop-közeli" riasztás** — n=5, változatlan (4 visszapattant, 1 valódi).
- **Outage-késleltetett exit** — n=4, változatlan.
- **Rally/risk-off aszimmetria** — ma enyhén eső nap (SPY −0,20%), a könyv −0,24% → excess −0,04%
  (**semleges**). A sorozat: 6 rally-lemaradás vs 5 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: ma 1 exit, **0 pozitív**.
- **Várt-vs-tény pontosság**: ma **+$13 / +5%** — pontos.

## 8. Hétfő (08-17) — várt + feltevés
- **Nincs ütemezett exit-flag.** A legrégebbi tételek: DLB és STE (day 4) → **kedden** érik a day-5
  max_holdot, tehát hétfőn eval-fordulat várható rajtuk.
- 🔔 **HÉTFŐ = Day 63** — a D1-döntés szerint: **a freeze feloldódik** + lefut az **ELSŐ, LEÍRÓ
  `signal_attribution` futás** (pinned `c5e9ed0`). **NEM go/no-go** (a kapu 2026-09-22).
  ⚠️ **Előfeltétel: a kizárási lista véglegesítése** (protokoll §8/B) — hétvégén elvégzendő.
- **Fókuszlista**: (1) **Day 63 futás előkészítése**; (2) a STOP-trigger `mean` (−0,46%);
  (3) a DLB/STE day-5 fordulat; (4) az EQH #2 alakulása (a „rés" sorozat 3. esete).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** **A freeze hétfőn (Day 63) feloldódik** a D1-döntés szerint.

## 10. A nap egy mondatban
A GTES day-5 exitje −$236,60-nal zárt (pontos becslés), a kumulatív −$449,88-ra csúszott, és összeállt
egy markáns megfigyelés: mindhárom „rés utáni visszalépés" magasabb áron történt, mint az előző exit,
és mindkét lezárt eset nettó veszteséggel végződött.

---

## Heti zárás — W33 (2026-08-10 → 08-14) — forrás: `docs/analysis/weekly/2026-W33.md`
**5 trading nap** — az első teljes, zavartalan hét 07-31 óta (nincs outage).

| Nap | Realized | Excess | SPY | Equity (EOD) |
|---|---|---|---|---|
| 08-10 (H) | **+$110,77** | +0,14% | −0,03% | $100 423,14 |
| 08-11 (K) | **+$164,95** | +0,49% | −0,32% | $100 163,53 |
| 08-12 (Sze) | $0,00 | −0,25% | +0,25% | $99 939,71 |
| 08-13 (Cs) | **−$409,02** | −1,10% | +0,70% | $100 109,84 |
| 08-14 (P) | **−$236,60** | −0,04% | −0,20% | $99 963,29 |

- **Heti net: −$369,90** (gross −$363,25, komm. $6,65).
  **Cumulative: −$79,98 (08-06 zárás) → −$449,88** — Δ **−$369,90** ✓ (a +$195,74 a hét **kedd esti
  csúcsa** volt, nem a nyitó szint).
- **Excess vs SPY: −0,76%** (portfolio −0,36% vs SPY +0,40%). **Win days 2/5.**
- **Exit-bontás**: 6 exit — 5 MOC (mind day-5 TIME_STOP), 1 TP2 (SAIC). **A hét kizárólag
  max_hold-exiteket hozott a SAIC TP2-n kívül.**
- **A hét karaktere (tényszerű)**: a kedd végi csúcs (+$195,74 kumulatív) után a szerda-csütörtök-péntek
  **hat exitje** (JAZZ −$407, GTES −$237, SSNC −$32 stb.) fordította negatívba. Az unrealized viszont
  a 08-12-i **−$960,92-es mélypontról −$289,53-ra javult** — a veszteségek nagyrészt realizálódtak.
- **NetLiq**: az utolsó elérhető záró (**08-06**: $100 471,62) → **$99 963,29** = **−$508,33**.
  ⚠️ A 08-07 (péntek) **outage-nap, nincs equity-rekord** — ezért a hasonlítás alapja 08-06, nem 08-07.
- **Exit-oldali megjegyzés**: a `daily_metrics` a SAIC-ot **`TP1`**-ként írja, a kanonikus `pending_exits`
  **TP2**-t — ez az ismert `exit_type` defekt (3. élő megerősítés), nem új hiba.

## Biweekly scoring_validation — forrás: `docs/analysis/scoring-validation.md` (regenerálva)
**490 trade** (+6 az előző, 08-08-i futáshoz képest), **490/490 SPY-joined**, 279 enriched.
Headline: total P&L −$1 613,54 | win rate 47,6%.

### A G5 éra-bontás — a swing-hatás tovább erősödött
| Éra | N | Pearson (score vs excess) | Előző (08-08) |
|---|---|---|---|
| legacy | 442 | +0,022 (p=0,651) | változatlan (null) |
| **swing** | **48** (volt 42) | **−0,409\*\*** (p=**0,004**) | −0,393\* (p=0,010) |
| pooled ⚠️ | 490 | −0,151\*\* | −0,150\*\* |

**Leíró megfigyelés (G1/G3 — NEM jel-ítélet, NEM kapu-input):** a swing-éra negatív együttmozgása
**6 új trade-del tovább erősödött** (−0,393 → −0,409), a p-érték javult (0,010 → 0,004). A legacy
továbbra is tiszta null. **A „magas pontszám paradoxon" iránya immár n=48-on konzisztens** — de a
kapu egyetlen inputja a `signal_attribution.py`, nem ez a riport.
