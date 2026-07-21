Status: OPEN
Updated: 2026-07-21
Note: Session-indító a FRL (Factor Research Loop) BUILD-szálhoz — külön session. Ez a párhuzamos fejlesztési munkamenet első példánya. A napi/heti review-feladatok NEM ide tartoznak (azok a review-sessionben maradnak).

# FRL Build — Session-indító (új session ezzel kezdjen)

## Mi ez

A **Factor Research Loop (FRL)** egy fegyelmezett, iteratív faktor-kutatási keret (hipotézis → teszt →
pontozás → visszacsatolás) az IFDS keresztmetszeti adatán. Célja strukturálisan lehetetlenné tenni a Day 63
gyökérok (ad-hoc súlyok, keresztmetszeti validáció nélkül) megismétlődését. **Read-only elemző-tooling**,
a `signal_attribution`-wiring precedens szerint — production kódot/cront/scoringot NEM módosít.

**Ez egy CC-build session.** Lane-higiénia ([[division-of-labor-chat-cc]]): Chat/Dev írja a specet és a
hipotéziseket; **CC implementálja a toolingot és futtatja a batch-et**; Tamás dönt PROMOTE/deploy-nál.

## Olvasandó ELSŐKÉNT (a kanonikus források)

1. `docs/design/2026-07-21-factor-research-loop-spec.md` — **DRAFT v2** (Appendix R-ben a Log Review chat
   6-pontos kritikája beépítve). Ez a teljes keret: G1–G7 governance, 8-lépéses loop, forrás-hierarchia,
   §4.3 sync-topológia, IC/ICIR/half-life matematika (Newey-West, BH-FDR), gördülő embargózott holdout.
2. A 4 task (mind `docs/tasks/2026-07-21-frl-*.md`, egységes Status/Updated/Note fejléc):
   - `frl-scan-matrix-loader.md` (OPEN) — **FRL-0 kapu + FRL-1 loader**
   - `frl-ic-engine.md` (OPEN, előfeltétel: loader DONE) — IC-motor, ledger, holdout, batch
   - `frl-hypothesis-registry.md` (OPEN) — template + lint (hypothesis-first gépi kikényszerítés)
   - `frl-cross-section-enrichment.md` (BLOCKED) — v2 sink, **D_A-ra vár**

## Az EGYETLEN blokkoló: D_A

- **D_A** (v2 enrichment sink freeze alatti deploy): **Tamás megerősítésére vár.** Mindkét chat ajánlása
  **IGEN** (§4.2/1 display/tracking carve-out, viselkedés-invariáns, minden nap v2 adatveszteség). Két
  **kemény előfeltétel a taskba kódolva**: (1) sink-audit regressziós tesztek zöldek MINDKÉT e2e
  patch-stackben; (2) a pytest-suite után a `state/research_cross_section/` **mtime nem változik**
  (a [[test-env-hygiene]]-ből; ez deploy-tiltó feltétel). → **Ha Tamás azt mondja „D_A ok", a teljes
  sorrend vihető.**
- **D_B = 4 hét** (holdout K) és **D_C = q 0.10** (FDR): **eldöntve, defaultként** (mindkét chat + nincs
  kifogás). A `frl_config.py`-ban élnek, D_A-tól függetlenek — a CC ezekkel indulhat.

## Kickoff-sorrend (kötelező)

```
FRL-0  V1 GO/STOP kapu (jelentés-köteles)  ← ELSŐ, önálló, ~1h, freeze-safe
   │      └─ ha score-oszlop éra-inkonzisztens/degenerált → STOP + re-scope (NE építs loadert)
   ▼ (GO)
FRL-1  loader + return-mátrix + research/ bootstrap
FRL-2  ic-engine + ledger + holdout + batch
FRL-3  registry + lint + HYP-001..004 váz (tartalom: Chat, külön kör)
FRL-5  enrichment build  ← csak D_A=ok után; a Mini-deploy külön Tamás-push
```

### FRL-0 a legfontosabb lépés — miért go/no-go

