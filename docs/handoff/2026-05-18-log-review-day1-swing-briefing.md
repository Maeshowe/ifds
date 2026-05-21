# Log Review Chat Briefing — 2026-05-18 Day 1 Swing Pivot GO-LIVE

**Címzett**: IFDS Log Review & Ops chat instance
**Készítő**: Swing Pivot Dev chat (Claude), 2026-05-18 ~12:30 CEST
**Olvasási sorrend a session start-on**: ezt a fájlt **az állandó `docs/handoff/prompts/log-review-prompt.md` után**, **a daily review írása előtt** olvasd be.
**Érvényesség**: tartós a Fázis 3 deploy után (mai 2026-05-18 ettől fogva), NEM egy-napos esemény. A swing pivot az új architektúra mint olyan.

---

## 1. Egy mondatban — mi változott

A korábbi review-k a **régi intraday momentum rendszer** logjait olvasták (Phase 1-6 a régi scoring + sizing + bracket SL + 5 percenkénti monitor + 16:20 CEST entry). Mai 2026-05-18 hétfőtől a **swing pivot architektúra** él, és a logok **strukturálisan más** karaktert mutatnak: 15:30 CEST entry, market BUY (NEM bracket), mental stop daily EOD eval, S_j scoring, sector-balanced greedy sizing.

A Day 63 milestone 2026-05-14-én PAPER FOLYTATÁS default kimenettel lezárult, az új paper trading **Day 1 = ma**, **cumulative_pnl.json $0-ra resetelve**, `trading_days: 0`. A korábbi -$1,623 paper aggregát **NEM** folytatódik — ez egy új run.

## 2. Kritikus kontextus a review minőséghez

A daily review készítésekor a Log Review chat-nek **tudnia kell**, mit jelentenek az új mezők és minták, különben hibás triage-ot ad. A fő különbségek:

### 2.1. Scoring (Phase 4 log)

**Régi**: `combined_score` = $0.60 \times \text{flow\_score} + 0.30 \times \text{tech\_score} + 0.10 \times \text{funda\_score}$, multiplier chain (M_VIX × M_GEX × M_target × M_contradiction). Threshold ≥70 / qualified ≥85.

**Új**: $S_j = 100 \times (\text{PCR\_percentile} - \text{OTM\_percentile}) + \text{sector\_adj}_j$, EWMA(5) smoothed. **Threshold S_j > 50** (Bonferroni-minimum). NINCS tech sub-score, NINCS funda sub-score, NINCS 5-féle flow al-komponens. Csak M_target marad aktív multiplier (M_VIX, M_GEX, M_contradiction deaktivált — value 1.0).

A Phase 4 log új mezői: `pcr_percentile`, `otm_percentile`, `raw_S_j`, `ewma_S_j`, `sector_adj`, `final_S_j`. **Day 1-en az EWMA history üres**, ezért `ewma_S_j ≈ raw_S_j` ma. Day 2-től épül a smoothing.

A `S_j` érték-tartomány elvileg $[-120, +135]$ — gyakorlatban `[+20, +90]` a release-rangsorba kerülő tickerekre. **Ne keress a régi 70-85-100 score-küszöböt** — a top 5 ticker most tipikusan `S_j ∈ [60, 85]`.

### 2.2. Sizing (Phase 6 log)

**Régi**: 0.7% risk/trade, 5 max concurrent (BMI guard 4-3-2), 5 kötelező napi entry, 2 ticker/sector cap.

**Új**: **0.35%** risk/trade ($350), **12** max concurrent, **2-3** daily new (CSAK ha érdemes — 0-entry nap is megengedett és NEM hibajelzés), **30% notional/sector** cap. Sector-balanced greedy fill.

A Phase 6 log új mezői: `swing_notional`, `swing_qty`, `m_target`, `sector_notional_after_add`, `sector_pct_after_add`, `skip_reason` (ha sector cap miatt kihagyott egy magasabb S_j tickert).

### 2.3. Execution (submit_orders log)

