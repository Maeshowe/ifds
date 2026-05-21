Status: DONE
Updated: 2026-04-06
Note: P1 — a Telegram üzenetek nem adnak elég információt a kereskedési döntésekhez

# Telegram kimenet újratervezés — teljes rendszer

## Kontextus

A jelenlegi Telegram kimenetek félrevezetők és hiányosak:
- A submit üzenet nem mutatja a tickereket (csak "2 tickers, 4 brackets")
- A Company Intel piac UTÁN megy ki (22:01), nem ELŐTTE
- Az EOD report nem tartalmaz ticker-szintű bontást
- Az EOD "Day 36/21" hibás (kellene /63)
- Nincs fill rate összefoglaló

A pipeline schedule megváltozott (22:00 CEST), ami az egész Telegram flow-t érinti.

## Érintett Telegram üzenetek és javítások

---

### 1. Submit Telegram — ticker tábla hozzáadása (P1)

**RÉGI:**
```
[2026-04-06 15:45 CET] SUBMIT
📊 PAPER TRADING — 2026-04-06
Submitted: 2 tickers (4 brackets)
Exposure: $8,893 / $100,000 limit
Tickers: UNIT, SPHR
```

**ÚJ:**
```
[2026-04-06 15:45 CET] SUBMIT
📈 IFDS Trading Plan — 2026-04-06
8 pozíció | Risk: $2,216 | Exp: $67,646

TICKER  QTY  ENTRY    SL       TP1      RISK  EARN
UNIT    555  $10.33   $9.48    $10.75   $471  05-05
SPHR     25  $127.22  $117.85  $131.91  $235  05-07

New: 2 | Skip: 6 (existing)
Submitted: 2 tickers (4 brackets)
```

**Implementáció (submit_orders.py):**
A `tickers` lista tartalmazza az összes adatot. Építs egy formázott táblát a Telegram üzenetbe:

```python
# submit_orders.py — Telegram üzenet bővítés
tg_lines = [f"📈 IFDS Trading Plan — {today_str}"]
tg_lines.append(f"{len(tickers)} pozíció | Risk: ${total_risk:,.0f} | Exp: ${exposure:,.0f}")
tg_lines.append("")
tg_lines.append("<pre>")
tg_lines.append(f"{'TICKER':<7}{'QTY':>4} {'ENTRY':>8} {'SL':>8} {'TP1':>8} {'RISK':>5} {'EARN':<5}")
for t in tickers:
    status = "NEW" if t['symbol'] in submitted_tickers else "SKIP"
    tg_lines.append(
        f"{t['symbol']:<7}{t['total_qty']:>4} ${t['limit_price']:>7.2f} "
        f"${t['stop_loss']:>7.2f} ${t['take_profit_1']:>7.2f} "
        f"${t.get('risk_usd', 0):>4.0f}"
    )
tg_lines.append("</pre>")
tg_lines.append(f"New: {submitted} | Skip: {len(skipped_existing)} (existing)")
```

---

### 2. EOD Telegram — ticker bontás + Day/63 fix (P1)

**RÉGI:**
```
📊 PAPER TRADING EOD — 2026-04-06
Trades: 8 | Filled: 8/8
TP1: 0 | TP2: 0 | SL: 0 | MOC: 8
P&L today: $-91.23 (-0.09%)
Cumulative: $-1,497.00 (-1.50%) [Day 36/21]
Circuit breaker: $-1,497 / $-5,000 threshold
```

**ÚJ:**
```
[2026-04-06 22:05 CET] EOD
📊 PAPER TRADING EOD — 2026-04-06

P&L: $-91.23 (-0.09%) | Cum: $-1,497 (-1.50%) [Day 36/63]
TP1: 0 | SL: 0 | LOSS: 0 | TRAIL: 0 | MOC: 8

TICKER   P&L      TYPE
UNIT    +$101.67  MOC  ✅
BRX      +$2.81   MOC
DBRG    -$12.81   MOC
SPHR    -$23.25   MOC
KGC     -$29.60   MOC
LIN     -$50.40   MOC
NEM     -$79.65   MOC  ❌

Leftover: nincs ✅
CB: $-1,497 / $-5,000
BMI: 46.8% (+1.8) | VIX: 24.38
```

**Implementáció (eod_report.py):**
- A `trades` lista tartalmazza a ticker-szintű adatokat — rendezd P&L szerint
- Cseréld a `[Day X/21]`-et `[Day X/63]`-ra (hardcoded "21" → config vagy 63)
- Adj hozzá BMI/VIX emlékeztetőt (olvasd a bmi_history.json + Phase 0 log-ból)
- Top/Bottom ticker kiemelés (✅/❌ emoji)

