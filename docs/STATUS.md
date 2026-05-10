# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-05-10 Budapest, CC /wrap-up (vasárnap délelőtt — két P1 fix deployed: snapshot regression + dp_pct sign-flip + per-ticker UW fetch) -->

## Paper Trading
Day 59/63 | cum. PnL: **−$1,616.13 (−1.62%)** ⚠️ papir aggregát (valós ~-$1,460) | IBKR DUH118657
**BC23 W19 Day 4 (csütörtök máj 7):** **-$501 net (papir)**, excess vs SPY **-0.18%** ✓ marginal underperform mild risk-off napon
**⚠️ ÚJABB STRUKTÚRÁLIS BUG:** SQM 3-split LOSS_EXIT+SL **duplikált zárás** — leftover -91 SHORT! Ugyanaz mint péntek (máj 1) DTE eset. Két alkalom 6 napon belül = struktúrális bug! Új **P1 backlog idea**: LOSS_EXIT bracket SL cancellation
**⭐ QCOM TP1+TP2 sequence: +$556** (a hét legjobbja!) — +10.55% TP2 net 1 nap alatt
**SQM valós veszteség:** csak ~$425 (LOSS_EXIT realízalva), a SHORT 91 holnap reggel `nuke.py`-szel zárul, valószínűleg ~+$110 profittal (mert az ár jelenleg $91.50)
**Score → P&L NEGATÍV korreláció 4 nap egymás után:** RMBS 93.5 = -$160, QCOM 92.5 = +$556, SQM 89.5 = -$425
**Alacsony exposure (3 ticker) 2 nap egymás után** — flow signal konzervatív, megfigyelendő trend
**VIX 17.13** stabil 17 körül, leállítási feltétel inaktív
**4 nap** Day 63-ig — **paper folytatás default** kimenet a legvalószínűbb

## W19 átmenet (4 nap)

| Metrika | W18 hét | W19 D1 | W19 D2 | W19 D3 ⭐ | W19 D4 | W19 átlag |
|---------|---------|--------|--------|----------|--------|------------|
| Net P&L (paper) | -$1,106 | -$191 | -$269 | +$234 | -$501 | -$182/nap |
| Excess vs SPY | -1.90% | +0.21% | -1.04% | -1.14% | -0.18% | -0.54%/nap |
| Win rate | 11/38 (29%) | 3/5 | 2/5 | 2/3 | 1/3 | 8/16 (50%) |
| TP1 hits | 0/38 | 0/5 | 3/5 | 0/3 | 1/3 | 4/16 (25%) |
| TP2 hits | 0/38 | 0/5 | 0/5 | 0/3 | 1/3 ⭐ | 1/16 (6%) |

## W19+ backlog idea-k (most **7**)

1. **⚠️ ÚJ SÜRGŐS: LOSS_EXIT bracket SL cancellation** — P1, ~30-45 min CC (DTE+SQM bug)
2. **10-Q / 10-K SEC Filing Exclusion** — P1, ~2-3h CC (AGNC eset)
3. **ADR earnings adatforrás fix** — P1, ~3-4h CC (BUD eset, FMP hiány)
4. **Breakeven Lock profit-küszöb csökkentés** — P2, ~10-15 min config + tesztek
5. **TP1 cél revízió** — P2, ~30 min config (DBRG TP1 cél túl szűk)
6. **Phase 4 snapshot enrichment** — P3, ~30-45 min (W18 elemzésből)
7. **High-score liquidity check** — P3, ~1h (NE +0.72% slippage)

## Holnapi (péntek máj 8) reggeli teendő

**⚠️ Tamás Mac Mini-n először:** `nuke.py --positions` az SQM SHORT 91 zárására! Második ilyen eset 6 napon belül.

## Előző nap (hétfő máj 4)

**3 nyertes (BG +$179, NOV +$88, OII +$49) kompenzálta** az AGNC veszteséget; csak VTR -$91 másik vesztes
**VIX 18.30** (+9.65% napi) — **vissza 18 fölé**, leállítási feltétel monitor aktív
**Új backlog idea:** 10-Q/10-K SEC Filing Exclusion (W19+ scope, P2)
**7 nap** Day 63-ig — **paper folytatás default** kimenet a legvalószínűbb

