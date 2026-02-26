#!/usr/bin/env python3
"""IBKR Paper Trading — Submit bracket orders from IFDS execution plan.

Usage:
    python scripts/paper_trading/submit_orders.py              # Live submit
    python scripts/paper_trading/submit_orders.py --dry-run    # Parse only, no IBKR
    python scripts/paper_trading/submit_orders.py --test-connection  # Connection test
"""
import argparse
import csv
import glob
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_DAILY_EXPOSURE = 100_000
CIRCUIT_BREAKER_USD = -5_000
SCALE_OUT_PCT = 0.33
MIN_QUANTITY = 2

EXECUTION_PLAN_DIR = 'output'
LOG_DIR = 'scripts/paper_trading/logs'
CUMULATIVE_PNL_FILE = 'scripts/paper_trading/logs/cumulative_pnl.json'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('submit_orders')

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
# CSV loading
# ---------------------------------------------------------------------------


def find_todays_csv():
    """Find the latest execution plan CSV for today."""
    today = date.today().strftime("%Y%m%d")
    pattern = f"{EXECUTION_PLAN_DIR}/execution_plan_run_{today}_*.csv"
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    return Path(files[-1])


def find_latest_csv():
    """Find the most recent execution plan CSV (any date)."""
    pattern = f"{EXECUTION_PLAN_DIR}/execution_plan_run_*.csv"
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    return Path(files[-1])


def load_execution_plan(csv_path):
    """Load ticker data from execution plan CSV."""
    tickers = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_qty = int(row['quantity'])
            if total_qty < MIN_QUANTITY:
                logger.info(f"  Skipping {row['instrument_id']}: qty {total_qty} < {MIN_QUANTITY}")
                continue

            qty_tp1 = max(1, int(round(total_qty * SCALE_OUT_PCT)))
            qty_tp2 = total_qty - qty_tp1
            if qty_tp2 < 1:
                qty_tp2 = 1
                qty_tp1 = total_qty - 1

            tickers.append({
                'symbol': row['instrument_id'],
                'direction': row['direction'],
                'limit_price': float(row['limit_price']),
                'total_qty': total_qty,
                'qty_tp1': qty_tp1,
                'qty_tp2': qty_tp2,
                'stop_loss': float(row['stop_loss']),
                'take_profit_1': float(row['take_profit_1']),
                'take_profit_2': float(row['take_profit_2']),
                'score': float(row['score']),
                'sector': row['sector'],
            })
    return tickers


# ---------------------------------------------------------------------------
# Circuit breaker check
# ---------------------------------------------------------------------------


def check_circuit_breaker():
    """Check cumulative P&L. Returns (pnl, alert_needed)."""
    if not os.path.exists(CUMULATIVE_PNL_FILE):
        return 0.0, False
    try:
        with open(CUMULATIVE_PNL_FILE) as f:
            data = json.load(f)
        pnl = data.get('cumulative_pnl', 0.0)
        return pnl, pnl <= CIRCUIT_BREAKER_USD
    except Exception:
        return 0.0, False


# ---------------------------------------------------------------------------
# Existing position/order check
# ---------------------------------------------------------------------------


