"""Financial Modeling Prep (FMP) API client.

Provides: Company screener (fundamentals), earnings calendar, insider trading.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from typing import Any, TYPE_CHECKING
from urllib.parse import urlencode

from ifds.data.base import BaseAPIClient
from ifds.models.market import APIHealthResult

if TYPE_CHECKING:
    from ifds.data.cache import FileCache


#: Days after quarter end before a 13F quarter is treated as reportable. The statutory
#: deadline is 45 days; filings keep arriving afterwards, so the extra margin is what
#: separates "the quarter closed" from "the tally is in". Probed 2026-10-23 on the
#: 2026-Q3 (Sep-30) summary, 23 days after quarter end: AAPL -96.78%, MSFT -96.06%,
#: NVDA -97.20% QoQ — a partial tally that would have stamped `decreasing` on the whole
#: universe. The same probe on 2026-Q2: AAPL +18.85%, MSFT +4.69%, NVDA +20.10%.
FILING_LAG_DAYS = 75

#: A quarter is also rejected when its filer count is far below the previous quarter's,
#: whatever the calendar says. Belt and braces against a vendor backfill arriving late.
MIN_FILER_COVERAGE = 0.80


def latest_complete_13f_quarter(today: date | None = None) -> tuple[int, int]:
    """The newest ``(year, quarter)`` whose 13F filings can be considered complete."""
    today = today or date.today()
    year, quarter = today.year, (today.month - 1) // 3 + 1
    for _ in range(8):  # walk back at most two years; the loop always exits on the first
        quarter -= 1
        if quarter == 0:
            year, quarter = year - 1, 4
        quarter_end = date(year, quarter * 3, 1) + timedelta(days=31)
        quarter_end = date(quarter_end.year, quarter_end.month, 1) - timedelta(days=1)
        if (today - quarter_end).days >= FILING_LAG_DAYS:
            return year, quarter
    return year, quarter


def is_complete_13f_row(row: dict) -> bool:
    """Reject a summary row whose filer count betrays a half-filed quarter."""
    if not row:
        return False
    current = row.get("investorsHolding") or 0
    previous = row.get("lastInvestorsHolding") or 0
    if not row.get("totalInvested") or not row.get("lastTotalInvested"):
        return False
    if previous <= 0:
        return False
    return (current / previous) >= MIN_FILER_COVERAGE


#: The CBOE volatility index, as FMP spells it. Named so the symbol cannot drift between
#: the quote route and the EOD route.
VIX_SYMBOL = "^VIX"

class FMPClient(BaseAPIClient):
    """Client for FMP REST API.

    Endpoints used:
    - /stable/company-screener — Fundamental screening
    - /stable/earnings-calendar — Earnings dates
    - /stable/insider-trading/search — Insider transactions
    - /stable/key-metrics — Key financial metrics (TTM)
    - /stable/financial-growth — Revenue/EPS growth rates
    """

    HEALTH_CHECK_ENDPOINT = "/stable/company-screener"

    def __init__(
        self,
        api_key: str,
        timeout: int = 10,
        max_retries: int = 3,
        cache: FileCache | None = None,
        circuit_breaker=None,
    ):
        super().__init__(
            base_url="https://financialmodelingprep.com",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="fmp",
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _health_check_params(self) -> dict[str, Any]:
        return {"apikey": self._api_key, "limit": 1, "marketCapMoreThan": 1_000_000_000_000}

    def check_health(self) -> APIHealthResult:
        """Check FMP API connectivity."""
        return self.health_check(self.HEALTH_CHECK_ENDPOINT, is_critical=True)

    def screener(self, params: dict[str, Any]) -> list[dict] | None:
        """Run the company screener with given filters.

        Args:
            params: Screener filter parameters (marketCapMoreThan, etc.)

        Returns:
            List of company dicts matching filters, or None on failure.
        """
        query = {"apikey": self._api_key, **params}
        # Debug: log the full request URL (redact API key)
        debug_params = {k: v for k, v in query.items() if k != "apikey"}
        url = f"{self._base_url}{self.HEALTH_CHECK_ENDPOINT}?{urlencode(debug_params)}"
        print(f"  [FMP SCREENER] {url}", file=sys.stderr)
        return self._get(self.HEALTH_CHECK_ENDPOINT, params=query, headers=self._auth_headers())

    def get_earnings_calendar(self, from_date: str, to_date: str) -> list[dict] | None:
        """Get earnings calendar for a date range.

        Args:
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
        """
        cache_date = f"{from_date}_{to_date}"
        if self._cache:
            cached = self._cache.get("fmp", "earnings-calendar", cache_date, "ALL")
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "from": from_date, "to": to_date}
        result = self._get("/stable/earnings-calendar", params=params, headers=self._auth_headers())
        if result and self._cache:
            self._cache.put("fmp", "earnings-calendar", cache_date, "ALL", result)
        return result

    def get_insider_trading(self, ticker: str) -> list[dict] | None:
        """Get insider trading transactions for a ticker."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "insider-trading", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 50}
        result = self._get(
            "/stable/insider-trading/search", params=params, headers=self._auth_headers()
        )
        if result and self._cache:
            self._cache.put("fmp", "insider-trading", yesterday, ticker, result)
        return result

    def get_key_metrics(self, ticker: str) -> dict | None:
        """Trailing-twelve-month ratios for the fundamental block.

        ``/stable/ratios-ttm``, NOT ``/stable/key-metrics``. The scorer reads
        ``netProfitMarginTTM``, ``debtToEquityRatioTTM``, ``interestCoverageRatioTTM`` and
        derives ROE from ``netIncomePerShareTTM`` / ``shareholdersEquityPerShareTTM`` —
        every one of those lives here and NONE of them exists on ``key-metrics``, which
        carries ``returnOnEquity`` and no debt or coverage fields at all. The old call
        returned HTTP 200 and the scorer read None: 0 of 16,425 ticker-days had a non-null
        roe, debt_equity or net_margin. Live schema probed 2026-10-23.

        One call replaces one call, so the Phase 4 request rate is unchanged.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "ratios-ttm", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker}
        result = self._get("/stable/ratios-ttm", params=params, headers=self._auth_headers())
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "ratios-ttm", yesterday, ticker, result[0])
            return result[0]
        return None

    def get_sector_mapping(self, limit: int = 10000) -> dict[str, str]:
        """Get ticker→sector mapping from FMP screener.

        Single API call. Returns {ticker: fmp_sector_name}.
        Cached via FileCache if available.

        .. versionchanged:: 2026-10-20
           Two measured fixes, same root cause as the universe screener
           (docs/review/2026-10-20-screener-intraday-volume-bug.md):

           * ``avgVolumeMoreThan`` replaces ``volumeMoreThan``. FMP's ``volume`` is
             TODAY'S PARTIAL intraday volume, so the mapping's membership used to
             depend on the time of day the phase ran.
           * ``limit`` 3000 -> 10000. The old call returned exactly 3000 rows, i.e.
             it was ALWAYS truncated at the limit, so which names got a sector
             depended on the screener's ordering. Measured after both fixes: 5006
             rows, no truncation. Sector feeds Phase 3 breadth and the sector caps,
             so a silently truncated mapping is not a cosmetic problem.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "sector-mapping", yesterday, "ALL")
            if cached is not None:
                return cached

        params = {
            "marketCapMoreThan": 500_000_000,
            "avgVolumeMoreThan": 100_000,
            "limit": limit,
        }
        result = self.screener(params)
        if not result:
            return {}

        mapping = {r["symbol"]: r["sector"] for r in result if r.get("symbol") and r.get("sector")}

        if mapping and self._cache:
            self._cache.put("fmp", "sector-mapping", yesterday, "ALL", mapping)
        return mapping

    def get_institutional_ownership(self, ticker: str) -> list[dict] | None:
        """13F position summary for ``ticker``: this quarter and the previous one.

        ``institutional-ownership/latest`` SILENTLY IGNORES ``?symbol=`` and returns the
        market-wide filing feed — probed 2026-10-23 with ``symbol=AAPL`` it answered
        "RUBICON ADVISORS, GP" and "AMANAH HOLDINGS TRUST", with no ``totalInvested``
        field anywhere. That is why ``inst_ownership_score`` was 0 in all 16,425
        production ticker-days. ``symbol-positions-summary`` is the per-symbol route and
        carries ``totalInvested`` AND ``lastTotalInvested`` in a single row, so the QoQ
        comparison no longer needs two rows.

        Returns a one-element list to keep the caller's availability probe (``is None``)
        meaningful, or None when the quarter is not yet complete.
        """
        year, quarter = latest_complete_13f_quarter()
        cache_key = f"{ticker}_{year}Q{quarter}"
        if self._cache:
            cached = self._cache.get("fmp", "inst-positions-summary", f"{year}Q{quarter}", cache_key)
            if cached is not None:
                return cached

        params = {
            "apikey": self._api_key,
            "symbol": ticker,
            "year": year,
            "quarter": quarter,
        }
        result = self._get(
            "/stable/institutional-ownership/symbol-positions-summary",
            params=params,
            headers=self._auth_headers(),
        )
        if not result or not isinstance(result, list):
            return None
        row = result[0]
        if not is_complete_13f_row(row):
            return None
        if self._cache:
            self._cache.put("fmp", "inst-positions-summary", f"{year}Q{quarter}", cache_key, [row])
        return [row]

    def get_index_quote(self, symbol: str = VIX_SYMBOL) -> dict | None:
        """Live index quote. ``price`` is intraday; ``previousClose`` is the official D-1.

        Live schema probed 2026-10-23: price 20.24, previousClose 19.03 — and 19.03 is
        exactly the official CBOE close for 10-22, so ``previousClose`` is a free,
        already-final value. ``price`` is NOT: it moves all session.
        """
        result = self._get(
            "/stable/quote",
            params={"apikey": self._api_key, "symbol": symbol},
            headers=self._auth_headers(),
        )
        if result and isinstance(result, list) and result:
            return result[0]
        return None

    def get_index_eod(self, symbol: str, from_date: str, to_date: str) -> list[dict] | None:
        """Daily index bars.

        ⚠️ This route serves a LIVE, MUTATING bar for the current session — it is not
        close-only. Probed 2026-10-23 minutes apart: close 20.10, then 20.35, while
        Polygon said 20.51. Any caller wanting the day's CLOSE must apply a finality
        guard on the clock; presence of a bar proves nothing.
        """
        return self._get(
            "/stable/historical-price-eod/full",
            params={
                "apikey": self._api_key,
                "symbol": symbol,
                "from": from_date,
                "to": to_date,
            },
            headers=self._auth_headers(),
        )

    def get_etf_holdings(self, etf_symbol: str) -> list[dict] | None:
        """Get ETF constituent holdings.

        FMP endpoint: /stable/etf/holdings?symbol={ETF}
        Returns list of holding dicts with 'symbol', 'weightPercentage', etc.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "etf-holdings", yesterday, etf_symbol)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": etf_symbol}
        result = self._get("/stable/etf/holdings", params=params, headers=self._auth_headers())
        if result and self._cache:
            self._cache.put("fmp", "etf-holdings", yesterday, etf_symbol, result)
        return result

    def get_next_earnings_date(self, ticker: str) -> str | None:
        """Get the next upcoming earnings date for a ticker from FMP.

        Uses /stable/earnings?symbol={ticker} endpoint (ticker-specific,
        more reliable than bulk /stable/earnings-calendar for ADRs).

        Returns:
            Date string 'YYYY-MM-DD' of next earnings, or None if not found.
        """
        today = date.today().isoformat()

        params = {"apikey": self._api_key, "symbol": ticker}
        result = self._get("/stable/earnings", params=params, headers=self._auth_headers())

        if not result or not isinstance(result, list):
            return None

        # Find the next upcoming earnings date (date >= today, epsActual is null)
        upcoming = [
            entry
            for entry in result
            if entry.get("date", "") >= today and entry.get("epsActual") is None
        ]

        if not upcoming:
            # Fallback: first entry with date >= today regardless of epsActual
            upcoming = [entry for entry in result if entry.get("date", "") >= today]

        if not upcoming:
            return None

        # Return earliest upcoming date
        return min(upcoming, key=lambda e: e["date"])["date"]

    def get_price_target_consensus(self, ticker: str) -> dict | None:
        """Get analyst consensus price target.

        Returns dict with: targetConsensus, targetHigh, targetLow, etc.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "price-target-consensus", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker}
        result = self._get(
            "/stable/price-target-consensus", params=params, headers=self._auth_headers()
        )
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "price-target-consensus", yesterday, ticker, result[0])
            return result[0]
        return None

    def get_earnings_history(self, ticker: str, n_quarters: int = 4) -> list[dict] | None:
        """Get the last *n* quarters of reported earnings (actuals only).

        FMP's ``/stable/earnings`` returns past + upcoming quarters mixed.
        Upcoming entries have ``epsActual=None``; this helper filters them
        out and returns the last ``n_quarters`` actual reports, newest first.

        Returns list of ``{"date", "epsActual", "epsEstimated", ...}`` or None
        on fetch failure.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "earnings-history", yesterday, ticker)
            if cached is not None:
                return cached[:n_quarters]

        params = {"apikey": self._api_key, "symbol": ticker}
        result = self._get("/stable/earnings", params=params, headers=self._auth_headers())
        if not result or not isinstance(result, list):
            return None

        actuals = [entry for entry in result if isinstance(entry.get("epsActual"), (int, float))]
        if self._cache:
            self._cache.put("fmp", "earnings-history", yesterday, ticker, actuals)
        return actuals[:n_quarters]

    def get_recent_grades(self, ticker: str, limit: int = 10) -> list[dict] | None:
        """Get recent analyst grade changes for a ticker.

        Returns list of ``{"date", "action", "gradingCompany",
        "newGrade", "previousGrade"}`` or None on fetch failure.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "grades", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": limit}
        result = self._get("/stable/grades", params=params, headers=self._auth_headers())
        if not result or not isinstance(result, list):
            return None
        if self._cache:
            self._cache.put("fmp", "grades", yesterday, ticker, result)
        return result

    def get_financial_growth(self, ticker: str) -> dict | None:
        """Get most recent financial growth rates.

        Returns dict with: revenueGrowth, epsgrowth, etc.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "financial-growth", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 1}
        result = self._get("/stable/financial-growth", params=params, headers=self._auth_headers())
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "financial-growth", yesterday, ticker, result[0])
            return result[0]
        return None