## W18 → W19 átmenet

| Metrika | W18 hét | W19 Day 1 |
|---------|---------|-----------|
| Net P&L | -$1,106 | -$191 |
| Excess vs SPY | -1.90% | **+0.21%** ⭐ |
| Win rate | 11/38 (29%) | 3/5 (60%) |
| LOSS_EXIT | 7 | 6 (mind AGNC) |
| Avg score | 91.1 | 92.2 |

## W18 Day 3 (szerda ápr 29) — két task DEPLOYED

**vix-close (`0a23a35`):** `daily_metrics.py` Phase 0 `MACRO_REGIME` event-ből + Polygon I:VIX fallback. 8 új teszt. 2026-04-28 → vix=18.04 (Δ=-0.88%).

**LOSS_EXIT whipsaw audit (`a77d425`):** `scripts/analysis/loss_exit_whipsaw_analysis.py`. BC23 minta (6 esemény, 04-13 → 04-29): **net whipsaw cost +$87.98** — a -2% szabály átlagosan védett, nem rontott. Stop saved: GME +$140, SKM +$107, CRWV +$47. Stop hurt: NIO -$128, POWI -$50, ON -$28. **Tanulság:** a NIO eset egy kivétel, nem szabály. **Ne nyúljunk a LOSS_EXIT-hez.** Részletes táblázat: `docs/analysis/loss-exit-whipsaw-analysis.md`.

**M_contradiction multiplier (BLOCKED):** CC felfedezése: a Company Intel script a Phase 6 UTÁN fut (Telegram-only, nem strukturált flag). 2026-04-29 reggeli Tamás megfigyelés: a Company Intel funkciója NEM döntéstámogatás (saját tanulási eszköz), és a CONTRADICTION jelzés strukturált FMP adatból származik (earnings beat ratio, target consensus, analyst downgrades). **Holnap reggel (Chat) re-scope:** új modul `contradiction_signal.py` direkt FMP-ből, Company Intel érintetlenül.

**Tesztek: 1535 passing**, 0 failure (1380 baseline + 138 Breakeven Lock + 8 vix-close + 9 whipsaw).

## W17 összefoglalás (2026-04-20 — 2026-04-24)

| Nap | Net P&L | Excess vs SPY | TP1 |
|-----|---------|---------------|-----|
| Hétfő | -$433 | -0.21% | 0/5 |
| Kedd | **+$553** | **+1.22%** | 2/5 (POWI) |
| Szerda | +$60 | -0.94% | 0/3 |
| Csütörtök | -$227 | +0.19% | 0/5 |
| Péntek | **+$640** | -0.13% | 1/3 (NVDA) |
| **Σ W17** | **+$593** | **+0.13%** | **3/21 (14%)** |

**Heti metrika:** weekly_metrics.py lefutott, hivatalos report: `docs/analysis/weekly/2026-W17.md`. Kulcs számok: Net +$593.09, 34 trades, Win days 3/5, TP1 3/34 (9%), TP2 2, LOSS_EXIT 7, MOC 22, R:R 1:1.59, Commission $82 (12% of gross), **Score→P&L korreláció r=+0.180** (első pozitív a BC23 óta). Teljes elemzés: `docs/analysis/weekly/2026-W17-analysis.md`.

## BC23 2 hetes kumulatív (W16 + W17)

| Mérés | W16 | W17 | Együtt |
|-------|-----|-----|--------|
| Net P&L | +$1,661 | +$593 | **+$2,254** |
| Cumulative | -$694 | -$19 | **-$19** |
| Excess vs SPY átlag | -2.73% | **+0.13%** | **-1.30%** |
| **Score→P&L korreláció** | **r=-0.414** | **r=+0.180** | **irány váltott** |
| TP1 hit rate | 0/18 (0%) | 3/34 (9%) | 3/52 (6%) |
| Win days | 4/5 | 3/5 | 7/10 (70%) |