A teljes IC-motor a `full_scan_matrix` score-oszlopán fut. A 2026-07-21 felderítés 3 gyanús jelet hagyott:
(a) `Total_Score>0` csak **115/257** a 07-20-i fájlban; (b) a swing-érás JSONL `TICKER_SCORED`
**legacy-stílusú kompozitot** logolt (07-14 minta, .0/.5 lépésköz); (c) a uw_shadow tizedes S_j-ket mutat.
Ez ugyanaz a hibaosztály, mint a **dp_pct strukturális-nulla** és a **phase4 AAPL-mock** (`ifds-rules`).
**Ha a swing-érás score-oszlop valójában a legacy kompozit, a v1 faktorteszt rossz oszlopon fut** — ezért
FRL-0 önálló, jelentés-köteles kapu **STOP-ággal**; a loader-build a GO előtt nem indul. A V1 kérdések +
V2 (Mini polygon-cache `du -sh`) + V3 (3 mintanap keresztvalidáció) a loader-task 0. szekciójában.

## Governance, amit NEM lehet megsérteni (spec §2)

- **G1 gate-szeparáció (mindkét irányban):** minden FRL-output ÖRÖKRE leíró. A Day 63/126 kapu egyetlen
  inputja a `signal_attribution.py` (pinned `c5e9ed0`). **Pozitív FRL-eredmény ugyanúgy inadmissibilis a
  kapuba, mint negatív.** Riport-fejléc kötelező sora: *„Leíró elemzés — Day 63 gate-input NEM (G1/G3)."*
- **G3:** signal-validity nyelv tilalom Day 63-ig („edge/alpha/működik" tilos; „leíró IC-becslés" megy).
- **G4 PENDING-first:** minden tesztelt variáns (a KILL-ek is) a ledgerbe kerül, `decision: PENDING`-gel a
  teszt FUTTATÁSA ELŐTT. Ledger-en kívüli teszt = protokollsértés.
- **G5 éra-tisztelet:** legacy (02-09→05-15) és swing (05-18→) SOHA nem pooled éra-bontás nélkül.
- **G6 holdout egy-érintés:** hipotézisenként max 1 holdout-teszt; bukás = halott.
- **G7 lane-higiénia:** Chat=spec+hipotézisek; CC=tooling+batch; Tamás=PROMOTE/deploy.

## A 6 review-pont, ami a v2-be került (amit a build-nak tudnia kell)

1. **V1 → FRL-0 GO/STOP kapu** (fent). §11/§12.
2. **Éra-kvalifikált PROMOTE-küszöb — KÉPLET, nem fix:** `era_bar = max(0.02, 2×SE(mean IC_éra))` a
   futáskori tényleges T_eff-ből. Automatikusan lazul, ahogy a swing-minta nő. §5.2/5.4, `era_bar()`.
3. **Empirikus költségmodell:** `research/cost_model.json`, amit a heti batch a `pending_exits`
   slippage-mezőiből frissít; a cost-input a next-day-fill **|slippage| eloszlás mediánja/p75-e** (NEM a
   szélső printek — a ±1% előjeles nyomatok az overnight driftet is tartalmazzák). Induló **75 bp/oldal ⚠️
   kis-n**. §5.3. → **Keresztbeporzás: a review-session napi slippage-adata táplálja ezt** (lásd lent).