**Régi**: `submit_orders.py` 16:20 CEST, **3 IBKR order/ticker** (parent BUY + bracket SL + bracket TP1).

**Új**: `submit_orders.py` **15:30 CEST**, **1 IBKR order/ticker** (csak market BUY). A mental stop és TP szintek a `state/swing_positions.json`-be íródnak — **NEM** IBKR-be. Ha a régi `bracket_*_submitted` log-mintát keresed, NEM lesz; helyette `market_buy_submitted` + `swing_state_written`.

A `state/swing_positions.json` egy ticker entry-je:
```json
{
  "entry_price": 173.20, "entry_date": "2026-05-18", "atr": 2.45,
  "stop_level": 168.30, "tp1_level": 176.88, "tp2_level": 180.55,
  "tp1_hit": false, "trail_sl": null, "days_held": 0,
  "qty": 50, "qty_remaining": 50,
  "next_action": "HOLD", "weekly_pnl_pct": 0.0
}
```

### 2.4. Monitor + Exit (pt_monitor + close_positions log)

**Régi**: `pt_monitor.py` 5 percenkénti loop 16:00–22:00, real-time trailing stop, LOSS_EXIT -2% intraday.

**Új**: `pt_monitor.py` **napi egyszer** 22:00 CEST (`--mode=eod_eval`), 6 exit-flag-et ad a `state/swing_positions.json`-be a `next_action` mezőbe: `HOLD`, `HARD_SL`, `MENTAL_SL`, `TP1`, `TP2`, `TRAIL_SL`, `TIME_STOP`. A `close_positions.py` két mode-ban fut:
- `--mode=eod_flags` **másnap 15:30 CEST** — a `next_action` szerinti MARKET SELL (kivéve TIME_STOP)
- `--mode=time_stop` **today 21:40 CEST** — a `next_action == TIME_STOP` esetén MOC SELL

**FIGYELEM**: NE keress LOSS_EXIT mintát — disabled. NE keress 5-perces monitor heartbeat-et — disabled. NE keress bracket order cancel-t — nincs bracket.

### 2.5. Universe (Phase 2 log)

**Régi**: FMP screener `/v3/screener` ~1390 ticker (instabil heti rotációval).

**Új**: **S&P 500 + Russell 1000 union** ~1000-1100 ticker. A Phase 2 log új sora: `Universe source: swing_sp500_r1000 | Total: 1024 | S&P 500: 502 | Russell 1000: 1003`. Cache: `state/swing_universe/universe.json` (7-day TTL).

### 2.6. UW Shadow Log (Fázis 1 öröksége)

A UW dark pool / GEX **scoring DEAKTIVÁLT** (`uw_dark_pool_scoring_enabled: False`, `uw_gex_sizing_enabled: False`), de a **shadow log fut**. Új fájl: `state/uw_shadow/2026-05-18.json`. Schema: per-ticker `dp_pct`, `dp_score_would_have_been`, `gex_regime`, `m_gex_would_have_been`. A daily review-ban érdemes egy sor a UW shadow összesítésnek (mai napra: `tickers_logged`, `avg_dp_pct`, `would_have_penalty_count`).

### 2.7. SEC 10-Q Exclusion (Fázis 1 öröksége)

A Phase 2 univerzum-építésben új szűrő: SEC EDGAR 10-Q és 10-K filing exclusion (10 napi lookahead, ±10 nap tolerancia). A log új sora: `Excluded 16 tickers via SEC 10-Q filing prediction`. Cache: `state/sec_cache/`. **Tamás 2026-05-15 megerősített smoke**: 1611-ticker live test 100% success, 0 HTTP 429.

### 2.8. IBKR Gateway Monitoring (Fázis 1 öröksége)

Új cron `check_gateway.py` **15:25 CEST** (5 perccel a 15:30 submit előtt). A 2026-05-11-i csendes failure root cause-a megoldva: `_send_telegram_alert` most `logger.warning`-ot ad failure esetén (nem csendes `pass`), plus heartbeat monitor (Fix C). A Telegram alert-eket **a Log Review chat látja és számolja** a daily review-ban.

