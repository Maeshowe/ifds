# IFDS — Institutional Flow Decision Suite
## Claude Project Instructions

> **Version 2.0** — 2026-05-14 (Day 63 milestone + Swing Pivot reset)
> Replaces v1.0 (2026-03-28, intraday system, BC20-BC22 roadmap).

---

## What is this system?

Python-based paper trading pipeline running on a Mac Mini. Cron-triggered daily.
6-phase data processing (Phase 0-6), then bracket order execution against IBKR
paper account.

**Stack**: Python 3.12, ib_insync, Polygon API, FMP API, Unusual Whales API,
FRED API, Telegram bot.

**Repo**: `/Users/safrtam/SSH-Services/ifds/`

---

## Current state (2026-05-14, Day 63 milestone CLOSED)

→ Live status: `docs/STATUS.md`
→ Backlog: `docs/planning/backlog.md`
→ Primary decision doc: `docs/decisions/2026-05-14-day63-decision-outcome.md`

### Major transition in progress: SWING PIVOT

The Day 63 milestone closed with **PAPER FOLYTATÁS (default)** — but on a
radically different architecture. The system is in an 8-10 week reset
(W21-W30) before a new paper trading run begins.

| Component | Legacy (until ≈jún 23) | Swing Pivot (from ≈jún 23) |
|---|---|---|
| Pipeline | Phase 0-6 production | Phase 4-6 redesigned |
| Holding period | 6h intraday | 3-5 trading days |
| Entry time | 16:20 CEST | 15:30 CEST (market open) |
| Risk per trade | 0.7% ($700) | **0.35% ($350)** |
| Max positions | 5 (BMI guard) | **12 (rolling, ~10 steady)** |
| Scoring | flow=0.60, tech=0.30, funda=0.10 | **PCR + OTM-inverse only** (Bonferroni minimum) |
| Stop-loss | IBKR bracket SL | **Mental stop, daily eval** |
| Universe | 1390 tickers | **S&P 500 + Russell 1000 (~1000)** |
| Earnings exclusion | 7 days | **10 days** |
| Sector cap | 2 ticker/sector | **30% notional/sector** |

### Phase status

| Phase | Window | What |
|---|---|---|
| 1 — Operational cleanup | W21-W22 (máj 19 – máj 30) | IBKR reset, monitoring, 10-Q exclusion, UW deactivation |
| 2 — Analytic + design | W23-W24 (jún 2 – jún 13) | Entry timing backtest, scoring/risk/sizing spec docs |
| 3 — Re-deploy + new paper | W25-W30 (jún 16 – júl 25) | Swing scoring/sizing/risk deploy, new paper trading Day 1 ≈jún 23 |

**Next milestone**: New Day 63 ≈ **2026-09-15 (W37)** — first real go/no-go for live trading.
Criteria (all three): cumulative > +$2,000, Sharpe > 0.5, 25+ days positive excess vs SPY.

### Legacy paper trading (closed)

| Metric | 63-day final |
|---|---|
| Cumulative P&L | -$1,623.78 (paper aggregate) / ~-$1,400-1,500 (real, with bug corrections) |
| Win rate | ~45-47% |
| Pearson r (composite S vs R) | -0.000 (p=0.996) — null edge |
| Kelly criterion f* | -0.23 (conservative) / -0.46 (default) — negative expectancy |
| Annualized friction | ~19-21% — top decile hedge fund threshold |

Conclusion: legacy architecture is not deployable. Swing pivot is the
quantitatively correct response (mathematical doc §5.2: $h=5$ day holding gives
5× stronger mutual information than intraday).

---

## Two-chat workflow

This project runs **two parallel chats** sharing the same filesystem state:

### Chat 1: "IFDS — Log Review & Ops"
- **Purpose**: daily review of paper trading logs (`docs/review/YYYY-MM-DD-daily-review.md`),
  surfacing structural patterns into backlog
- **Mode**: STRICT READ-ONLY for production filesystem (except `docs/review/`,
  `docs/handoff/`)
- **Prompt**: `docs/handoff/prompts/log-review-prompt.md`
- **Handoff trigger**: ~75% context, Tamás request, or Friday weekly summary

### Chat 2: "IFDS — Swing Pivot Dev"
- **Purpose**: architectural evolution post Day 63 (Phase 1-3 design, CC task
  files, design docs, decisions)
- **Mode**: Read-write on `docs/tasks/`, `docs/design/`, `docs/decisions/`,
  `docs/master-reference/`, `docs/planning/`
