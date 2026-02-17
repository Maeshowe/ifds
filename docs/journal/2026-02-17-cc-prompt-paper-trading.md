# IFDS Paper Trading — CC Implementation Prompt

> **Date:** 2026-02-17
> **Scope:** IBKR Paper Trading daytrading module for IFDS pipeline
> **Duration:** 21 trading days
> **Account:** IBKR Paper $100K (DUH118657)
> **Status:** Clean implementation (no code reuse from reference/IBKR)

---

## CONTEXT

The IFDS pipeline runs daily at 10:00 CET on MacMini, generating an execution plan CSV with 8 stock picks. We want to automatically submit these as daytrading bracket orders to IBKR Paper Trading account via IB Gateway (port 7497), track performance, and close all positions at market close every day.

**This is a 21-day paper trading test to measure execution quality (fill rate, slippage, P&L) before considering live trading.**

---

## ARCHITECTURE

### File Structure

```
scripts/paper_trading/
├── submit_orders.py          # 15:35 CET — Read IFDS CSV → submit bracket orders
├── close_positions.py        # 21:45 CET — MOC orders for remaining positions
├── eod_report.py             # 22:05 CET — Daily report + cancel all + Telegram
├── lib/
│   ├── __init__.py
│   ├── connection.py         # IBKR connection (ib_insync)
│   └── orders.py             # Bracket order creation
├── logs/
│   └── (auto-created daily)
└── README.md                 # Usage instructions
```

### Daily Flow (all times CET)

```
10:00  IFDS pipeline runs → output/execution_plan_run_YYYYMMDD_*.csv
15:30  US market opens
15:35  submit_orders.py → reads latest execution_plan → submits bracket orders to IBKR
       Telegram: "📊 PAPER TRADING — Submitted X orders, $Y exposure"
...    During the day: TP1/TP2/SL may hit automatically
21:45  close_positions.py → MOC SELL for any remaining open positions (15:45 ET)
22:00  US market closes
22:05  eod_report.py → query fills → save CSV → Telegram EOD report → cancel all remaining orders
```

### Cron Jobs (MacMini)

```bash
# Add to existing crontab:
# Paper Trading — Order Submission (market open + 5 min)
35 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py >> logs/paper_trading.log 2>&1

# Paper Trading — MOC Close (15:45 ET = 21:45 CET)
45 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py >> logs/paper_trading.log 2>&1

# Paper Trading — EOD Report + Cleanup (16:05 ET = 22:05 CET)
05 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py >> logs/paper_trading.log 2>&1
```

---

## DETAILED SPECIFICATIONS

### 1. submit_orders.py

**Purpose:** Read the latest IFDS execution plan and submit bracket orders to IBKR.

