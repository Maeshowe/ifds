# IFDS Daily Review — 2026-08-17 (hétfő, **Day 63/63 — a freeze-feloldás napja**)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett; IBKR MCP kereszt-ellenőrzés lefutott.

## 1. Fejléc
- 🔔 **Day 63/63 ELÉRVE** — `pt_eod` log: *„Cumulative: $-449.88 (-0.45%) [Day 63/63]"*.
  **A parameter freeze mai nappal feloldódik** (D1). ⚠️ Az **első leíró `signal_attribution` futás
  MÉG NEM történt meg** — előfeltétele a kizárási lista véglegesítése (§8).
- **Realized net: $0,00** (0 exit). **Cumulative: −$449,88 (−0,45%)** — változatlan.
- **Net Liq: $99 110,62** — `daily_equity.json`; **napi Δ: −$852,67** (08-14: $99 963,29).
  **A swing-éra legnagyobb egynapos NetLiq-esése** nulla realizált mellett.
- **Excess: +0,47%** — `daily_metrics::excess_return` (portfolio 0,00% vs SPY **−0,47%**).
  ⚠️ **De lásd §6: a MTM-olvasat ellentétes előjelű** — ez a D3 szerinti P1-eset.
- **VIX 15,22 (+6,81%)** — risk-off nap.
- **Nyitott pozíciók: 8** (`swing_positions` ≡ IBKR 8 ✓, `reconcile::no_divergence`).

## 2. Exits (0)
Nincs végrehajtott exit. **Ma beállított flagek: DLB, STE — mindkettő TIME_STOP** (day-5 max_hold)
→ **holnap (08-18) 21:40 MOC**. A könyv 8 → 6 tételre könnyül.

## 3. Entries (2) — `pt_events` 13:31 + `daily_metrics::execution`
| Ticker | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|
| ZBRA | 10 | 376,03 → **379,63** | **+0,96%** | 342,29 / 401,33 / 426,63 |
| BANC | 269 | 19,74 → **19,76** | +0,10% | 18,44 / 20,71 / 21,69 |

Átlag +0,13% (`avg_fill_slippage_pct`), komm. $0,00. A `submit` a DLB-t `existing_skip`-pel kihagyta ✓.

## 4. Nyitott pozíciók (8) — IBKR `get_account_positions` (**08-18 reggeli mark**)
| Ticker | days_held | Mark | Unrealized | next_action |
|---|---|---|---|---|
| BANC | 0 | 19,69 | −$20,18 | HOLD |
| DLB | **5** | 61,35 | −$38,60 | **TIME_STOP** (holnap 21:40) |
| ZBRA | 0 | 371,26 | −$84,70 | HOLD |
| SN | 2 | 183,62 | −$96,52 | HOLD |
| EQH | 1 | 51,51 | −$155,02 | HOLD |
| STE | **5** | 229,75 | −$199,00 | **TIME_STOP** (holnap 21:40) |
| ADT | 4 | 7,18 | −$260,98 | HOLD |
| FBIN | 2 | 46,55 | −$264,25 | HOLD |

⚠️ **Total unrealized: −$1 119,25** — **mind a 8 tétel negatív**, és ez **mélyebb, mint a 08-12-i
−$960,92-es addigi mélypont**.
> **Módszertani megjegyzés**: ezek a markok a **mai (08-18) reggeli** IBKR-olvasatot tükrözik, nem a
> 08-17-i zárót — a 08-17-i NetLiq-kel nem záródik pontosan az azonosság. A **trend** (mind a 8 negatív,
> új mélypont) robusztus; a pontos 08-17-i záró unrealized ennél kisebb abszolút értékű.

## 5. Ops-checklist
- ✓ **Reconcile 8/8 silent OK** — `pt_events` 20:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 10:10 + 13:26 monitor (`no_true_leftover`), 12:30 pipeline, 13:31 submit (2 belépő),
  15:30 close (nincs flag), 21:40 time_stop (nincs flag), 22:00 eod_eval (**2 TIME_STOP flag**),
  22:10 metrics, 22:11 eod, 22:15 reconcile.
