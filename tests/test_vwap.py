"""Tests for VWAP module (BC20A Phase_20A_1).

Covers:
- calculate_vwap: correct calculation, zero volume, empty bars
- vwap_entry_check: REJECT, REDUCE, BOOST, NORMAL thresholds
- vwap_distance_pct: distance calculation
- Edge cases (zero VWAP, zero price)
"""

import pytest

from ifds.phases.vwap import (
    calculate_vwap,
    vwap_distance_pct,
    vwap_entry_check,
)


class TestCalculateVwap:

    def test_basic_calculation(self):
        """5 bars → correct VWAP."""
        bars = [
            {"h": 102.0, "l": 98.0, "c": 100.0, "v": 1000},  # tp = 100.0
            {"h": 103.0, "l": 99.0, "c": 101.0, "v": 2000},  # tp = 101.0
            {"h": 104.0, "l": 100.0, "c": 102.0, "v": 1500},  # tp = 102.0
        ]
        vwap = calculate_vwap(bars)
        # tp×vol: 100*1000 + 101*2000 + 102*1500 = 100000 + 202000 + 153000 = 455000
        # total vol: 1000 + 2000 + 1500 = 4500
        # VWAP = 455000 / 4500 = 101.1111...
        assert abs(vwap - 101.1111) < 0.001

    def test_zero_volume_bar_skipped(self):
        """Bars with volume=0 are ignored."""
        bars = [
            {"h": 100.0, "l": 98.0, "c": 99.0, "v": 1000},  # tp = 99.0
            {"h": 110.0, "l": 90.0, "c": 100.0, "v": 0},     # skipped
        ]
        vwap = calculate_vwap(bars)
        assert vwap == 99.0  # Only first bar counts

    def test_empty_bars(self):
        assert calculate_vwap([]) == 0.0

    def test_all_zero_volume(self):
        bars = [{"h": 100.0, "l": 98.0, "c": 99.0, "v": 0}]
        assert calculate_vwap(bars) == 0.0

    def test_single_bar(self):
        bars = [{"h": 102.0, "l": 98.0, "c": 100.0, "v": 5000}]
        vwap = calculate_vwap(bars)
        assert vwap == 100.0  # tp = (102+98+100)/3 = 100


class TestVwapEntryCheck:

    def test_reject_above_2_pct(self):
        """Price 3% above VWAP → REJECT."""
        assert vwap_entry_check(103.0, 100.0) == "REJECT"

    def test_reduce_above_1_pct(self):
        """Price 1.5% above VWAP → REDUCE."""
        assert vwap_entry_check(101.5, 100.0) == "REDUCE"

    def test_boost_below_neg1_pct(self):
        """Price 2% below VWAP → BOOST."""
        assert vwap_entry_check(98.0, 100.0) == "BOOST"

    def test_normal_at_vwap(self):
        """Price at VWAP → NORMAL."""
        assert vwap_entry_check(100.0, 100.0) == "NORMAL"

    def test_normal_within_1pct(self):
        """Price 0.5% above VWAP → NORMAL."""
        assert vwap_entry_check(100.5, 100.0) == "NORMAL"

    def test_zero_vwap_normal(self):
        """VWAP=0 → NORMAL (no data)."""
        assert vwap_entry_check(100.0, 0.0) == "NORMAL"

    def test_zero_price_normal(self):
        assert vwap_entry_check(0.0, 100.0) == "NORMAL"

    def test_custom_thresholds(self):
        """Custom reject/reduce/boost thresholds."""
        # 5% above, reject at 3% → REJECT
        assert vwap_entry_check(105.0, 100.0, reject_pct=3.0) == "REJECT"
        # 5% above, reject at 6%, reduce at 4% → REDUCE
        assert vwap_entry_check(105.0, 100.0, reject_pct=6.0, reduce_pct=4.0) == "REDUCE"

    def test_exact_boundary_reject(self):
        """Price exactly at reject boundary → REJECT (>2%)."""
        assert vwap_entry_check(102.01, 100.0) == "REJECT"

    def test_exact_boundary_reduce(self):
        """Price exactly at reduce boundary edge."""
        # 1.01% above → REDUCE
        assert vwap_entry_check(101.01, 100.0) == "REDUCE"


class TestVwapDistancePct:

    def test_above_vwap(self):
        assert vwap_distance_pct(102.0, 100.0) == 2.0

    def test_below_vwap(self):
        assert vwap_distance_pct(98.0, 100.0) == -2.0

    def test_at_vwap(self):
        assert vwap_distance_pct(100.0, 100.0) == 0.0

    def test_zero_vwap(self):
        assert vwap_distance_pct(100.0, 0.0) == 0.0
