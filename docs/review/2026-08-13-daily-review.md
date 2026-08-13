# IFDS Daily Review — 2026-08-13 (csütörtök, Day 61/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 61/63** (NYSE-count). ⚠️ `cumulative_trading_days=53`.
- **Realized net: −$409,02** (3 exit, komm. $3,36). **Cumulative: −$213,28 (−0,213%)** — a tegnapi
  +$195,74-ről **negatívba fordult**.
- **Net Liq: $100 109,84** — `daily_equity.json`; **napi Δ: +$170,13** (08-12: $99 939,71).
  **Vissza $100k fölé** — a negatív realizált ellenére (a maradó könyv javult).
- **Excess: −1,10%** — `daily_metrics::excess_return` (portfolio **−0,41%** vs SPY **+0,70%**).
  Emelkedő tape (VIX 14,64), a könyv **érdemben lemaradt**.
- **Nyitott pozíciók: 6** (`swing_positions` ≡ IBKR 6 ✓, `reconcile::no_divergence`).

## 2. Exits (3) — típus: `pending_exits`; realized: IBKR `get_account_trades` (mind verifikálva)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | 08-12 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59 | VLTO | TIME_STOP (MOC) | 56 | 97,04 → 97,58 | **+$30,36** | ~−$19 | **+$49** |
| 21:59 | SSNC | TIME_STOP (MOC) | 65 | 82,53 → 82,04 | **−$32,02** | ~−$154 | **+$122** |
| 21:59 | JAZZ | TIME_STOP (MOC) | 22 | 264,10 → 245,58 | **−$407,36** | ~−$332 | **−$75** |

**Összeg −$409,02** (= a `cumulative` Δ ✓). **Várt ~−$506 → tény −$409,02: +$97 (+19%)** — a VLTO és a
SSNC jóval jobban, a JAZZ rosszabbul zárt. Mindhárom **day-5 max_hold**.

### 📌 A JAZZ két ciklusának mérlege (a „rés utáni visszalépés" mintázat)
| Ciklus | Belépő | Exit | Realizált |
|---|---|---|---|
| #1 | 07-20 @ 250,09 | 07-28 TIME_STOP @ 256,89 | **+$156,34** |
| #2 (6 nap rés után) | 08-05 @ 264,00 | 08-13 TIME_STOP @ 245,58 | **−$407,36** |
| **Nettó** | | | **−$251,02** |

A **magasabb áron (264,00 vs 256,89) történt visszalépés** veszteségbe fordult. **n=1 lezárt eset**
ebből a mintázatból (a GTES #2 még nyitva) — **nem általánosítható**, de rögzítendő: ez **NEM** a
self-reentry sorozat (ott a kényszerű, azonnali round-trip a jellemző), hanem **friss jel alapján,
réssel** történt visszalépés. Day 63-input.

## 3. Entries (2) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| SN | Consumer Cyclical | 24 | 186,13 → **187,60** | +0,79% | 171,81 / 196,87 / 207,62 |
| **FBIN** | Industrials | 75 | 48,87 → **50,06** | **+2,44%** ⚠️ | 44,21 / 52,37 / 55,86 |

⚠️ **Az FBIN +2,44% a sorozat LEGNAGYOBB ADVERZ slippage-e** (az eddigi max adverz a ROIV +1,40% volt;
a −2,06%-os DE kedvező irányú volt). Átlag +2,04% (a `daily_metrics` súlyozása szerint), komm. $3,36.
📌 **Következmény**: a stop (44,21) a **tervezett** 48,87-ből számolódott, a tényleges belépő 50,06 —
a valós kockázat-a-stopig **11,7%** a tervezett 9,5% helyett (a §11.10 `entry_price=planned` defekt
konkrét megnyilvánulása, ma a szokásosnál nagyobb mértékben).

## 4. Nyitott pozíciók (6) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| DLB | 3 | 62,37 | **+$57,28** | 6,89% | HOLD |
| SN | 0 | 188,59 | +$22,76 | 8,90% | HOLD |
| ADT | 2 | 7,46 | −$36,14 | 5,23% | HOLD |
| STE | 3 | 236,07 | −$47,32 | 5,39% | HOLD |
| FBIN | 0 | 48,43 | −$123,25 | 8,71% | HOLD |
| GTES | **5** | 27,67 | −$250,24 | 3,54% | **TIME_STOP** (holnap 21:40) |

**Total unrealized: −$376,91** — **jelentős javulás** a tegnapi −$960,92-ról (a három exit levitte a
veszteségeket a könyvről). Notional **37,89% → 29,59%**.

## 5. Ops-checklist
- ✓ **Reconcile 6/6 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 10:10 monitor (tiszta), 15:31 submit (2 belépő), 21:40 time_stop (**3 MOC**),
  22:00 eod_eval (GTES TIME_STOP flag), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (6) normál.
- ✓ **`pt_events` tiszta** (10 sor).
- 🔴 **STOP-triggerek** (D4: `mean` az irányadó): `excess_10d_mean` **−0,62%** vs −1,0% → **✓ nincs halt**,
  **DE a távolság 3,1× → 1,6×-re csökkent** egyetlen nap alatt. Részletek §6.
- ✓ **v2 enrichment sink**: `766/510` ≡ scan-matrix **766/510** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)
- **🔴 P1-figyelmeztetés — a STOP-trigger `mean` a legközelebb került a küszöbhöz.**
  | Nap | `10d_mean` | távolság | `10d_sum` | MTM (10d) |
  |---|---|---|---|---|
  | 08-11 | −0,29% | 3,4× | −2,94% | −0,40% |
  | 08-12 | −0,32% | 3,1× | −3,22% | −0,47% |
  | **08-13** | **−0,62%** | **1,6×** | **−6,22%** | **−0,62%** |
  A mai **−1,10%-os excess** (a legnagyobb negatív a 07-30-i −1,68% óta) belépett a 10 napos ablakba.
  📌 **A MTM és a realized `mean` MA PONTOSAN EGYEZIK (−0,62%)** — a tegnapi szétnyílás (−0,47 vs −0,32)
  megszűnt, tehát a mai lemaradás **valós**, nem mérési artifact.
  ⚠️ **Ez nem halt-jelzés**, de a legszorosabb állás eddig. **Ha a `mean` a −1,0% alá megy, az a
  pre-reg szerinti LEÁLLÍTÁSI feltétel** (D4: a `mean` az irányadó) → azonnali P1-jelzés Tamásnak.
  *(Kontextus: a `cum_30d` −1,50%, a küszöb felénél; a cumulative −$213,28.)*
