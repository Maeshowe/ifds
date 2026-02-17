# IFDS Paper Trading — IBKR Integration

21-day paper trading test using IBKR Paper Trading account ($100K).
Reads IFDS execution plan CSV and submits daytrading bracket orders.

## Prerequisites

- IB Gateway running on localhost:7497 (paper trading mode)
- Paper trading account (starts with `D`)
- `.env` with `IFDS_TELEGRAM_BOT_TOKEN` and `IFDS_TELEGRAM_CHAT_ID`

## Daily Flow (CET)

| Time  | Script            | Action                                    |
|-------|-------------------|-------------------------------------------|
| 10:00 | IFDS pipeline     | Generates execution_plan CSV              |
| 15:35 | submit_orders.py  | Reads CSV, submits bracket orders to IBKR |
| 21:45 | close_positions.py| MOC SELL for remaining open positions     |
| 22:05 | eod_report.py     | Daily report, P&L update, cancel orders   |

## Usage

```bash
# Dry run (no IBKR connection needed)
python scripts/paper_trading/submit_orders.py --dry-run

# Test IBKR connection
python scripts/paper_trading/submit_orders.py --test-connection

# Live paper trading
python scripts/paper_trading/submit_orders.py
python scripts/paper_trading/close_positions.py
python scripts/paper_trading/eod_report.py
```

## Order Structure

Each ticker gets TWO independent bracket orders:

- **Bracket A** (33%): Entry → TP1 / SL
- **Bracket B** (67%): Entry → TP2 / SL

All orders are DAY TIF (expire at market close).

## Safety Rails

- Max daily exposure: $50,000
- Circuit breaker alert at -$5,000 cumulative (continues trading)
- Min quantity: 2 shares (skip if less)
- Contract validation before submission
- Idempotency check (skip if position/order already exists)

## Cron Jobs

```bash
# Paper Trading (add to crontab -e)
35 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py >> logs/paper_trading.log 2>&1
45 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py >> logs/paper_trading.log 2>&1
05 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py >> logs/paper_trading.log 2>&1
```

## Output Files

- `logs/trades_YYYY-MM-DD.csv` — Daily trade details
- `logs/cumulative_pnl.json` — Running P&L tracker
