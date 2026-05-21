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

EXECUTION_PLAN_DIR = "output"
LOG_DIR = "scripts/paper_trading/logs"
CUMULATIVE_PNL_FILE = "scripts/paper_trading/logs/cumulative_pnl.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

try:
    from lib.log_setup import setup_pt_logger

    logger = setup_pt_logger("submit")
except ModuleNotFoundError:
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("submit")

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
        sym = t["symbol"]
        risk = round((t["limit_price"] - t["stop_loss"]) * t["total_qty"], 2)
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
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_qty = int(row["quantity"])
            if total_qty < MIN_QUANTITY:
                logger.info(f"  Skipping {row['instrument_id']}: qty {total_qty} < {MIN_QUANTITY}")
                continue

            qty_tp1 = max(1, int(round(total_qty * SCALE_OUT_PCT)))
            qty_tp2 = total_qty - qty_tp1
            if qty_tp2 < 1:
                qty_tp2 = 1
                qty_tp1 = total_qty - 1

            tickers.append(
                {
                    "symbol": row["instrument_id"],
                    "direction": row["direction"],
                    "limit_price": float(row["limit_price"]),
                    "total_qty": total_qty,
                    "qty_tp1": qty_tp1,
                    "qty_tp2": qty_tp2,
                    "stop_loss": float(row["stop_loss"]),
                    "take_profit_1": float(row["take_profit_1"]),
                    "take_profit_2": float(row["take_profit_2"]),
                    "score": float(row["score"]),
                    "sector": row["sector"],
                }
            )
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
        pnl = data.get("cumulative_pnl", 0.0)
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
# Swing-mode entry (Task #4 — mental stop architecture)
# ---------------------------------------------------------------------------