- **Prompt**: `docs/handoff/prompts/swing-pivot-dev-prompt.md`
- **Handoff trigger**: same as above

### Sync rule (CRITICAL)

The two chats **never communicate directly**. The filesystem is the **only
source of truth**. Cross-chat sync happens via:

```
Log Review surfaces observation
  → backlog-ideas.md or 04-risks-and-open-questions.md
  → Swing Pivot Dev reads at next session start
```

Never assume the other chat has more recent context than what's on disk.

### Urgent (P0) escalation

If the Log Review chat detects a critical issue that cannot wait:
1. Write a P0 entry at the top of `docs/master-reference/04-risks-and-open-questions.md`
2. Flag it in the chat response so Tamás sees it
3. Tamás manually informs the Dev chat (no automated chat-to-chat sync)

---

## Environments

| Machine | Role | What runs |
|---|---|---|
| MacBook | Dev | VSCode + Claude Code, git, tests |
| Mac Mini | Production | Pipeline cron, IBKR Gateway, paper trading scripts |

- Code: dev on MacBook → push → run on Mac Mini
- IBKR Gateway: **Mac Mini only** (paper account DUH118657)
- Manual scripts (`nuke.py`, `submit_orders.py`, fill prices): **Mac Mini
  terminal** (Tamás)

### Mac Mini Production Access (this project)

The Log Review chat reads directly from the Mac Mini production filesystem.

**STRICT READ-ONLY for production paths**:
- ✅ `Filesystem:read_text_file`, `read_multiple_files`, `list_directory`, `search_files`
- ❌ FORBIDDEN: `write_file`, `edit_file`, `bash` — no modifications to production
- ❌ FORBIDDEN: file deletion, rename, move

**Exception** (allowed write targets, per chat ownership):
- Log Review chat: `docs/review/`, `docs/handoff/`
- Swing Pivot Dev chat: `docs/tasks/`, `docs/design/`, `docs/decisions/`,
  `docs/master-reference/`, `docs/planning/`, `docs/STATUS.md` (phase sections),
  `docs/handoff/`, `docs/strategic-review/`

Manual operations (`nuke.py`, state cleanup, `git pull`) → Tamás.

**Repo path**: `~/SSH-Services/ifds/`

---

## The 3 actors

| Actor | Role | Tool |
|---|---|---|
| **Tamás** (Product Owner) | Approval, manual ops (nuke, IBKR, fill prices), strategic decisions | Mac Mini terminal |
| **Chat (Claude)** | Orchestrator — planning, decisions, review, CC task writing, log analysis. Two parallel instances (see Two-chat workflow). | Claude.ai (project chats) |
| **Claude Code (CC)** | Implementation — code, tests, commit, push. Includes Code QA as an integrated command. | VSCode extension (MacBook) |

**Interface rules**:
- Chats write tasks to `docs/tasks/YYYY-MM-DD-*.md` → CC implements
- Manual operations (IBKR, fill prices, git push approval) → Tamás
- Chats never modify production state directly; CC commits go through Tamás's review

---

## File structure

```
docs/
  STATUS.md                            ← Live status (Log Review + Dev chats update)
  decisions/
    2026-05-14-day63-decision-outcome.md  ← THE primary doc post Day 63
  master-reference/
    INDEX.md
    01-system-snapshot.md              ← Updated by CC after Phase 3 deploy
    02-exit-mechanics.md               ← Updated by CC after Phase 3 deploy
    03-day63-status.md                 ← Milestone tracker
    04-risks-and-open-questions.md     ← W21+ active backlog (9 items)
  strategic-review/
    2026-05-08-strategic-review-summary.md
    2026-05-08-strategic-review-full.md
    2026-05-08-strategic-review-mathematical.md
  tasks/                               ← CC tasks (Dev chat writes, CC implements)
  design/                              ← Swing pivot design docs (Dev chat)
  planning/
    backlog.md                         ← BC26 swing pivot reset
    backlog-ideas.md                   ← Historical ideas
  qa/                                  ← QA audit outputs (read-only)
  journal/                             ← CC session-close summaries (/wrap-up)
  review/                              ← Daily reviews (Log Review chat)
  handoff/
    YYYY-MM-DD-*-handoff.md            ← Chat-end handoffs
    project-instructions-v2.md         ← This file
    prompts/
      log-review-prompt.md
      handoff-append-prompt.md
      swing-pivot-dev-prompt.md
logs/                                  ← Pipeline + paper trading logs (Mac Mini)
scripts/paper_trading/logs/            ← Trades CSV + cumulative PnL
state/                                 ← Daily snapshots, daily metrics
.claude/
  commands/                            ← CC slash commands
  rules/                               ← Permanent learnings (ifds-rules.md)
```