def get_existing_symbols(ib):
    """Get set of symbols with existing positions or open orders."""
    existing = set()
    for pos in ib.positions():
        if pos.position != 0:
            existing.add(pos.contract.symbol)
    for trade in ib.openTrades():
        existing.add(trade.contract.symbol)
    return existing


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description='IBKR Paper Trading — Submit Orders')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse CSV and show orders without connecting to IBKR')
    parser.add_argument('--test-connection', action='store_true',
                        help='Test IBKR connection only')
    parser.add_argument('--file', help='Specific execution plan CSV path')
    parser.add_argument('--override-circuit-breaker', action='store_true',
                        help='Override circuit breaker and submit orders anyway (use with caution)')
    args = parser.parse_args()

    today_str = date.today().strftime('%Y-%m-%d')
    print(f"\nIFDS Paper Trading — {today_str}")

    # --- Test connection mode ---
    if args.test_connection:
        from lib.connection import connect, get_account, disconnect
        ib = connect(client_id=10)
        account = get_account(ib)
        summary = ib.accountSummary(account)
        for item in summary:
            if item.tag in ('NetLiquidation', 'TotalCashValue', 'BuyingPower'):
                print(f"  {item.tag}: ${float(item.value):,.2f}")
        disconnect(ib)
        return

    # --- Find CSV ---
    if args.file:
        csv_path = Path(args.file)
    else:
        csv_path = find_todays_csv()
        if not csv_path:
            csv_path = find_latest_csv()

    if not csv_path or not csv_path.exists():
        logger.error("No execution plan CSV found. Exiting.")
        sys.exit(0)

    print(f"Reading: {csv_path.name}")

    # --- Load tickers ---
    tickers = load_execution_plan(csv_path)
    if not tickers:
        logger.error("No valid tickers in CSV. Exiting.")
        sys.exit(0)

    # --- Circuit breaker check ---
    cum_pnl, cb_alert = check_circuit_breaker()
    if cb_alert:
        if args.override_circuit_breaker:
            msg = f"⚠️ CIRCUIT BREAKER TRIGGERED — override flag used, continuing.\nCumulative P&L: ${cum_pnl:,.0f} (threshold: ${CIRCUIT_BREAKER_USD:,.0f})"
            logger.warning(msg)
            send_telegram(msg)
        else:
            msg = f"🛑 CIRCUIT BREAKER TRIGGERED — order submission HALTED.\nCumulative P&L: ${cum_pnl:,.0f} (threshold: ${CIRCUIT_BREAKER_USD:,.0f})\nUse --override-circuit-breaker to proceed."
            logger.error(msg)
            send_telegram(msg)
            sys.exit(1)

    # --- Dry run mode ---
    if args.dry_run:
        print(f"\n[DRY RUN] — No IBKR connection\n")
        exposure = 0.0
        submitted = 0
        submitted_tickers = []
        skipped = []

        for t in tickers:
            ticker_exposure = t['limit_price'] * t['total_qty']
            if exposure + ticker_exposure > MAX_DAILY_EXPOSURE:
                skipped.append(t['symbol'])
                print(f"  [EXPOSURE LIMIT] Skipping {t['symbol']} — would exceed ${MAX_DAILY_EXPOSURE:,} daily limit")
                continue

            exposure += ticker_exposure
            submitted += 1
            submitted_tickers.append(t['symbol'])
            print(f"  {t['symbol']}: {t['direction']} {t['total_qty']} @ ${t['limit_price']} | SL ${t['stop_loss']}")
            print(f"    Bracket A: {t['qty_tp1']} shares → TP1 ${t['take_profit_1']}")
            print(f"    Bracket B: {t['qty_tp2']} shares → TP2 ${t['take_profit_2']}")

        print(f"\nWould submit: {submitted} tickers ({submitted * 2} brackets) | Exposure: ${exposure:,.0f}")
        if skipped:
            print(f"Skipped (exposure limit): {', '.join(skipped)}")

        if submitted > 0:
            tg_msg = (
                f"📊 PAPER TRADING [DRY RUN] — {today_str}\n"
                f"Would submit: {submitted} tickers ({submitted * 2} brackets)\n"
                f"Exposure: ${exposure:,.0f} / ${MAX_DAILY_EXPOSURE:,} limit\n"
                f"Tickers: {', '.join(submitted_tickers)}"
            )
            send_telegram(tg_msg)
            print("Telegram sent.")
        return

    # --- Live mode ---
    from lib.connection import connect, get_account, disconnect
    from lib.orders import validate_contract, create_day_bracket, submit_bracket

    ib = connect(client_id=10)
    account = get_account(ib)

    existing = get_existing_symbols(ib)
    if existing:
        logger.info(f"Existing positions/orders: {existing}")

    exposure = 0.0
    submitted = 0
    submitted_tickers = []
    skipped = []

    print()
    for t in tickers:
        sym = t['symbol']

        # Skip if already has position/orders
        if sym in existing:
            logger.info(f"  Skipping {sym}: already has active position/orders")
            continue

        # Exposure check
        ticker_exposure = t['limit_price'] * t['total_qty']
        if exposure + ticker_exposure > MAX_DAILY_EXPOSURE:
            skipped.append(sym)
            print(f"  [EXPOSURE LIMIT] Skipping {sym} — would exceed ${MAX_DAILY_EXPOSURE:,} daily limit")
            continue

        # Validate contract
        contract = validate_contract(ib, sym)
        if not contract:
            logger.warning(f"  Skipping {sym}: contract not found in IBKR")
            continue

        # Create and submit Bracket A (TP1)
        bracket_a = create_day_bracket(
            ib, contract, t['direction'], t['qty_tp1'],
            t['limit_price'], t['take_profit_1'], t['stop_loss'],
            account, tag_suffix=f"{sym}_A",
        )
        submit_bracket(ib, contract, bracket_a)

        # Create and submit Bracket B (TP2)
        bracket_b = create_day_bracket(
            ib, contract, t['direction'], t['qty_tp2'],
            t['limit_price'], t['take_profit_2'], t['stop_loss'],
            account, tag_suffix=f"{sym}_B",
        )
        submit_bracket(ib, contract, bracket_b)

        exposure += ticker_exposure
        submitted += 1
        submitted_tickers.append(sym)

        print(f"  {sym}: {t['direction']} {t['total_qty']} @ ${t['limit_price']} | SL ${t['stop_loss']}")
        print(f"    Bracket A: {t['qty_tp1']} shares → TP1 ${t['take_profit_1']}")
        print(f"    Bracket B: {t['qty_tp2']} shares → TP2 ${t['take_profit_2']}")

    ib.sleep(1)  # Let orders propagate

    print(f"\nSubmitted: {submitted} tickers ({submitted * 2} brackets) | Exposure: ${exposure:,.0f}")
    if skipped:
        print(f"Skipped (exposure limit): {', '.join(skipped)}")

    # Telegram notification
    if submitted > 0:
        tg_msg = (
            f"📊 PAPER TRADING — {today_str}\n"
            f"Submitted: {submitted} tickers ({submitted * 2} brackets)\n"
            f"Exposure: ${exposure:,.0f} / ${MAX_DAILY_EXPOSURE:,} limit\n"
            f"Tickers: {', '.join(submitted_tickers)}"
        )
        send_telegram(tg_msg)

    disconnect(ib)


if __name__ == '__main__':
    main()