- **⚠️ ÚJ — FBIN +2,44% slippage, a sorozat legnagyobb adverz printje** (§3), a stop-számítás
  tervezett-ár alapú következményével.
- **📌 A JAZZ két ciklusának nettó mérlege −$251,02** (§2) — a rés utáni, magasabb áron történő
  visszalépés veszteségbe fordult. n=1, nem általánosítható.
- **Ismert, nyitott** (nem ismételve): `exit_type` mező hibás, entry_price=planned (§11.10 — ma az FBIN-nél
  kiugróan), **FileVault** (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=21** (+SN +0,79%, **FBIN +2,44%**). **|medián| 0,91%**
  (változatlan); előjeles átlag **+0,24% → +0,37%** (14 adverz / 7 kedvező). Az FBIN egyetlen printje
  érdemben mozdította a torzítást. *(FRL `cost_model.json` input.)*
- **Self-reentry** — n=2, változatlan.
- **„Rés utáni visszalépés"** — **n=1 lezárt** (JAZZ, −$251,02 nettó a két cikluson); a GTES #2 nyitva
  (−$250,24 unrealized, holnap TIME_STOP).
- **„Stop-közeli" riasztás** — n=5, változatlan (4 visszapattant, 1 valódi).
- **Outage-késleltetett exit** — n=4, változatlan.
- **Rally/risk-off aszimmetria** — ma emelkedő nap (SPY +0,70%), a könyv **−0,41%** → excess **−1,10%**.
  A sorozat: **6 rally-lemaradás vs 5 eső-napi felülteljesítés**. **Az aszimmetria konzisztens.**
- **TP-hit / pozitív-exit**: ma 3 exit, **1 pozitív** (VLTO +$30,36).
- **Várt-vs-tény pontosság**: ma **+$97 / +19%**.

## 8. Holnap (péntek, 08-14) — várt + feltevés
- **GTES TIME_STOP** 21:40 MOC (134) — `várt` ≈ **−$250** (feltevés: pénteki close ≈ mai mark 27,67;
  IBKR-bázis 29,537). **Ez a GTES 2. ciklusa** (az első: 07-17→07-27, −$29,31) → a „rés utáni
  visszalépés" sorozat **2. lezárt esete** lesz.
- **Péntek → heti zárás (W33)**: `weekly_metrics.py` + Telegram.
- **Fókuszlista**: (1) **a STOP-trigger `mean`** (−0,62%, 1,6× a küszöbtől) — a nap legfontosabb mutatója;
  (2) a GTES exit; (3) a heti zárás (W33); (4) az FBIN/SN friss belépők;
  (5) **kapu: Day 63 ~08-17 — 2 trading nap** (freeze-feloldás + első leíró `signal_attribution`).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
A három day-5 TIME_STOP −$409,02-tel zárt (a becsültnél $97-tel jobban, de a JAZZ két ciklusa nettó
−$251-gyel végződött), a kumulatív negatívba fordult (−$213,28), és a STOP-trigger `mean` egyetlen nap
alatt 3,1×-ről **1,6×-re** közelítette meg a leállítási küszöböt.
