# FRL — Factor Research Loop — Design Specifikáció

**Státusz:** DRAFT v2 — 2026-07-21 (R1 review beépítve: Log Review chat 6-pontos kritika — lásd Appendix R)
**Szerző:** Chat (Dev), Tamás jóváhagyás előtt
**Prioritás:** P2 (infra-build freeze-safe most; éles felhasználás Day 63 után)
**Scope:** Fegyelmezett, iteratív faktor-kutatási keret (hipotézis → teszt → pontozás → visszacsatolás) az IFDS keresztmetszeti adatán
**Érint (új, read-only):** `research/` (ÚJ top-level), `scripts/research/` (ÚJ), `docs/design/frl/hypotheses/` (ÚJ)
**NEM érint:** production pipeline, scoring, sizing, exit, cron — a Day 63 parameter freeze teljes tiszteletben tartásával
**Kontextus:** a "loop engineering" koncepció (Horizon Trade viral framework) IFDS-re adaptált, statisztikailag korrekt változata. Előzmény-elemzés: 2026-07-21 helyzetelemzés (jelen chat), a Day 63 outcome doc és az edge-audit (`docs/foundational/strategic-review/2026-06-10-edge-audit.md`) keretein belül.

---

## 1. Motiváció és verdikt

### 1.1 Miért loop

A Day 63 (legacy) fő tanulsága: a scoring-komponensek élesbe kerültek ad-hoc súlyokkal,
keresztmetszeti validáció nélkül — az eredmény a "magas pontszám paradoxon" és a Pearson
r ≈ 0 edge. Az FRL célja, hogy **strukturálisan lehetetlenné tegye ennek megismétlődését**:
komponens nem kerülhet scoringba a hipotézis → teszt → holdout → shadow lánc nélkül.

A loop nem edge-generátor. Ha a swing pivot alap-edge-e (PCR + OTM-inverse) a Day 63 kapun
elbukik, a loop nem pótolja — de fegyelmezetten és gyorsan öli meg a rossz hipotéziseket,
és a jókat auditálható úton juttatja el a deploy-ig.

### 1.2 Hol van statisztikai erő (és hol nincs)

| Minta | n | Loop-alkalmasság |
|---|---|---|
| Trade-szintű P&L (swing) | ~48 exit-láb, ~40-45 pozíció Day 63-ra | ❌ TILOS — a signal_attribution.py pre-reg territóriuma |
| Napi keresztmetszet (scan) | ~250-430 név/nap (swing), ~800-1370 (legacy), ~105 nap | ✅ az FRL elsődleges terepe |

Napi keresztmetszeti Spearman IC standard hibája ≈ 1/√N ≈ 0.05-0.08. T nap fölött az
ICIR t-statisztikája √T_eff-fel élesedik (T_eff < T az 5-napos forward-return overlap
miatt, lásd §5.3). A kombinált (legacy+swing, éra-bontott) mintán IC ≈ 0.03-0.05
detektálható; a tiszta swing-érán (~31 tiszta nap) még határeset — a dev-ablak minden
további paper trading héttel erősödik.

### 1.3 A Horizon-loop és az FRL döntő különbsége

A generálás nálunk NEM vak keresés: minden jelölt **regisztrált hipotézisből** indul
(mechanizmus, várt előjel, ki a vesztes oldal, költségprofil — ELŐBB leírva, UTÁNA
tesztelve). A "feed the result back" nem paraméter-mutáció, hanem a hipotézis-registry
gazdagítása: mi halt meg és miért. A loop a teszt-pontozás-adminisztráció részt
automatizálja, a hipotézisképzést nem helyettesíti.

---

## 2. Governance és guardrailek (NEM-TÁRGYALHATÓ)

