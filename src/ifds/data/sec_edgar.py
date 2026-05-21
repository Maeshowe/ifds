"""SEC EDGAR client — 10-Q / 10-K filing exclusion for Phase 2 universe.

Real API schema (verified 2026-05-16):
    GET https://data.sec.gov/submissions/CIK{cik_10}.json
    -> {filings: {recent: {form: [...], filingDate: [...], reportDate: [...],
                           accessionNumber: [...]}}}
    Filings are stored as PARALLEL ARRAYS, not list-of-dicts.

Schema rules:
    - CIK is zero-padded 10-digit string in the URL ("0000320193")
    - The tickers→CIK file (https://www.sec.gov/files/company_tickers.json)
      stores integer cik_str; we zero-pad on load
    - reportDate may be empty string for non-periodic filings
    - User-Agent header is MANDATORY (rate-limit / rejection otherwise)
    - 10 req/sec rate cap → 0.11s sleep between calls

Failure mode (Tamás 2026-05-15):
    1. Fetch fresh from API
    2. On error: fall back to local cache if <= 2 days old
    3. Cache miss / stale: return [] (fail-open) and log WARNING
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


SEC_BASE_URL = "https://data.sec.gov"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
RATE_LIMIT_SLEEP = 0.11  # 10 req/sec cap
DEFAULT_QUARTERLY_DAYS = 90
DEFAULT_TOLERANCE_DAYS = 10
USER_AGENT_ENV = "IFDS_SEC_EDGAR_USER_AGENT"
USER_AGENT_PLACEHOLDER = "IFDS-Trading <set IFDS_SEC_EDGAR_USER_AGENT env>"

# Filing forms considered binary-event for swing exclusion
EXCLUDED_FORMS = frozenset({"10-Q", "10-K"})


class SecEdgarError(RuntimeError):
    """Raised on SEC EDGAR HTTP / parsing failure."""


def predict_next_10q_date(
    filings: list[dict],
    quarterly_days: int = DEFAULT_QUARTERLY_DAYS,
    tolerance_days: int = DEFAULT_TOLERANCE_DAYS,
) -> tuple[datetime, int]:
    """Estimate next 10-Q filing date from the most recent 10-Q.

    Args:
        filings: list of {form, filingDate, reportDate, accessionNumber}.
        quarterly_days: cycle length (default 90).
        tolerance_days: ± uncertainty applied symmetrically.

    Returns:
        (predicted_datetime_utc, tolerance_days)

    Raises:
        SecEdgarError: if no 10-Q history is available.
    """
    ten_q = [f for f in filings if f.get("form") == "10-Q" and f.get("filingDate")]
    if not ten_q:
        raise SecEdgarError("no 10-Q history available")

    latest = max(ten_q, key=lambda f: f["filingDate"])
    last_date = datetime.strptime(latest["filingDate"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    predicted = last_date + timedelta(days=quarterly_days)
    return predicted, tolerance_days


def _flatten_recent_filings(payload: dict) -> list[dict]:
    """Convert SEC parallel-array structure → list[dict]."""
    recent = payload.get("filings", {}).get("recent") or {}
    forms = recent.get("form") or []
    filing_dates = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    accession = recent.get("accessionNumber") or []
    n = len(forms)
    return [
        {
            "form": forms[i],
            "filingDate": filing_dates[i] if i < len(filing_dates) else "",
            "reportDate": report_dates[i] if i < len(report_dates) else "",
            "accessionNumber": accession[i] if i < len(accession) else "",
        }
        for i in range(n)
    ]


class SecEdgarClient:
    """SEC EDGAR client with per-ticker filing cache and fail-open semantics."""

    def __init__(
        self,
        cache_dir: Path | str,
        user_agent: str | None = None,
        cik_refresh_days: int = 30,
        filings_refresh_days: int = 1,
        stale_fallback_days: int = 2,
        quarterly_days: int = DEFAULT_QUARTERLY_DAYS,
        tolerance_days: int = DEFAULT_TOLERANCE_DAYS,
    ):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        (self._cache_dir / "filings").mkdir(parents=True, exist_ok=True)

        self._user_agent = user_agent or os.getenv(USER_AGENT_ENV, USER_AGENT_PLACEHOLDER)
        if USER_AGENT_PLACEHOLDER in self._user_agent:
            logger.warning(
                "%s not configured — SEC EDGAR requests may be rate-limited or rejected. "
                "Set env var to 'Your Name your.email@example.com' format.",
                USER_AGENT_ENV,
            )

        self._cik_refresh_days = cik_refresh_days
        self._filings_refresh_days = filings_refresh_days
        self._stale_fallback_days = stale_fallback_days
        self._quarterly_days = quarterly_days
        self._tolerance_days = tolerance_days

        self._cik_map: dict[str, str] = {}
        self._last_request_ts = 0.0

    # ------------------------------------------------------------------ HTTP

    def _http_get_json(self, url: str) -> dict | list:
        """GET with mandatory User-Agent + rate-limit sleep."""
        delta = time.monotonic() - self._last_request_ts
        if delta < RATE_LIMIT_SLEEP:
            time.sleep(RATE_LIMIT_SLEEP - delta)
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
                timeout=10,
            )
            self._last_request_ts = time.monotonic()
        except requests.RequestException as exc:
            raise SecEdgarError(f"network error: {exc}") from exc

        if resp.status_code != 200:
            raise SecEdgarError(f"HTTP {resp.status_code} for {url}")
        try:
            return resp.json()
        except ValueError as exc:
            raise SecEdgarError(f"invalid JSON from {url}") from exc

    # ----------------------------------------------------------- CIK mapping

    def _cik_map_path(self) -> Path:
        return self._cache_dir / "cik_map.json"

    def _fetch_cik_map_remote(self) -> dict[str, str]:
        """Fetch the SEC ticker→CIK file and normalize to {TICKER: '0000xxxxxxxx'}."""
        raw = self._http_get_json(SEC_TICKERS_URL)
        if not isinstance(raw, dict):
            raise SecEdgarError("unexpected company_tickers payload shape")
        out: dict[str, str] = {}
        for row in raw.values():
            ticker = str(row.get("ticker", "")).upper()
            cik_int = row.get("cik_str")
            if not ticker or cik_int is None:
                continue
            out[ticker] = f"{int(cik_int):010d}"
        return out

    def _load_or_fetch_cik_map(self) -> dict[str, str]:
        path = self._cik_map_path()
        if path.exists():
            try:
                payload = json.loads(path.read_text())
                updated = datetime.fromisoformat(payload["_updated"])
                age = datetime.now(timezone.utc) - updated
                if age.days < self._cik_refresh_days:
                    self._cik_map = dict(payload["map"])
                    return self._cik_map
            except (KeyError, ValueError, OSError) as exc:
                logger.warning("CIK map cache unreadable (%s) — refetching", exc)

        try:
            fresh = self._fetch_cik_map_remote()
        except SecEdgarError as exc:
            # Fall back to whatever stale cache we have (if any)
            if path.exists():
                try:
                    payload = json.loads(path.read_text())
                    logger.warning("SEC tickers fetch failed (%s) — using stale CIK map cache", exc)
                    self._cik_map = dict(payload.get("map") or {})
                    return self._cik_map
                except (KeyError, ValueError, OSError):
                    pass
            logger.warning("SEC tickers fetch failed and no cache available: %s", exc)
            self._cik_map = {}
            return self._cik_map

        payload = {
            "_updated": datetime.now(timezone.utc).isoformat(),
            "map": fresh,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, path)
        self._cik_map = fresh
        return self._cik_map

    def ticker_to_cik(self, ticker: str) -> str | None:
        if not self._cik_map:
            self._load_or_fetch_cik_map()
        return self._cik_map.get(ticker.upper())

    # ----------------------------------------------------------- filings I/O

    def _filings_cache_path(self, cik: str) -> Path:
        return self._cache_dir / "filings" / f"{cik}.json"

    def _read_filings_cache(self, cik: str) -> tuple[list[dict] | None, timedelta | None]:
        """Return (flat_filings_or_None, age_or_None)."""
        path = self._filings_cache_path(cik)
        if not path.exists():
            return None, None
        try:
            payload = json.loads(path.read_text())
            updated = datetime.fromisoformat(payload["_updated"])
            age = datetime.now(timezone.utc) - updated
            data = payload.get("data") or {}
            return _flatten_recent_filings(data), age
        except (KeyError, ValueError, OSError) as exc:
            logger.warning("filings cache unreadable for %s (%s)", cik, exc)
            return None, None

    def _write_filings_cache(self, cik: str, data: dict) -> None:
        path = self._filings_cache_path(cik)
        tmp = path.with_suffix(".tmp")
        payload = {"_updated": datetime.now(timezone.utc).isoformat(), "data": data}
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, path)

    def get_recent_filings(self, ticker: str) -> list[dict]:
        """Return list of {form, filingDate, reportDate, accessionNumber}.

        Caches per-CIK for `filings_refresh_days` (default 1). On API failure,
        falls back to a cache up to `stale_fallback_days` (default 2) old,
        otherwise returns [] (fail-open).
        """
        cik = self.ticker_to_cik(ticker)
        if cik is None:
            logger.debug("no CIK for ticker %s — returning empty filings", ticker)
            return []

        cached, age = self._read_filings_cache(cik)
        if cached is not None and age is not None and age.days < self._filings_refresh_days:
            return cached

        url = f"{SEC_BASE_URL}/submissions/CIK{cik}.json"
        try:
            data = self._http_get_json(url)
            if not isinstance(data, dict):
                raise SecEdgarError("submissions payload not a dict")
            self._write_filings_cache(cik, data)
            return _flatten_recent_filings(data)
        except SecEdgarError as exc:
            if cached is not None and age is not None and age.days <= self._stale_fallback_days:
                logger.info(
                    "SEC EDGAR fallback to %d-day-old cache for %s (%s)",
                    age.days,
                    ticker,
                    exc,
                )
                return cached
            logger.warning(
                "SEC EDGAR API failed for %s and cache stale (age=%s) — fail-open",
                ticker,
                age,
            )
            return []

    # --------------------------------------------------------------- domain

    def has_upcoming_10q_or_10k(self, ticker: str, lookahead_days: int = 10) -> bool:
        """True if a 10-Q (or, by quarterly proxy, a 10-K) is predicted within
        the [-tolerance, +lookahead] window from today (UTC).

        Fail-open: empty filings list (unknown ticker, API down + stale cache)
        returns False — do NOT exclude the ticker.
        """
        filings = self.get_recent_filings(ticker)
        if not filings:
            return False

        try:
            predicted, tolerance = predict_next_10q_date(
                filings,
                quarterly_days=self._quarterly_days,
                tolerance_days=self._tolerance_days,
            )
        except SecEdgarError:
            return False

        now = datetime.now(timezone.utc)
        days_until = (predicted - now).days
        return -tolerance <= days_until <= lookahead_days


__all__: list[str] = [
    "SEC_BASE_URL",
    "SEC_TICKERS_URL",
    "SecEdgarClient",
    "SecEdgarError",
    "predict_next_10q_date",
    "EXCLUDED_FORMS",
    "USER_AGENT_ENV",
]
