Status: DONE
Updated: 2026-06-03
Note: §1-7 implementálva + tesztelve (1870 passing) + deploy. §1 NYSE Day-N, §2 top movers, §3a day-change (daily_equity store), §4 exit-merge, §5 S_j labels, §6 Day 21 chkpt, §7 TRADING PLAN shadow cleanup (Option A). Első éles render: ma 22:05 EOD.

# Telegram EOD finomítás + TRADING PLAN legacy-cleanup (phase 2)

**Priority**: P2 — display/clarity, nincs trading-logika érintés
**Scope**: ~2-3 óra CC (EOD render 6 pont + TRADING PLAN legacy field cleanup)
**Érintett fájlok**: `src/ifds/output/swing_telegram.py`, `scripts/paper_trading/eod_report.py`, `scripts/paper_trading/daily_metrics.py`, `src/ifds/output/telegram.py`, + új napi-equity store

## Probléma

A Day 11 (6/1) EOD Telegram már lényegesen jobb a Day 8-i kaotikushoz képest (realized/unrealized szétválasztva, triggered exits, CB buffer, cumulative real-mark). 6 kisebb finomítás maradt + egy audit kimutatta, hogy a TRADING PLAN üzenet még a swing pivot előtti (day-trade-era) legacy mezőket mutatja.

## Döntések (Chat + CC review, 2026-06-01)

- **Day-N**: NYSE trading-nap count a `start_date: 2026-05-18`-tól (`ifds.utils.trading_calendar`). NEM `cumulative_pnl.trading_days` (=9, P&L-entry alapú, torzított), NEM naptári hétköznap (=11, holiday beleszámol). 6/1 = **Day 10**. Indok: a swing tézis trading-napokban gondolkodik (`days_held` is trading-day a `0b2ddaa` óta) → konzisztens kalendárium.
- **Top movers**: 3-3, magnitúdó-küszöbbel (csak |upnl| ≥ $50 jelenik meg) → csendes napon auto-tömörít.
- **3a (Day change)**: BENNE, `total_equity` napi mentéssel. **3b (BEST DAY címke)**: KÜLÖN későbbi task.
- **Top S_j címke**: `[holding]`/`[selected]`/`[skipped]`; ha könnyen van skip-ok, in-place magyarázat, ha nem, sima `[skipped]`.
- **TRADING PLAN cleanup**: az audit szerint legacy GEX/MMS/breadth/crowd mezők → swing-era takarítás (a konkrét vágások Tamás design-sign-off-fal, lásd §7).

---

## EOD finomítások (`swing_telegram.format_swing_compact_telegram`)

### 1. Day-N fix (NYSE trading-nap count)
- Új helper (pl. `daily_metrics._compute_trading_day_number(target_date, start_date="2026-05-18")`) az `ifds.utils.trading_calendar` NYSE napjaiból (inkluzív, holiday kizárva).
- `daily_metrics.build_daily_metrics` `day_number` ezt használja (ne a `trading_days`-t).
- `eod_report.main()` `metrics["day_number"] = trading_days` override **eltávolítandó/cserélendő** a NYSE-count-ra.
- Telegram header: `🌅 IFDS Swing — 2026-06-01 (Day 10/63, W23 D1)` — a `/63` és a `W{n} D{d}` opcionális, de hasznos.
- `cumulative_pnl.trading_days` szemantikája VÁLTOZATLAN (P&L-tracking mérőszám marad, NEM kalendárium).

### 2. Top movers (per-pozíció unrealized)
- **Plumbing**: `eod_report` már lekéri `ib.portfolio()`-ból a per-pozíció `unrealizedPNL`-t (a `unrealized_total` loopban). Építsen egy `{ticker: upnl}` dict-et és injektálja: `metrics["pnl"]["per_position_unrealized"] = {...}`.
- `swing_telegram`: ha van `per_position_unrealized`, rendereljen Top/Bottom **3-3**-at, **csak |upnl| ≥ $50** moverekre:
  ```
  📊 Unrealized: $+265.64 (8 open)
     ⭐ Top: CDNS +$553 | AKAM +$128 | AMH +$99
     ⚠️ Bot: EOG -$168 | WST -$137 | ROIV -$88
  ```
- Single-position koncentráció a kulcs-jel (CDNS = a nettó unrealized 207%-a) — a $50 küszöb természetesen kiemeli.