| # | Szabály | Forrás-elv |
|---|---|---|
| G1 | **Gate-szeparáció**: az FRL minden outputja ÖRÖKRE leíró. A Day 63/126 kapuk kizárólagos inputja a `signal_attribution.py` (pinned `c5e9ed0`). Ez az irányra is igaz: pozitív FRL-eredmény ugyanúgy inadmissibilis a kapuba, mint negatív (§6.6 tükörveszély-guardrail). | 04-risks §6.6 |
| G2 | **Freeze-kompatibilitás**: az FRL infra read-only elemző-tooling (a signal_attribution-wiring precedens). Production kód, cron, scoring, config NEM módosul Day 63-ig. Kivétel: a v2 enrichment sink (§4.4) — külön Tamás-döntés (D_A). | edge-audit §4.2/1 |
| G3 | **Signal-validity nyelv tilalma Day 63-ig**: az FRL-riportok "leíró IC-becslés" nyelvet használnak, "edge/alpha/működik" kijelentést nem tesznek. | Day 63 protokoll |
| G4 | **Attempt-számolás**: MINDEN tesztelt variáns (a KILL-ek is) az attempt-ledgerbe kerül. A szignifikancia-küszöb a ledger-számból deflálódik (§5.4). Ledger-en kívüli teszt = protokollsértés. | Bonferroni-fegyelem kiterjesztése |
| G5 | **Éra-tisztelet**: legacy (02-09→05-15) és swing (05-18→) minta pooled eredménye SOHA nem riportolható éra-bontás nélkül. | §6.6 pooling-tanulság |
| G6 | **Holdout egy-érintés**: hipotézisenként max 1 holdout-teszt. Bukás = halott; nincs újra-tuning a holdout ellen. | Horizon-cikk hiányzó mechanizmusa |
| G7 | **Lane-hygiene**: Chat/Dev írja a hipotéziseket és a spec-et; CC implementálja a tooling-ot és futtatja a batch-et; Tamás dönt a PROMOTE→SHADOW és SHADOW→DEPLOY lépéseknél. | 3-actor modell |

---

## 3. A loop definíciója

```
1. HYPOTHESIS   Tamás/Chat → docs/design/frl/hypotheses/HYP-###.md
                Kötelező mezők: mechanizmus, várt előjel, vesztes oldal,
                költségprofil, adatsáv (v1/v2), pre-reg metrika, kill-kritérium
2. IMPLEMENT    CC → faktor-számító függvény (scripts/research/factors/)
                Tiszta függvény: (nap, univerzum) → faktor-érték vektor
3. TEST         Heti batch (CC futtatja, MacBook) → napi sector-relative
                Spearman IC h∈{1,3,5,7}, KIZÁRÓLAG a dev-ablakon
4. SCORE        ICIR + half-life + költség-szembesítés a ledger-deflált
                küszöbök ellen (§5)
5. DECIDE       KILL (indok a registrybe) / PARK (trigger-címkével) / PROMOTE
6. HOLDOUT      PROMOTE esetén EGYSZERI teszt az embargózott ablakon (§7)
7. SHADOW       Túlélő → shadow-perzisztálás élesben 4+ hét (uw_shadow minta)
                — KIZÁRÓLAG Day 63 után deploy-olható
8. GATE         Tamás-döntés + deploy freeze-ablakon kívül, a scoring-revízió
                normál CC-task útján
```

A visszacsatolás: a 4-5. lépés eredménye (miért halt meg / mi volt gyenge) a registry
KILL-szekciójába kerül; a következő hipotézis-generálás (Chat) ezt olvassa. Az iteráció
tehát a **hipotézis-térben** történik, nem a paraméter-térben.

---

## 4. Adat-architektúra

### 4.1 Forrás-hierarchia (2026-07-21 felderítés alapján, verifikált)

| Rang | Forrás | Tartalom | Lefedés | Ismert korlát |
|---|---|---|---|---|
| 1 | `output/full_scan_matrix_*.csv` | teljes napi scan-keresztmetszet: Total/Flow/Funda/Tech_Score, Status, Reason, Price, ATR, Sector | 2026-02-09 → , ~105 nap | **FRL-0 GO (30b948c):** a Total_Score éra-konzisztens kanonikus oszlop — legacy: rácsos kompozit (05-15-ig), swing: folytonos S_j EWMA(5) (05-18-tól); a rescore megelőzi a CSV-írást. 66 legacy + 36 swing nap, degenerált swing-nap: 0 |
| 2 | `logs/ifds_run_*.jsonl` | TICKER_SCORED (+sub-score a message-ben), TICKER_FILTERED (kizárási ok), GEX_EXCLUSION, POSITION_SIZED | 2026-02-11 → | **FRL-0 verdikt (30b948c):** a swing-érában NEM score-validátor — legacy nyers kompozitot logol (emitter a legacy min_score ágban, a `_apply_swing_scoring` ELŐTT), és torzított részhalmazon (csak legacy-passed ~50-90 ticker). Validátor-szerep legacy-érára korlátozva; swing-érában diagnosztikai forrás |
| 3 | Polygon daily bars (`get_grouped_daily` — teljes piac/hívás, V2 verdikt) | return-mátrix + OHLCV-faktorok a teljes univerzumra | visszamenőleg korlátlan | ~110-130 hívás a teljes történeti mátrixhoz; Mini-cache üres, nem forrás |
| 4 | `state/uw_shadow/` | gex_value/gex_regime nyers keresztmetszet | 2026-05-18 → , ~25-40 név/nap | kis N; dp_pct halott (UW 07-04); 05-19 elveszett |
| 5 | `state/phase4_snapshots/` | gazdag nyers mezők, csak winnerek (~3-7/nap) | 2026-02-19 → | nem keresztmetszet; legacy-éra pollution-gyanús (04-15 = AAPL mock, verifikált) |

