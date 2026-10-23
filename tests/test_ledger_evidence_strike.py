"""Striking a verdict from the EVIDENCE tally without touching the verdict itself.

The 2026-10-23 §4 step 2. Five attempts (A-0019..A-0023, HYP-007 funda) were measured on
a factor whose inputs were structurally empty: roe, debt_equity and net_margin were
non-null in 0 of 16,425 ticker-days, so 4 of the 6 funda branches could never fire. Those
KILL verdicts are not evidence about the DESIGNED funda factor — they are the fourth
occurrence of the house's "X feature nem prediktív over structurally empty inputs" class.

Two rules shape the mechanism, and they pull against each other:

* the verdict must NOT change and the attempt must NOT be re-run. Re-running after seeing
  the result is garden-of-forking-paths, and the house rule says existing ledger rows stay
  on their original verdicts;
* but a tally that keeps counting them as evidence about the funda block is wrong.

So the strike is an ADDITIVE annotation — `evidence_status` — and the multiplicity tally
excludes struck rows while the audit chain keeps every original field intact.

The idempotency requirement is not theoretical: `confirm_decision` once corrupted
`auto_decision` by being called twice on one row, erasing the fact that a human had
changed a KILL to a PARK. Every confirm-shaped operation here must survive being run twice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import frl_ledger as ledger  # noqa: E402

REASON = "funda inputs structurally empty (0/16425 non-null) — 04-risks §6.7"


@pytest.fixture
def a_ledger(tmp_path):
    rows = [
        {
            "attempt_id": "A-0019", "hyp_id": "HYP-007", "data_lane": "v1", "horizon": 1,
            "decision": "KILL", "human_confirmed": True, "decision_source": "human",
            "decision_note": "original note",
            "metrics": {"swing": {"p_value": 0.74, "ic_mean": 0.0015}},
        },
        {
            "attempt_id": "A-0013", "hyp_id": "HYP-006", "data_lane": "v1", "horizon": 5,
            "decision": "KILL", "human_confirmed": True,
            "metrics": {"swing": {"p_value": 0.62, "ic_mean": -0.0011}},
        },
    ]
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def _row(path, attempt_id):
    return next(r for r in ledger.read_ledger(path) if r["attempt_id"] == attempt_id)


class TestTheStrikeAnnotatesAndNeverRewrites:
    def test_it_records_the_strike_with_its_reason(self, a_ledger) -> None:
        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        row = _row(a_ledger, "A-0019")
        assert row["evidence_status"] == "struck"
        assert REASON in row["evidence_strike_reason"]
        assert row["evidence_struck_by"] == "Tamás"
        assert row["evidence_struck_at"]

    def test_the_verdict_itself_is_untouched(self, a_ledger) -> None:
        """The whole point: strike the EVIDENCE, not the record of what was decided."""
        before = _row(a_ledger, "A-0019")
        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        after = _row(a_ledger, "A-0019")
        for field in ("decision", "human_confirmed", "decision_source", "metrics", "horizon"):
            assert after[field] == before[field], f"{field} was modified by the strike"

    def test_the_original_note_survives(self, a_ledger) -> None:
        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        assert "original note" in _row(a_ledger, "A-0019")["decision_note"]

    def test_it_leaves_every_other_row_alone(self, a_ledger) -> None:
        before = _row(a_ledger, "A-0013")
        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        assert _row(a_ledger, "A-0013") == before


class TestItSurvivesBeingRunTwice:
    """`confirm_decision` was corrupted exactly this way by a cross-session double call."""

    def test_a_second_strike_changes_nothing(self, a_ledger) -> None:
        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        first = _row(a_ledger, "A-0019")
        ledger.strike_from_evidence("A-0019", reason="a different reason", by="someone else", path=a_ledger)
        second = _row(a_ledger, "A-0019")
        assert second == first, (
            "the strike must be idempotent: the first reason and attributor are the "
            "record, and a later call must not overwrite them"
        )

    def test_an_unknown_attempt_raises(self, a_ledger) -> None:
        with pytest.raises(ValueError, match="not found"):
            ledger.strike_from_evidence("A-9999", reason=REASON, by="Tamás", path=a_ledger)

    def test_a_strike_needs_a_reason(self, a_ledger) -> None:
        with pytest.raises(ValueError, match="reason"):
            ledger.strike_from_evidence("A-0019", reason="  ", by="Tamás", path=a_ledger)


class TestTheTallyExcludesStruckRows:
    def test_a_struck_family_drops_out_of_the_multiplicity_correction(self, a_ledger) -> None:
        """BH's m must not count evidence the project has disowned."""
        before = {(r["hyp_id"], r["era"]) for r in ledger.deflate(ledger.read_ledger(a_ledger))}
        assert ("HYP-007", "swing") in before

        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        after = {(r["hyp_id"], r["era"]) for r in ledger.deflate(ledger.read_ledger(a_ledger))}
        assert ("HYP-007", "swing") not in after
        assert ("HYP-006", "swing") in after, "an untouched family must stay in the tally"

    def test_the_rows_are_still_readable_and_still_say_KILL(self, a_ledger) -> None:
        """Excluded from the TALLY is not erased from the LEDGER."""
        ledger.strike_from_evidence("A-0019", reason=REASON, by="Tamás", path=a_ledger)
        row = _row(a_ledger, "A-0019")
        assert row["decision"] == "KILL"
        assert row["metrics"]["swing"]["p_value"] == 0.74


class TestTheProductionLedger:
    def test_exactly_the_five_funda_attempts_are_struck(self) -> None:
        """A-0019..A-0023 and nothing else. 18 of 23 verdicts stand."""
        rows = ledger.read_ledger()
        struck = {r["attempt_id"] for r in rows if r.get("evidence_status") == "struck"}
        assert struck == {"A-0019", "A-0020", "A-0021", "A-0022", "A-0023"}, (
            f"expected the five HYP-007 rows, got {sorted(struck)}"
        )
        assert all(r["hyp_id"] == "HYP-007" for r in rows if r["attempt_id"] in struck)

    def test_every_struck_row_still_carries_its_original_verdict(self) -> None:
        rows = ledger.read_ledger()
        for row in rows:
            if row.get("evidence_status") == "struck":
                assert row["decision"] == "KILL"
                assert row.get("human_confirmed") is True

    def test_the_other_eighteen_are_untouched(self) -> None:
        rows = ledger.read_ledger()
        intact = [r for r in rows if r.get("evidence_status") != "struck"]
        assert len(intact) == 18
        assert not any("evidence_strike_reason" in r for r in intact)
