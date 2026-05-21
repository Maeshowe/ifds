"""Tests for SEC EDGAR 10-Q / 10-K filing exclusion module.

Real schema verified against AAPL (CIK 0000320193) on 2026-05-16.
Fixture: tests/fixtures/sec_edgar_aapl_submissions.json (parallel-array layout).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ifds.data.sec_edgar import (
    SEC_BASE_URL,
    SEC_TICKERS_URL,
    SecEdgarClient,
    SecEdgarError,
    predict_next_10q_date,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def aapl_submissions() -> dict:
    return json.loads((FIXTURES / "sec_edgar_aapl_submissions.json").read_text())


@pytest.fixture
def company_tickers() -> dict:
    return json.loads((FIXTURES / "sec_edgar_company_tickers.json").read_text())


@pytest.fixture
def temp_cache(tmp_path: Path) -> Path:
    return tmp_path / "sec_cache"


@pytest.fixture
def fixed_user_agent(monkeypatch) -> str:
    ua = "IFDS-Test test@example.com"
    monkeypatch.setenv("IFDS_SEC_EDGAR_USER_AGENT", ua)
    return ua


# ---------------------------------------------------------------------------
# predict_next_10q_date — pure function
# ---------------------------------------------------------------------------


def _filings_from_fixture(payload: dict) -> list[dict]:
    """Convert SEC parallel-array payload to list[dict] for tests."""
    recent = payload["filings"]["recent"]
    return [
        {
            "form": recent["form"][i],
            "filingDate": recent["filingDate"][i],
            "reportDate": recent["reportDate"][i],
            "accessionNumber": recent["accessionNumber"][i],
        }
        for i in range(len(recent["form"]))
    ]


def test_predict_next_10q_quarterly_cycle(aapl_submissions):
    """Last 10-Q filingDate + 90 days = predicted next 10-Q."""
    filings = _filings_from_fixture(aapl_submissions)
    predicted, tolerance = predict_next_10q_date(filings)
    # AAPL last 10-Q: 2026-05-01 → predicted 2026-07-30
    assert predicted.date() == date(2026, 7, 30)
    assert tolerance == 10


def test_predict_next_10q_no_history_raises():
    """No 10-Q in history → cannot predict."""
    filings = [{"form": "4", "filingDate": "2026-05-01", "reportDate": "", "accessionNumber": "x"}]
    with pytest.raises(SecEdgarError, match="no 10-Q history"):
        predict_next_10q_date(filings)


def test_predict_next_10q_picks_most_recent():
    """Even with multiple 10-Qs out of order, the most recent filingDate wins."""
    filings = [
        {
            "form": "10-Q",
            "filingDate": "2025-08-01",
            "reportDate": "2025-06-28",
            "accessionNumber": "a",
        },
        {
            "form": "10-Q",
            "filingDate": "2026-01-30",
            "reportDate": "2025-12-27",
            "accessionNumber": "b",
        },
        {
            "form": "10-Q",
            "filingDate": "2025-05-02",
            "reportDate": "2025-03-29",
            "accessionNumber": "c",
        },
    ]
    predicted, _ = predict_next_10q_date(filings)
    # 2026-01-30 + 90 days = 2026-04-30
    assert predicted.date() == date(2026, 4, 30)


# ---------------------------------------------------------------------------
# has_upcoming_10q_or_10k — window logic (-tolerance ... lookahead)
# ---------------------------------------------------------------------------


def _client_with_mock_filings(
    cache_dir: Path,
    ua: str,
    filings_by_ticker: dict[str, list[dict]],
    ticker_to_cik: dict[str, str] | None = None,
) -> SecEdgarClient:
    """Build a client with mocked fetch methods and an in-memory cik map."""
    client = SecEdgarClient(cache_dir=cache_dir, user_agent=ua)
    client._cik_map = ticker_to_cik or {t: f"{i:010d}" for i, t in enumerate(filings_by_ticker, 1)}
    client.get_recent_filings = MagicMock(
        side_effect=lambda t: filings_by_ticker.get(t.upper(), [])
    )
    return client


def test_has_upcoming_within_lookahead(temp_cache, fixed_user_agent):
    """Predicted 10-Q in 5 days, lookahead 10 → exclude."""
    today = datetime.now(timezone.utc).date()
    last_10q_date = today - timedelta(days=85)  # predicted = today + 5
    filings = [
        {
            "form": "10-Q",
            "filingDate": last_10q_date.isoformat(),
            "reportDate": "",
            "accessionNumber": "x",
        }
    ]
    client = _client_with_mock_filings(temp_cache, fixed_user_agent, {"FAKE": filings})
    assert client.has_upcoming_10q_or_10k("FAKE", lookahead_days=10) is True


def test_has_upcoming_outside_lookahead(temp_cache, fixed_user_agent):
    """Predicted 10-Q in 25 days, lookahead 10, tolerance 10 → don't exclude."""
    today = datetime.now(timezone.utc).date()
    last_10q_date = today - timedelta(days=65)  # predicted = today + 25
    filings = [
        {
            "form": "10-Q",
            "filingDate": last_10q_date.isoformat(),
            "reportDate": "",
            "accessionNumber": "x",
        }
    ]
    client = _client_with_mock_filings(temp_cache, fixed_user_agent, {"FAKE": filings})
    assert client.has_upcoming_10q_or_10k("FAKE", lookahead_days=10) is False