**Vélemény:** A BC23 1.5 hét alatt **nem adott pozitív alpha-t** SPY-hoz képest, de **drámai javulás** a W16-W17 közötti átmenettel. Kumulatív **breakeven közelben**.

## Azonosított strukturális problémák (W17 után)

1. **Contradiction pattern 5/6 (83%)** — CONTRADICTION flagged tickerek szinte mindig veszítenek
2. **POWI paradoxon** — recent winner másnap korrigál, scoring nem veszi figyelembe
3. **TP1 fix 1.25×ATR** — csak magas-vol napokon elérhető
4. **Score threshold 85** — gyakran csak 1 qualified, de 5 pozíció (alacsony konverzió)

**Rögzítve backlog-ideas.md-be:** M_contradiction multiplier ×0.80, Recent Winner Penalty / Position Dedup, TP1 dinamikus skálázás, M_target szigorítás.

## Piaci környezet (W17 záró)

- **VIX záró:** 18.72 (-3.01%) — a stressz teljesen feloldódott
- **SPY heti kumulatív:** +0.55% (5 nap)
- **MID regime:** STAGFLATION Day 7 (változatlan a teljes héten)
- **MID events:** 0 egész héten — az event detector konzervatív, regime stabil

## UW Quick Wins + Snapshot v2

**Commits:** `533763b` (QW) + `97fbeda` (Snapshot Enrichment) — W17 elejétől élesben.

## MID API (új fejlemények)

- **2026-04-21:** `/api/bundle/latest` élesben
- **2026-04-22:** `/api/bundle/{date}` historical + webhook/SSE + Alembic normalize
- **2026-04-24:** W17 alatt 0 event (stabil regime)
- **W18:** IFDS MID Bundle Integration shadow mode task CC-nél

## Élesben futó feature-ök

- Pipeline Split: Phase 1-3 (22:00 CEST) + Phase 4-6 (16:15 CEST)
- MKT entry + VWAP guard (csak REJECT >2%)
- Swing Management: 5 napos hold, TP1 50% partial, TRAIL, breakeven SL, D+5 MOC
- Dynamic positions: max 5, score threshold 70 (Phase 4) / 85 qualified
- **UW Client v2**: kötelező header, limit 500, premium aggregálás, dollár-alapú DP
- **Snapshot v2**: dollár + GEX mezők minden új snapshotban ✅
- **MID Bundle Snapshot (shadow mode)**: napi MID bundle mentés `state/mid_bundles/`-be, Phase 0 végén non-blocking. Phase 3 NINCS érintve, csak adatgyűjtés a W19 BC25 GO/NO-GO döntéshez. Aktiválás Mac Mini `MID_API_KEY` beállítás után.
- Cross-Asset Regime + Korrelációs Guard + Portfolio VaR 3%
- Company Intel: 16:15 submit után
- EWMA simítás, M_target penalty, BMI momentum guard
- TP1 1.25×ATR — W17-ben 3 hit (POWI kedd TP1+TP2, NVDA péntek TP1)

## Shadow mode

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | TBD |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés ~máj 2 |
| **MID Bundle Shadow** | **W18 hétfőn indul** | **W19 eleji döntés** |

## W18 prioritásos terv (hétfő ápr 27-től)

### Párhuzamos futtatás

**1. BC23 folytatódik** — normál pipeline, paper trading Day 51-55. Célok:
- A W17-es +0.13% excess **fenntartása vagy javítása**
- TP1 hit rate **stabilizálódása** a 9-15% sávba
- Nincs új strukturális hiba

**2. MID Bundle Integration Shadow Mode** — CC task kész, hétfő reggel kezdés
- `docs/tasks/2026-04-21-mid-bundle-integration-shadow.md`
- Effort: 4-5h
- Output: 5 napi MID bundle snapshot, W19 eleji comparison

**3. Kis priority CC task (ha idő van):**
- **M_contradiction multiplier ×0.80** implementáció (2-3h)
- Alapja: 5/6 W17 pattern
- Risk: alacsony, konzervatív paraméter

