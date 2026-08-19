# IFDS Daily Review — 2026-08-18 (kedd, **Day 64/63 — az első nap a periódus után**)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett; IBKR MCP kereszt-ellenőrzés lefutott.

## 1. Fejléc
- **Realized net: −$191,66** (gross −$189,40, komm. $2,26) — **2 exit, mindkettő TIME_STOP MOC**.
  A 08-17-i várakozás **≈ −$238** volt → **Δ +$46 kedvezőbb**, de a kettő **ellentétes irányban** tért el (§2).
- **Cumulative: −$641,54 (−0,64%)** — `pt_eod` 22:11:04. A swing-éra **mélypontja**.
- **Net Liq: $98 711,59** — napi Δ **−$399,03** (08-17: $99 110,62).
- **Excess: +0,49%** — `daily_metrics::excess_return` (portfolio −0,19% vs SPY −0,68%).
  ℹ️ **Ma a két olvasat EGYETÉRT**: MTM-excess **+0,28%** (NetLiq −0,40% vs SPY −0,68%).
  A 08-17-i ellentétes-előjelű eset **nem ismétlődött** — ma volt exit, tehát a §D3/M
  0-exit-artefakt nem áll fenn.
- **VIX 15,79 (+3,95%)** — **második egymást követő risk-off nap** (SPY −0,47% → −0,68%).
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR ✓, `reconcile_silent_ok`).

## 2. Exits (2) — mindkettő `TIME_STOP` MOC, day-5 max_hold
| Ticker | Qty | Entry → Exit | Realized | `várt` (08-17 mark) | Δ |
|---|---|---|---|---|---|
| DLB | 94 | 61,77 → **61,13** | **−$60,42** (−1,04%) | ≈ −$39 | **−$21** |
| STE | 24 | 238,09 → **232,62** | **−$131,24** (−2,30%) | ≈ −$199 | **+$68** |
| **Σ** | | | **−$191,66** | ≈ −$238 | **+$46** |

**Bróker-verifikáció** (`get_account_trades`): DLB SELL 94 @ 61,13 MOC 19:59:31Z,
`realized_pnl` **−60,417284**; STE SELL 24 @ 232,62 MOC 19:59:36Z, **−131,239859**.
Σ **−191,657143** ≡ a `daily_metrics` netto **pennyre** ✓

> A `pending_exits` (kanonikus) STE `entry_price` **237,47**, a `daily_metrics::details`
> **238,09** — az ismert `entry_price=planned` defekt (§11.10). A **realizált P&L nem érintett**
> (bróker-authoritatív); a tétel kozmetikai.

## 3. Entries (1) — `daily_metrics::execution`
| Ticker | Qty | Planned→Fill | Slippage | Komm. |
|---|---|---|---|---|
| IMAX | 88 | 52,39 → **52,75** | **+0,69%** (adverz) | $1,00 |

Belépő-jelöltek top-3 (`swing_score_distribution`): BANC 93,2 | DLB 93,1 | **IMAX 90,9** —
68 ticker lépte át a küszöböt, 1 belépő.
⚠️ **A DLB itt a 2. legmagasabb pontszámmal szerepel — ugyanazon a napon, amikor max_hold-on kiszálltunk belőle.** Lásd §6.

## 4. Nyitott pozíciók (7) — 08-18 **záró** mark (Polygon; IBKR `daily_pnl`-lel keresztezve)
| Ticker | days_held | Bázis | Záró | Unrealized | next_action |
|---|---|---|---|---|---|
| SN | 3 | 187,64 | 182,82 | −$115,72 | HOLD |
| BANC | 1 | 19,77 | 19,30 | −$125,09 | HOLD |
| ZBRA | 1 | 379,73 | 366,42 | −$133,10 | HOLD |
| IMAX | 0 | 52,76 | 50,55 | −$194,60 | HOLD |
| EQH | 2 | 53,03 | 50,84 | −$223,36 | HOLD |
| ADT | **5** | 7,51 | 7,22 | −$228,86 | **TIME_STOP** (holnap 21:40) |
| FBIN | 3 | 50,07 | 45,30 | **−$358,00** | HOLD |
| **Σ** | | | | **−$1 378,72** | |

