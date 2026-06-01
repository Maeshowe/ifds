# IFDS Daily Review — 2026-06-01 (hétfő, Day 10 Swing Pivot, W23 D1)

> CC-generált review. Fókusz: **Part A ledger forward-fix DEPLOY** + **WST nyitó MKT fill execution-quality vizsgálat** (paper-fill realizmus, szisztematikus nyitó-slippage check Polygon vs IBKR).

---

## 0. Part A (ledger forward-fix, P0 §0.11) — DEPLOY-OLVA ✅

A 2026-05-29-i locked spec alapján a Part A implementálva + élesítve (Tamás jóváhagyással).

- **6 implementációs darab**: `lib/pending_exits.py` (ledger), `lib/ibkr_reconciliation` helper-move, `close_positions` guarded ledger-write (mindkét swing ág), `daily_metrics.record_pending_exits` (egyetlen cumulative writer, clientId=18, `--date` backfill), `eod_report` write-kikapcsolás + silent-0-pnl WARNING.
- **Tesztek**: 1828 → **1862 passing**, 0 failure, 0 warning. Mac Mini pre-flight zöld.
- **Push**: `66faf29..a6d6d19`. Backup: `cumulative_pnl.json.bak.pre_partA.20260601_140510`.
- **Day 9 AMH backfill**: a `record_pending_exits --date 2026-05-28` **0 executiont** kapott — az IBKR `reqExecutions` csak az aktuális session fill-jeit adja, 4 napos historikus fillt nem ér el → a recorder **helyesen** unprocessed-ben hagyta (nem fabrikált P&L-t, a guard élesen validálva). A backfill az IBKR connector `get_account_trades` (DAYS_30) authoritatív értékéből: **AMH realized -$57,48** (SELL 249@31.99 MOC, valós entry 32.21 weighted, NEM a doc-beli 32.11). **Cumulative -651,10 → -708,58**, ledger processed, idempotencia igazolva.
- **Forward-fix ÉL**: Day 10-től (5/29+) a `close_positions` natívan ledger-be ír, a 22:10 cron same-day befogja. Az első éles same-day próba a hétfői (6/01) 21:40 close.

---

## 1. Mai entry — WST (1 db új belépő)

- **WST** (West Pharmaceutical Services, Health Technology / Medical Specialties): **BUY 18 @ $324.33** MKT, 2026-06-01T13:31:10Z (09:31 ET).
- Tervezett: LIMIT $322.81 (= előző záró), score **83,93** (magas), Healthcare, sector_BMI 50,0.
- ⚠️ `contradiction_flag = 1` — `price_above_consensus_2.2pct` (belépő az elemzői konszenzus fölött 2,2%-kal).
- WST a nap során leesett ~$314,13-ra (-2,69%), azaz a belépő jelenleg unrealized mínuszban.

---

## 2. ⭐ Execution-quality vizsgálat — nyitó MKT fill paper-realizmus

**Kiváltó ok** (Tamás megfigyelése): a WST fill $324,33 volt, de a valós nyitás ~$321,66 — $2,67-tal a piac fölött. Kérdés: szisztematikus-e a nyitó paper-slippage?

### 2.1 Módszer

IBKR `get_account_trades` (DAYS_30) BUY fill-ek vs Polygon 1-perces valós nyitóbárok. A swing-era (5/18+) MKT-at-open belépők (~13:30–13:31Z) az érdekesek; a régi (5/4–5/15) ~14:18Z day-trade belépők más rezsim, kihagyva. Benchmark: a nyitó-ablak (13:30 → fill-perc) **high-ja** — ez a "ki lehetett-e volna tölteni a valós tapen" mérce (a MKT buy az ask-en tölt, ami pár centtel a trade-high fölött lehet — ez normális spread).

### 2.2 Eredmény (15 swing belépő)

| Ticker | Dátum | Fill | Valós open | Ablak HI | dev vs open | flag |
|---|---|---|---|---|---|---|
| LBRT | 5/18 | 33,33 | 33,11 | 33,31 | +0,66% | marginális (+$0,02 HI fölött) |
| EC | 5/18 | 13,07 | 12,93 | 13,07 | +1,08% | in_range |
| MASI | 5/18 | 178,50 | 178,49 | 178,49 | +0,01% | marginális (+$0,01) |
| PFGC | 5/19 | 96,55 | 95,78 | 96,37 | +0,80% | +$0,18 HI fölött |
| WMB | 5/21 | 78,35 | 78,19 | 78,25 | +0,20% | +$0,10 HI fölött |
| DXCM | 5/21 | 71,83 | 71,50 | 72,00 | +0,46% | in_range |
| AMH | 5/22 | 32,21 | 32,24 | 32,24 | -0,09% | in_range |
| EOG | 5/26 | 140,40 | 139,89 | 140,41 | +0,36% | in_range (13:37) |
| AKAM | 5/26 | 146,40 | 148,45 | 149,60 | **-1,38%** | below (kedvező, 13:54) |
| JHG | 5/27 | 51,82 | 51,81 | 51,82 | +0,02% | in_range |
| ST | 5/28 | 50,22 | 50,12 | 50,28 | +0,20% | in_range |
| ROIV | 5/28 | 29,70 | 29,53 | 29,68 | +0,58% | marginális (+$0,02) |
| AMH | 5/29 | 31,91 | 31,90 | 32,01 | +0,03% | in_range |
| CDNS | 5/29 | 374,79 | 375,00 | 375,36 | -0,06% | in_range (kedvező) |
| **WST** | **6/01** | **324,33** | **321,65** | **321,65** | **+0,83%** | **🚩 +$2,68 HI fölött** |

