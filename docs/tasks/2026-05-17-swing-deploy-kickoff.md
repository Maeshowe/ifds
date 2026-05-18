# Task: Swing Daily Metrics + Telegram Template + Deploy Kickoff

**Status:** WIP
**Updated:** 2026-05-18
**Note:** A rész (CC technikai) DONE 1711 tests; B rész (Tamás manual + push) PENDING
**Priority:** P1 (Fázis 3 deploy lezárás)
**Created:** 2026-05-17
**Owner:** Claude Code (technikai rész) + Tamás (manual config + push)
**Estimated effort:** ~1h CC + ~30 min Tamás manual

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3 (összes döntés), §6 (deploy ütemterv).

**Depends on:** [`2026-05-17-swing-execution-exit.md`](2026-05-17-swing-execution-exit.md) — az új state schema és exit-flag-ek

---

## 1. Scope

Két részfeladat egy task-ban (mind a kettő kicsi, együtt deploy-olható):

**A) Daily metrics + Telegram template frissítés** (CC, ~45 min)
- A `scripts/paper_trading/daily_metrics.py`-ben új field-ek a swing state-hez
- Telegram daily report új template (új field-ek, kompaktabb formátum)

**B) Deploy kickoff: kezdő-állapot reset + git push + cron entry** (Tamás manual + CC verify, ~30 min)
- Circuit breaker reset
- Meglévő pozíciók ellenőrzése (ha vannak, lezárás)
- Git push (5 commit a HEAD-ben + a vasárnapi 4-5 commit)
- Cron entry frissítések (új idők, új scriptek)
- STATUS.md + 04-risks frissítés a Fázis 3 deploy állapotra

## 2. Daily metrics új field-ek

A `daily_metrics.py`-ben a daily output JSON struktúra bővül:

```python
"swing_state": {
    "open_positions": 8,                          # 0-12
    "new_entries_today": 2,                       # 0-3
    "total_notional": 87_500.00,                  # $
    "total_notional_pct_equity": 87.5,            # % of $100k account
    "sector_distribution": {
        "XLK": 25_000,  # $25k = 25% (under 30% cap)
        "XLF": 18_500,
        "XLE": 12_000,
        # ...
    },
    "sector_max_pct": 25.0,                       # max sector notional %
    "avg_days_held": 2.3,                          # átlag hold idő
    "max_days_held": 4,                            # leghosszabb hold

    "exits_today": {
        "TP1": 1,
        "TP2": 0,
        "MENTAL_SL": 1,
        "HARD_SL": 0,
        "TIME_STOP": 1,
        "TRAIL_SL": 0,
    },

    "next_day_planned": {
        "exits_at_1530": ["AAPL_TP1", "MSFT_MENTAL_SL"],
        "time_stops_at_2140": [],
    },

    "swing_score_distribution": {
        "qualifying_threshold_50": 173,            # # of tickers above S_j=50
        "selected_for_entry": 2,
        "top_5_scores": [{"ticker": "NVDA", "S_j": 78.4}, ...],
    },
},

"uw_shadow_summary": {
    # (változatlan a Fázis 1 task-ból)
},
```

## 3. Telegram daily report template

A `scripts/paper_trading/eod_report.py` (vagy ahol a Telegram daily report generálódik) új template:

```
🌅 IFDS Swing — 2026-05-18 (Mon, Day 1)
─────────────────────────────────────
📊 Nettó P&L:       +$X.XX   (cum +$Y.YY)
📈 Pozíciók:        8 nyitva / 12 cap
🆕 Új entry today:  2 (NVDA, JPM)
📤 Exit today:      1 TP1, 1 MENTAL_SL, 1 TIME_STOP

🎯 Top 3 S_j today:
   NVDA  78.4 | tech | +1.2 ATR
   JPM   71.8 | financial | +0.4 ATR
   XOM   68.2 | energy | +0.9 ATR

⚡ Holnap 15:30 exit:
   AAPL TP1 (50%), MSFT MENTAL_SL (100%)

🔬 UW shadow:
   154 tickers logged | dp_pct avg 8.7%
   23 would-have penalty | M_GEX avg 0.87

VIX: 18.5 (Δ +2.1%) | SPY: +0.5%
─────────────────────────────────────
```

