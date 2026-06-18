"""Freeze-safety unit proof for uw_gex_fetch_enabled (2026-06-18).

The flag, when False, builds a Polygon-only GEX provider (skips the UW
greek-exposure call). This is output-invariant because, empirically, UW
greek-exposure returns None for 100% of tickers (429 / no data — verified over
92 days by scripts/analysis/verify_gex_uw_invariance.py, source=uw==0). These
tests prove the *mathematical* core of that invariance at the provider level:
when the UW primary returns None, FallbackGEXProvider(UW, Polygon) is identical
to Polygon alone — so disabling the UW primary changes nothing.
"""

from __future__ import annotations

from ifds.config.defaults import TUNING
from ifds.data.adapters import FallbackGEXProvider, GEXProvider


class _StubProvider(GEXProvider):
    def __init__(self, name: str, result: dict | None):
        self._name = name
        self._result = result

    def get_gex(self, ticker: str) -> dict | None:
        return self._result

    def provider_name(self) -> str:
        return self._name


def test_flag_default_is_true():
    """Default must keep the legacy UW→Polygon chain (no silent behavior flip)."""
    assert TUNING["uw_gex_fetch_enabled"] is True


def test_uw_none_fallback_equals_polygon_only():
    """When UW returns None (the realized 100%-429 regime), the fallback chain's
    output is identical to Polygon-only → disabling the UW primary is invariant."""
    polygon_out = {"net_gex": 248545.0, "zero_gamma": 19.0, "source": "polygon_calculated"}
    uw_none = _StubProvider("uw", None)
    polygon = _StubProvider("polygon", polygon_out)

    fallback = FallbackGEXProvider(uw_none, polygon)
    polygon_only = polygon

    for t in ("VNO", "NNN", "JAZZ", "ROIV"):
        assert fallback.get_gex(t) == polygon_only.get_gex(t) == polygon_out


def test_uw_none_and_polygon_none_both_default():
    """When both return None (the no-data POSITIVE-default case), on/off agree —
    both yield None → caller defaults to POSITIVE either way (UW-independent)."""
    fallback = FallbackGEXProvider(_StubProvider("uw", None), _StubProvider("polygon", None))
    assert fallback.get_gex("X") is None


def test_uw_success_is_the_only_case_that_differs():
    """Sanity: the flag matters ONLY when UW *succeeds* — which never happens in
    practice (source=uw==0 over 92 days). This documents why the flip is safe."""
    uw_out = {"net_gex": 999.0, "source": "uw"}
    polygon_out = {"net_gex": 111.0, "source": "polygon_calculated"}
    fallback = FallbackGEXProvider(
        _StubProvider("uw", uw_out), _StubProvider("polygon", polygon_out)
    )
    # UW success → fallback returns UW (differs from Polygon-only). This is the
    # ONLY divergent case, and it is empirically empty.
    assert fallback.get_gex("X") == uw_out
    assert fallback.get_gex("X") != polygon_out