**Mind a hét negatív** — a 08-17-i sorozat folytatódik. A hét ára mind a hét záró **verifikálva**
az IBKR `daily_pnl`-jén keresztül (08-19 mark − napi Δ), egyenként.

> **A nap valódi mozgása nem az exitekben van.** A **6 továbbvitt** tétel unrealizedje
> −$881,65 → **−$1 184,12**, azaz **−$302,47 egyetlen nap alatt** — másfélszerese a realizált
> veszteségnek. Az IMAX (−$194,60) ehhez **új** tételként jön.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 13:31 submit (IMAX), 21:40 time_stop (DLB/STE MOC),
  22:11 eod, metrics, review_data.
- ✓ **`reconcile_silent_ok`** — state ≡ IBKR, 0 divergencia.
- ✓ **P&L-lánc bróker-pontos**: a tracked cumulative az **egész DAYS_7 ablakban** pennyre
  egyezik a bróker `realized_pnl`-jével (08-13 −409,02 | 08-14 −236,60 | 08-18 −191,66).
  **Nulla tracking-hiba.**
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó): `excess_10d_mean` **−0,17%** vs −1,0% →
  **nincs halt**. `excess_15d_mean` −0,22%, `cum_30d` −1,18%.
  ⚠️ A `sum`-olvasat BREACH-en áll (10d −1,66%, 15d −3,37%) — **D4 szerint megfigyelés, nem trigger**.
- ⚠️ **`Day 64/63`** — a periódus-számláló túllépte a névleges 63-at. Display-artefakt
  (a periódus 08-17-én lezárult), a kapu **2026-09-22**. Nem hiba; a `pt_eod` sablon
  kapu utáni takarítási tétel.

## 6. Anomáliák (új/változott/lezárt)
- **🟡 P2 (ÚJ, KAPU-RELEVÁNS) — a `docs/analysis/` a `sync_from_mini.sh --delete` halmazában van.**
  A mai sync **letörölte** a tegnap a MacBookon generált attribution-riportokat
  (`signal-attribution-2026-08-18-*`, `gate-sample-attribution-*`). Most nincs kár
  (gitignore-olt, **regenerálható** output), **de a gate-protokoll §6/4 épp ide teszi a
  kapu-futás riportját** — vagyis egy MacBookon generált kapu-riportot a **következő sync
  megsemmisítene**. **Teendő 09-22 előtt**: a kapu-futás a **Minin** történjen, vagy a
  `--out-dir` mutasson sync-halmazon kívülre. Hibaosztály: [[sync-delete-vs-local-commits]].
- **📌 ÚJ MEGFIGYELÉS — DLB self-reentry MÁSNAP, magasabb áron.** A DLB tegnap 21:40-kor
  max_hold-on **kiszállt** 61,13-on; **ma (08-19) 13:31-kor a rendszer visszavette** 94 db-ot
  **61,95**-ön (`get_account_trades`, MKT) — **+1,34%-kal drágábban**, egy nap alatt.
  A jelenség a `daily_metrics`-ben **előre látszott**: a DLB a tegnapi belépő-jelöltek
  **2. legjobbja** volt (S_j 93,1) azon a napon, amikor kiléptettük.
  → **Self-reentry sorozat n=2 → n=3** (PFGC 07-21, USFD 07-23, **DLB 08-19**).
  ⚠️ **Ez 08-19-i esemény** — a holnapi review tárgya; itt azért szerepel, mert a tegnapi
  exit közvetlen következménye. **§5.5: a self-reentry NEM kizárási ok** (a stratégia normál
  működése, nem outage-artefakt) — leíró megfigyelés (G3).
- **📌 A `uw_shadow` tovább ír, de üresen.** 68 ticker logolva, `avg_dp_pct` **0,0**,
  `would_have_been_penalty_count` **0** — konzisztens az **UW kivezetéssel**
  (`docs/decisions/2026-08-18-uw-decommission.md`): dark-pool input nélkül a shadow-log
  már nem rögzít használható adatot. **Nem defekt** — a dormant ág takarítása a
  **kapu utáni** cleanup-task tétele.
