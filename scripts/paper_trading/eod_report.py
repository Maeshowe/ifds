#!/usr/bin/env python3
"""IBKR Paper Trading — End-of-Day report, P&L tracking, and cleanup.

Runs at 22:05 CET (16:05 ET) — after market close.
Queries today's executions, builds trade report, updates cumulative P&L,
sends Telegram summary, cancels all remaining orders.

Usage:
    python scripts/paper_trading/eod_report.py
"""
import csv
import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_DIR = 'scripts/paper_trading/logs'
CUMULATIVE_PNL_FILE = 'scripts/paper_trading/logs/cumulative_pnl.json'
CIRCUIT_BREAKER_USD = -5_000
INITIAL_CAPITAL = 100_000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('eod_report')

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def send_telegram(message):
    """Send message via Telegram Bot API."""
    import requests

    token = os.getenv('IFDS_TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('IFDS_TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


# ---------------------------------------------------------------------------
# Execution plan loading (for score/sector/target prices)
# ---------------------------------------------------------------------------


def load_execution_plan_metadata(today_str):
    """Load metadata from today's execution plan for enriching reports."""
    import glob

    pattern = f"output/execution_plan_run_{today_str.replace('-', '')}_*.csv"
    files = sorted(glob.glob(pattern))
    if not files:
        # Try most recent
        pattern = "output/execution_plan_run_*.csv"
        files = sorted(glob.glob(pattern))
    if not files:
        return {}

    meta = {}
    with open(files[-1], newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            meta[row['instrument_id']] = {
                'score': float(row['score']),
                'sector': row['sector'],
                'sl_price': float(row['stop_loss']),
                'tp1_price': float(row['take_profit_1']),
                'tp2_price': float(row['take_profit_2']),
            }
    return meta


# ---------------------------------------------------------------------------
# Fill matching and P&L calculation
# ---------------------------------------------------------------------------


def classify_exit(exit_price, sl_price, tp1_price, tp2_price, tolerance=0.02):
    """Determine exit type based on fill price vs planned targets."""
    if abs(exit_price - tp1_price) <= tolerance:
        return "TP1"
    if abs(exit_price - tp2_price) <= tolerance:
        return "TP2"
    if abs(exit_price - sl_price) <= tolerance:
        return "SL"
    return "MOC"


def build_trade_report(executions, meta):
    """Match BUY and SELL fills by symbol. Returns list of trade dicts."""
    # Group executions by symbol
    by_symbol = defaultdict(lambda: {'buys': [], 'sells': []})

    for exe in executions:
        sym = exe.contract.symbol
        side = exe.execution.side
        price = exe.execution.price
        qty = int(exe.execution.shares)
        commission = exe.commissionReport.commission if exe.commissionReport else 0.0

        record = {
            'price': price,
            'qty': qty,
            'commission': commission,
            'time': exe.execution.time,
        }

        if side == 'BOT':
            by_symbol[sym]['buys'].append(record)
        else:
            by_symbol[sym]['sells'].append(record)

    trades = []
    for sym, fills in by_symbol.items():
        ticker_meta = meta.get(sym, {})
        sl_price = ticker_meta.get('sl_price', 0)
        tp1_price = ticker_meta.get('tp1_price', 0)
        tp2_price = ticker_meta.get('tp2_price', 0)
        score = ticker_meta.get('score', 0)
        sector = ticker_meta.get('sector', 'N/A')

        # Calculate average entry price
        total_buy_qty = sum(b['qty'] for b in fills['buys'])
        if total_buy_qty == 0:
            continue
        avg_entry = sum(b['price'] * b['qty'] for b in fills['buys']) / total_buy_qty
        buy_commission = sum(b['commission'] for b in fills['buys'])

        # Process each sell fill as a separate trade leg
        for sell in fills['sells']:
            exit_type = classify_exit(sell['price'], sl_price, tp1_price, tp2_price)
            pnl = (sell['price'] - avg_entry) * sell['qty']
            pnl_pct = ((sell['price'] / avg_entry) - 1) * 100 if avg_entry else 0
            # Proportional buy commission
            prop_commission = (buy_commission * sell['qty'] / total_buy_qty) if total_buy_qty else 0

            trades.append({
                'date': date.today().isoformat(),
                'ticker': sym,
                'direction': 'LONG',
                'entry_price': round(avg_entry, 2),
                'entry_qty': sell['qty'],
                'exit_price': round(sell['price'], 2),
                'exit_qty': sell['qty'],
                'exit_type': exit_type,
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'commission': round(sell['commission'] + prop_commission, 2),
                'score': score,
                'sector': sector,
                'sl_price': sl_price,
                'tp1_price': tp1_price,
                'tp2_price': tp2_price,
            })

    return trades


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def save_daily_csv(trades, today_str):
    """Save daily trade CSV."""
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    csv_path = Path(LOG_DIR) / f"trades_{today_str}.csv"

    fieldnames = [
        'date', 'ticker', 'direction', 'entry_price', 'entry_qty',
        'exit_price', 'exit_qty', 'exit_type', 'pnl', 'pnl_pct',
        'commission', 'score', 'sector', 'sl_price', 'tp1_price', 'tp2_price',
    ]

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)

    logger.info(f"Saved: {csv_path}")
    return csv_path


# ---------------------------------------------------------------------------
# Cumulative P&L
# ---------------------------------------------------------------------------


def update_cumulative_pnl(trades, today_str):
    """Update cumulative P&L JSON file."""
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    # Load existing data
    if os.path.exists(CUMULATIVE_PNL_FILE):
        with open(CUMULATIVE_PNL_FILE) as f:
            data = json.load(f)
    else:
        data = {
            'start_date': today_str,
            'initial_capital': INITIAL_CAPITAL,
            'trading_days': 0,
            'cumulative_pnl': 0.0,
            'cumulative_pnl_pct': 0.0,
            'daily_history': [],
        }

    # Calculate daily stats
    daily_pnl = sum(t['pnl'] for t in trades)
    total_trades = len(trades)
    filled = len([t for t in trades if t['exit_type'] != 'UNFILLED'])
    tp1_hits = len([t for t in trades if t['exit_type'] == 'TP1'])
    tp2_hits = len([t for t in trades if t['exit_type'] == 'TP2'])
    sl_hits = len([t for t in trades if t['exit_type'] == 'SL'])
    moc_exits = len([t for t in trades if t['exit_type'] == 'MOC'])

    # Update cumulative
    data['trading_days'] += 1
    data['cumulative_pnl'] = round(data['cumulative_pnl'] + daily_pnl, 2)
    data['cumulative_pnl_pct'] = round(
        data['cumulative_pnl'] / INITIAL_CAPITAL * 100, 3
    )

    data['daily_history'].append({
        'date': today_str,
        'pnl': round(daily_pnl, 2),
        'trades': total_trades,
        'filled': filled,
        'tp1_hits': tp1_hits,
        'tp2_hits': tp2_hits,
        'sl_hits': sl_hits,
        'moc_exits': moc_exits,
    })

    with open(CUMULATIVE_PNL_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    return data, daily_pnl


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    from lib.connection import connect, get_account, disconnect

    today_str = date.today().isoformat()
    print(f"\nEOD Report — {today_str}")

    ib = connect()
    account = get_account(ib)

    # --- Query today's executions ---
    executions = ib.fills()

    # Filter to today
    today_date = date.today()
    todays_fills = [
        e for e in executions
        if e.execution.time.date() == today_date
    ]

    if not todays_fills:
        print("No fills today")
        # Still cancel orders and update P&L with empty trades
        trades = []
    else:
        # Load execution plan metadata
        meta = load_execution_plan_metadata(today_str)

        # Build trade report
        trades = build_trade_report(todays_fills, meta)

        # Print trade summary
        print(f"\nTrades: {len(trades)}")
        for t in trades:
            pnl_sign = '+' if t['pnl'] >= 0 else ''
            print(f"  {t['ticker']}: {t['exit_type']} | Entry ${t['entry_price']} → Exit ${t['exit_price']} | P&L {pnl_sign}${t['pnl']}")

    # --- Save daily CSV ---
    if trades:
        save_daily_csv(trades, today_str)

    # --- Update cumulative P&L ---
    cum_data, daily_pnl = update_cumulative_pnl(trades, today_str)

    cum_pnl = cum_data['cumulative_pnl']
    cum_pct = cum_data['cumulative_pnl_pct']
    trading_days = cum_data['trading_days']

    print(f"\nP&L today: ${daily_pnl:+,.2f}")
    print(f"Cumulative: ${cum_pnl:+,.2f} ({cum_pct:+.2f}%) [Day {trading_days}/21]")

    # --- Cancel all remaining orders ---
    open_orders = ib.openOrders()
    if open_orders:
        for order in open_orders:
            ib.cancelOrder(order)
        ib.sleep(2)
        remaining = ib.openOrders()
        if remaining:
            logger.warning(f"Still {len(remaining)} orders after cancel!")
        else:
            print(f"Cancelled {len(open_orders)} remaining orders")
    else:
        print("No open orders to cancel")

    # --- Verify clean state ---
    positions = [p for p in ib.positions() if p.position != 0]
    if positions:
        logger.warning(f"Still {len(positions)} open positions!")
        for p in positions:
            logger.warning(f"  {p.contract.symbol}: {p.position} shares")

    # --- Telegram EOD report ---
    total_trades = len(trades)
    daily_stats = cum_data['daily_history'][-1] if cum_data['daily_history'] else {}

    tg_lines = [
        f"📊 PAPER TRADING EOD — {today_str}",
        "",
        f"Trades: {total_trades} | Filled: {daily_stats.get('filled', 0)}/{total_trades}",
        f"TP1: {daily_stats.get('tp1_hits', 0)} | TP2: {daily_stats.get('tp2_hits', 0)} | SL: {daily_stats.get('sl_hits', 0)} | MOC: {daily_stats.get('moc_exits', 0)}",
        "",
        f"P&L today: ${daily_pnl:+,.2f} ({daily_pnl / INITIAL_CAPITAL * 100:+.2f}%)",
        f"Cumulative: ${cum_pnl:+,.2f} ({cum_pct:+.2f}%) [Day {trading_days}/21]",
    ]

    if cum_pnl <= CIRCUIT_BREAKER_USD:
        tg_lines.extend([
            "",
            f"⚠️ CIRCUIT BREAKER ALERT",
            f"Cumulative P&L: ${cum_pnl:+,.2f} ({cum_pct:+.2f}%)",
            f"Threshold reached. Test continues — review recommended.",
        ])
    else:
        tg_lines.extend([
            "",
            f"Circuit breaker: ${cum_pnl:+,.0f} / ${CIRCUIT_BREAKER_USD:,} threshold",
        ])

    send_telegram("\n".join(tg_lines))

    disconnect(ib)
    print("\nDone.")


if __name__ == '__main__':
    main()
