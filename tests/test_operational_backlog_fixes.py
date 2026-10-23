"""The three production-path defects deferred on 2026-10-04 (operational backlog §2).

All three were diagnosed then and parked because the session was long and these touch
the live trading path. Trading has been halted since, so none of them produced a new
error — but none became moot either: each is a defect in the path that ANY future signal
family would run on, so they resolve only with a full shutdown, not with the null verdict.

* §2.3 — `pt_monitor --mode=eod_eval` dispatched BEFORE `check_trading_day()` and
  returned early, so it has always bypassed the NYSE-closed guard. The D8 work in
  October put `check_trading_enabled()` in front of the dispatch and deliberately left
  the older guard where it was, out of mandate; the code comment says so.
* §2.1 — `daily_metrics::exit_type` inferred the label from the TIME WINDOW a fill
  landed in, so a late fill (the 2026-08-21 outage pushed one 2h21m) degraded to "MOC".
  Window-conditional, not a general decay.
* §2.2 — the review's `sector_cap_proximity` flag measured CURRENT exposure against 25%,
  while the Phase 6 constraint is FORWARD-looking (`new_sector_total > sector_cap_usd`).
  On 2026-09-03 the flag stayed silent at 21.86% while the cap really did exclude
  candidates.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "paper_trading"))

PT_MONITOR = ROOT / "scripts" / "paper_trading" / "pt_monitor.py"


class TestTheEodEvalGuardOrder:
    """§2.3 — a non-trading day must stop eod_eval too, not only the 5-min loop."""

    def _main_body(self) -> list[ast.stmt]:
        tree = ast.parse(PT_MONITOR.read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        return main.body

    def _index_of_call(self, body: list[ast.stmt], name: str) -> int:
        for i, node in enumerate(body):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and getattr(sub.func, "id", None) == name:
                    return i
        return -1

    def _index_of_dispatch(self, body: list[ast.stmt]) -> int:
        for i, node in enumerate(body):
            if isinstance(node, ast.If):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and getattr(sub.func, "id", None) == "run_eod_eval":
                        return i
        return -1

    def test_check_trading_day_runs_before_the_mode_dispatch(self) -> None:
        body = self._main_body()
        guard = self._index_of_call(body, "check_trading_day")
        dispatch = self._index_of_dispatch(body)
        assert guard >= 0, "check_trading_day is not called in main() at all"
        assert dispatch >= 0, "the eod_eval dispatch disappeared — this guard is stale"
        assert guard < dispatch, (
            "check_trading_day still sits AFTER the mode dispatch, so --mode=eod_eval "
            "returns before reaching it and runs on NYSE holidays"
        )

    def test_check_trading_enabled_also_still_runs_before_the_dispatch(self) -> None:
        """The D8 guard must not regress while the older one moves."""
        body = self._main_body()
        assert 0 <= self._index_of_call(body, "check_trading_enabled") < self._index_of_dispatch(body)

    def test_neither_guard_is_duplicated_after_the_dispatch(self) -> None:
        """A guard that runs twice reads as defence; it is really a merge artefact."""
        source = PT_MONITOR.read_text()
        assert source.count("check_trading_day(logger)") == 1
        assert source.count("check_trading_enabled(logger)") == 1

    def test_the_stale_note_about_the_bypass_is_gone(self) -> None:
        source = PT_MONITOR.read_text()
        assert "has always bypassed the NYSE-closed guard" not in source, (
            "the comment documents a bypass that no longer exists"
        )


class TestExitTypeComesFromTheLedgerNotTheClock:
    """§2.1 — the label must survive a late fill.

    `_exit_type_from_fill_time` read the hour: 13-14 UTC meant TP1, 19-20 UTC meant the
    5-day TIME_STOP market-on-close, anything else fell through to "MOC". That is not a
    classification, it is an assumption about punctuality — and on 2026-08-21 an outage
    pushed a fill 2h21m late, so a real TIME_STOP was recorded as "MOC".

    `state/pending_exits/{date}.json` carries the exit_type the system itself decided
    when it submitted the order, keyed by ticker. That is the canonical answer, and it is
    the same invariant `signal_attribution` relies on. The clock stays as the fallback for
    fills with no ledger row (manual TWS exits, pre-ledger history), never as the primary.
    """

    def _ledger(self, tmp_path, rows):
        import json

        (tmp_path / "2026-08-21.json").write_text(json.dumps(rows))
        return tmp_path

    def test_a_late_fill_keeps_its_ledger_label(self, tmp_path) -> None:
        import daily_metrics as dm

        ledger = self._ledger(
            tmp_path,
            [{"ticker": "XPO", "exit_type": "TIME_STOP", "key": "XPO_TIME_STOP_2026-08-21"}],
        )
        # 22:01 UTC — 2h21m past the expected 19-20 UTC window, which is exactly the
        # 2026-08-21 outage shape. The clock-only classifier returned "MOC" here.
        label = dm.resolve_exit_type("XPO", "2026-08-21", fill_time_hour_utc=22, ledger_dir=ledger)
        assert label == "TIME_STOP"

    def test_the_clock_alone_would_have_got_it_wrong(self) -> None:
        """Pin the defect, so the regression is visible if anyone reverts the source."""
        import daily_metrics as dm

        assert dm._exit_type_from_fill_time_hour(22) == "MOC"

    def test_a_ticker_absent_from_the_ledger_falls_back_to_the_clock(self, tmp_path) -> None:
        """Manual TWS exits leave no ledger row; they must still get a best-effort label."""
        import daily_metrics as dm

        ledger = self._ledger(tmp_path, [{"ticker": "OTHER", "exit_type": "TP1"}])
        assert dm.resolve_exit_type("XPO", "2026-08-21", 13, ledger_dir=ledger) == "TP1"
        assert dm.resolve_exit_type("XPO", "2026-08-21", 22, ledger_dir=ledger) == "MOC"

    def test_a_missing_ledger_file_is_not_an_error(self, tmp_path) -> None:
        import daily_metrics as dm

        assert dm.resolve_exit_type("XPO", "2026-01-01", 19, ledger_dir=tmp_path) == "TIME_STOP_MOC"

    def test_every_ledger_label_maps_to_a_counter(self) -> None:
        """The ledger's vocabulary and the counter map must not drift apart.

        Measured across the 63 production ledger files: TP1, TP2, TIME_STOP, TRAIL_SL,
        MENTAL_SL. A label with no counter would silently fall to "moc_exits".
        """
        import daily_metrics as dm

        observed = {"TP1", "TP2", "TIME_STOP", "TRAIL_SL", "MENTAL_SL"}
        missing = sorted(observed - set(dm.EXIT_TYPE_TO_COUNTER))
        assert not missing, f"ledger exit_type with no counter mapping: {missing}"


class TestTheSectorCapFlagIsForwardLooking:
    """§2.2 — the flag has to ask the question the cap actually asks.

    `generate_review_data` flagged a sector when its CURRENT exposure crossed 25% of
    equity. Phase 6's constraint is a different question: `new_sector_total >
    sector_cap_usd` (phase6_sizing.py:1581) — it rejects a CANDIDATE whose notional would
    push the sector past 30%. On 2026-09-03 the flag stayed silent at 21.86% while the
    cap really was excluding candidates (04-risks §11.18), because a sector at 21.86% has
    only 8.14 points of headroom and the next position was bigger than that.

    So the fix is not a lower threshold — a threshold cannot express a forward-looking
    constraint. The flag has to compare the sector's REMAINING HEADROOM against the size
    of a position the system would actually open.
    """

    def _flag_for(self, module, *, sector_pct, equity=100_000.0, typical_pos_pct=0.10):
        return module.sector_cap_flag(
            sector="Technology",
            sector_notional=equity * sector_pct,
            equity=equity,
            typical_position_notional=equity * typical_pos_pct,
        )

    def test_the_2026_09_03_case_now_fires(self) -> None:
        """21.86% exposure, 30% cap: 8.14 points of headroom against a 10% position."""
        import generate_review_data as grd

        flag = self._flag_for(grd, sector_pct=0.2186)
        assert flag is not None, (
            "a sector with less headroom than one position is BINDING; the old "
            "current-exposure test called this quiet"
        )
        assert "headroom" in flag["detail"].lower()

    def test_a_sector_with_room_for_another_position_stays_quiet(self) -> None:
        import generate_review_data as grd

        assert self._flag_for(grd, sector_pct=0.10) is None

    def test_a_sector_already_over_the_cap_fires(self) -> None:
        import generate_review_data as grd

        flag = self._flag_for(grd, sector_pct=0.33)
        assert flag is not None and flag["priority"] == "P2"

    def test_the_boundary_is_the_cap_minus_one_position(self) -> None:
        """Exactly at the edge the sector can still take one more — just."""
        import generate_review_data as grd

        assert self._flag_for(grd, sector_pct=0.199) is None   # 10.1 pts headroom
        assert self._flag_for(grd, sector_pct=0.201) is not None  # 9.9 pts headroom

    def test_it_uses_the_same_cap_as_phase_6(self) -> None:
        """A review flag calibrated to a different number than the constraint it watches
        is worse than no flag: it reports on a rule nobody enforces."""
        import generate_review_data as grd

        sys.path.insert(0, str(ROOT / "src"))
        from ifds.config.defaults import TUNING

        assert grd.SECTOR_CAP_PCT == TUNING["swing_sector_cap_pct"]

    def test_zero_equity_is_not_a_division(self) -> None:
        import generate_review_data as grd

        assert grd.sector_cap_flag("Technology", 1000.0, 0.0, 10_000.0) is None