def submit_swing_market_only(
    tickers,
    dry_run,
    today_str,
    cfg,
    state_file,
):
    """Submit market BUYs only and persist swing position state.

    Per Day 63 §3.12, the swing horizon replaces the IBKR bracket (BUY+SL+TP1)
    with a single market BUY. The mental stop/TP1/TP2 levels live in
    ``state/swing_positions.json`` and are evaluated by the daily EOD pt_monitor.
    """
    from ifds.state.swing_positions import (
        SwingPosition,
        load_swing_positions,
        save_swing_positions,
    )

    stop_mult = cfg.tuning.get("swing_mental_stop_atr_multiple", 2.0)

    # --- Reconstruct ATR per ticker from CSV's stop_loss (entry - stop_mult*ATR)
    # so the SwingPosition has a clean ATR for downstream trail math.
    def _atr_from_row(t):
        if stop_mult <= 0:
            return 0.0
        return (t["limit_price"] - t["stop_loss"]) / stop_mult

    existing_swings = {p.ticker: p for p in load_swing_positions(state_file)}

    if dry_run:
        logger.info("[DRY RUN — SWING] No IBKR connection")
        submitted_tickers = []
        new_state: list[SwingPosition] = list(existing_swings.values())
        for t in tickers:
            sym = t["symbol"]
            if sym in existing_swings:
                logger.info(f"  Skipping {sym}: already in swing state")
                continue
            atr = _atr_from_row(t)
            pos = SwingPosition(
                ticker=sym,
                entry_date=today_str,
                entry_price=t["limit_price"],
                atr=atr,
                stop_level=t["stop_loss"],
                tp1_level=t["take_profit_1"],
                tp2_level=t["take_profit_2"],
                qty=t["total_qty"],
                qty_remaining=t["total_qty"],
                sector=t.get("sector", ""),
                direction=t["direction"],
            )
            new_state.append(pos)
            submitted_tickers.append(sym)
            logger.info(
                f"  {sym}: MKT BUY {t['total_qty']} @ ~${t['limit_price']:.2f} "
                f"| stop ${pos.stop_level:.2f} | TP1 ${pos.tp1_level:.2f} "
                f"| TP2 ${pos.tp2_level:.2f}"
            )

        logger.info(f"[SWING DRY RUN] Would submit: {len(submitted_tickers)} tickers")
        return

    # --- Live swing submit ---
    from lib.connection import connect, get_account, disconnect
    from lib.heartbeat import touch as heartbeat_touch
    from ib_insync import MarketOrder

    heartbeat_touch("submit_attempt", label=today_str)
    # raise_on_exhaust=True so the outer orchestrator (lib.retry_orchestrator)
    # can catch IBKRConnectionExhausted and retry on a later cycle instead of
    # the legacy sys.exit(1) which made Day 3 Gateway-down requires manual
    # operator re-trigger. See docs/tasks/2026-05-21-submit-retry-storm.md.
    ib = connect(
        client_id=10,
        context_label="submit_orders.py (swing)",
        raise_on_exhaust=True,
    )
    account = get_account(ib)

    existing = get_existing_symbols(ib)
    if existing:
        logger.info(f"Existing IBKR positions/orders: {existing}")

    submitted_tickers = []
    new_state: list[SwingPosition] = list(existing_swings.values())

    for t in tickers:
        sym = t["symbol"]
        if sym in existing or sym in existing_swings:
            logger.info(f"  Skipping {sym}: already has position or swing state")
            if evt:
                evt.log("submit", "existing_skip", ticker=sym)
            continue

        from lib.orders import validate_contract

        contract = validate_contract(ib, sym)
        if not contract:
            logger.warning(f"  Skipping {sym}: contract not found in IBKR")
            continue

        # Single market BUY (no bracket).
        # Explicit tif='DAY' set short-circuits the IBKR paper-account preset
        # lookup (Workstation Configuration → Order Presets → Stocks → Default
        # TIF), which otherwise triggers "Error 10349, Order TIF was set to
        # DAY based on order preset" + a hard Cancel on the swing market-only
        # path. The legacy bracket builder (lib/orders.py) set tif='DAY'
        # explicitly, but the swing rewrite (`e887749`/`5dfab55`) omitted it.
        #
        # Note: tif='GTC' was tried first (16:05 Day 3) and silently failed
        # — GTC is only valid for limit orders; with MarketOrder the IBKR
        # paper account marked the trade PreSubmitted then cancelled it
        # after disconnect, creating a state/IBKR divergence. tif='DAY'
        # is the correct/native MarketOrder TIF.
        #
        # outsideRth=True keeps the order alive across the RTH boundary
        # if it doesn't fill immediately (defensive — at 15:31 CEST the
        # NYSE has been open ~1 min, the order should fill within seconds).
        order = MarketOrder(action="BUY", totalQuantity=t["total_qty"])
        order.account = account
        order.orderRef = f"IFDS_SWING_{sym}"
        order.tif = "DAY"
        order.outsideRth = True
        trade = ib.placeOrder(contract, order)
        ib.sleep(1.5)

        # Silent-reject check (paper account guard — see ifds-rules.md 2026-04-08)
        status = getattr(trade.orderStatus, "status", "")
        _VALID = {"PreSubmitted", "Submitted", "Filled", "PendingSubmit"}
        if status and status not in _VALID:
            logger.warning(
                f"{sym}: market BUY status={status} — silent reject possible. "
                f"trade.log={getattr(trade, 'log', [])}"
            )
            if evt:
                evt.log("submit", "swing_silent_reject", ticker=sym, status=status)
            continue

        atr = _atr_from_row(t)
        pos = SwingPosition(
            ticker=sym,
            entry_date=today_str,
            entry_price=t["limit_price"],
            atr=atr,
            stop_level=t["stop_loss"],
            tp1_level=t["take_profit_1"],
            tp2_level=t["take_profit_2"],
            qty=t["total_qty"],
            qty_remaining=t["total_qty"],
            sector=t.get("sector", ""),
            direction=t["direction"],
        )
        new_state.append(pos)
        submitted_tickers.append(sym)
        logger.info(
            f"  {sym}: MKT BUY {t['total_qty']} @ ~${t['limit_price']:.2f} "
            f"| stop ${pos.stop_level:.2f} | TP1 ${pos.tp1_level:.2f} "
            f"| TP2 ${pos.tp2_level:.2f}"
        )
        if evt:
            evt.log(
                "submit",
                "swing_order_submitted",
                ticker=sym,
                qty=t["total_qty"],
                entry=t["limit_price"],
                stop=pos.stop_level,
                tp1=pos.tp1_level,
                tp2=pos.tp2_level,
                atr=atr,
            )

    # Race-condition guard (Day 2 bug): the cron schedules submit_orders.py
    # and close_positions.py --mode=eod_flags both at 15:30. If we save state
    # here with 0 new submitted, we may overwrite a fresh state that
    # close_positions just wrote (e.g. EC TP1 partial). Only save when we
    # actually added a ticker; otherwise leave the state file untouched.
    if submitted_tickers:
        save_swing_positions(state_file, new_state)
        logger.info(
            f"[SWING] Submitted: {len(submitted_tickers)} tickers | "
            f"State: {state_file} ({len(new_state)} open)"
        )
    else:
        logger.info(
            f"[SWING] Submitted: 0 tickers — state file untouched "
            f"(race guard, {len(existing_swings)} open)"
        )

    # Telegram notification — always send (Task #T §3.2): a 0-submit case is
    # operatively meaningful ("submit ran, 3 existing skipped, no new entries")
    # and silence-by-success was the Day 1-2 confusion source.
    if submitted_tickers:
        lines = [
            f"📈 IFDS Swing Submit — {today_str}",
            f"{len(submitted_tickers)} pozíció | Total open: {len(new_state)}",
            "",
        ]
        for sym in submitted_tickers:
            t = next(t for t in tickers if t["symbol"] == sym)
            atr = _atr_from_row(t)
            lines.append(
                f"{sym}  qty {t['total_qty']}  @${t['limit_price']:.2f}  "
                f"SL ${t['stop_loss']:.2f}  ATR ${atr:.2f}"
            )
        send_telegram("\n".join(lines))
    else:
        # Heartbeat — 0 new entry case (mind already-position)
        existing_in_plan = [t["symbol"] for t in tickers if t["symbol"] in existing_swings]
        skipped_other = [
            t["symbol"]
            for t in tickers
            if t["symbol"] not in existing_swings and t["symbol"] not in submitted_tickers
        ]
        lines = [
            f"✓ IFDS Swing Submit — {today_str}",
            f"0 new entry | {len(existing_swings)} swing open",
        ]
        if existing_in_plan:
            lines.append(f"Skip (existing): {', '.join(existing_in_plan)}")
        if skipped_other:
            lines.append(f"Skip (other): {', '.join(skipped_other)}")
        lines.append(f"Next: 22:00 EOD eval | swing state: {len(existing_swings)} pos")
        send_telegram("\n".join(lines))

    disconnect(ib)
    heartbeat_touch(
        "submit_success",
        label=today_str,
        extra={"submitted_count": len(submitted_tickers), "mode": "swing"},
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    try:
        from lib.trading_day_guard import check_trading_day

        check_trading_day(logger)
    except ModuleNotFoundError:
        pass
    parser = argparse.ArgumentParser(description="IBKR Paper Trading — Submit Orders")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse CSV and show orders without connecting to IBKR",
    )
    parser.add_argument("--test-connection", action="store_true", help="Test IBKR connection only")
    parser.add_argument("--file", help="Specific execution plan CSV path")
    parser.add_argument(
        "--override-circuit-breaker",
        action="store_true",
        help="Override circuit breaker and submit orders anyway (use with caution)",
    )
    parser.add_argument(
        "--override-witching",
        action="store_true",
        help="Submit orders on Witching day (use with caution)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume mode: ignore the heartbeat STUCK alert and re-attempt "
            "submit. Operator triggers this after manual investigation of a "
            "stuck submit. Existing positions are automatically skipped via "
            "the state-aware deduplication."
        ),
    )
    args = parser.parse_args()

    today_str = date.today().strftime("%Y-%m-%d")
    logger.info(f"IFDS Paper Trading — {today_str}")

    # --- Test connection mode ---
    if args.test_connection:
        from lib.connection import connect, get_account, disconnect

        ib = connect(client_id=10)
        account = get_account(ib)
        summary = ib.accountSummary(account)
        for item in summary:
            if item.tag in ("NetLiquidation", "TotalCashValue", "BuyingPower"):
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
    for part in csv_stem.split("_"):
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
            ticker_exposure = t["limit_price"] * t["total_qty"]
            if exposure + ticker_exposure > MAX_DAILY_EXPOSURE:
                skipped.append(t["symbol"])
                logger.warning(
                    f"[EXPOSURE LIMIT] Skipping {t['symbol']} — would exceed ${MAX_DAILY_EXPOSURE:,} daily limit"
                )
                continue

            exposure += ticker_exposure
            submitted += 1
            submitted_tickers.append(t["symbol"])
            logger.info(
                f"  {t['symbol']}: {t['direction']} {t['total_qty']} @ ${t['limit_price']} | SL ${t['stop_loss']}"
            )
            logger.info(f"    Bracket A: {t['qty_tp1']} shares → TP1 ${t['take_profit_1']}")
            logger.info(f"    Bracket B: {t['qty_tp2']} shares → TP2 ${t['take_profit_2']}")

        logger.info(
            f"Would submit: {submitted} tickers ({submitted * 2} brackets) | Exposure: ${exposure:,.0f}"
        )
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

    # --- Swing-mode dispatch (Task #4) ---
    # When swing_execution_enabled=True (defaults.py TUNING), submit market BUYs
    # only and persist the new state/swing_positions.json. The legacy bracket
    # path (3 IBKR orders per ticker) is taken only when the flag is False.
    try:
        from ifds.config.loader import Config as _IFDSConfig

        _cfg = _IFDSConfig()
        _swing_mode = bool(_cfg.tuning.get("swing_execution_enabled", False))
        _swing_state_file = _cfg.tuning.get(
            "swing_positions_state_file",
            "state/swing_positions.json",
        )
    except Exception:
        _swing_mode = False
        _swing_state_file = "state/swing_positions.json"

    if _swing_mode:
        if args.resume:
            logger.info(
                "[RESUME] Manual resume mode — state-aware deduplication will "
                "skip already-open positions. Backoff cycle starts fresh."
            )
        # Outer retry orchestrator: handles the Day 3 (2026-05-20) Gateway-down
        # window by re-attempting submit_swing_market_only on later cycles.
        # State (swing_positions + IBKR positions) is reloaded inside the
        # submit callable on every attempt — no double-submit risk.
        from lib.retry_orchestrator import (
            IBKRSubmitOrchestrator,
            SubmitExhaustedError,
        )

        def _gateway_probe() -> bool:
            try:
                from lib.connection import connect, disconnect

                _probe_ib = connect(
                    client_id=17,  # check_gateway clientId
                    context_label="submit_orders.py gateway probe",
                    raise_on_exhaust=True,
                )
                disconnect(_probe_ib)
                return True
            except Exception:
                return False

        orchestrator = IBKRSubmitOrchestrator(
            submit_callable=submit_swing_market_only,
            gateway_check=_gateway_probe,
            telegram_notify=send_telegram,
        )
        try:
            orchestrator.submit_with_retry(
                tickers=tickers,
                dry_run=args.dry_run,
                today_str=today_str,
                cfg=_cfg,
                state_file=_swing_state_file,
            )
        except SubmitExhaustedError as exc:
            logger.error(
                f"[SUBMIT_EXHAUSTED] {exc}. "
                f"Operator notified via Telegram. Exiting with code 1."
            )
            sys.exit(1)
        return

    # --- Live mode (legacy bracket) ---
    from lib.connection import connect, get_account, disconnect
    from lib.orders import validate_contract, create_day_bracket, submit_bracket
    from lib.heartbeat import touch as heartbeat_touch

    heartbeat_touch("submit_attempt", label=today_str)
    ib = connect(client_id=10, context_label="submit_orders.py")
    account = get_account(ib)

    existing = get_existing_symbols(ib)
    if existing:
        logger.info(f"Existing positions/orders: {existing}")

    exposure = 0.0
    submitted = 0
    submitted_tickers = []
    skipped = []

    for t in tickers:
        sym = t["symbol"]

        # Skip if already has position/orders
        if sym in existing:
            logger.info(f"  Skipping {sym}: already has active position/orders")
            if evt:
                evt.log("submit", "existing_skip", ticker=sym)
            continue

        # Exposure check
        ticker_exposure = t["limit_price"] * t["total_qty"]
        if exposure + ticker_exposure > MAX_DAILY_EXPOSURE:
            skipped.append(sym)
            logger.warning(
                f"[EXPOSURE LIMIT] Skipping {sym} — would exceed ${MAX_DAILY_EXPOSURE:,} daily limit"
            )
            continue

        # Validate contract
        contract = validate_contract(ib, sym)
        if not contract:
            logger.warning(f"  Skipping {sym}: contract not found in IBKR")
            continue

        # Create and submit Bracket A (TP1)
        bracket_a = create_day_bracket(
            ib,
            contract,
            t["direction"],
            t["qty_tp1"],
            t["limit_price"],
            t["take_profit_1"],
            t["stop_loss"],
            account,
            tag_suffix=f"{sym}_A",
        )
        submit_bracket(ib, contract, bracket_a)

        # Create and submit Bracket B (TP2)
        bracket_b = create_day_bracket(
            ib,
            contract,
            t["direction"],
            t["qty_tp2"],
            t["limit_price"],
            t["take_profit_2"],
            t["stop_loss"],
            account,
            tag_suffix=f"{sym}_B",
        )
        submit_bracket(ib, contract, bracket_b)

        if evt:
            evt.log(
                "submit",
                "order_submitted",
                ticker=sym,
                qty=t["total_qty"],
                limit=t["limit_price"],
                sl=t["stop_loss"],
                tp1=t["take_profit_1"],
                tp2=t["take_profit_2"],
                bracket_a_qty=t["qty_tp1"],
                bracket_b_qty=t["qty_tp2"],
            )

        exposure += ticker_exposure
        submitted += 1
        submitted_tickers.append(sym)

        logger.info(
            f"  {sym}: {t['direction']} {t['total_qty']} @ ${t['limit_price']} | SL ${t['stop_loss']}"
        )
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
        ib_position_syms = {p.contract.symbol for p in ib.positions() if p.position != 0}

        missing_tickers = []
        for sym in submitted_tickers:
            has_open_order = f"IFDS_{sym}_A" in ib_open_refs or f"IFDS_{sym}_B" in ib_open_refs
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
                    "submit",
                    "post_submit_missing_orders",
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

    logger.info(
        f"Submitted: {submitted} tickers ({submitted * 2} brackets) | Exposure: ${exposure:,.0f}"
    )
    if skipped:
        logger.warning(f"Skipped (exposure limit): {', '.join(skipped)}")

    # Telegram notification
    if submitted > 0:
        skipped_existing = [s for s in existing if s not in submitted_tickers] if existing else []
        table, total_risk = _build_ticker_table(
            [t for t in tickers if t["symbol"] in submitted_tickers],
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
                ExecutionFilter(time=date.today().strftime("%Y%m%d") + " 00:00:00")
            )
            for f in todays_fills:
                order_ref = getattr(f.execution, "orderRef", "") or ""
                if order_ref.startswith("IFDS_") and (
                    order_ref.endswith("_A_TP") or order_ref.endswith("_B_TP")
                ):
                    # IFDS_{sym}_A_TP → sym
                    sym = order_ref[len("IFDS_") :].rsplit("_", 2)[0]
                    instant_tp1_filled.add(sym)
            if instant_tp1_filled:
                logger.info(
                    f"Instant TP1 fill detected on submit: " f"{sorted(instant_tp1_filled)}"
                )
        except Exception as e:
            logger.warning(f"Instant TP fill detection failed: {e}")

        monitor_state = {}
        for t in [tk for tk in tickers if tk["symbol"] in submitted_tickers]:
            sym = t["symbol"]
            monitor_state[sym] = {
                "entry_price": t["limit_price"],
                "sl_distance": round(t["limit_price"] - t["stop_loss"], 4),
                "tp1_price": t["take_profit_1"],
                "tp2_price": t["take_profit_2"],
                "stop_loss": t["stop_loss"],
                "total_qty": t["total_qty"],
                "qty_b": t["qty_tp2"],
                "tp1_filled": sym in instant_tp1_filled,
                "trail_active": False,
                "trail_scope": None,
                "trail_sl_current": None,
                "trail_high": None,
                "scenario_b_activated": False,
                "scenario_b_eligible": True,
                "breakeven_locked": False,
                "avwap_state": "IDLE",
                "avwap_dipped": False,
                "avwap_last": None,
                "avwap_converted": False,
            }
        state_path = f"{LOG_DIR}/monitor_state_{today_str}.json"
        with open(state_path, "w") as f:
            json.dump(monitor_state, f, indent=2)
        logger.info(f"Monitor state written: {state_path} ({len(monitor_state)} tickers)")

    disconnect(ib)
    heartbeat_touch("submit_success", label=today_str, extra={"submitted_count": submitted})


if __name__ == "__main__":
    main()