**Day/63 fix:**
```python
# eod_report.py — RÉGI:
f"Cumulative: ${cum_pnl:+,.2f} ({cum_pct:+.2f}%) [Day {trading_days}/21]"
# ÚJ:
PAPER_TRADING_TARGET_DAYS = 63  # config-ba is tehető
f"Cum: ${cum_pnl:+,.2f} ({cum_pct:+.2f}%) [Day {trading_days}/{PAPER_TRADING_TARGET_DAYS}]"
```

---

### 3. Company Intel időzítés (P1 — BC20A Pipeline Split scope)

A Company Intel jelenleg a pipeline teljes futás végén generálódik (22:00+). A BC20A Pipeline Split-tel a Phase 4-6 15:45-kor fog futni — a Company Intel is ekkor kellene menjen.

**Nem kell most implementálni** — a BC20A design-ba beleírni, hogy a Company Intel a Phase 4-6 Telegram üzenet után menjen (15:46), nem a 22:00-ás macro snapshot után.

Jelöld a Company Intel scriptet (`scripts/company_intel.py` vagy hasonló) a BC20A task-ba.

---

### 4. Fill Summary (P2 — opcionális)

Egy összefoglaló Telegram a fill window zárásakor (~16:30 ET = ~22:30 CET, vagy az AVWAP window végén):

```
[2026-04-07 16:30 CET] FILL SUMMARY
✅ 6/8 filled
❌ 2 unfilled: AAPL (limit $175.20 not reached), MSFT (limit $405.30 not reached)
AVWAP: CF @ $134.46 (plan $127.98, slip +5.1%)
```

Ez lehet az AVWAP script utolsó lépése (az AVWAP window zárásakor összefoglaló).

**Nem P1** — de értékes lenne ha a submit_orders.py skip-jei és az AVWAP fill-ek összefoglalása egy helyen lenne.

---

### 5. Macro Snapshot (22:00) — kompaktabb formátum (P2)

A jelenlegi Daily Report (22:00) túl hosszú (2 Telegram üzenet). A Pipeline Split után a 22:00-ás üzenet csak a Phase 0-3 macro snapshot — rövidebb, kompaktabb:

```
[2026-04-06 22:00 CET] PIPELINE
📊 IFDS Macro Snapshot — 2026-04-06

VIX=24.38 (elevated) | TNX=4.31% | 2s10s=+0.52%
BMI=46.8% YELLOW (+1.8) | Strategy: LONG

Leaders: XLK ↑5.3% | XLC ↑4.4% | XLRE ↑4.4%
VETO: XLE XLP XLU
Breadth: weakening (11/11)

Skip Day Shadow: NEM aktív
Holnap 15:45: Phase 4-6 + MKT entry
```

Ez BC20A scope — a `send_macro_snapshot()` függvény a telegram.py-ban már létezik.

---

## Összefoglaló — mit implementáljon CC

| # | Mit | Fájl | Effort |
|---|-----|------|--------|
| 1 | **Submit Telegram ticker tábla** | `submit_orders.py` | 1h |
| 2 | **EOD ticker bontás + Day/63 fix + BMI/VIX** | `eod_report.py` | 1.5h |
| 3 | Company Intel timing → BC20A design doc | `docs/planning/` | Megjegyzés |
| 4 | Fill Summary → opcionális, P2 | `pt_avwap.py` | 1h (opcionális) |
| 5 | Macro Snapshot kompaktabb → BC20A | `telegram.py` | BC20A scope |

**Most implementálandó: #1 és #2 (~2.5h CC)**

## Tesztelés

- Submit Telegram tartalmaz ticker táblát (monospace formázás)
- EOD Telegram tartalmaz ticker-szintű P&L bontást
- EOD "Day X/63" nem "Day X/21"
- EOD tartalmaz BMI és VIX emlékeztetőt
- `--dry-run` módban is helyes a formázás
- `pytest` all green

## Commit

```
feat(telegram): add ticker details to submit and EOD messages

submit_orders.py now sends a formatted ticker table with qty, entry,
SL, TP1, and risk. eod_report.py now includes per-ticker P&L breakdown,
fixes Day/63 counter, and adds BMI/VIX reminder. These changes ensure
the Telegram feed provides actionable information for trading decisions.
```
