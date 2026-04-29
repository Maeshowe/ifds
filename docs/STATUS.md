# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-29 Budapest, CC /wrap-up (szerda délelőtt — W18 Day 3, vix-close + whipsaw audit deployed, M_contradiction BLOCKED) -->

## Paper Trading
Day 52/63 | cum. PnL: **−$617.46 (−0.62%)** | IBKR DUH118657
**BC23 W18 Day 2 (kedd ápr 28):** -$308 net, excess vs SPY **+0.22%** ⭐ outperform negatív napon
**Breakeven Lock első éles aktiválás:** PAA pozíción 19:00:19 CEST — soft floor entry-re, profit megőrzve (+$135.75)
**MID Bundle Integration:** ÉLES — Stagflation Day 12/28, top XLK/XLE/XLB változatlan

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

**1535 passing** (1377 + 138 Breakeven Lock + 8 vix-close + 9 whipsaw + 3 egyéb), 0 failure

## Utolsó commitok

- `a77d425` — feat(analysis): LOSS_EXIT whipsaw cost retrospective audit (W18 Day 3)
- `0a23a35` — feat(daily_metrics): populate vix_close from Phase 0 log + Polygon fallback (W18 Day 3)
- `f024976` — feat(monitor): add 19:00 CEST breakeven lock for B bracket positions (W18 Day 2)
- `431fc5e` — docs: W18 Day 1 review + status update + 2 új task
- `b92b509` — docs(rules): add live-API schema verification rule (lessons from 25806f2)
- `25806f2` — fix(mid): correct bundle.flat field paths for GIP gauges and TPI
- `41f8e23` — feat(mid): add top_sectors/bottom_sectors and freshness metadata to get_regime()
- `a3dfaf7` — feat(mid): integrate MID bundle API in shadow mode

## Blokkolók

**M_contradiction multiplier (P1, BLOCKED 2026-04-29):** `scripts/company_intel.py` post-submit fut, a CONTRADICTION flag csak LLM prompt template-ben él — Phase 6 sizing-time-ban nem létezik. Re-scoping: Chat 2026-04-30 reggel a tényleges company_intel output formátum alapján.