- ✓ **Nincs ERROR** a pipeline-ban; a 20:11 `eod::leftover_warning` (8) normál.
- ✓ **`pt_events` tiszta** (8 sor).
- ⚠️ **STOP-triggerek** (D4: a `mean` az irányadó): `excess_10d_mean` **−0,36%** vs −1,0% → **✓ nincs halt**.
  **Harmadszor javult**: −0,62% (08-13) → −0,46% (08-14) → **−0,36%**; a küszöbtől mért távolság **2,8×**.
  A `sum`-olvasat továbbra is BREACH (−3,57%) — **D4 szerint nem irányadó**, megfigyelésként rögzítve.
  `cum_30d` −1,01% (tovább javult).
- ✓ **v2 enrichment sink**: `1338/903` ≡ scan-matrix **1338/903** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)
- **🔴 P1 (ÚJ) — a D3 szerinti ELLENTÉTES-ELŐJELŰ eset MA ELŐSZÖR áll fenn.**
  | Olvasat | Érték |
  |---|---|
  | **realized-only** (pre-reg, irányadó) | **+0,47%** (portfolio 0,00% vs SPY −0,47%) |
  | **MTM** (NetLiq Δ − SPY, diagnosztika) | **−0,38%** (NetLiq −0,85% vs SPY −0,47%) |
  A két olvasat **ellentétes irányba mutat**, ~0,85 százalékpont réssel. Ok: a realized-only mező
  0 exit mellett **definíció szerint 0,00%-ot** ad, tehát egy eső napon **automatikusan „felülteljesítést"
  mér** — miközben a nyitott könyv $852-t veszített. **A D3-döntés szerint a realized-only marad az
  irányadó mező** (a kapu ezt használja), **de ez a nap a mező ismert torzítását élesben mutatja**:
  a 08-13-i review-ban rögzített ~38%-os „−SPY-t mér" arány itt 100%.
  📌 **Kapu-relevancia**: a `signal_attribution` futás előtt ezt **írásban rögzíteni kell** a
  protokoll módszertani szakaszában — nem a mező cseréjeként (az pre-reg-sértés lenne), hanem
  **ismert korlátként**.
- **📌 ÚJ TÉNY — az UW (Unusual Whales) API kulcs 2026-06-24 óta hiányzik a Mini `.env`-jéből.**
  Bizonyíték: `API_HEALTH_CHECK: unusual_whales → skipped ("No API key configured")`; az átfordulás
  napja a log-sorozatból **2026-06-24** (`ok` → `skipped`). A Mini `.env`-ben a kulcs **nincs jelen**.
  ✅ **A pipeline NEM áll**: van **dokumentált fallback** —
  `API_FALLBACK: primary=unusual_whales, fallback=polygon ("will use Polygon for GEX/Dark Pool")`,
  és a **Phase 5 egészséges** (79 analyzed / 73 passed / 6 GEX-exclusion / mms_count 79).
  ⚠️ **De ez adat-proveniencia tény a kapuhoz**: a GEX/dark-pool jel **~2 hónapja Polygon-forrásból**
  jön, nem UW-ből — vagyis **a teljes kapu-minta ezen a fallback-úton keletkezett**. Emellett a
  Day 90-re tervezett **UW dark-pool Bayesian rekalibráció** input nélkül maradna. **Tamás-döntés
  kell**: pótoljuk a kulcsot, vagy tudatosan a Polygon-úton maradunk (és a tervet módosítjuk).
- **✅ MEGDŐLT HIPOTÉZIS — az univerzum-növekedés NEM halmozódás.** A scan-univerzum 766 → **1338**
  (+75%), de a halmaz-teszt **cáfolja** az „append-bug" gyanút: **91 ticker kiesett, 663 új jött be,
  0 duplikátum** — vagyis **valódi újra-szűrés**, nem akkumuláció. A sorozat (226 → 380 → 765 → 1338)
  a vasárnapi Phase 1-3 frissítésekhez kötött, **negyedik** független megerősítés. A növekedés
  **mértéke** viszont továbbra is megfigyelés-tárgy.