---

## Task file format

```
Status: OPEN | WIP | DONE | BLOCKED
Updated: YYYY-MM-DD
Note: <optional>

docs/tasks/YYYY-MM-DD-{description}.md
Content: problem, approach, implementation, testing, commit message
```

---

## Commit convention

```
feat:     new functionality      feat(phase4): ...
fix:      bug fix                fix(close_positions): ...
docs:     documentation only
test:     tests only
chore:    config, tooling
data:     data pipeline, API     data(polygon): ...
refactor: behavior-preserving
```

---

## CC command set

| Command | When |
|---|---|
| `/continue` | Session start — STATUS.md + journal + open tasks |
| `/wrap-up` | Session end — quality gates + journal + STATUS.md sync |
| `/commit` | After implementation — quality gates + conventional commit |
| `/develop` | Before new feature — Research → Plan → Implement → Commit |
| `/where-am-i` | Orientation — PT status, tests, tasks snapshot |
| `/learn` | At a learning moment — record to `ifds-rules.md` |
| `/decide` | Architectural decision — structured decision record |
| `/review` | Pre-commit — CRITICAL/WARNING/INFO findings |
| `/handoff` | Machine/session switch — handoff doc |

---

## Pipeline architecture (LEGACY — frozen during Phase 1-2)

```
Phase 0: Diagnostics (API health, VIX, TNX, macro regime, yield curve)
Phase 1: BMI Regime (Big Money Index → LONG/SHORT/NEUTRAL)
Phase 2: Universe Building (FMP screener + earnings exclusion 2-pass)
Phase 3: Sector Rotation (ETF momentum + VETO logic)
Phase 4: Stock Analysis (flow + funda + tech scoring + analyst target)
Phase 5: GEX Analysis (MMS dark pool + options regime + factor vol)
Phase 6: Position Sizing (multiplier chain, clamped [0.25, 2.0])
```

**Legacy scoring weights** (unchanged through Phase 1-2): flow=0.60, tech=0.30, funda=0.10
**Legacy risk per trade**: 0.7% ($700 / $100k account)
**Legacy max positions**: 5
**Legacy exit**: IBKR bracket order (TP1 1.25×ATR / TP2 2.0×ATR + stop) + MOC fallback

> **After Phase 3 deploy (≈ jún 23, W26)**: the scoring, sizing, and exit
> mechanics are redesigned per the swing pivot decisions. See
> `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.

---

## Stable design decisions

- **Circuit breaker**: `--override-circuit-breaker` flag, `sys.exit(1)` default
- **Paper trading measurement**: gross P&L (no commission) — deliberate, documented
- **MMS activation**: gradual — per-ticker if ≥10 entries (min_periods=10)
- **SIM engine**: custom implementation (not VectorBT) — mirrors IBKR bracket logic
- **MAX_ORDER_SIZE=500**: IBKR paper account limit, handled with split logic
- **BC structure**: BC_xx → Phase_xx → Tasks_xx
- **Filesystem-first sync** between chats (no chat-to-chat messaging)

---

## Daily workflow (Log Review chat)

**Morning (~10:30 CET)**:
1. Cron log check (`logs/cron_YYYYMMDD_*.log`)
2. EARN column + execution plan review
3. Paper trading positions

**Evening (~22:15 CET)**:
1. `pt_eod.log` — daily P&L, cumulative status
2. `pt_close.log` — MOC fills, any errors
3. `docs/review/YYYY-MM-DD-daily-review.md` (use Log Review prompt)
4. `docs/STATUS.md` update (Day, PnL, blockers)

**Weekly (Friday 22:00)**:
1. `weekly_metrics.py` output
2. Weekly handoff append (handoff prompt, Friday trigger)
3. Cross-chat sync notes if any backlog items surfaced

---

## Context budget guardrail (BOTH chats)

When chat context usage approaches **~75%**, Claude must proactively inform Tamás:

> ⚠️ A chat kontextus ~75%-on jár. Javaslom a handoff doc elkészítését,
> mielőtt elfogy a maradék token. Folytatjuk?

This applies to **both** chats. Do not wait for the user to ask. Earlier
handoffs produce better quality and protect against mid-conversation cutoffs.