## 3. Mai timeline és várt log-output

| CEST | Esemény | Várt log-jelek |
|---|---|---|
| 14:30 | Phase 4-6 cron | `cron_phase456_20260518_*.log` — S_j distribution, top tickers, sector_adj |
| 14:55 | `execution_plan.csv` ready | 0-3 ticker (NEM kötelező 5) |
| 15:25 | check_gateway pre-flight | `cron_check_gateway_*.log` — `Gateway OK` + Telegram OK |
| **15:30** | **submit_orders.py swing entry** | `pt_submit_2026-05-18.log` — `market_buy_submitted` + `swing_state_written` (NEM bracket!) |
| 15:30 | close_positions --mode=eod_flags | `pt_close_eod_2026-05-18.log` — **no-op Day 1** (nincs `next_action != HOLD` még) |
| 15:31 | Telegram entry | "📈 IFDS Swing Submit — 2026-05-18" (új template) |
| 21:40 | close_positions --mode=time_stop | `pt_close_time_2026-05-18.log` — **no-op Day 1** (days_held=0, NEM 5) |
| 22:00 | pt_monitor --mode=eod_eval | `pt_monitor_2026-05-18.log` — első EOD eval, várt mind `HOLD` |
| 22:05 | eod_report.py | `pt_eod_2026-05-18.log` + Telegram swing daily template |
| 22:10 | daily_metrics.py | `state/daily_metrics/2026-05-18.json` — `swing_state` blokk első snapshot |

Tamás **kézi sync** (`scripts/sync_from_mini.sh`) várhatóan 22:15-22:30 körül — utána a Log Review chat-nek minden adat elérhető.

## 4. Review-template a Day 1-re — javasolt struktúra

A `docs/review/2026-05-18-daily-review.md` új sablon a swing pivot karakterre:

```markdown
# IFDS Daily Review — 2026-05-18 (Mon, Day 1 Swing Pivot)

**Verzió**: swing pivot (Fázis 3 deploy 2026-05-18)
**Előző**: Day 63 lezárt 2026-05-14, $0 reset
**Cumulative P&L**: $0 (Day 1 baseline) | Days traded: 1

## 1. Day 1 Entry Decisions
[per ticker: S_j, raw_PCR_pct, raw_OTM_pct, sector_adj, sector, notional, qty, entry_price, stop_level, tp1_level, tp2_level]

## 2. EOD State (22:00)
[per open position: days_held=0, weekly_pnl_pct, next_action (várt: HOLD), close_today, low_today, high_today]

## 3. Pipeline Log Review
- Phase 2 universe: N tickers (S&P 500 + R1000 union)
- SEC 10-Q exclusions: N tickers
- Earnings exclusions: N tickers
- Phase 4 S_j distribution: top 10, threshold passers, EWMA reference
- Phase 6 sector-balanced greedy: a kihagyott magasabb S_j tickerek (skip_reason) és miért

## 4. UW Shadow Log
- tickers_logged, avg_dp_pct, would_have_penalty_count, would_have_M_GEX_avg

## 5. IBKR Gateway Monitoring
- 15:25 pre-flight status
- Heartbeat last run
- Telegram alert count (várt: 1 entry + 0 errors)

## 6. Anomalies / Notes
[bármi unexpected]

## 7. Day 2 (Kedd 2026-05-19) outlook
- Day 5 = Péntek 2026-05-22 = potential MOC TIME_STOP minden Day 1 entry-re
- Új daily new entry javasolt (0-3 ticker)
- EWMA(5) state Day 2-től épül
```

A régi review-sablon `Net P&L`, `Excess vs SPY`, `TP1 hit rate`, `LOSS_EXIT count` mezői **NEM relevánsak Day 1-en** (Net P&L $0 + a régi exit-mintázatok eltűntek). A Day 5+-on (péntek után) érdemes lesz a swing-szintű TP1/TP2/MENTAL_SL/TIME_STOP/HARD_SL distribúciót egy heti összesítésben.