Kulcs különbség a régi formátumtól: **kompaktabb**, csak a swing-releváns mezők, a régi BMI / GEX / Cross-Asset Regime soraink **elhagyva** (azok a Phase 1-5 shadow lognak adnak, de a daily report-ban túl sok info).

## 4. Tesztek (CC, A rész)

```python
def test_daily_metrics_includes_swing_state():
    """A daily_metrics JSON tartalmazza a swing_state field-eket."""

def test_daily_metrics_sector_distribution_sums_to_total():
    """Σ sector_distribution = total_notional."""

def test_telegram_template_compact_format():
    """A Telegram daily report < 800 char (mobile-friendly)."""

def test_telegram_template_renders_zero_entries():
    """0 új entry + 0 exit → 'Új entry: 0' helyes string."""

def test_telegram_template_renders_max_entries():
    """3 új entry, 12/12 cap → helyes formátum, NO overflow."""
```

## 5. Deploy kickoff checklist (Tamás manual + CC verify)

### 5.1. Vasárnap (5/17) estére, a vasárnapi 5 task DONE után

```bash
# 1. Git status ellenőrzés
cd ~/SSH-Services/ifds
git log --oneline -10
# Várt: ~9-10 commit a HEAD-ben (4 Fázis 1 + 5-6 Fázis 3 swing + 1-2 docs)

# 2. Test suite teljes futás
pytest -v --tb=short
# Várt: 1624 + N tests passing (N ≈ 40-60 vasárnapi új)

# 3. Smoke test — mock 1 napi futás
python scripts/dev/swing_smoke_test.py --date 2026-05-18 --mock
# Várt: 0-3 új entry, state/swing_positions.json létrejön, exit flags HOLD

# 4. Circuit breaker reset
echo '{"active": false, "reason": null, "reset_at": "2026-05-17T22:00:00Z"}' > state/circuit_breaker.json

# 5. Meglévő pozíciók ellenőrzése (régi rendszerből, ha vannak)
python scripts/paper_trading/monitor_positions.py
# Ha vannak nyitott pozíciók → manuális nuke vagy lezárás Tamás-tól
# Várt 5/17 estére: 0 nyitott (péntek 5/16 MOC zárt mindent)

# 6. Cron entry frissítés
crontab -e
# Új entries (régi entries comment-elve / törölve):
# 30 14 * * 1-5  /usr/bin/python3 scripts/run_phase456.py    # Phase 4-6 cron 14:30
# 25 15 * * 1-5  /usr/bin/python3 scripts/paper_trading/check_gateway.py
# 30 15 * * 1-5  /usr/bin/python3 scripts/paper_trading/submit_orders.py
# 30 15 * * 1-5  /usr/bin/python3 scripts/paper_trading/close_positions.py --mode=eod_flags
# 40 21 * * 1-5  /usr/bin/python3 scripts/paper_trading/close_positions.py --mode=time_stop
# 0  22 * * 1-5  /usr/bin/python3 scripts/paper_trading/pt_monitor.py --mode=eod_eval
# 5  22 * * 1-5  /usr/bin/python3 scripts/paper_trading/eod_report.py

# 7. Env var ellenőrzés
launchctl getenv IFDS_TELEGRAM_BOT_TOKEN
launchctl getenv IFDS_TELEGRAM_CHAT_ID
launchctl getenv IFDS_SEC_USER_AGENT
# Mind a három NEM-üres string kell

# 8. Git push
git push origin main
# Várt: ~9-10 commit feltöltve

# 9. STATUS.md update (CC vagy Tamás)
# Phase: "Fázis 3 deploy LIVE (2026-05-17 vasárnap este)"
# Next milestone: New Day 63 ≈ 2026-08-18 (Day 1 + 90 trading days)
```

### 5.2. Hétfő (5/18) reggel pre-market verifikáció