### 2.3 Verdikt — NEM szisztematikus, WST egyedi anomália

- **14/15 belépő realisztikus**: a fill a nyitó-ablakon belül vagy marginálisan (≤$0,18) fölötte — ez a normál **ask-oldali spread** (MKT buy az ask-en tölt). Néhány kedvező is van (CDNS -0,06%, AKAM -1,38%, AMH -0,09%).
- **WST 6/01 az egyetlen valódi kiugró**: a teljes nyitó-ablak high-ja **321,65** volt (a 13:31-es percre Polygonban nincs is print), mégis **324,33-on** töltött — **+$2,68 (+0,83%) a valós tape fölött**. Ez nem spread, hanem **paper-fill artefakt** (IBKR paper sim szimulált ask vékony/print-mentes nyitó-percben).
- **Dollár-hatás**: WST 18 × ~$2,68 ≈ **~$48 fantom belépési költség**. A többi 14 belépő összesített ablak-fölötti torzítása elhanyagolható (~cent-szint).
- **Irónia**: a swing pivot MKT-t ad be (Day 63 §3.12, garantált fill), de egy valódi LIMIT $322,81 itt ~321,65-ön töltött volna — **jobban**. A MKT-at-open a nyitó-volatilitásnak + paper-sim torzításnak van kitéve.

### 2.4 Következmény a P&L-értelmezésre

- A paper belépő-fillek **alkalmanként** (nem szisztematikusan) felülbecslik a belépési költséget → a paper P&L ezeknél **pesszimistább** a valósnál. WST esetén ~$48 fantom mínusz.
- Élesben (valós NBBO + szűkebb spread) ez a torzítás nem, vagy sokkal kisebb mértékben jelentkezne. Ugyanaz a realizmus-kérdéskör, mint a `cumulative_pnl.json` disclaimer (nuke-záró árak).
- **Akció (megfontolásra, Chat hatáskör)**: a nyitó MKT helyett **MKT a nyitó-auction után pár perccel** vagy **marketable LIMIT** (pl. open + X bps) csökkenthetné a nyitó paper-slippage kitettséget. NEM sürgős — egyetlen anomália 13 nap alatt.

---

## 3. Cumulative állapot

- **Hivatalos (Part A után)**: **-$708,58** (Day 1-9, trading_days=9). Day 9 AMH -$57,48 most már rögzítve.
- A WST belépő friss, exit még nincs — a Day 10 realized a hétfői EOD-tól indul a forward-fix-en.

---

## 4. Aktív megfigyelések

- **§EXEC-1 (új, P2)**: nyitó MKT paper-fill anomália — WST 6/01 +$2,68 a valós tape fölött. NEM szisztematikus (14/15 ok). Megfontolandó: belépő-timing finomítás (post-auction MKT / marketable LIMIT). Lásd [[learnings-archive]].
- **Part A forward-fix**: első éles same-day befogás a hétfői 21:40 close-tól — figyelni a 22:10 `daily_metrics` cron-t + `state/pending_exits/`-et.
- **WST unrealized** -2,69% a belépő óta — Day 10+ figyelő.

**A nap egy mondatban**: A Part A ledger forward-fix élesítve (cumulative -708,58, Day 9 AMH végre rögzítve a broker-authoritatív -$57,48-cal), és egy Tamás-megfigyelésből indított execution-quality vizsgálat kimutatta, hogy a nyitó MKT paper-fillek **általában realisztikusak** (14/15 a nyitó-ablakon belül/ask-spread), a WST 6/01-i **+$2,68 fill viszont egyedi paper-sim artefakt** (~$48 fantom költség) — nem szisztematikus, de a paper P&L pesszimista-irányú torzításának dokumentált példája.

---

**Adatforrások**: IBKR `get_account_trades` (DAYS_30), Polygon 1-perces aggregátumok (`state` nem érintve, read-only), `state/phase4_snapshots/`, `output/execution_plan_run_*`.
