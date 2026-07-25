"""FRL-2 ledger tests — PENDING-first invariant, rewrite-on-close, deflation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import frl_ledger as ledger  # noqa: E402


def _spec(variant="reversal_h5", hyp="HYP-004"):
    return ledger.AttemptSpec(
        hyp_id=hyp,
        variant=variant,
        data_lane="v1",
        dev_window={"swing": ["2026-05-18", "2026-06-22"]},
        n_days_used={"swing": 25},
        code_ref="factors/reversal.py@abc1234",
        horizon=5,
    )


class TestPendingFirstInvariant:
    def test_attempt_is_on_disk_before_any_result_exists(self, tmp_path):
        path = tmp_path / "attempt_ledger.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)

        entries = ledger.read_ledger(path)
        assert len(entries) == 1
        assert entries[0]["attempt_id"] == attempt_id
        assert entries[0]["decision"] == "PENDING"
        assert entries[0]["metrics"] == {}
        assert ledger.pending_attempts(path) == entries

    def test_ids_increment_from_the_ledger_itself(self, tmp_path):
        path = tmp_path / "l.jsonl"
        first = ledger.open_attempt(_spec("a"), path=path)
        second = ledger.open_attempt(_spec("b"), path=path)
        assert (first, second) == ("A-0001", "A-0002")

    def test_close_fills_metrics_on_the_same_line(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(
            attempt_id,
            metrics={"swing": {"mean_ic": 0.031, "p": 0.04}},
            decision="PROMOTE",
            decision_note="clears the swing bar",
            half_life_days=12.0,
            implied_turnover_cost_bps=401.0,
            path=path,
        )
        entries = ledger.read_ledger(path)
        assert len(entries) == 1  # updated, not appended
        assert entries[0]["decision"] == "PROMOTE"
        assert entries[0]["metrics"]["swing"]["p"] == 0.04
        assert entries[0]["closed_at"]
        assert ledger.pending_attempts(path) == []

    def test_close_keeps_a_backup_of_the_previous_state(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)

        backup = path.with_suffix(path.suffix + ".bak")
        assert backup.exists()
        assert json.loads(backup.read_text().splitlines()[0])["decision"] == "PENDING"

    def test_unknown_attempt_id_raises(self, tmp_path):
        path = tmp_path / "l.jsonl"
        ledger.open_attempt(_spec(), path=path)
        with pytest.raises(ValueError, match="not found"):
            ledger.close_attempt("A-9999", metrics={}, decision="KILL", path=path)

    def test_unknown_decision_raises(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        with pytest.raises(ValueError, match="unknown decision"):
            ledger.close_attempt(attempt_id, metrics={}, decision="LOOKS_GOOD", path=path)

    def test_killed_attempts_stay_in_the_ledger(self, tmp_path):
        """KILLs count toward the deflation denominator — they must not vanish."""
        path = tmp_path / "l.jsonl"
        for i in range(3):
            attempt_id = ledger.open_attempt(_spec(f"v{i}"), path=path)
            ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)
        assert len(ledger.read_ledger(path)) == 3


class TestSidakFamily:
    def test_single_variant_family_is_unchanged(self):
        assert ledger.sidak_family_p([0.04]) == pytest.approx(0.04)

    def test_four_variants_inflate_the_minimum(self):
        p = ledger.sidak_family_p([0.04, 0.30, 0.55, 0.80])
        assert p == pytest.approx(1 - 0.96**4)
        assert p > 0.04, "picking the best horizon must cost something"

    def test_empty_family_is_nan(self):
        import math

        assert math.isnan(ledger.sidak_family_p([]))


class TestBenjaminiHochberg:
    def test_known_vector_against_a_hand_computed_reference(self):
        # q=0.10, m=5: sorted p = .002 .012 .04 .30 .70
        # thresholds  = .02  .04  .06 .08 .10  -> largest rank meeting p<=thr is 3
        flags = ledger.benjamini_hochberg([0.30, 0.002, 0.70, 0.012, 0.04], q=0.10)
        assert flags == [False, True, False, True, True]

    def test_nothing_passes_when_all_are_weak(self):
        assert ledger.benjamini_hochberg([0.4, 0.5, 0.6], q=0.10) == [False] * 3

    def test_more_attempts_make_a_fixed_p_harder(self):
        few = ledger.benjamini_hochberg([0.03, 0.9], q=0.10)
        many = ledger.benjamini_hochberg([0.03] + [0.9] * 20, q=0.10)
        assert few[0] is True
        assert many[0] is False, "the ledger count must deflate the threshold"


class TestDeflate:
    def _closed(self, path, hyp, variant, metrics):
        attempt_id = ledger.open_attempt(_spec(variant, hyp), path=path)
        ledger.close_attempt(attempt_id, metrics=metrics, decision="KILL", path=path)

    def test_rows_are_per_family_and_era(self, tmp_path):
        path = tmp_path / "l.jsonl"
        self._closed(path, "HYP-004", "h1", {"swing": {"p": 0.5}, "legacy": {"p": 0.2}})
        self._closed(path, "HYP-004", "h5", {"swing": {"p": 0.02}, "legacy": {"p": 0.4}})
        rows = ledger.deflate(ledger.read_ledger(path))

        by_era = {r["era"]: r for r in rows}
        assert set(by_era) == {"swing", "legacy"}
        assert by_era["swing"]["n_variants"] == 2
        assert by_era["swing"]["p_family"] == pytest.approx(1 - 0.98**2)

    def test_pending_rows_are_excluded_from_deflation(self, tmp_path):
        path = tmp_path / "l.jsonl"
        ledger.open_attempt(_spec("open"), path=path)
        self._closed(path, "HYP-004", "h5", {"swing": {"p": 0.02}})
        rows = ledger.deflate(ledger.read_ledger(path))
        assert len(rows) == 1
        assert rows[0]["n_variants"] == 1

    def test_bonferroni_is_stricter_than_bh(self, tmp_path):
        path = tmp_path / "l.jsonl"
        # m=6 families, q=0.10 -> Bonferroni alpha = 0.0167; p=0.02 clears BH
        # (rank 2 threshold 0.033) but not Bonferroni.
        for i in range(6):
            self._closed(path, f"HYP-{i:03d}", "h5", {"swing": {"p": 0.02}})
        rows = ledger.deflate(ledger.read_ledger(path))
        assert all(r["bh_pass"] for r in rows)
        assert not any(r["bonferroni_pass"] for r in rows)


class TestDecisionProvenance:
    """Audit chain: an auto verdict is a default, never a human decision (spec §10)."""

    def test_auto_close_is_marked_unconfirmed(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        entry = ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)
        assert entry["decision_source"] == "auto"
        assert entry["human_confirmed"] is False

    def test_unconfirmed_decisions_are_listable(self, tmp_path):
        path = tmp_path / "l.jsonl"
        for i in range(3):
            attempt_id = ledger.open_attempt(_spec(f"v{i}"), path=path)
            ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)
        assert [e["attempt_id"] for e in ledger.unconfirmed_decisions(path)] == [
            "A-0001",
            "A-0002",
            "A-0003",
        ]

    def test_pending_rows_are_not_unconfirmed_decisions(self, tmp_path):
        """A PENDING row has no decision yet — it is a crash signal, not a backlog item."""
        path = tmp_path / "l.jsonl"
        ledger.open_attempt(_spec(), path=path)
        assert ledger.unconfirmed_decisions(path) == []

    def test_human_confirmation_records_who_and_when(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)

        entry = ledger.confirm_decision(attempt_id, by="Tamás", note="pre-reg (a)", path=path)
        assert entry["human_confirmed"] is True
        assert entry["decision_source"] == "human"
        assert entry["confirmed_by"] == "Tamás"
        assert entry["confirmed_at"]
        assert "pre-reg (a)" in entry["decision_note"]
        assert ledger.unconfirmed_decisions(path) == []

    def test_confirmation_may_override_the_auto_verdict(self, tmp_path):
        """The human decision wins — that is the point of the confirmation step."""
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)

        entry = ledger.confirm_decision(attempt_id, by="Tamás", decision="PARK", path=path)
        assert entry["decision"] == "PARK"
        assert entry["auto_decision"] == "KILL"
        assert entry["human_confirmed"] is True

    def test_confirming_a_pending_attempt_is_an_error(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        with pytest.raises(ValueError, match="PENDING"):
            ledger.confirm_decision(attempt_id, by="Tamás", path=path)

    def test_confirmation_keeps_a_backup(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)
        ledger.confirm_decision(attempt_id, by="Tamás", path=path)
        assert path.with_suffix(path.suffix + ".bak").exists()


class TestConfirmIdempotency:
    """Re-confirming must never corrupt the preserved machine verdict."""

    def test_double_override_keeps_the_original_auto_decision(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)

        # First override: KILL -> PARK, auto_decision snapshots KILL.
        ledger.confirm_decision(attempt_id, by="Tamás", decision="PARK", path=path)
        # Second confirm (accidental re-run): auto_decision must STILL be KILL.
        entry = ledger.confirm_decision(attempt_id, by="Tamás", decision="PARK", path=path)

        assert entry["auto_decision"] == "KILL", "re-confirm corrupted the machine verdict"
        assert entry["decision"] == "PARK"

    def test_reconfirming_without_override_preserves_auto_decision(self, tmp_path):
        path = tmp_path / "l.jsonl"
        attempt_id = ledger.open_attempt(_spec(), path=path)
        ledger.close_attempt(attempt_id, metrics={}, decision="KILL", path=path)
        ledger.confirm_decision(attempt_id, by="Tamás", decision="PARK", path=path)
        entry = ledger.confirm_decision(attempt_id, by="Tamás", path=path)  # no decision
        assert entry["auto_decision"] == "KILL"
        assert entry["decision"] == "PARK"