Trade-szintű adat (`pending_exits/`, ledger): az FRL-ből **kizárva** (G1).

### 4.2 Két adatsáv

- **v1 (történeti, azonnal él):** scan-matrix + JSONL + Polygon-return. Tesztelhető:
  kompozit- és sub-score-szintű faktorok, valamint bármely OHLCV-ből számolható faktor
  (momentum, reversal, ATR-relatív, volumen-alapú, szektor-relatív spread-ek).
- **v2 (forward-gyűjtés, enrichment után):** a teljes pontozott keresztmetszet nyers
  al-komponensei (PCR-érték, OTM-percentilis, RVOL, EWMA-előtti nyers S_j-inputok).
  Minden hipotézis a registryben `data_lane: v1|v2` címkét kap; v2-hipotézis nem
  tesztelhető, amíg a forward-minta < 40 nap.

### 4.3 Sync-topológia döntés (KRITIKUS)

A `sync_from_mini.sh` a `data/ logs/ output/ state/ scripts/paper_trading/logs/
docs/analysis/` mappákat **Mini-master, --delete** módban tükrözi. Ha az FRL a MacBookon
ezekbe írna, a következő sync TÖRÖLNÉ az outputjait.

**Döntés:** az FRL teljes állapota egy ÚJ top-level `research/` könyvtárban él, ami
NINCS a sync-halmazban:

```
research/
  attempt_ledger.jsonl        ← append-only, git-tracked
  runs/YYYY-MM-DD/            ← heti batch outputok (IC-táblák, riport-md), git-tracked
  cache/                      ← Polygon return-mátrix parquet, .gitignore
```

A hipotézis-fájlok (emberi dokumentum) a `docs/design/frl/hypotheses/` alatt, git-ben.
Az FRL a **MacBookon fut** (kutató-gép), a Mini-t nem érinti. A v2 enrichment sink az
egyetlen Mini-oldali elem (D_A döntés után).

### 4.4 v2 enrichment sink (D_A döntési pont)

Javaslat: a Phase 4 futás végén a teljes pontozott tábla (nyers mezőkkel, a
phase4_snapshot rekord-sémájával) írása `state/research_cross_section/YYYY-MM-DD.json.gz`
fájlba. Jelleg: display/tracking-carve-out (§4.2/1) — kereskedési viselkedést nem érint,
kizárólag perzisztálás. Sink-audit fegyelem KÖTELEZŐ: az új sink mindkét e2e patch-stackbe
felveendő (04-risks §8.1.6-8.1.9 szabály). **Freeze alatti deploy: D_A DÖNTVE IGEN (Tamás, 2026-07-21).** Minden
késlekedő nap egy nappal rövidíti a Day 63 utáni v2 dev-ablakot.

### 4.5 Ismert lefedettségi hézagok és kezelésük