**Input:** Latest `output/execution_plan_run_YYYYMMDD_*.csv` (today's date)

**CSV columns (IFDS format):**
```csv
instrument_id,direction,order_type,limit_price,quantity,stop_loss,take_profit_1,take_profit_2,risk_usd,score,gex_regime,sector,multiplier_total,mult_vix,mult_utility,sector_bmi,sector_regime,is_mean_reversion
WEC,BUY,LIMIT,115.79,113,112.26,120.49,122.84,401.38,142.5,positive,Utilities,0.8027,0.988,1.3,54.51,neutral,False
```

**Finding the latest file:**
```python
import glob
from pathlib import Path

today = date.today().strftime("%Y%m%d")
pattern = f"output/execution_plan_run_{today}_*.csv"
files = sorted(glob.glob(pattern))
if not files:
    logger.error("No execution plan found for today. Exiting.")
    sys.exit(0)  # Not an error — pipeline may not have run
latest = files[-1]  # Last one chronologically (sorted by timestamp in filename)
```

**Order Logic — TWO INDEPENDENT BRACKETS per ticker:**

For each ticker in the CSV, create TWO completely independent bracket orders:

```
Bracket A (33% of quantity — TP1 target):
    Entry: BUY qty_a @ limit_price (LMT, DAY)
    ├── TP1:  SELL qty_a @ take_profit_1 (LMT, DAY)
    └── SL_A: SELL qty_a @ stop_loss (STP, DAY)

Bracket B (67% of quantity — TP2 target):
    Entry: BUY qty_b @ limit_price (LMT, DAY)
    ├── TP2:  SELL qty_b @ take_profit_2 (LMT, DAY)
    └── SL_B: SELL qty_b @ stop_loss (STP, DAY)
```

**Quantity calculation:**
```python
total_qty = int(row['quantity'])
qty_tp1 = max(1, int(round(total_qty * 0.33)))  # 33% for TP1
qty_tp2 = total_qty - qty_tp1                     # 67% for TP2
# Ensure both are at least 1
if qty_tp2 < 1:
    qty_tp2 = 1
    qty_tp1 = total_qty - 1
```

**TIF: ALL orders are DAY** — entries, TPs, and SLs all expire at market close. No GTC orders.

**Safety Rails:**
- `MAX_DAILY_EXPOSURE = 50_000` ($50K per day)
- Track cumulative exposure as orders are submitted; skip remaining tickers if limit reached
- Minimum quantity: skip ticker if total_qty < 2 (can't split into two brackets)
- Validate each contract with `ib.reqContractDetails()` before submitting
- Idempotency: check for existing positions/orders before submitting (skip if already active)

**Circuit Breaker Check:**
- Before submitting, read cumulative P&L from `logs/cumulative_pnl.json`
- If cumulative loss >= $5,000 (-5%), send Telegram alert but **continue trading** (do NOT stop)

**IBKR Connection:**
- Host: 127.0.0.1, Port: 7497 (paper), Client ID: 10
- Use `ib_insync` library
- Python 3.14+ asyncio compatibility: create event loop before importing ib_insync

**Bracket Order Creation (using ib_insync):**
```python
# Use ib.bracketOrder() for each bracket — it handles parent-child linking
# Entry: LMT, DAY, with Adaptive algo for better fills
# TP: LMT, DAY (child of entry)
# SL: STP, DAY (child of entry)
# transmit=True on last child order
```

**Console output format:**
```
IFDS Paper Trading — 2026-02-18
Reading: execution_plan_run_20260218_100023_abc123.csv

  WEC: BUY 113 @ $115.79 | SL $112.26
    Bracket A: 37 shares → TP1 $120.49
    Bracket B: 76 shares → TP2 $122.84
  OHI: BUY 421 @ $47.40 | SL $45.66
    Bracket A: 139 shares → TP1 $49.72
    Bracket B: 282 shares → TP2 $50.88
  ...
  [EXPOSURE LIMIT] Skipping IFF — would exceed $50K daily limit

Submitted: 6 tickers (12 brackets) | Exposure: $48,230
```

**Telegram message (sent after all orders submitted):**
```
📊 PAPER TRADING — 2026-02-18
Submitted: 6 tickers (12 brackets)
Exposure: $48,230 / $50,000 limit
Tickers: WEC, OHI, BHP, AEE, NI, SPG
```

### 2. close_positions.py

**Purpose:** At 15:45 ET (21:45 CET), submit MOC (Market-on-Close) SELL orders for any positions still open.

**Logic:**
```python
# 1. Connect to IBKR
# 2. Query open positions: ib.positions()
# 3. For each position with qty > 0:
#    - Create MOC SELL order for full quantity
#    - Submit order
# 4. Log what was sent
# 5. Telegram notification if any MOC orders were submitted
```

**MOC Order:**
```python
from ib_insync import MarketOrder
order = MarketOrder('SELL', quantity)
order.tif = 'DAY'
order.orderType = 'MOC'  # Market-on-Close
order.account = account
```

**IMPORTANT:** NYSE requires MOC orders before 15:50 ET. Our 15:45 ET timing gives 5 minutes buffer.

**If no open positions → log "No positions to close" and exit quietly (no Telegram).**

**Console output:**
```
MOC Close — 2026-02-18
  WEC: MOC SELL 113 shares (no TP/SL hit today)
  NI: MOC SELL 431 shares (no TP/SL hit today)
MOC submitted: 2 positions
```

**Telegram (only if MOC orders were sent):**
```
🔔 PAPER TRADING MOC — 2026-02-18
Closing 2 remaining positions at market close:
WEC: 113 shares | NI: 431 shares
```

### 3. eod_report.py

**Purpose:** After market close, generate daily trade report, save to CSV, update cumulative P&L, send Telegram summary, and cancel any remaining orders.

**Logic:**
```python
# 1. Connect to IBKR
# 2. Query today's executions: ib.executions()
#    Filter by today's date
# 3. Build trade report:
#    - Match BUY fills (entries) with SELL fills (TP/SL/MOC)
#    - Calculate per-trade P&L
#    - Identify exit type: TP1, TP2, SL, MOC (based on fill price vs target prices)
# 4. Save daily CSV: logs/trades_YYYY-MM-DD.csv
# 5. Update cumulative P&L: logs/cumulative_pnl.json
# 6. Send Telegram EOD summary
# 7. Cancel ALL remaining open orders: cancel_all()
# 8. Verify: no open positions, no open orders
```

**Daily CSV format (logs/trades_YYYY-MM-DD.csv):**
```csv
date,ticker,direction,entry_price,entry_qty,exit_price,exit_qty,exit_type,pnl,pnl_pct,commission,score,sector,sl_price,tp1_price,tp2_price
2026-02-18,WEC,LONG,115.79,37,120.49,37,TP1,173.90,4.06,0.37,142.5,Utilities,112.26,120.49,122.84
2026-02-18,WEC,LONG,115.79,76,116.50,76,MOC,53.96,0.61,0.76,142.5,Utilities,112.26,120.49,122.84
2026-02-18,OHI,LONG,47.40,139,45.66,139,SL,-241.86,-3.67,1.39,141.75,Real Estate,45.66,49.72,50.88
```

**exit_type determination:**
```python
# Compare fill price to planned targets (with small tolerance ±0.02):
if abs(exit_price - tp1_price) <= 0.02: exit_type = "TP1"
elif abs(exit_price - tp2_price) <= 0.02: exit_type = "TP2"
elif abs(exit_price - sl_price) <= 0.02: exit_type = "SL"
else: exit_type = "MOC"
```

**Cumulative P&L tracking (logs/cumulative_pnl.json):**
```json
{
  "start_date": "2026-02-18",
  "initial_capital": 100000,
  "trading_days": 1,
  "cumulative_pnl": -14.00,
  "cumulative_pnl_pct": -0.014,
  "daily_history": [
    {"date": "2026-02-18", "pnl": -14.00, "trades": 12, "filled": 10, "tp1_hits": 2, "tp2_hits": 1, "sl_hits": 3, "moc_exits": 4}
  ]
}
```

**Cancel all remaining orders:**
```python
open_orders = ib.openOrders()
for order in open_orders:
    ib.cancelOrder(order)
# Verify
ib.sleep(2)
remaining = ib.openOrders()
if remaining:
    logger.warning(f"Still {len(remaining)} orders after cancel!")
```

**Telegram EOD report:**
```
📊 PAPER TRADING EOD — 2026-02-18

Trades: 12 | Filled: 10/12 (83%)
TP1: 2 | TP2: 1 | SL: 3 | MOC: 4

P&L today: -$14.00 (-0.01%)
Cumulative: -$14.00 (-0.01%) [Day 1/21]

⚠️ Circuit breaker: -$14 / -$5,000 threshold
```

**If cumulative P&L <= -$5,000, add warning:**
```
⚠️ CIRCUIT BREAKER ALERT
Cumulative P&L: -$5,230 (-5.23%)
Threshold reached. Test continues — review recommended.
```

### 4. lib/connection.py

**Simplified IBKR connection module:**
```python
"""IBKR Paper Trading — Connection Manager"""
import asyncio
import logging
import sys

# Python 3.14+: event loop must exist before importing ib_insync
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB

logger = logging.getLogger(__name__)

PAPER_PORT = 7497
CLIENT_ID = 10  # Dedicated client ID for paper trading scripts

def connect(host='127.0.0.1', port=PAPER_PORT, client_id=CLIENT_ID):
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        logger.info(f"Connected to IBKR: {host}:{port}")
        return ib
    except Exception as e:
        logger.error(f"IBKR connection failed: {e}")
        sys.exit(1)

def get_account(ib):
    accounts = ib.managedAccounts()
    target = next((a for a in accounts if a.startswith('D')), accounts[0])
    logger.info(f"Account: {target}")
    return target

def disconnect(ib):
    try:
        ib.disconnect()
    except:
        pass
```

### 5. lib/orders.py

**Bracket order creation — two independent brackets:**
```python
"""IBKR Paper Trading — Order Creation"""
from ib_insync import Stock, LimitOrder, StopOrder, MarketOrder, TagValue

def validate_contract(ib, symbol):
    """Validate stock exists in IBKR."""
    contract = Stock(symbol, 'SMART', 'USD')
    details = ib.reqContractDetails(contract)
    if not details:
        return None
    return details[0].contract

def create_day_bracket(ib, contract, action, qty, limit_price, tp_price, sl_price, account, tag_suffix=""):
    """
    Create a single bracket order: Entry + TP + SL, all DAY TIF.

    Returns (entry, tp, sl) order tuple.
    """
    entry_id = ib.client.getReqId()
    tp_id = ib.client.getReqId()
    sl_id = ib.client.getReqId()

    exit_action = 'SELL' if action == 'BUY' else 'BUY'

    entry = LimitOrder(
        action=action,
        totalQuantity=qty,
        lmtPrice=round(limit_price, 2),
        orderId=entry_id,
        account=account,
        tif='DAY',
        outsideRth=False,
        orderRef=f"IFDS_{tag_suffix}",
        transmit=False,
        algoStrategy='Adaptive',
        algoParams=[TagValue('adaptivePriority', 'Normal')],
    )

    tp = LimitOrder(
        action=exit_action,
        totalQuantity=qty,
        lmtPrice=round(tp_price, 2),
        orderId=tp_id,
        account=account,
        tif='DAY',
        parentId=entry_id,
        orderRef=f"IFDS_{tag_suffix}_TP",
        transmit=False,
    )

    sl = StopOrder(
        action=exit_action,
        totalQuantity=qty,
        stopPrice=round(sl_price, 2),
        orderId=sl_id,
        account=account,
        tif='DAY',
        parentId=entry_id,
        orderRef=f"IFDS_{tag_suffix}_SL",
        transmit=True,  # Last child transmits all
    )

    return entry, tp, sl

def submit_bracket(ib, contract, orders, dry_run=False):
    """Submit bracket order tuple to IBKR."""
    if dry_run:
        return []
    trades = []
    for order in orders:
        trade = ib.placeOrder(contract, order)
        trades.append(trade)
    return trades

def create_moc_order(qty, account):
    """Create Market-on-Close SELL order."""
    order = MarketOrder('SELL', qty)
    order.tif = 'DAY'
    order.orderType = 'MOC'
    order.account = account
    return order
```

---

## TELEGRAM INTEGRATION

Use the same Telegram bot as IFDS pipeline. Read from `.env`:
```
IFDS_TELEGRAM_BOT_TOKEN=...
IFDS_TELEGRAM_CHAT_ID=...
```

**Telegram send function (reuse pattern from company_intel.py):**
```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def send_telegram(message):
    token = os.getenv('IFDS_TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('IFDS_TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    })
```

---

## DEPENDENCIES

The project already has `ib_insync` and `python-dotenv` in the venv. Verify:
```bash
pip install ib_insync python-dotenv --break-system-packages
```

Note: `ib_insync` requires asyncio event loop before import on Python 3.14+. The connection.py module handles this.

---

## TESTING SEQUENCE

### Phase 1: Dry Run (no IBKR needed)
```bash
python scripts/paper_trading/submit_orders.py --dry-run
```
Should:
- Find latest execution_plan CSV
- Parse all tickers
- Show what would be submitted (quantities, prices, brackets)
- NOT connect to IBKR

### Phase 2: Connection Test
```bash
python scripts/paper_trading/submit_orders.py --test-connection
```
Should:
- Connect to IBKR Gateway
- Print account info and balance
- Disconnect

### Phase 3: Live Paper Test (single day)
```bash
# Before market open
python scripts/paper_trading/submit_orders.py

# At 15:45 ET
python scripts/paper_trading/close_positions.py

# After market close
python scripts/paper_trading/eod_report.py
```
Verify in TWS that orders appear, fills happen, positions close.

### Phase 4: Cron Automation (21 days)
Add cron jobs and let it run autonomously.

---

## CONFIGURATION CONSTANTS (top of each script)

```python
# Paper Trading Configuration
IBKR_HOST = '127.0.0.1'
IBKR_PORT = 7497          # Paper trading
CLIENT_ID = 10             # Dedicated for paper trading
ACCOUNT_PREFIX = 'D'       # Paper accounts start with 'D'

# Risk Limits
MAX_DAILY_EXPOSURE = 50_000    # $50K per day
CIRCUIT_BREAKER_USD = -5_000   # Alert at -$5K cumulative
SCALE_OUT_PCT = 0.33           # 33% at TP1, 67% at TP2
MIN_QUANTITY = 2               # Skip ticker if qty < 2

# Paths
EXECUTION_PLAN_DIR = 'output'
LOG_DIR = 'scripts/paper_trading/logs'
CUMULATIVE_PNL_FILE = 'scripts/paper_trading/logs/cumulative_pnl.json'
```

---

## IMPORTANT IMPLEMENTATION NOTES

1. **NO code reuse from reference/IBKR/** — clean implementation. The reference is there for reading/understanding only.

2. **ALL TIF = DAY** — no GTC orders. This is a daytrading system. Every order expires at market close.

3. **Two independent brackets** — no OCA groups, no event handlers, no SL sync needed. Each bracket is self-contained with its own entry, TP, and SL.

4. **Adaptive algo on entry orders** — `algoStrategy='Adaptive'` with `adaptivePriority='Normal'` for better fill prices.

5. **asyncio event loop** — Must create before importing ib_insync on Python 3.14+.

6. **IB Gateway must be running** — If connection fails, log error and exit cleanly (don't crash).

7. **Execution plan filename pattern** — `execution_plan_run_YYYYMMDD_HHMMSS_hash.csv`. Use glob to find today's files, take the last one (most recent).

8. **Quantity from CSV is for $100K portfolio** — use as-is for the $100K paper account, but enforce $50K daily exposure limit.

9. **Commission** — IBKR Paper Trading simulates realistic commissions. No need to calculate manually.

10. **Fill matching in eod_report** — Match by symbol. Each ticker has 2 BUY fills (bracket A + B entries) and potentially multiple SELL fills (TP, SL, MOC). Group by ticker for P&L calculation.

---

## DELIVERABLES

After implementation:
1. All 5 Python files created and working
2. `--dry-run` mode tested with latest execution_plan
3. `--test-connection` verified with IBKR Gateway
4. README.md with usage instructions
5. Cron entries documented and ready to add

---

## SUCCESS CRITERIA (21-day test)

| Metric | Target |
|--------|--------|
| Fill rate (entries) | >60% |
| System uptime | >95% (max 1 missed day) |
| Order rejections | 0 |
| Data completeness | 21/21 daily CSVs |
| P&L tracking accuracy | Matches IBKR account statement |
