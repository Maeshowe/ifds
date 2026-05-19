# Task: Telegram Comprehensive Audit + Swing-Aware Refactor

**Status:** DONE
**Priority:** P1 (operatív értelmezhetőség — a Day 1-2 finding-ek alapján)
**Created:** 2026-05-19
**Updated:** 2026-05-19 (CC complete, 27 új teszt, 1712 → 1728 passing)
**Owner:** Claude Code
**Estimated effort:** ~2-3 óra CC (5 réteg refactor + tests)

**Source**:
- [`docs/review/2026-05-18-daily-review.md`](../review/2026-05-18-daily-review.md) — Day 1 cosmetic warnings + missing context
- [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) §8.1.3, §8.1.4, §8.1.5, §8.1.7 (új)
- Day 2 (2026-05-19) operatív megfigyelések — `LEFTOVER` + `TRADING PLAN` legacy üzenetek

**Supersedes**: ezzel a task-kal a korábban megírt 3 különálló task **lezárható és törölhető**:
- `2026-05-19-eod-report-swing-refactor.md` (Task #A, integrálva ide §3)
- `2026-05-19-submit-telegram-heartbeat.md` (Task #B, integrálva ide §4)
- `2026-05-19-pt-monitor-telegram-expand.md` (Task #C, integrálva ide §5)

---

## 1. A probléma — Telegram-réteg NEM swing-aware

A swing pivot Fázis 3 deploy a scoring/sizing/exit logikát átalakította, de a **Telegram-réteg** (6 üzenettípus) **nagy részében legacy** maradt. A Day 1-2 napi tapasztalat 6 strukturális problémát mutatott:

| # | Üzenet | Cron | Probléma |
|---|---|---|---|
| 1 | `📤 IFDS Swing 15:30 Exit` | 15:30 close_positions | ✅ OK (új, swing-aware) |
| 2 | `📈 IFDS Trading Plan` | 14:30 Phase 4-6 cron belső | ❌ Régi template + scoring output (NEM submit), félrevezető |
| 3 | `📈 IFDS Swing Submit` | 15:30 submit_orders | ⚠️ Hiányzik 0-submit case (§8.1.3) |
| 4 | `🌙 IFDS Swing EOD` | 22:00 pt_monitor | ⚠️ Túl minimális, csak exit-flag list (§8.1.5) |
| 5 | `📊 PAPER TRADING EOD` | 22:05 eod_report | ❌ Régi template "Leftover: 3 ⚠️" + 0 P&L félrevezető (§8.1.4) |
| 6 | `LEFTOVER POSITIONS` | 10:10 monitor_positions | ❌ Régi leftover semantics — swing carry-over-t leftover-ként jelzi (új §8.1.8) |

## 2. Általános elv

**Minden Telegram üzenet** a 6 közül a swing rendszer **operatív kontextusában** értelmezhető legyen:
- **Realized vs unrealized** szétválasztás (NEM csak closed trades)
- **Triggered exits** (today eval) vs **fill events** (másnap close) különálló
- **Open swing book** mint **normál állapot**, NEM "leftover" anomália
- **Cron heartbeat**: minden cron futás után visszajelzés, "hallgatás ≠ siker"

## 3. Üzenettípusonkénti refactor

### 3.1. `📈 IFDS Trading Plan` (14:30) — §8.1.7

**Cél**: NEM elnémítani, hanem **swing-aware kontextualizálás**. A scoring output a tickerjelöltek listája, az `existing_positions` guard utáni cross-reference.

**Új template**:
```
📈 IFDS Swing Scoring — 2026-05-19 (Day 2/63)

Phase 4-6 elemezte: 1479 ticker
Qualified (S_j > 50): 77
Selected for entry plan: 3

Today's plan (execution_plan.csv):
  LBRT  $33.07  S_j 101.7  Energy            ALREADY OPEN
  MASI  $178.80  S_j 101.6  Healthcare       ALREADY OPEN
  PFGC  $96.14  S_j 92.0   Consumer Defensive  NEW CANDIDATE

15:30 submit: 1 new entry expected (PFGC) | 2 existing skipped
```

**Implementáció**:
- A `Trading Plan` Telegram függvény áthelyezése a Phase 4-6 utánról a **submit_orders.py-ba** (15:30 cron belső, közvetlenül a submit before/after)
- VAGY: a 14:30 cron a Phase 4-6 után `state/swing_positions.json`-t olvas, és a `ALREADY OPEN` jelölést hozzáadja
- A régi "MMS / GEX regime / gamma_negative" mezők **kivéve** (a swing config alapján 1.0-ra forcelt multiplier-ek)

**Effort**: ~30 min CC

### 3.2. `📈 IFDS Swing Submit` (15:30) — §8.1.3

**Cél**: 0-submit case-en is küldjön heartbeat-et.

**Új viselkedés**:
```python
if len(submitted) > 0:
    # Meglévő full template
    message = format_swing_submit_message(submitted)
else:
    # ÚJ: heartbeat
    message = (
        f"✓ IFDS Swing Submit ran {now_cest():%H:%M}. "
        f"Submitted: 0 new "
        f"({len(existing)} existing, {len(skipped_other)} other skipped). "
        f"Next: 22:00 EOD eval."
    )
send_telegram(message)
```

**Effort**: ~15 min CC

### 3.3. `🌙 IFDS Swing EOD` (22:00) — §8.1.5

**Cél**: kibővített open book + sectors + time-stop countdown + market context.

**Új template**:
```
🌙 IFDS Swing EOD — Day {N}/63 (YYYY-MM-DD)

Open: {M} | Total notional: ${X,XXX} ({Y.Y}%)
Sectors: Energy {a}% | Health {b}% | Tech {c}%

EOD eval:
  EC   $13.59 ✅ TP1 (+3.9%)  → holnap 15:30 50% SELL
  LBRT $33.69 ⏸ HOLD (-0.04%)
  MASI $178.65 ⏸ HOLD (+0.02%)

Time-stops:
  EC (Day 5 = Fri 5/22)  166 share remainder
  LBRT (Day 5 = Fri 5/22)  127 share
  MASI (Day 5 = Fri 5/22)  84 share

VIX 18.54 (+2.3%) | SPY -0.07%
```

**Effort**: ~30 min CC

### 3.4. `📊 PAPER TRADING EOD` (22:05) — §8.1.4

**Cél**: a régi "Leftover: 3 ⚠️" + 0 P&L félrevezető template helyett swing-aware.

**Új template**:
```
📊 IFDS Swing Day {N}/63 — YYYY-MM-DD

Realized today:    $X.XX  ({N} closed trades)
Unrealized today:  $+Y.YY  ({M} open positions)
Cumulative:        $+Z.ZZ  (real-mark)

Triggered exits (fill holnap 15:30):
  EC TP1 → 50% SELL @ ~$13.59 expected (+$84)

Open swing book: 3 tickers (LBRT, MASI, EC) | Total: $23,570 (23.6%)
Sectors: Energy 8.6% | Health 15.0%

Circuit breaker: $+219 / $-5,000 (4.4% buffer)
```

A régi `Leftover: N ⚠️` sor **eltávolítva** — swing-mode-ban a nyitott pozíciók a normál működés.
A `TP1 / SL / MOC` counts **kontextualizálva**: closed vs triggered szétválasztás.

**Effort**: ~45 min CC

### 3.5. `LEFTOVER POSITIONS` (10:10) — §8.1.8 (új, fontos)

**Cél**: a `monitor_positions.py` swing-aware-szegmentálása — csak a **valódi** leftover-t (NEM swing pozíciókat) jelentse.

**Új logika**:
```python
def detect_leftovers():
    state = json.loads(Path("state/swing_positions.json").read_text())
    state_tickers = set(state.keys())

    ibkr_positions = {p.contract.symbol: p.position for p in ib.positions()}
    ibkr_tickers = set(ibkr_positions.keys())

    # Permanent orphan exclusions (§8.3.1)
    PERMANENT_ORPHANS = {"AVDL.CVR"}

    # True leftovers: IBKR-ben, DE NEM swing state-ben ÉS NEM permanent orphan
    true_leftovers = ibkr_tickers - state_tickers - PERMANENT_ORPHANS

    # Swing carry-overs: IBKR-ben ÉS swing state-ben (normál működés, ignored)
    swing_carry_over = ibkr_tickers & state_tickers

    if true_leftovers:
        message = (
            f"⚠️ TRUE LEFTOVER POSITIONS — {today_str()}\n"
            + "\n".join(f"  {t}: {ibkr_positions[t]} shares" for t in sorted(true_leftovers))
            + f"\n\nSwing carry-over (NORMAL, ignored): {sorted(swing_carry_over)}"
            + "\nAction for true leftovers: nuke.py or manual close in IBKR."
        )
        send_telegram(message)
    elif swing_carry_over:
        # Heartbeat — minden reggel megerősítés
        message = (
            f"✓ Morning leftover check — {today_str()}\n"
            f"  Swing carry-over (NORMAL): {sorted(swing_carry_over)}\n"
            f"  No true leftovers detected."
        )
        if os.getenv("IFDS_LEFTOVER_VERBOSE"):
            send_telegram(message)
```

A `Swing carry-over (NORMAL)` az új semantics — a tegnapi swing pozíciók **NEM hibajelzés**.

**Effort**: ~45 min CC + 3 unit teszt (true_leftover, swing_carry_over, AVDL_orphan_excluded)

### 3.6. `📤 IFDS Swing 15:30 Exit` (15:30 close) — már OK

A `close_positions.py --mode=eod_flags` Telegram template **már swing-aware** (15:30 Telegram message megfelelő: "EC: TP1 qty 166"). **NINCS** változtatás szükséges.

## 4. Implementációs sorrend

| Sorrend | Réteg | Effort | Miért az adott helyen |
|---|---|---|---|
| 1 | §3.5 LEFTOVER swing-aware (10:10) | 45 min | Holnap reggel **NEM kapunk hibás nuke javaslatot** — operatív értelmezhetőség most kritikus |
| 2 | §3.4 EOD report swing-aware (22:05) | 45 min | Ma 22:05 már új template-tel — Day 2 review-ban jó |
| 3 | §3.3 pt_monitor EOD Telegram (22:00) | 30 min | Ma 22:00 már informatív |
| 4 | §3.2 Submit silence (15:30) | 15 min | Másnap mar heartbeat |
| 5 | §3.1 Trading Plan swing-aware (14:30) | 30 min | Másnap mar swing kontextualizálva |

**Összesen**: ~2 óra 45 min CC + ~30 min tesztek = **~3 óra**.

## 5. Tesztek (összesített)

```python
# §3.5
def test_leftover_only_true_leftovers_alerts():
def test_leftover_swing_carry_over_silent():
def test_leftover_avdl_cvr_excluded():

# §3.4
def test_eod_report_swing_template_zero_realized():
def test_eod_report_swing_template_with_triggered():
def test_eod_report_swing_template_compact_length():

# §3.3
def test_pt_monitor_telegram_with_3_positions_1_tp1():
def test_pt_monitor_telegram_0_open_positions():

# §3.2
def test_submit_telegram_zero_submit_heartbeat():

# §3.1
def test_trading_plan_telegram_distinguishes_open_vs_new():
def test_trading_plan_telegram_no_legacy_multipliers():
```

## 6. Commit message draft

```
feat(telegram): comprehensive swing-aware Telegram audit + refactor

Day 1-2 (2026-05-18, 19) showed 5 of 6 Telegram message types still
operate on legacy semantics — misleading in swing pivot architecture.

Refactored 5 message types:
1. monitor_positions LEFTOVER: distinguish true_leftover vs swing_carry_over
2. eod_report EOD: realized + unrealized + triggered + open book + sectors
3. pt_monitor EOD: open book + time-stops + market context
4. submit_orders SUBMIT: heartbeat on 0-submit case
5. Phase 4-6 Trading Plan: ALREADY OPEN vs NEW CANDIDATE cross-reference

Excludes AVDL.CVR permanent orphan (§8.3.1).
The 15:30 Exit message already swing-aware, no change.

Tests: 11 new (3 per major template).

Refs: docs/review/2026-05-18-daily-review.md
      docs/master-reference/04-risks-and-open-questions.md §8.1.3-§8.1.5, §8.1.7-§8.1.8
```

## 7. A 3 korábbi task-fájl törlése

A `git rm` parancsokkal:
- `docs/tasks/2026-05-19-eod-report-swing-refactor.md`
- `docs/tasks/2026-05-19-submit-telegram-heartbeat.md`
- `docs/tasks/2026-05-19-pt-monitor-telegram-expand.md`

Helyettesítve ezzel az átfogó task-tal.

## 8. Kapcsolódó

- `04-risks` §8.1.3, §8.1.4, §8.1.5, §8.1.7 (új), §8.1.8 (új)
- `scripts/paper_trading/monitor_positions.py` (LEFTOVER §3.5)
- `scripts/paper_trading/eod_report.py` (EOD report §3.4)
- `scripts/paper_trading/pt_monitor.py` (EOD eval §3.3)
- `scripts/paper_trading/submit_orders.py` (SUBMIT §3.2)
- `src/ifds/pipeline/runner.py` vagy hasonló (Trading Plan §3.1) — a régi `📈 IFDS Trading Plan` Telegram-küldő helye azonosítandó