4. **Legacy-only PROMOTE tiltva:** swing-előjel-egyezés minimum-feltétel; legacy-pozitív + swing-inconclusive
   → **PARK-until-swing-power** automatikus újrateszt-triggerrel (amint a T_eff eléri a #2 bar-t).
5. **HYP a/b szétválasztás:** HYP-001/002/003 kettéválik a-változatra (transzform-szintű, v1 — az ÉLŐ
   scoring-transzform IC-je) és b-változatra (nyers jel, v2). **Aszimmetria-szabály:** az a-eredmény a b-t
   sem megerősíteni, sem ölni nem tudja. HYP-004 (tiszta v1 OHLCV reversal) marad az első teljes futás.
6. **Per-faktor sanity-gate:** minden faktor-függvény kötelező `sanity()` párral (ismert-előjelű szintetikus
   panel); a lint + batch-előfeltétel futtatja; bukott sanity = az attempt el sem indul (a holdout-touch a
   szűkös erőforrás — buggos faktor elpazarolt érintése a legdrágább hiba). §10.

## Architektúra-emlékeztetők (kritikus)

- **`research/` ÚJ top-level, a `sync_from_mini.sh --delete` halmazán KÍVÜL** (§4.3) — különben a következő
  sync törölné. `research/attempt_ledger.jsonl` + `runs/YYYY-MM-DD/` git-tracked; `research/cache/` gitignore.
  A hipotézis-fájlok `docs/design/frl/hypotheses/` alatt, git-ben.
- **A batch a MacBookon fut** (`scripts/research/run_frl_batch.py`), a Mini-t nem érinti. SSH a Mini-re csak
  a V1/V2 verifikációhoz. A permission már megvan: `Bash(ssh ifds-mini:*)` az allowlisten.
- **Freeze:** build+teszt a freeze alatt OK; éles felhasználás/deploy Day 63 után. Az enrichment sink
  (FRL-5) az egyetlen Mini-oldali elem, az is csak D_A=ok után.
- **TDD, baseline 1985 passing** (csak nőhet); commit-konvenció `feat(research): …`; **Tamás pushol**
  (CC commitol). Task-workflow: OPEN→WIP (megnyitáskor)→DONE (commit után).

## Cross-session határ (fontos)

- **Ez a review-session megtartja:** a napi/heti v6 review-kat (Fázis A) ÉS a next-day-fill slippage
  megfigyelés-sorozatot. Ez a slippage-adat (`pending_exits` slippage-mezők + a review §7 sorozat) a
  **közvetlen input** az FRL `cost_model.json`-jébe (#3). A build-session a `pending_exits`-ből olvassa;
  a review-session termeli/dokumentálja. Egyetlen megosztott adatfelület, nincs kód-ütközés.
- **A build-session NEM csinál review-t.** Ha review-igény jön, az a review-sessionbe tartozik.

## Első konkrét lépések a friss sessionnek

1. Olvasd a spec v2-t + a loader-task FRL-0 szekcióját teljesen.
2. **(Opcionális housekeeping):** a FRL spec + 4 task jelenleg **untracked** — commitold őket
   (`docs(design): FRL spec v2 + 4 task (Chat-szerzőség, R1 beépítve)`), hogy a build durable alapon menjen.
   Ez Chat-szerzőségű tartalom, de a commit CC-lane; Tamás pushol.
3. **Erősítsd meg D_A státuszát** Tamással (ha még nyitott, a loader/ic-engine/registry mehet nélküle is —
   csak az enrichment (FRL-5) vár rá).
4. **Futtasd az FRL-0 V1 auditot** (kód-olvasás: `_apply_swing_scoring`, `write_full_scan_matrix` hívási
   hely a runner.py-ban, TICKER_SCORED emitter; + 3 mintanap: 04-15 legacy, 06-25 + 07-14 swing) → írd a
   **kapu-riportot** a loader-task §Eredmény szekciójába. **GO** vagy **STOP+re-scope**.
5. GO esetén: loader → ic-engine → registry → (D_A=ok) enrichment. A kapu-riport után **Chat** frissíti a
   §5.5 erő-becslést a tényleges score-szemantikára, és megírja a HYP-tartalmakat (a/b struktúra).

## Referenciák

- Memória: [[division-of-labor-chat-cc]], [[test-env-hygiene]] (sink-audit), [[sync-delete-vs-local-commits]]
  (§4.3 indoka), [[mini-financial-write-guard]] (FRL read-only, nem érintett).
- 04-risks: §6.6 (pooling/tükör-guardrail), §8.1.6-9 (sink-audit szabály), §11.10 (outage edge-kizárás).
- edge-audit: `docs/foundational/strategic-review/2026-06-10-edge-audit.md`.