### 3a. Day change (total_equity napi mentés)
- **Forrás**: `eod_report` 22:05-kor `ib.accountSummary()` → `NetLiquidation` (float).
- **Tárolás**: külön könnyű store — `state/daily_equity.json` (`{ "2026-06-01": 99764.65, ... }`), eod_report írja atomikusan. **NEM** a `cumulative_pnl.json`-ba, hogy a Part A single-writer (`record_pending_exits`) invariáns ne sérüljön. (CC döntse el a végső helyet/kulcsot — csak backward-compat legyen: hiányzó equity → "n/a".)
- **Day change**: `today_netliq - yesterday_netliq` (Day 1-en `- initial_capital`). Render:
  ```
  📈 Day change:   $+523 (+0.53%)
  ```
- **3b (BEST DAY címke)**: NEM ebben a taskban — a teljes napi-change história + `max()` kell, a 3a deploy után pár hét adat gyűlik, akkor külön task.

### 4. Triggered/holnap exit egyesítés + gazdag detail
- A jelenlegi `📤 Triggered exits: 1 TP2 → holnap 15:30` + `⚡ Holnap exit-tervek: 15:30: CDNS_TP2` **duplikáció** → egy sorba:
  ```
  ⚡ Holnap (Day 11) 15:30 CEST exit:
     CDNS TP2 — entry $373.85 → mark $414.33 (+10.5%, várt fill ~$410, realized ~+$506)
  ```
- Detail forrás: `swing_positions` (entry_price, tp2_level, qty) + per-ticker mark. **A mark az EOD path-ban nincs kéznél** — vagy a per-pozíció unrealized-ból visszaszámolható (`mark = entry + upnl/qty`), vagy az `eod_report` injektálja a markokat. CC döntse el a legkisebb-diff megoldást. Ha a mark nem elérhető tisztán, a sima egyesített sor (entry + level + qty) is elég — a +%/várt-fill nice-to-have.

### 5. Top S_j státusz-címke
- `[holding]` = ticker a `swing_positions`-ben; `[selected]` = `swing_state.new_entries_tickers`-ben; egyébként `[skipped]`.
  ```
  🎯 Top S_j today:
     MASI  94.1 | Healthcare           [skipped]
     AKAM  89.8 | Technology           [holding]
     JHG   88.0 | Financial Services   [holding]
  ```
- Ha van könnyen elérhető skip-ok (selection_log), in-place: `[skipped — sector full]`. Ha nincs, sima `[skipped]` (a sector-balanced greedy nem feltétlen logol okot — CC dönti el, hogy triviális-e).

### 6. Day 21 checkpoint indikátor
- A meglévő `🟢 CB buffer: $-709 / $-5,000 (85.8%)` alá:
  ```
  📍 Day 21 chkpt: $-709 / $-1,500 (52.7% buffer, X days left)
  ```
- Küszöb (`-1500`) + Day 21 dátum a Day 63 decision doc-ból (`docs/decisions/2026-05-14-day63-decision-outcome.md`, §Day 126/Day 21 milestone). `X days left` = Day 21 − aktuális Day-N (NYSE-count).

---

## 7. TRADING PLAN legacy-cleanup (`telegram._format_phases_5_to_6`) — audit (B)

**Audit megállapítás (2026-06-01)**: a TRADING PLAN (`send_trading_plan` → `_format_phases_5_to_6`) a swing pivot előtti legacy mezőket mutatja prominensen, mintha döntéshozók lennének, pedig **shadow-only / deaktivált** (Day 63 §2: UW/GEX kikapcsolva, scoring = PCR + OTM-inverse):

| Sor | Jelenlegi | Swing-era státusz |
|-----|-----------|-------------------|
| `[5/6] GEX Analysis` + `Excluded (NEGATIVE regime): N` | prominens szekció | GEX scoring **deaktivált** → félrevezető |
| `Breadth: {regime} (n/11)` | megjelenik | breadth nem hajt swing döntést |
| `MMS (collect-only): {regimes}` + `Baseline: ...` + `MMS: collect-only (day N/21)` | teljes blokk | `mms_enabled` shadow-only → zaj |
| `Crowd: x good/neutral/bad` | megjelenik | crowdedness shadow-only |

**DÖNTÉS (Tamás, 2026-06-01): Opció A — agresszív.**
- A teljes `[ 5/6 ] GEX Analysis` blokkot (GEX NEGATIVE exclusion, breadth, MMS regime + baseline + day-estimation, crowd) **lecseréljük egy 1-soros shadow-jelzésre**:
  ```
  [ 5/6 ] Shadow signals
  GEX / MMS / breadth / crowd: collected (shadow — nem dönt)
  ```
  A `[ 6/6 ] Position Sizing` szekció (ami ténylegesen hajtja a swing döntést) változatlan marad.