| Hézag | Kezelés |
|---|---|
| **score == 0 → NaN (9f49a38, FRL-0 szabály-revizió)** | a reason-alapú tech_filter-azonosítás szűknek bizonyult: az `execution_plan.py:179` a Reason-t "Sector VETO"-ra írja felül, elfedve a valódi exclusion_reason-t — 6179 legacy sor lépett volna panelbe hamis 0.0-val. Új szabály empirikusan megalapozva a 102 napon: 0 db ACCEPTED 0.0-val, min valós |score| 0.01. A pontozott VETO-sorok (4357) maradnak — a veto portfólió-döntés, nem hiányzó mérés. A mögöttes Reason-felülírás prod-bug: post-Day-63 fix-jelölt (04-risks) |
| 2026-04-06, 04-07 scan-matrix hiányzik | nem dokumentált gap (fájlok 04-03 → 04-08 ugranak), ok nem vizsgált — kezelés azonos: explicit hiányzó nap, nem interpoláció |
| tech_filter (nem pontozott) sorok | **NaN, SOHA nem 0** (FRL-0 tanulság: a `Total_Score==0` halmaz mind a 4 mintanapon pontosan a tech_filter halmaz — 0-ként bevonva a swing-panel ~40%-a hamis nulla lenne, dp_pct-hibaosztály) |
| 06-27 → 07-06 (Mini SSH-orphan) | kimarad a dev-mintából; IC-idősorban explicit NaN, nem interpoláció |
| 07-15/16 (áramszünet) | ugyanígy; konzisztens a §11.10 Day 63 edge-minta kizárással |
| 2026-06-19 (Juneteenth), ünnepek | NYSE-naptár a kanonikus napszámláló (`trading_days_between`) |
| legacy snapshot pollution (pl. 04-15) | snapshot forrásként csak integritás-check után (len>3 ÉS nem mock-szignatúra) |

---

## 5. Metrikák és statisztika

### 5.1 Elsődleges metrika

Napi **szektor-relatív Spearman IC**, h ∈ {1, 3, 5, 7} forward trading-nap horizonton
(konzisztensen a signal_attribution.py L2 konvenciójával):

```
IC_t(h) = SpearmanCorr( rank_szektoron_belül(faktor_t),
                        rank_szektoron_belül(r_{t→t+h} − r_szektor,{t→t+h}) )
```

Forward return: Polygon close-to-close, h NYSE trading nap. A h=5 az elsődleges
(a swing pivot mutual-information tézisének közvetlen empirikus párja); a h-görbe
alakja (1→7) maga is riportált diagnosztika.

### 5.2 Aggregátum

- **mean(IC)**, **ICIR = mean(IC)/std(IC)** évesítés nélkül, nyersen riportolva
- **t-stat**: Newey-West korrigált SE-vel, lag = h−1 (az overlapping forward return
  autokorrelációja miatt); alternatív robusztussági nézet: nem-átfedő mintavétel
  (minden h-adik nap) — mindkettő a riportban
