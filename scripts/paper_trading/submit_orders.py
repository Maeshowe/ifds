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
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_DAILY_EXPOSURE = 100_000
CIRCUIT_BREAKER_USD = -5_000
SCALE_OUT_PCT = 0.50  # BC23: equal bracket split (was 0.33)
MIN_QUANTITY = 2

EXECUTION_PLAN_DIR = 'output'
LOG_DIR = 'scripts/paper_trading/logs'
CUMULATIVE_PNL_FILE = 'scripts/paper_trading/logs/cumulative_pnl.json'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("submit")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger('submit')

try:
    from lib.event_logger import PTEventLogger
    evt = PTEventLogger()
except ModuleNotFoundError:
    evt = None

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def send_telegram(message):
    """Send message via Telegram Bot API with CET timestamp header."""
    from lib.telegram_helper import telegram_header
    from lib.telegram_helper import send_telegram as _send
    _send(f"{telegram_header('SUBMIT')}\n{message}")


def _build_ticker_table(tickers: list, submitted_tickers: list, existing: set | None = None) -> str:
    """Build a monospace ticker table for Telegram."""
    lines = []
    header = f"{'SYM':<6}{'QTY':>4} {'ENTRY':>7} {'SL':>7} {'TP1':>7} {'RISK':>6}"
    lines.append(header)
    total_risk = 0.0
    for t in tickers:
        sym = t['symbol']
        risk = round((t['limit_price'] - t['stop_loss']) * t['total_qty'], 2)
        total_risk += risk
        status = ""
        if existing and sym in existing:
            status = " skip"
        elif sym not in submitted_tickers:
            status = " skip"
        lines.append(
            f"{sym:<6}{t['total_qty']:>4} "
            f"{t['limit_price']:>7.2f} "
            f"{t['stop_loss']:>7.2f} "
            f"{t['take_profit_1']:>7.2f} "
            f"{'$'}{risk:>5.0f}{status}"
        )
    return "\n".join(lines), total_risk


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
    try:
        from lib.trading_day_guard import check_trading_day
        check_trading_day(logger)
    except ModuleNotFoundError:
        pass
    parser = argparse.ArgumentParser(description='IBKR Paper Trading — Submit Orders')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse CSV and show orders without connecting to IBKR')
    parser.add_argument('--test-connection', action='store_true',
                        help='Test IBKR connection only')
    parser.add_argument('--file', help='Specific execution plan CSV path')
    parser.add_argument('--override-circuit-breaker', action='store_true',
                        help='Override circuit breaker and submit orders anyway (use with caution)')
    parser.add_argument('--override-witching', action='store_true',
                        help='Submit orders on Witching day (use with caution)')
    args = parser.parse_args()

    today_str = date.today().strftime('%Y-%m-%d')
    logger.info(f"IFDS Paper Trading — {today_str}")

    # --- Test connection mode ---
    if args.test_connection:
        from lib.connection import connect, get_account, disconnect
        ib = connect(client_id=10)
        account = get_account(ib)
        summary = ib.accountSummary(account)
        for item in summary:
            if item.tag in ('NetLiquidation', 'TotalCashValue', 'BuyingPower'):
                logger.info(f"  {item.tag}: ${float(item.value):,.2f}")
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

    # --- Stale CSV guard: refuse to submit with execution plans older than today ---
    csv_stem = csv_path.stem  # e.g. "execution_plan_run_20260407_153012"
    csv_date_str = None
    for part in csv_stem.split('_'):
        if len(part) == 8 and part.isdigit():
            csv_date_str = part
            break
    if csv_date_str:
        csv_date = datetime.strptime(csv_date_str, "%Y%m%d").date()
        if csv_date != date.today():
            msg = (
                f"STALE CSV — refusing to submit. "
                f"Latest execution plan is from {csv_date} (today: {date.today()}). "
                f"Phase 4-6 may have failed to generate today's plan."
            )
            logger.error(msg)
            send_telegram(f"⚠️ {msg}")
            sys.exit(1)

    logger.info(f"Reading: {csv_path.name}")

    # --- Load tickers ---
    tickers = load_execution_plan(csv_path)
    if not tickers:
        logger.error("No valid tickers in CSV. Exiting.")
        sys.exit(0)

    # --- Witching day check ---
    from ifds.utils.calendar import is_witching_day

    if is_witching_day(date.today()) and not args.override_witching:
        msg = (
            f"WITCHING DAY — order submission SKIPPED.\n"
            f"{date.today()} is a Triple/Quadruple Witching day.\n"
            f"Pipeline ran normally. No orders submitted.\n"
            f"Use --override-witching to proceed."
        )
        logger.warning(msg)
        send_telegram(msg)
        if evt:
            evt.log("submit", "witching_skip", date=date.today().isoformat())
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
            if evt:
                evt.log("submit", "circuit_breaker", cum_pnl=cum_pnl, threshold=CIRCUIT_BREAKER_USD)
            sys.exit(1)

    # --- Dry run mode ---
    if args.dry_run:
        logger.info("[DRY RUN] — No IBKR connection")
        exposure = 0.0
        submitted = 0
        submitted_tickers = []
        skipped = []

        for t in tickers:
            ticker_exposure = t['limit_price'] * t['total_qty']
            if exposure + ticker_exposure > MAX_DAILY_EXPOSURE:
                skipped.append(t['symbol'])
                logger.warning(f"[EXPOSURE LIMIT] Skipping {t['symbol']} — would exceed ${MAX_DAILY_EXPOSURE:,} daily limit")
                continue

            exposure += ticker_exposure
            submitted += 1
            submitted_tickers.append(t['symbol'])
            logger.info(f"  {t['symbol']}: {t['direction']} {t['total_qty']} @ ${t['limit_price']} | SL ${t['stop_loss']}")
            logger.info(f"    Bracket A: {t['qty_tp1']} shares → TP1 ${t['take_profit_1']}")
            logger.info(f"    Bracket B: {t['qty_tp2']} shares → TP2 ${t['take_profit_2']}")

        logger.info(f"Would submit: {submitted} tickers ({submitted * 2} brackets) | Exposure: ${exposure:,.0f}")
        if skipped:
            logger.warning(f"Skipped (exposure limit): {', '.join(skipped)}")

        if submitted > 0:
            table, total_risk = _build_ticker_table(tickers, submitted_tickers)
            tg_msg = (
                f"📈 IFDS Trading Plan [DRY RUN] — {today_str}\n"
                f"{submitted} pozíció | Risk: ${total_risk:,.0f} | Exp: ${exposure:,.0f}\n\n"
                f"<pre>{table}</pre>\n\n"
                f"Submitted: {submitted} tickers ({submitted * 2} brackets)"
            )
            send_telegram(tg_msg)
            logger.info("Telegram sent.")
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

    for t in tickers:
        sym = t['symbol']

        # Skip if already has position/orders
        if sym in existing:
            logger.info(f"  Skipping {sym}: already has active position/orders")
            if evt:
                evt.log("submit", "existing_skip", ticker=sym)
            continue

        # Exposure check
        ticker_exposure = t['limit_price'] * t['total_qty']
        if exposure + ticker_exposure > MAX_DAILY_EXPOSURE:
            skipped.append(sym)
            logger.warning(f"[EXPOSURE LIMIT] Skipping {sym} — would exceed ${MAX_DAILY_EXPOSURE:,} daily limit")
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

        if evt:
            evt.log(
                "submit", "order_submitted", ticker=sym,
                qty=t['total_qty'], limit=t['limit_price'],
                sl=t['stop_loss'], tp1=t['take_profit_1'], tp2=t['take_profit_2'],
                bracket_a_qty=t['qty_tp1'], bracket_b_qty=t['qty_tp2'],
            )

        exposure += ticker_exposure
        submitted += 1
        submitted_tickers.append(sym)

        logger.info(f"  {sym}: {t['direction']} {t['total_qty']} @ ${t['limit_price']} | SL ${t['stop_loss']}")
        logger.info(f"    Bracket A: {t['qty_tp1']} shares → TP1 ${t['take_profit_1']}")
        logger.info(f"    Bracket B: {t['qty_tp2']} shares → TP2 ${t['take_profit_2']}")

    ib.sleep(3)  # Let orders propagate fully before final status check

    # --- Post-submission verification ---
    # MKT entry orders may fill instantly and disappear from openTrades(). A
    # ticker is considered successfully submitted if EITHER:
    #   - its entry orderRef (IFDS_{sym}_A or _B) is visible in openTrades(), OR
    #   - a position exists for the ticker in ib.positions() (instant fill)
    # A WARNING fires only when a ticker is missing from BOTH sources.
    try:
        ib_open_refs = {
            getattr(t.order, "orderRef", "")
            for t in ib.openTrades()
            if getattr(t.order, "orderRef", "").startswith("IFDS_")
        }
        ib_position_syms = {
            p.contract.symbol
            for p in ib.positions()
            if p.position != 0
        }

        missing_tickers = []
        for sym in submitted_tickers:
            has_open_order = (
                f"IFDS_{sym}_A" in ib_open_refs or f"IFDS_{sym}_B" in ib_open_refs
            )
            has_position = sym in ib_position_syms
            if not has_open_order and not has_position:
                missing_tickers.append(sym)

        if missing_tickers:
            logger.warning(
                f"POST-SUBMIT VERIFICATION: {len(missing_tickers)} tickers "
                f"NOT visible in IBKR (no open order, no position): "
                f"{sorted(missing_tickers)}"
            )
            if evt:
                evt.log(
                    "submit", "post_submit_missing_orders",
                    missing=sorted(missing_tickers),
                    expected=len(submitted_tickers),
                )
        else:
            logger.info(
                f"POST-SUBMIT VERIFICATION: all {len(submitted_tickers)} tickers "
                f"accounted for (open orders or filled positions)"
            )
    except Exception as e:
        logger.warning(f"POST-SUBMIT VERIFICATION failed: {e}")

    logger.info(f"Submitted: {submitted} tickers ({submitted * 2} brackets) | Exposure: ${exposure:,.0f}")
    if skipped:
        logger.warning(f"Skipped (exposure limit): {', '.join(skipped)}")

    # Telegram notification
    if submitted > 0:
        skipped_existing = [s for s in existing if s not in submitted_tickers] if existing else []
        table, total_risk = _build_ticker_table(
            [t for t in tickers if t['symbol'] in submitted_tickers],
            submitted_tickers,
        )
        tg_lines = [
            f"📈 IFDS Trading Plan — {today_str}",
            f"{submitted} pozíció | Risk: ${total_risk:,.0f} | Exp: ${exposure:,.0f}",
            "",
            f"<pre>{table}</pre>",
        ]
        if skipped_existing:
            tg_lines.append(f"\nSkip (existing): {', '.join(sorted(skipped_existing))}")
        if skipped:
            tg_lines.append(f"Skip (exposure): {', '.join(skipped)}")
        tg_lines.append(f"\nSubmitted: {submitted} tickers ({submitted * 2} brackets)")
        send_telegram("\n".join(tg_lines))

    # --- Monitor state initialization ---
    if submitted > 0:
        # Instant TP1 fill detection: with MKT entry, the entry may fill
        # above TP1 (e.g. NSA 2026-04-08: entry $40.45, TP1 $40.00). IBKR
        # triggers the child TP immediately, and the position enters the
        # monitor cycle with tp1_filled already true. Query today's fills
        # once and mark tickers whose IFDS_{sym}_A_TP or _B_TP is filled.
        instant_tp1_filled: set[str] = set()
        try:
            from ib_insync import ExecutionFilter
            todays_fills = ib.reqExecutions(
                ExecutionFilter(time=date.today().strftime('%Y%m%d') + ' 00:00:00')
            )
            for f in todays_fills:
                order_ref = getattr(f.execution, 'orderRef', '') or ''
                if order_ref.startswith('IFDS_') and (
                    order_ref.endswith('_A_TP') or order_ref.endswith('_B_TP')
                ):
                    # IFDS_{sym}_A_TP → sym
                    sym = order_ref[len('IFDS_'):].rsplit('_', 2)[0]
                    instant_tp1_filled.add(sym)
            if instant_tp1_filled:
                logger.info(
                    f"Instant TP1 fill detected on submit: "
                    f"{sorted(instant_tp1_filled)}"
                )
        except Exception as e:
            logger.warning(f"Instant TP fill detection failed: {e}")

        monitor_state = {}
        for t in [tk for tk in tickers if tk['symbol'] in submitted_tickers]:
            sym = t['symbol']
            monitor_state[sym] = {
                'entry_price': t['limit_price'],
                'sl_distance': round(t['limit_price'] - t['stop_loss'], 4),
                'tp1_price': t['take_profit_1'],
                'tp2_price': t['take_profit_2'],
                'stop_loss': t['stop_loss'],
                'total_qty': t['total_qty'],
                'qty_b': t['qty_tp2'],
                'tp1_filled': sym in instant_tp1_filled,
                'trail_active': False,
                'trail_scope': None,
                'trail_sl_current': None,
                'trail_high': None,
                'scenario_b_activated': False,
                'scenario_b_eligible': True,
                'breakeven_locked': False,

                'avwap_state': 'IDLE',
                'avwap_dipped': False,
                'avwap_last': None,
                'avwap_converted': False,
            }
        state_path = f'{LOG_DIR}/monitor_state_{today_str}.json'
        with open(state_path, 'w') as f:
            json.dump(monitor_state, f, indent=2)
        logger.info(f'Monitor state written: {state_path} ({len(monitor_state)} tickers)')

    disconnect(ib)


if __name__ == '__main__':
    main()
