"""FRL-3 registry lint tests — hypothesis-first enforced by machine."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import factors.base as fb  # noqa: E402
import frl_lint as lint  # noqa: E402

_FULL = """Status: {status}
Updated: 2026-07-21
Data-lane: v1
Attempt-family: A-0001..

# {hyp_id} — teszt hipotézis

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

Likviditás-nyújtás kompenzációja: a nem-informált nyomás túllövést okoz.

## Várt előjel és horizont

NEGATÍV IC, h=5.

## Ki a vesztes oldal / milyen frikció tartja fenn

Flow-chaser kereslet; inventory-kockázat tartja fenn.

## Költségprofil (várt turnover)

Magas turnover, half-life 2-4 nap.

## Pre-reg metrika és kill-kritérium

Spearman IC h=5; családi p >= 0.10 -> KILL.

## Eredmény (a batch tölti)

—
"""


def _write(
    tmp_path: Path, status: str = "REGISTERED", hyp_id: str = "HYP-004", body: str | None = None
) -> Path:
    path = tmp_path / f"{hyp_id}-test.md"
    path.write_text(body if body is not None else _FULL.format(status=status, hyp_id=hyp_id))
    return path


class TestFileLint:
    def test_complete_registered_file_passes(self, tmp_path):
        result = lint.lint_file(_write(tmp_path))
        assert result.ok, result.errors
        assert result.hyp_id == "HYP-004"
        assert result.status == "REGISTERED"

    def test_missing_mechanism_section_fails(self, tmp_path):
        body = _FULL.format(status="REGISTERED", hyp_id="HYP-004").replace(
            "Likviditás-nyújtás kompenzációja: a nem-informált nyomás túllövést okoz.", ""
        )
        result = lint.lint_file(_write(tmp_path, body=body))
        assert not result.ok
        assert any("Mechanizmus" in e for e in result.errors)

    def test_placeholder_section_counts_as_empty(self, tmp_path):
        body = _FULL.format(status="REGISTERED", hyp_id="HYP-004").replace(
            "Magas turnover, half-life 2-4 nap.", "<TODO>"
        )
        result = lint.lint_file(_write(tmp_path, body=body))
        assert any("Költségprofil" in e for e in result.errors)

    def test_draft_skips_section_checks_but_warns(self, tmp_path):
        body = "Status: DRAFT\nUpdated: 2026-07-21\nData-lane: v2\n\n# HYP-001b — váz\n"
        result = lint.lint_file(_write(tmp_path, hyp_id="HYP-001b", body=body))
        assert result.ok
        assert any("DRAFT" in w for w in result.warnings)

    def test_invalid_status_is_an_error(self, tmp_path):
        body = _FULL.format(status="MAYBE", hyp_id="HYP-004")
        assert any(
            "invalid Status" in e for e in lint.lint_file(_write(tmp_path, body=body)).errors
        )

    def test_missing_header_key_is_an_error(self, tmp_path):
        body = "Updated: 2026-07-21\nData-lane: v1\n\n# HYP-004 — x\n"
        assert any("Status" in e for e in lint.lint_file(_write(tmp_path, body=body)).errors)

    def test_missing_title_is_an_error(self, tmp_path):
        body = "Status: DRAFT\nUpdated: 2026-07-21\nData-lane: v1\n\n# Valami más\n"
        assert any("HYP-###" in e for e in lint.lint_file(_write(tmp_path, body=body)).errors)


class TestShadowGateGuard:
    """The guard is a flag, not a date — a date would open ~a month early."""

    def test_shadow_is_rejected_while_the_gate_flag_is_false(self, tmp_path):
        path = _write(tmp_path, status="SHADOW")
        result = lint.lint_file(path, today=date(2026, 7, 21))
        assert any("Day 63 gate" in e for e in result.errors)

    def test_passing_the_nyse_date_alone_does_not_open_the_gate(self, tmp_path, monkeypatch):
        """2026-08-17 is the 63rd NYSE day but NOT the gate event (§11.10)."""
        monkeypatch.setattr(lint.cfg, "DAY63_GATE_PASSED", False)
        path = _write(tmp_path, status="SHADOW")
        result = lint.lint_file(path, today=date(2026, 9, 30))
        assert not result.ok, "a later calendar date must not authorise SHADOW"

    def test_shadow_is_allowed_once_the_gate_flag_is_set(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint.cfg, "DAY63_GATE_PASSED", True)
        path = _write(tmp_path, status="SHADOW")
        result = lint.lint_file(path, today=date(2026, 7, 21))
        assert result.ok, result.errors

    def test_gate_flag_ships_closed(self):
        import frl_config

        assert frl_config.DAY63_GATE_PASSED is False


class TestTransitions:
    def test_draft_to_registered_is_legal(self):
        lint.check_transition("DRAFT", "REGISTERED")

    def test_draft_straight_to_promoted_is_illegal(self):
        with pytest.raises(ValueError, match="illegal transition"):
            lint.check_transition("DRAFT", "PROMOTED")

    def test_holdout_pass_requires_promoted(self):
        lint.check_transition("PROMOTED", "HOLDOUT-PASS")
        with pytest.raises(ValueError):
            lint.check_transition("TESTED", "HOLDOUT-PASS")

    def test_shadow_requires_holdout_pass(self):
        lint.check_transition("HOLDOUT-PASS", "SHADOW")
        with pytest.raises(ValueError):
            lint.check_transition("PROMOTED", "SHADOW")

    def test_killed_is_terminal(self):
        with pytest.raises(ValueError, match="terminal|illegal"):
            lint.check_transition("KILLED", "REGISTERED")


class TestAttemptGate:
    def test_registered_hypothesis_is_runnable(self, tmp_path):
        _write(tmp_path, status="REGISTERED")
        lint.assert_runnable("HYP-004", directory=tmp_path)

    def test_draft_hypothesis_blocks_the_attempt(self, tmp_path):
        body = "Status: DRAFT\nUpdated: 2026-07-21\nData-lane: v1\n\n# HYP-004 — váz\n"
        _write(tmp_path, body=body)
        with pytest.raises(lint.HypothesisNotRunnable, match="DRAFT"):
            lint.assert_runnable("HYP-004", directory=tmp_path)

    def test_unknown_hypothesis_blocks_the_attempt(self, tmp_path):
        with pytest.raises(lint.HypothesisNotRunnable, match="no registered hypothesis"):
            lint.assert_runnable("HYP-999", directory=tmp_path)

    def test_lint_error_blocks_even_a_registered_hypothesis(self, tmp_path):
        body = _FULL.format(status="REGISTERED", hyp_id="HYP-004").replace(
            "Spearman IC h=5; családi p >= 0.10 -> KILL.", "—"
        )
        _write(tmp_path, body=body)
        with pytest.raises(lint.HypothesisNotRunnable, match="fails lint"):
            lint.assert_runnable("HYP-004", directory=tmp_path)

    def test_tested_hypothesis_may_be_retested(self, tmp_path):
        _write(tmp_path, status="TESTED")
        lint.assert_runnable("HYP-004", directory=tmp_path)


class TestSanityPairRequirement:
    def setup_method(self):
        fb.clear_registry()

    def teardown_method(self):
        fb.clear_registry()

    def _factor(self, sign, compute):
        return fb.Factor(
            name="probe",
            hyp_id="HYP-004",
            data_lane="v1",
            expected_sign=sign,
            compute=compute,
            sanity_panel=fb.linear_sanity_panel("raw", sign=1),
        )

    def test_green_sanity_pair_passes(self):
        lint.assert_sanity_pair(self._factor(1, lambda panel: panel["raw"]))

    def test_missing_or_failing_sanity_pair_blocks_registration(self):
        with pytest.raises(lint.HypothesisNotRunnable, match="sanity"):
            lint.assert_sanity_pair(self._factor(1, lambda panel: -panel["raw"]))


class TestRealRegistry:
    """The checked-in hypothesis files must themselves stay lint-clean."""

    def test_all_registry_files_pass_lint(self):
        results = lint.lint_dir(today=date(2026, 7, 21))
        assert results, "no hypothesis files found"
        failures = [r.line() for r in results if not r.ok]
        assert not failures, failures

    def test_hyp_004_is_fully_written_even_while_draft(self):
        """Chat supplied the full content; only the REGISTERED flip is pending."""
        path = lint.HYPOTHESIS_DIR / "HYP-004-sector-relative-reversal.md"
        text = path.read_text()
        assert "Jegadeesh 1990" in text
        assert "expected_sign = -1" in text
        for section in lint.REQUIRED_SECTIONS:
            assert section in text