def test_has_upcoming_negative_tolerance_recent_filing(temp_cache, fixed_user_agent):
    """Predicted 5 days ago (filing just happened): still within -tolerance...lookahead → exclude."""
    today = datetime.now(timezone.utc).date()
    last_10q_date = today - timedelta(days=95)  # predicted = today - 5
    filings = [
        {
            "form": "10-Q",
            "filingDate": last_10q_date.isoformat(),
            "reportDate": "",
            "accessionNumber": "x",
        }
    ]
    client = _client_with_mock_filings(temp_cache, fixed_user_agent, {"FAKE": filings})
    assert client.has_upcoming_10q_or_10k("FAKE", lookahead_days=10) is True


def test_has_upcoming_too_far_past_no_exclude(temp_cache, fixed_user_agent):
    """Last 10-Q 200 days ago → predicted 110 days past → outside window → don't exclude."""
    today = datetime.now(timezone.utc).date()
    last_10q_date = today - timedelta(days=200)
    filings = [
        {
            "form": "10-Q",
            "filingDate": last_10q_date.isoformat(),
            "reportDate": "",
            "accessionNumber": "x",
        }
    ]
    client = _client_with_mock_filings(temp_cache, fixed_user_agent, {"FAKE": filings})
    assert client.has_upcoming_10q_or_10k("FAKE", lookahead_days=10) is False


def test_has_upcoming_no_filings_returns_false(temp_cache, fixed_user_agent):
    """Empty filings (unknown ticker, fail-open) → False (don't exclude)."""
    client = _client_with_mock_filings(temp_cache, fixed_user_agent, {})
    assert client.has_upcoming_10q_or_10k("UNKNOWN", lookahead_days=10) is False


# ---------------------------------------------------------------------------
# AGNC retroactive validation — the case the rule was built for
# ---------------------------------------------------------------------------


def test_agnc_2026_05_04_excluded_retroactively(temp_cache, fixed_user_agent):
    """AGNC 2026-05-04: last 10-Q 2026-02-03, predicted 2026-05-04. From 2026-05-04 it's 0 days → exclude."""
    filings = [
        {
            "form": "10-Q",
            "filingDate": "2026-02-03",
            "reportDate": "2025-12-31",
            "accessionNumber": "agnc-q1",
        }
    ]
    client = _client_with_mock_filings(temp_cache, fixed_user_agent, {"AGNC": filings})

    # Simulate "today = 2026-05-04" by freezing time inside has_upcoming
    with patch("ifds.data.sec_edgar.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 5, 4, tzinfo=timezone.utc)
        # Keep real datetime constructor for predict_next_10q parsing
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mock_dt.strptime = datetime.strptime
        assert client.has_upcoming_10q_or_10k("AGNC", lookahead_days=10) is True


# ---------------------------------------------------------------------------
# CIK map — cache + refresh
# ---------------------------------------------------------------------------


def test_cik_map_resolves_ticker(temp_cache, fixed_user_agent, company_tickers):
    """ticker → zero-padded 10-digit CIK string."""
    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    # Inject the map manually (skip network)
    client._cik_map = {
        row["ticker"].upper(): f"{row['cik_str']:010d}" for row in company_tickers.values()
    }

    assert client.ticker_to_cik("AAPL") == "0000320193"
    assert client.ticker_to_cik("AGNC") == "0001467373"
    assert client.ticker_to_cik("UNKNOWN_TICKER") is None


def test_cik_map_uses_cache_when_fresh(temp_cache, fixed_user_agent, company_tickers):
    """30-day cache: a fresh on-disk cache prevents HTTP call."""
    cik_map_path = temp_cache / "cik_map.json"
    cik_map_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_updated": datetime.now(timezone.utc).isoformat(),
        "map": {
            row["ticker"].upper(): f"{row['cik_str']:010d}" for row in company_tickers.values()
        },
    }
    cik_map_path.write_text(json.dumps(payload))

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    with patch.object(client, "_fetch_cik_map_remote") as mock_fetch:
        client._load_or_fetch_cik_map()
        mock_fetch.assert_not_called()
    assert client._cik_map["AAPL"] == "0000320193"


def test_cik_map_refresh_on_stale(temp_cache, fixed_user_agent):
    """31-day-old cache → refetch."""
    cik_map_path = temp_cache / "cik_map.json"
    cik_map_path.parent.mkdir(parents=True, exist_ok=True)
    stale_ts = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    cik_map_path.write_text(json.dumps({"_updated": stale_ts, "map": {"OLD": "0000000001"}}))

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    with patch.object(
        client, "_fetch_cik_map_remote", return_value={"AAPL": "0000320193"}
    ) as mock_fetch:
        client._load_or_fetch_cik_map()
        mock_fetch.assert_called_once()
    assert client._cik_map == {"AAPL": "0000320193"}