### NEM W18-ra

- **Recent Winner Penalty / Position Dedup** — várunk W18 adatra, ha ismétlődik a POWI-minta
- **TP1 dinamikus skálázás** — BC24 scope
- **BC25 Phase 3 refactor** — W19 után, shadow mode eredménye alapján
- **BC24 UW Institutional Flow** — W19+ scope

## Paper Trading Day 63 (~máj 14) döntési keret

**13 nap múlva** éles/paper döntés. A jelenlegi -$19 breakeven nem indokol élesre váltást.

**Valószínű kimenet:** +1 hónap paper trading, közben a fenti javítások implementálása, és **június elején** újra-kiértékelés.

## Anomáliák

- **ARMK 4-split péntek** — 428 shares → 100+103+100+125. Érdekes lenne hétfő utáni elemzés a IBKR paper account max order size viselkedéséről.
- **Telegram regresszió** változatlanul él ("4/6 breakdown" hiányzik).
- **CRGY + AAPL leftover** — 5 napja folyamatosan, hétvégi Tamás nuke.
- **`docs/analysis/weekly/2026-W17.md`** — a hivatalos weekly_metrics.py report **megérkezett** ✅

## Tervezett BC-k (változatlan)

- **BC24 Institutional Flow Intelligence** (~W19-W22, máj 4-29) — UW új endpoints, dollar-weighted scoring
- **BC25 IFDS Phase 3 ← MID CAS** (~W20+) — MID bundle API kész, shadow mode W18-ban, GO/NO-GO W19 elején
- **Paper Trading Day 63** (~máj 14): éles/paper folytatás döntés

## Hétvégi teendők

- **Tamás:** CRGY + AAPL leftover manuális nuke
- **Tamás:** pt_daily_metrics cron időzítés (W17 két napon ~1 óra késés)
- **Chat:** MID vs IFDS sector rotation informális elemzés (CAS heatmap alapú)
- **Chat:** W17 weekly elemzés ✅ elkészült (`docs/analysis/weekly/2026-W17-analysis.md`)

## Tesztek

**1556 passing** (1535 + 1 snapshot regression + 6 dp_pct rec — 11 legacy frissítve net), 0 failure

## Utolsó commitok

- `9a169b9` — feat(scoring): dp_pct sign-flip + threshold recalibration + per-ticker UW fetch (W19 hétvége)
- `d3fce73` — fix(tests): mock save_phase4_snapshot in e2e — production state pollution regression (W19 hétvége)
- `f7b9024` — analysis(dp_pct): retrospective audit — UW dark-pool % shows significant INVERSE correlation with P&L per share
- `cf5cafa` — docs: 2026-05-07 daily review + LOSS_EXIT bracket SL cancellation P1 backlog
- `1e418f0` — docs: 2026-05-06 daily review — Breakeven Lock profit-trigger discovery
- `220a96c` — docs: W19 D2 daily review + 4 new W19+ backlog ideas
- `ada8f28` — docs: backlog — ADR earnings adatforrás fix diagnosztika megerősítve (BUD)
- `62f9c52` — docs: backlog idea — 10-Q/10-K SEC filing exclusion (AGNC 2026-05-04)

## Blokkolók

Nincs.

**Aktív P1 fix-ek (2026-05-10 deployolva, hatás W20-tól mérhető):**
- **dp_pct sign-flip** (`9a169b9`): magas-DP tickerek -10/-15 score reduction; flow-súly 0.40 mellett ~-4/-6 pont a combined_score-on
- **Snapshot regression fix** (`d3fce73`): Mac Mini `git pull` után a holnapi 16:15 cron tisztán ment 90+ ticker, a flow_decomposition újrafuttatható lesz friss adaton

**W19+ backlog (Chat-oldal):** LOSS_EXIT bracket SL cancellation (P1, 2× ismétlődő bug), 10-Q/10-K SEC Filing Exclusion (P1, AGNC+BUD), ADR earnings adatforrás fix (P1, BUD)