- **Ismert, nyitott** (nem ismételve): `exit_type` mező hibás, entry_price=planned (§11.10),
  **FileVault** (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=24** (+ZBRA +0,96%, +BANC +0,10%; mindkettő adverz).
  17 adverz / 7 kedvező. *(FRL `cost_model.json` input.)*
- **„Rés utáni visszalépés"** — n=2 lezárt (JAZZ −$251,02, GTES −$265,91), **1 nyitva** (EQH,
  jelenleg **−$155,02**-n áll → a 3. eset is a negatív irányba tart, de **nyitva van**).
- **Self-reentry** — n=2 | **„Stop-közeli"** — n=5 | **Outage-késleltetett exit** — n=4: mind változatlan.
- **Rally/risk-off aszimmetria** — ma eső nap (SPY −0,47%), realized-olvasat szerint +0,47% excess.
  ⚠️ **A sorozat innentől óvatosan kezelendő**: a 0-exites napok automatikusan „felülteljesítést"
  mérnek eső tapén (§6). A **MTM-olvasat szerint ma −0,38% volt**, azaz **lemaradás**.
  Sorozat (realized-olvasat): 6 rally-lemaradás vs **6** eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: ma 0 exit. **Várt-vs-tény**: nem mérhető (0 exit volt tervezve ✓).

## 8. Holnap (kedd, 08-18) — várt + feltevés
**Két TIME_STOP 21:40 MOC** (mindkettő day-5 max_hold; feltevés: keddi close ≈ mai mark):
| Ticker | Qty | Mark / bázis | `várt` |
|---|---|---|---|
| DLB | 94 | 61,35 / 61,76 | **≈ −$39** |
| STE | 24 | 229,75 / 238,04 | **≈ −$199** |
| **Σ** | | | **≈ −$238** |

Ha teljesül: cumulative **−$449,88 → ~−$688**. A könyv **6 tételre** csökken.

- 🔔 **DAY 63 UTÁNI TEENDŐK (a nap fő feladata, nem trading):**
  1. **A kizárási lista véglegesítése** (gate-protokoll §8/B) — 5 outage-nap + 4 késett exit;
     **ez a `signal_attribution` futás előfeltétele**.
  2. **A §6-os realized/MTM korlát írásbeli rögzítése** a protokoll módszertani szakaszában.
  3. **Az első, LEÍRÓ `signal_attribution` futás** (pinned `c5e9ed0`) — **nem** go/no-go (a kapu 09-22).
  4. **UW-kulcs döntés** (§6).
- **Fókuszlista**: (1) a Day 63 utómunka; (2) a két TIME_STOP; (3) az unrealized −$1 119 alakulása;
  (4) a STOP-`mean` (−0,36%, javuló).

## 9. Freeze-sor
🔓 **A parameter freeze a mai nappal (Day 63) FELOLDÓDIK** a D1-döntés szerint.
**Paraméter-érintő változás ma nem történt.** A freeze-feloldás **nem** jelenti a guardrailek feloldását:
a **G1 (kapu-szeparáció), G3 (nincs jel-érvényességi nyelv a kapu-futásig), G4–G7 változatlanul élnek**,
és a kapu dátuma **2026-09-22** (D2).

## 10. A nap egy mondatban
Day 63 elérve (a freeze feloldódik), kereskedésileg csendes nap 0 exittel és 2 belépővel — de a nyitott
könyv új mélypontra esett (**−$1 119, mind a 8 tétel negatív**, NetLiq −$852), és a nap élesben mutatta
a realized-only excess-mező ismert korlátját: **+0,47%-ot mér ott, ahol a MTM −0,38%-ot**.