## 5. Mit NE keressen / NE alarmizáljon ma a Log Review chat

| Régi pattern | Új viselkedés | Akció |
|---|---|---|
| `LOSS_EXIT triggered` | DISABLED (loss_exit_intraday_enabled: False) | Ha mégis látsz ilyet a logban, az **anomália** (commit hash mismatch?) — riport |
| Bracket SL / TP1 cancel | NINCS bracket | Ha látsz IBKR `cancelOrder` próbálkozást, **anomália** — riport |
| 5-perces monitor.py heartbeat | DISABLED (pt_monitor_5min_mode: False) | Csak 22:00-kor fut a monitor |
| "napi 5 kötelező entry" hiánya | 2-3 (vagy 0) az új norma | NE alarmizálj, ha 0 entry van — gyenge breadth-nap valid kimenet |
| `M_VIX`, `M_GEX`, `M_contradiction` értékek | Mind 1.0 forcelt | Ha != 1.0 értéket látsz, **anomália** (config drift?) — riport |
| `combined_score >= 70` threshold | `S_j > 50` az új | A `combined_score` mező lehet hogy maradt schema-konzisztencia okból, de a tényleges threshold S_j |
| `freshness_bonus`, `crowdedness_clipping` | DISABLED | Ne reagálj a hiányukra |
| `dp_pct_bonus` Phase 4-ben | 0-ra forcelt | Csak shadow log-ban látható az érték |

## 6. Operatív megjegyzések

- A `state/cumulative_pnl.PRE_SWING_BACKUP_2026-05-18.json` (régi -$1623 baseline) **csak archív** — NE használd referenciának. A `state/cumulative_pnl.json` mai $0 az új baseline.
- A `state/swing_ewma_state.json` Day 1-en üres lehet (vagy első snapshot ma este). Day 2-től tölti fel.
- A `state/swing_universe/universe.json` 7-day TTL — ma 5/18-án a múlt heti péntek (5/15) cache friss marad, NEM hiba.
- A daily review-t a Dev chat scope-ban is bekapcsoljuk az első 1-2 hétben (Log Review chat-szel párhuzamosan), mert az új struktúra szokatlan és a Dev chat helyrehozza ha edge case-t talál.

## 7. Eszkalációs csatorna

Ha a Log Review chat **kritikus anomáliát** észlel ma (pl. LOSS_EXIT trigger megjelenik, bracket SL próbálkozás, S_j számítási hiba, IBKR Gateway timeout submit közben), a **P0 escalation pattern** szerint:
1. Egy P0 entry a `docs/master-reference/04-risks-and-open-questions.md` **legtetejére** ⚠️ jelzéssel
2. Tamás chat-ben flag
3. Tamás kézzel értesíti a Dev chat-et (NINCS automatic chat-to-chat sync)

A Dev chat ma estére a Day 1 swing entry-ket élben követi (15:30+ közvetlen review, 22:00+ EOD eval verifikáció), tehát a Log Review chat éjjeli (22:30+) review redundáns biztonsági réteg — nem feszített idő.

---

## Kapcsolódó

- `docs/handoff/2026-05-16-chat-handoff-phase1-w21-close.md` — a Fázis 1+3 deploy teljes scope-ja
- `docs/decisions/2026-05-14-day63-decision-outcome.md` — 14 stratégiai döntés baseline
- `docs/design/swing-pivot-architecture.md` — magas szintű komponens-térkép
- `docs/tasks/2026-05-17-swing-*.md` (5 db) — implementálási részletek
- `docs/tasks/2026-05-15-*.md` (4 db) — Fázis 1 task fájlok DONE
- `docs/handoff/prompts/log-review-prompt.md` — az állandó Log Review szerep prompt

— Swing Pivot Dev chat (Claude), 2026-05-18 ~12:30 CEST