- **Éra-bontás kötelező** (G5): legacy / swing / pooled, mindhárom oszlop
- **Éra-kvalifikált detektálhatósági bar (R1#2)**: éránként
  `bar_éra = max(0.02, 2 × SE(mean IC_éra))`, a futáskori tényleges T_eff-ből számolva
  — a küszöb a minta növekedésével automatikusan lazul, kézi hangolás nélkül

### 5.3 Half-life — költség-kapu, NEM kill-kapu

A faktor keresztmetszeti rangsor-perzisztenciája AR(1)-ként: ρ = napi
rank-autokorreláció átlaga, t½ = −ln2/ln ρ. A rövid half-life önmagában nem elutasítás:
turnover-becsléssel (rank-változásból) és a legacy súrlódás-tanulsággal (19-21%/év
teljes költségteher volt) szembesítendő. Riport-mező: `implied_annual_turnover_cost_bps`.

**Költség-input (R1#3): empirikus, nem feltevés.** A per-oldal költség forrása a
`research/cost_model.json`, amit a heti batch a `state/daily_metrics/<date>.json →
execution.slippage_per_ticker[*].slippage_pct` sorozatból frissít (forrás-korrekció
8b8b216: a pending_exits-ben nincs slippage-mező). Becslő: next-day-fill |slippage|
medián és p75 (előjeles nyomatok az overnight driftet is tartalmazzák, ezért az
abszolútérték-eloszlás a torzítatlan cost-becslő, nem a legrosszabb printek).

**Első valós output (8b8b216, 2026-07-21):** swing (05-20→07-20, n=28,
small_n_warning): medián **95.5 bp/oldal**, p75 137.0, max 377.0 — round-trip ~191 bp.
Legacy referencia: 19.0 bp medián (n=99) — az 5× szorzó a végrehajtási stílus-váltás
(intraday LMT → next-day MKT open) ára, ezért `era=swing` a default szűrő, a legacy
költség-minta NEM prior. Következmény: h=5 + teljes heti rotáció ≈ 50 round-trip/év
→ **~9.5%/év végrehajtási költség-korlát** — a faktor-szelekciónak strukturálisan az
alacsony-turnover jelöltek felé kell húznia. (G3-határ: költség-megfigyelés, nem
signal-állítás; Day 63-inputként jegyezve a végrehajtási stílus későbbi vitájához.)
A 3 bp-osztályú feltevések ehhez a stílushoz tiltottak; a korábbi 75 bp-s induló
érték ~27%-kal alábecsült — a HYP-004 costed-IC riport 95.5 bp-on fut.

### 5.4 Defláció — az attempt-ledger él

- Elsődleges: **Benjamini-Hochberg FDR, q = 0.10**, a ledger TELJES történetén
  (minden valaha tesztelt variáns p-értéke együtt, éra-fősorokon)
- Konzervatív másodnézet: Bonferroni a ledger-számmal (a meglévő ház-fegyelem)
- A riport mindkettőt mutatja; PROMOTE-hoz MIND kell (R1#2, R1#4):
  (a) BH-átmenet; (b) |mean IC| ≥ az éra-kvalifikált bar (§5.2) a hivatkozott érán;
  (c) előjel-egyezés a hipotézis várt előjelével; (d) **swing-érás előjel-egyezés
  minimum-feltétel** — pusztán legacy-erőből PROMOTE nincs (a legacy más stratégia:
  6 órás bracket, 800-1370 név, más horizont — gyenge prior a swingre)
- Legacy-pozitív + swing-inconclusive → **PARK-until-swing-power**: automatikus
  újrateszt-trigger, amint a swing T_eff eléri a szintet, ahol a képlet-bar
  elvileg átléphető (a batch minden futáskor újraértékeli a PARK-olt családokat)
- Egy hipotézis h-variánsai (h=1..7) EGY attempt-családnak számítanak, de a családon
  belüli max-IC szelekció ellen a családszintű p a Šidák-korrigált családi minimum-p

### 5.5 Erő-realizmus (FRL-0 után frissítve, 2026-07-21)

FRL-0-verifikált panelméretek: swing N≈257 pontozott/nap, T=36 nap; legacy N≈820
pontozott/nap, T=66 nap.

- Swing: SE(IC_napi) ≈ 1/√257 ≈ 0.062; T_eff(h=5) ≈ 7 → SE(mean IC) ≈ 0.024 →
  **bar_swing ≈ 0.05** (a §5.2 képlettel). A swing-only nézet Day 63 előtt továbbra
  is gyakran "inconclusive" lesz — a riport ezt KÖTELEZŐEN kiírja —, de a bar a
  paper-hetekkel automatikusan lazul (~+5 nap/hét).
- Legacy: SE(IC_napi) ≈ 0.035; T_eff(h=5) ≈ 13 → SE(mean IC) ≈ 0.010 →
  **bar_legacy = 0.02 floor**.
- A legacy+swing kombinált (éra-bontott) nézet a valódi munkafelület; PROMOTE-hoz
  a swing-előjel minimum (§5.4 d) mindenkor kötelező.

---

## 6. Attempt-ledger séma

`research/attempt_ledger.jsonl`, append-only, minden sor egy tesztelt variáns:

```json
{
  "attempt_id": "A-0001",
  "hyp_id": "HYP-001",
  "variant": "pcr_pctile_h5",
  "tested_at": "2026-07-25T21:00:00Z",
  "data_lane": "v1",
  "dev_window": {"legacy": ["2026-02-09","2026-05-15"], "swing": ["2026-05-18","2026-07-11"]},
  "n_days_used": {"legacy": 63, "swing": 29},
  "metrics": {
    "legacy": {"mean_ic": null, "icir": null, "nw_t": null, "p": null},
    "swing":  {"mean_ic": null, "icir": null, "nw_t": null, "p": null}
  },
  "half_life_days": null,
  "implied_turnover_cost_bps": null,
  "decision": "KILL|PARK|PROMOTE",
  "decision_note": "",
  "holdout_touched": false,
  "code_ref": "scripts/research/factors/pcr_pctile.py@<commit>"
}
```

A `decision` mező kitöltése előtt a sor már beírásra kerül (`decision: "PENDING"`) —
így a "teszteltem, de nem tetszett, nem logolom" kiskapu strukturálisan zárt.

---

## 7. Holdout-politika

- **Gördülő embargózott holdout**: mindig a legutolsó K=4 hét (D_B döntéssel
  módosítható), amit a dev-ablak SOHA nem érint. A dev/holdout határon **5 trading-napos
  purge** (a h=5 forward return átfedése miatt a határ-napok mindkét oldalról kiesnek).
- A holdout hetente előre gördül; ami kigördül belőle, az a dev-ablakba érkezik —
  DE egy adott hipotézis holdout-tesztje azon a fix ablakon fut, ami a PROMOTE
  pillanatában aktuális, és **hipotézisenként pontosan egyszer** (G6). A ledger
  `holdout_touched` mezője ezt auditálja.
- Holdout-átmenet kritériuma: előjel-egyezés ÉS |IC_holdout| ≥ 0.5 × |IC_dev| ÉS
  a Šidák-családi p < 0.10 a holdouton. Bukás → `decision: KILL`, a registry
  KILL-szekciójába az ok.
- **Holdout-kopás elleni védelem**: mivel a holdout gördül, a friss paper trading hetek
  folyamatosan valódi, még soha nem látott OOS-t szállítanak — ez az IFDS strukturális
  előnye a fix-holdout platformokkal szemben. A riport minden futásnál kiírja, hány
  hipotézis érintette már az aktuális holdout-ablakot; ha ≥3, a következő PROMOTE vár
  a következő gördülésig.

---

## 8. Hipotézis-registry

### 8.1 Struktúra és template

`docs/design/frl/hypotheses/HYP-###-<slug>.md`, fejléc a task-formátum mintájára:

```
Status: REGISTERED | TESTED | KILLED | PARKED | PROMOTED | HOLDOUT-PASS | SHADOW | DEPLOYED
Updated: YYYY-MM-DD
Data-lane: v1 | v2
Attempt-family: A-00xx..

# HYP-### — <cím>

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)
## Várt előjel és horizont
## Ki a vesztes oldal / milyen frikció tartja fenn
## Költségprofil (várt turnover)
## Pre-reg metrika és kill-kritérium
## Eredmény (a batch tölti)
## KILL/PARK indoklás (ha releváns)
```

### 8.2 Első négy regisztrálandó hipotézis (Chat írja, külön fájlokban)

| ID | Tartalom | Sáv | Megjegyzés |
|---|---|---|---|
| HYP-001a/b | PCR: (a) transzform-szintű IC (v1 — az ÉLŐ flow-sub-score-t méri, ami ténylegesen fut); (b) nyers PCR-percentilis IC-görbe h=1..7, a §5.2 mutual-information tézis (I ∝ h·ρ²) közvetlen tesztje | a: v1 / b: v2 | R1#5: az a-változat a b-t sem megerősíteni, sem ölni NEM tudja — külön attempt-család |
| HYP-002a/b | OTM-inverse: (a) transzform-szintű (v1); (b) nyers decay-profil h=1..7 (v2) | a: v1 / b: v2 | a második Bonferroni-szignifikáns komponens; a/b aszimmetria-szabály érvényes |
| HYP-003a/b | RVOL: (a) transzform-szintű (v1); (b) nyers, swing-horizonton (legacy-n +0.147* volt, intraday mintán mérve) | a: v1 / b: v2 | kikapcsolt komponens újraértékelése az ÚJ horizonton |
| HYP-004 | 5-napos szektor-relatív reversal (a "magas pontszám paradoxon" mean-reversion olvasata OHLCV-ből) | **v1 (tiszta)** | az egyetlen azonnal teljes értékűen tesztelhető — az első batch-futás jelöltje |

**a/b aszimmetria-szabály (R1#5):** a transzform-szintű (a) eredmény a megépített
pipeline-transzformot minősíti (EWMA, küszöbök, sign-flip együtt), nem a mögöttes nyers
jelet. Az a-eredmény a b-hipotézisre nézve nem bizonyíték egyik irányban sem; a ledgerben
külön attempt-családok.

Az M_contradiction sign-flip (04-risks §2.2) NEM FRL-tétel — trade-szintű, kis-n kérdés,
a meglévő Fázis 2 analitikus úton marad.

---

## 9. Shadow-integráció (Day 63 után)

A HOLDOUT-PASS faktor a meglévő shadow-minta szerint (uw_shadow precedens) kap
perzisztáló sinket élesben: a faktor-érték minden nap számolódik és mentődik, de a
scoringot NEM érinti. Minimum 4 hét élő shadow (≈20 nap valódi OOS) + Tamás-jóváhagyás
kell a deploy-javaslathoz, ami ezután normál scoring-revíziós CC-taskként fut — a
következő freeze-ablakon KÍVÜL. A shadow-kiértékelés maga is FRL-batch-tétel (ugyanaz
az IC-motor, shadow-adaton).

---

## 10. Működési rend

- **Kadencia:** heti EGY batch-futás, péntek este a 22:16 utáni sync után (vagy hétvégén).
  Napi loopolás TILOS — az adat hetente ~5 nappal nő, a gyakoribb iteráció csak a zajt
  rendezi újra és inflálja az attempt-számot.
- **Executor:** CC futtatja a MacBookon (`scripts/research/run_frl_batch.py`), a riportot
  a `research/runs/YYYY-MM-DD/report.md`-be írja, és 3-5 soros összefoglalót ad Tamásnak.
  A Mini-t a batch nem érinti; SSH a Mini-re csak a §11 verifikációkhoz kell.
- **Döntések:** KILL/PARK a batch-riport alapján Chat-javaslat + Tamás-ok; PROMOTE és
  minden holdout-érintés explicit Tamás-jóváhagyáshoz kötött.
- **Riport-fegyelem:** minden szám a batch-outputból forrásolható (a review-automatizáció
  validációs-kapu mintája); "inconclusive" kiírása kötelező, ahol az erő nem elég (§5.5).
- **Per-faktor sanity-gate (R1#6):** minden faktor-függvény kötelező `sanity()` párral
  szállítódik (ismert-előjelű szintetikus panelen a várt előjelű IC-t adja); a batch
  előfeltételként futtatja — bukott sanity mellett az attempt el sem indul, ledger-sor
  sem íródik. Cél: a holdout-touch budget (a szűkös erőforrás) védelme buggos
  faktor-implementációtól.

---

## 11. Előfeltételek és verifikációs tételek (CC, Mini SSH-val)

| # | Tétel | Miért blokkoló | Hol |
|---|---|---|---|
| V1 | **Score-szemantika audit — FRL-0 GO/STOP KAPU (R1#1)** — **EREDMÉNY: GO (30b948c + 990d855, 2026-07-21).** Mindhárom gyanús jel feloldva, egyik sem adathiba: (1) 115/257 = pozitív/negatív osztás egy medián≈0 percentilis-különbség jelen, a Total_Score==0 halmaz mind a 4 mintanapon pontosan a tech_filter halmaz; (2) a JSONL legacy-kompozit logolása megerősítve — validátor-szerep éra-függővé téve; (3) tizedes S_j helyes (folytonos EWMA). 102-napos sweep: éra-határ tiszta (05-15 utolsó rácsos / 05-18 első folytonos), degenerált swing-nap 0. Teljes riport: loader-task §Eredmény; tracker: docs/design/frl/TRACKER.md | LEZÁRVA — B-fázis felszabadítva | FRL-0 DONE |
| V2 | **Mini `data/cache/polygon` felmérés** — EREDMÉNY (990d855): cache üres (0B), NEM használható. Helyette: `get_grouped_daily(date)` — teljes US piaci napi OHLCV egy hívásban, a return-mátrix ~110-130 hívásból felépül (vs ~1500/nap per-ticker) | LEZÁRVA | loader B-fázis, return-builder |
| V3 | **Scan-matrix ↔ JSONL keresztvalidáció — ÉRA-FÜGGŐ (FRL-0 szűkítés)**: legacy-érán ticker-halmaz + score-egyezés; swing-érán KIZÁRÓLAG ticker-halmaz-részhalmaz check (JSONL ⊆ CSV pontozott), score-összevetés TILOS (más mennyiség) | a validátor-réteg hamis riasztásainak kizárása | loader B-fázis teszt-szekció |
| V4 | Legacy phase4_snapshot integritás-szűrő (mock-szignatúra detektor) | csak ha snapshot forrásként használatba kerül | loader-task, alacsony prioritás |

---

## 12. Fázisok és effort

| Fázis | Tartalom | Effort | Mikor |
|---|---|---|---|
| FRL-0 | **V1 GO/STOP kapu-riport** + V2 cache-felmérés (R1#1: önálló, jelentés-köteles; STOP-ág definiálva §11) | ~1h CC | most (freeze-safe), MINDEN más FRL-fázis előtt |
| FRL-1 | Loader + return-mátrix + éra-címkézés (task: frl-scan-matrix-loader) | ~4-5h CC | KIZÁRÓLAG FRL-0 GO után |
| FRL-2 | IC-motor + attempt-ledger + batch-riport (task: frl-ic-engine) | ~4-6h CC | freeze alatt build+teszt OK |
| FRL-3 | Registry-bootstrap + HYP-001..004 (task: frl-hypothesis-registry; hipotézis-szöveg: Chat) | ~1h CC + ~2h Chat | FRL-1 után |
| FRL-4 | Első éles batch-futás (HYP-004 a v1-tiszta jelölt) | ~1h CC | FRL-2+3 után; output "Day 63-input, leíró" címkével |
| FRL-5 | v2 enrichment sink (task: frl-cross-section-enrichment) | ~2-3h CC | **D_A DÖNTVE: IGEN** (2026-07-21) — build+teszt kész, deploy a szekvencia szerint |
| FRL-6 | Shadow-integráció + deploy-út | ~3-4h CC | KIZÁRÓLAG Day 63 után |

## 13. Nyitott döntési pontok (Tamás)

| # | Döntés | Státusz (2026-07-21) |
|---|---|---|
| D_A | v2 enrichment sink freeze alatti deploy-a | **DÖNTVE: IGEN (Tamás, 2026-07-21)**, az R1-előfeltételekkel: (1) sink-audit regressziós tesztek zöldek ÉS a teszt-suite futása után a `state/research_cross_section/` mtime **változatlan** (test-env-hygiene check ELŐFELTÉTELKÉNT, nem utólag); (2) napi ops-checklist sor a Log Review chatnél (sor-szám ≈ scan-matrix scored). Deploy-szekvencia: `docs/tasks/2026-07-21-frl-cross-section-enrichment.md`. |
| D_B | Holdout-ablak K | **DÖNTVE: 4 hét** (review-konszenzus). Kaveát rögzítve: a swing-holdout közeltávon alulfeszített (T_eff≈4-6) — eredményei informatívak, nem kötők, amíg a paper-hetek nem akkumulálnak. |
| D_C | FDR-szint q | **DÖNTVE: 0.10** (review-konszenzus). Megkötés: a valódi szűk keresztmetszet a holdout-touch budget — a §7 "≥3 érintés → várj" governor szigorúan betartandó; az éra-kvalifikált bar (§5.2) a swing-oldali zajátengedést zárja. |

---

## Appendix — Task-térkép

| Task fájl | Fázis | Owner |
|---|---|---|
| `docs/tasks/2026-07-21-frl-scan-matrix-loader.md` | FRL-0/1 (V1 kapu-riport, majd GO után loader) | CC |
| `docs/tasks/2026-07-21-frl-ic-engine.md` | FRL-2 | CC |
| `docs/tasks/2026-07-21-frl-hypothesis-registry.md` | FRL-3 | CC (struktúra) + Chat (tartalom) |
| `docs/tasks/2026-07-21-frl-cross-section-enrichment.md` | FRL-5 | CC, D_A után |

## Appendix R — Review Response Log

**R1 — Log Review chat, 6-pontos mérnöki kritika (2026-07-21, v1 → v2):**

| # | Review-pont | Verdikt | Beépítve |
|---|---|---|---|
| R1#1 | V1 audit → önálló GO/STOP kapu, loader-build blokkolva | Elfogadva | §11 V1, §12 FRL-0/1, loader-task |
| R1#2 | PROMOTE |IC|≥0.02 vs §5.5 erő-elemzés inkonzisztencia | Elfogadva + képlet-bar (fix 0.06 helyett `max(0.02, 2×SE)` futásidőben) | §5.2, §5.4 |
| R1#3 | 3 bp/oldal költség ~1-2 nagyságrenddel optimista | Elfogadva + módszertani finomítás (|slippage| medián/p75, nem worst-print; előjeles nyomatok overnight driftet tartalmaznak) | §5.3, `research/cost_model.json` |
| R1#4 | Legacy-only PROMOTE tiltás + swing-előjel minimum | Elfogadva + gépesített PARK-until-swing-power auto-retest trigger | §5.4 |
| R1#5 | v1-proxy a transzformot méri, nem a nyers jelet | Elfogadva + HYP-a/b ID-szétválasztás, aszimmetria-szabállyal | §8.2 |
| R1#6 | Per-faktor sanity-gate hiányzik | Elfogadva (holdout-touch budget védelme) | §10, ic-engine + registry task |

Döntések: D_B=4 hét és D_C=q0.10 LOCKED (két-chat konszenzus); **D_A: IGEN — Tamás,
2026-07-21**, a két R1-előfeltétellel.