- Indok: ezek shadow-only-k (Day 63 §2), a shadow-internals nem valók a TRADING PLAN-be; a `state/uw_shadow` log megőrzi a Day 90 UW-rekalibrációhoz szükséges adatot.
- **SUBMIT** (`submit_orders.py`): swing-aware, rendben — nincs változás (csak megerősítés).
- **CLOSE** (`close_positions.py`): tiszta swing sorok — nincs változás.

**CC implementáció**: A §1-6 EOD-rész és a §7 mehet (minden döntés megvan).

---

## Cél template (EOD, a 6 pont után)

```
🌅 IFDS Swing — 2026-06-01 (Day 10/63, W23 D1)
─────────────────────────────────────
💰 Realized today:    $+0.00  (0 closed)
📊 Unrealized:        $+265.64  (8 open)
   ⭐ Top: CDNS +$553 | AKAM +$128 | AMH +$99
   ⚠️ Bot: EOG -$168 | WST -$137 | ROIV -$88
📈 Day change:        $+523 (+0.53%)
📈 Cumulative:        $-709 (real-mark)

📂 Pozíciók:          8 nyitva / 12 cap
🆕 Új entry:          1 (WST — Healthcare, ATR 3.0%)
⚡ Holnap 15:30 exit: CDNS TP2 (entry $374 → $414, +10.5%, várt ~+$506)

📒 Open book:         $52,379  (52.4%)
🏷 Sectors:           Financial Services 15.0% | Technology 12.5% | Healthcare 10.0% | Real Estate 8.6% | Energy 6.2%

🎯 Top S_j today:
   MASI 94.1 | Healthcare [skipped] | AKAM 89.8 [holding] | JHG 88.0 [holding]

🔬 UW shadow:         36 logged | dp_pct 5.1% | M_GEX 0.92
VIX: 15.8 (Δ +0.2%) | SPY: +0.27%

🟢 CB buffer:         $-709 / $-5,000  (85.8% safe)
📍 Day 21 chkpt:      $-709 / $-1,500  (52.7% buffer, 11 days left)
─────────────────────────────────────
```

## Tesztelés

- `tests/test_swing_telegram.py` (vagy meglévő bővítése):
  - Day-N: start_date → NYSE-count (holiday kizárás, pl. 5/25 Memorial Day).
  - Top movers: per_position_unrealized → top/bottom 3, $50 küszöb (csendes nap → kevesebb sor).
  - Day change: today/yesterday equity → korrekt Δ + %; hiányzó equity → "n/a".
  - S_j címke: holding/selected/skipped helyes besorolás.
  - Day 21 chkpt: cum/-1500 + days_left.
- `tests/test_daily_metrics*.py`: `day_number` NYSE-count regresszió.
- Full suite 0 regression (baseline a deploy-kori `git log` szerint, jelenleg 1862).
- **Élő smoke**: `IFDS_TELEGRAM_BOT_TOKEN= IFDS_TELEGRAM_CHAT_ID= python ... eod_report.py --dry-run` (env-clear, hogy ne menjen éles üzenet — lásd smoke-no-external-send rule), vizuális ellenőrzés.

## Commit szekvencia (javasolt)

1. `feat(telegram): NYSE trading-day count for swing EOD Day-N` (§1)
2. `feat(telegram): top movers + day-change in swing EOD (total_equity store)` (§2 + §3a)
3. `feat(telegram): exit-merge detail + Top S_j status labels + Day 21 checkpoint` (§4-6)
4. `refactor(telegram): swing-era TRADING PLAN cleanup — demote shadow GEX/MMS/breadth/crowd` (§7, opció-választás után)
5. `test(telegram): swing EOD render regression (day-N, movers, day-change, labels)` (tesztek)

## Megjegyzések
- Nincs új API-hívás a §1-6-hoz (minden a meglévő `daily_metrics.json` + `swing_positions.json` + `ib.portfolio()`/`accountSummary` adatból). A `total_equity` az `accountSummary`-ból, amit az eod_report amúgy is hív.
- A §7 a `telegram.py`-t érinti (pipeline TRADING PLAN), ami a 14:30/15:45 cron-ból fut — élesen a következő trading napon validálódik.
- Smoke: minden eod_report smoke `IFDS_TELEGRAM_*=` env-clearrel (smoke-no-external-send-with-dotenv rule).