# ---------------------------------------------------------------------------
# Filings cache — 1d TTL + fail-open fallback
# ---------------------------------------------------------------------------


def test_filings_cache_hit_when_fresh(temp_cache, fixed_user_agent, aapl_submissions):
    """Fresh filings cache prevents fetch."""
    cache_file = temp_cache / "filings" / "0000320193.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "_updated": datetime.now(timezone.utc).isoformat(),
                "data": aapl_submissions,
            }
        )
    )

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    client._cik_map = {"AAPL": "0000320193"}

    with patch.object(client, "_http_get_json") as mock_get:
        filings = client.get_recent_filings("AAPL")
        mock_get.assert_not_called()
    # 33 historical 10-Qs in the fixture
    assert sum(1 for f in filings if f["form"] == "10-Q") == 33


def test_filings_cache_refresh_on_stale(temp_cache, fixed_user_agent, aapl_submissions):
    """2-day-old cache → fetch fresh."""
    cache_file = temp_cache / "filings" / "0000320193.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    stale_ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    cache_file.write_text(
        json.dumps({"_updated": stale_ts, "data": {"filings": {"recent": {"form": []}}}})
    )

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    client._cik_map = {"AAPL": "0000320193"}

    with patch.object(client, "_http_get_json", return_value=aapl_submissions) as mock_get:
        filings = client.get_recent_filings("AAPL")
        mock_get.assert_called_once()
    assert any(f["form"] == "10-Q" for f in filings)


def test_filings_fail_open_when_api_down_and_cache_stale(temp_cache, fixed_user_agent):
    """API fail + cache >2d → return [] (fail-open) without raising."""
    cache_file = temp_cache / "filings" / "0000320193.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    stale_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    cache_file.write_text(
        json.dumps({"_updated": stale_ts, "data": {"filings": {"recent": {"form": []}}}})
    )

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    client._cik_map = {"AAPL": "0000320193"}

    with patch.object(client, "_http_get_json", side_effect=SecEdgarError("503")):
        filings = client.get_recent_filings("AAPL")
    assert filings == []


def test_filings_fail_open_when_api_down_uses_2d_cache(
    temp_cache, fixed_user_agent, aapl_submissions
):
    """API fail + cache <=2d → return cached data."""
    cache_file = temp_cache / "filings" / "0000320193.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    age_ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    cache_file.write_text(json.dumps({"_updated": age_ts, "data": aapl_submissions}))

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    client._cik_map = {"AAPL": "0000320193"}

    # First call: API fails. Should fall back to 2d cache.
    with patch.object(client, "_http_get_json", side_effect=SecEdgarError("503")):
        filings = client.get_recent_filings("AAPL")
    assert any(f["form"] == "10-Q" for f in filings)


# ---------------------------------------------------------------------------
# Rate limit + User-Agent header
# ---------------------------------------------------------------------------


def test_user_agent_header_sent(temp_cache, fixed_user_agent, aapl_submissions):
    """SEC requires User-Agent header on every request."""
    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)

    with patch("ifds.data.sec_edgar.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = aapl_submissions
        mock_get.return_value = mock_resp
        client._http_get_json(f"{SEC_BASE_URL}/submissions/CIK0000320193.json")

    headers = mock_get.call_args.kwargs["headers"]
    assert headers["User-Agent"] == fixed_user_agent


def test_rate_limit_sleep_between_calls(
    temp_cache, fixed_user_agent, aapl_submissions, monkeypatch
):
    """Successive calls should sleep at least RATE_LIMIT_SLEEP (10 req/sec cap)."""
    import time as _time

    client = SecEdgarClient(cache_dir=temp_cache, user_agent=fixed_user_agent)
    sleeps: list[float] = []
    monkeypatch.setattr("ifds.data.sec_edgar.time.sleep", lambda s: sleeps.append(s))

    with patch("ifds.data.sec_edgar.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = aapl_submissions
        mock_get.return_value = mock_resp
        client._http_get_json("https://example/a")
        client._http_get_json("https://example/b")

    # At least one sleep between requests, with the documented cap
    assert any(s >= 0.10 for s in sleeps), sleeps


def test_user_agent_default_warns_when_unset(temp_cache, monkeypatch, caplog):
    """Construction without env var → WARNING log."""
    monkeypatch.delenv("IFDS_SEC_EDGAR_USER_AGENT", raising=False)
    import logging

    with caplog.at_level(logging.WARNING, logger="ifds.data.sec_edgar"):
        SecEdgarClient(cache_dir=temp_cache)
    assert any("IFDS_SEC_EDGAR_USER_AGENT" in r.message for r in caplog.records)