- **✅ NEM ISMÉTLŐDÖTT — a §D3/M ellentétes-előjelű eset.** Ma mindkét olvasat pozitív
  (realized +0,49%, MTM +0,28%), mert **volt exit**. Ez megerősíti a tegnap rögzített
  mechanizmust: a szétválás a **0-exites** napokhoz kötött.
- **Ismert, nyitott** (nem ismételve): `exit_type` mező (a `pending_exits` a kanonikus),
  `entry_price=planned` (§11.10), **FileVault** (Tamás felírta, parkolva).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=25** (+IMAX **+0,69%**, adverz). **18 adverz / 7 kedvező**.
  *(FRL `cost_model.json` input; G1: nem kapu-input.)*
- **Self-reentry** — **n=2 → n=3** (DLB, 08-19; lásd §6). Mindhárom a `max_hold` ↔ belépő-jel
  ellentmondásból ered.
- **„Rés utáni visszalépés"** — n=2 lezárt (JAZZ −$251,02, GTES −$265,91), **1 nyitva**:
  **EQH −$223,36** (08-17: −$155,02 → **tovább mélyült**).
- **Outage-késleltetett exit** — n=4, változatlan. **„Stop-közeli"** — n=5, változatlan.
- **Rally/risk-off aszimmetria** — eső nap (SPY −0,68%), **mindkét** olvasat felülteljesítést mér,
  és ma **nem** a 0-exit-artefakt hajtja (2 exit volt). Sorozat (realized-olvasat):
  6 rally-lemaradás vs **7** eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: ma **0/2**. A TIME_STOP-tömb aránya a lezárt mintában tovább nő
  (a Day 63-as bontásban 79,5% volt).
- **Várt-vs-tény**: Σ szinten **+$46 kedvezőbb**, de tételenként **ellentétes irányú**
  (DLB −$21, STE +$68) — a napi mark-alapú becslés **iránya sem** megbízható 1 tételre.

## 8. Holnap (szerda, 08-19) — várt + feltevés
**Egy TIME_STOP 21:40 MOC** (day-5 max_hold; feltevés: szerdai close ≈ keddi záró):

| Ticker | Qty | Bázis / záró | `várt` |
|---|---|---|---|
| ADT | 803 | 7,51 / 7,22 | **≈ −$229** |

Ha teljesül: cumulative **−$641,54 → ~−$871**. A könyv **6 tételre** csökken
(a DLB-visszavétellel viszont **7-re** áll vissza — lásd §6).

- **Fókuszlista**: (1) az ADT TIME_STOP; (2) a **DLB self-reentry** könyvelése és a
  sorozat n=3-ra állítása; (3) a **−$1 378,72 unrealized** alakulása — a 6 továbbvitt tétel
  egy nap alatt −$302-t vesztett; (4) a STOP-`mean` (−0,17%, **4× javult sorban**);
  (5) a `docs/analysis/` sync-rés lezárása a kapu előtt (§6).

## 9. Freeze-sor
🔓 A parameter freeze **08-17-én feloldódott** — **de a D6 (2026-08-18) szerint a production
konfiguráció FAGYVA marad 2026-09-22-ig** (kétsávos folytatás: a revíziók a SIM-L2 / Mode 2
re-score infrán futnak). A **G1/G3–G7 guardrailek változatlanul élnek**.
Ma **nem történt** production-kód változás; a napi kód-munka (`gate_sample.py`, `68fc00e`)
**read-only analízis**, a kereskedési kódutat nem érinti.

## 10. A nap egy mondatban
Két max_hold-exit **−$191,66**-tal a vártnál $46-tal kedvezőbben zárt (de tételenként ellentétes
irányú eltéréssel), a cumulative a swing-éra mélypontjára, **−$641,54**-re süllyedt — miközben a
nap valódi mozgása a **továbbvitt könyvben** volt (**−$302 egyetlen nap alatt, mind a 7 tétel
negatív**), és a rendszer a max_hold-on kiléptetett **DLB-t másnap 1,34%-kal drágábban visszavette**.