Lásd `docs/handoff/2026-05-16-chat-handoff-phase1-w21-close.md` §5.

## 6. STATUS.md frissítés (Vasárnap este)

```markdown
## Phase 3 — DEPLOY LIVE (2026-05-17 vasárnap)

Day 1 (új paper trading): 2026-05-18 hétfő 15:30 CEST

Komponensek deploy-olva:
- ✅ Universe: S&P 500 + Russell 1000 (~1000-1100)
- ✅ Scoring: PCR + OTM-inverse, percentile, EWMA(5), S_j > 50
- ✅ Sizing: 0.35% risk, 12 cap, 30% sector notional, sector-balanced greedy
- ✅ Execution: 15:30 entry, market BUY (no bracket), state/swing_positions.json
- ✅ Exit: daily EOD eval, mental stop 2.0×ATR, TP1/TP2 1.5×/3.0×, time-stop 5d, hard SL -8% weekly
- ✅ Daily metrics + Telegram template

Next milestone: New Day 63 ≈ 2026-08-18 (Day 1 + 63 trading days)
GO/NO-GO criteria (all three):
- Cumulative > +$2,000
- Sharpe ratio > 0.5
- 25+ days positive excess vs SPY

A Fázis 2 backtest még pending:
- Entry timing 15:30 vs 16:20 vs 17:15 (a 60 napi mintán)
- M_contradiction sign-flip elemzés (5/2-5/16 minta)
- A 3 detail spec doc (`swing-scoring-spec.md`, `-risk-spec.md`, `-sizing-spec.md`)
```

## 7. 04-risks frissítés (új W21+ active backlog)

```markdown
## Fázis 3 deploy utáni új risk register (2026-05-17+)

### P1 — operational
- §1.1 Mental stop EOD eval timezone bug-potenciál (22:00 CEST = 16:00 ET market close, ± 5 min tolerancia)
- §1.2 IBKR bracket order maradékok (régi rendszerből) — Tamás kézi cleanup a 5/17 vasárnap deploy-előtt

### P2 — analytical (Fázis 2 backtest függvénye)
- §2.1 Entry timing backtest (15:30 vs 16:20 vs 17:15)
- §2.2 M_contradiction sign-flip elemzés
- §2.3 PCR + OTM-inverse rolling-5 cross-sectional percentile (refinement)

### P3 — design follow-up
- §3.1 `swing-scoring-spec.md`, `-risk-spec.md`, `-sizing-spec.md` detail dokumentumok
- §3.2 UW shadow log Day 90 retroaktív audit (~2026-08-18)
```

## 8. Commit message

```
chore(deploy): swing pivot Phase 3 — Day 1 = 2026-05-18

Final integration commit for swing pivot deploy:
- daily_metrics.py: new swing_state field block (open_positions,
  sector_distribution, exits_today, next_day_planned, score_distribution)
- eod_report.py: compact Telegram template, swing-only fields
- STATUS.md: Phase 3 deploy LIVE entry
- 04-risks: new Fázis 3 backlog register (P1-P3)

Tests: 5 unit (daily metrics + Telegram template).

Deploy verification checklist: docs/tasks/2026-05-17-swing-deploy-kickoff.md §5
First-day operational protocol: docs/handoff/2026-05-16-chat-handoff-phase1-w21-close.md §5

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §6
```

## 9. Out of scope

- **Backtest scriptek** (entry timing, M_c sign-flip) — Fázis 2, az 5/18 hét folyamán
- **3 detail spec dokumentum** — Fázis 2, párhuzamosan a backtest-tel
- **Élesi pénzes kereskedés** ($10k capital) — leghamarabb új Day 63 (~8/18) után

## 10. Kapcsolódó

- [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §6
- [`docs/handoff/2026-05-16-chat-handoff-phase1-w21-close.md`](../handoff/2026-05-16-chat-handoff-phase1-w21-close.md) §5
- [`docs/design/swing-pivot-architecture.md`](../design/swing-pivot-architecture.md)
- A többi 4 vasárnapi swing task fájl
