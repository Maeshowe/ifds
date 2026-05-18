"""Swing pivot universe source — S&P 500 + Russell 1000 union (~1000 tickers).

Day 63 outcome §3.9 (Döntés 9): replace the FMP screener (~1390 unstable
weekly-rotating universe) with a stable index-membership-based universe.
Rationale:

* The swing horizon (3-5 nap hold) is liquidity-sensitive — Russell 2000
  small-cap noise hurts. The Russell 1000 lower bound (~$700M-1B cap) is
  the cleanest cutoff.
* The new Phase 4 scoring (PCR + OTM-inverse percentile normalization) needs
  a **stable** universe distribution. The FMP screener rotates ~30% daily
  → unstable percentile ranks.
* S&P 500 + Russell 1000 are well-documented, index-replicable, and
  monthly-rebalanced (low churn).

Primary source: Wikipedia (free, stable HTML structure).
Fallback: FMP `/stable/sp500-constituent` and `/stable/russell1000-constituent`
(if available). Both fail → caller may fall back to legacy FMP screener.

Cache: `state/swing_universe/universe.json` with 7-day TTL (covers
monthly rebalances with margin).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
R1000_WIKI_URL = "https://en.wikipedia.org/wiki/Russell_1000_Index"

# Plausibility windows. Indexes shift slightly month-to-month; if the parse
# result is outside these bounds we treat it as a parsing failure and either
# fall back to FMP or refuse to write the cache.
SP500_MIN, SP500_MAX = 480, 525
R1000_MIN, R1000_MAX = 950, 1050
UNION_MIN, UNION_MAX = 950, 1100

# Tickers on Wikipedia sometimes appear with class-share suffixes ("BRK.B").
# IFDS uses bare symbols ("BRK") or hyphen variants ("BRK-B") depending on
# data provider; we normalize to the form FMP/Polygon use (hyphen, uppercase).
_TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z]{1,2})?$")


def _http_get(url: str, timeout: float = 15.0) -> str:
    """GET a URL with a real-browser User-Agent (Wikipedia 403's on python-requests)."""
    req = Request(
        url,
        headers={
            "User-Agent": "IFDS-Trading/1.0 (research)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted URL
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


# ---------------------------------------------------------------------------
# HTML parser — extracts the symbol from the first column of the first
# ``<table class="wikitable ...">`` on a Wikipedia page.
# ---------------------------------------------------------------------------


class _FirstColumnSymbolParser(HTMLParser):
    """Collect the Symbol column from the components table on a Wikipedia page.

    Both the S&P 500 and Russell 1000 pages mark the components table with
    ``id="constituents"`` (verified 2026-05-18), but the Symbol column
    position differs (S&P = 0, Russell = 1). We read the header row first
    to find the "Symbol" / "Ticker" column, then extract that column.
    """

    TARGET_ID = "constituents"
    SYMBOL_HEADER_PATTERNS = ("symbol", "ticker")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth_table = 0          # nesting depth in the target wikitable
        self._seen_target_table = False
        self._symbol_col: int | None = None
        self._in_tr = False
        self._cell_index_in_row = -1
        self._in_header_row = False
        self._collect_text = False
        self._buffer: list[str] = []
        self._header_cells: list[str] = []
        self.symbols: list[str] = []

    # ------------------------------------------------------------------
    # Tag handlers
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table":
            cls = (attrs_dict.get("class") or "").lower()
            table_id = attrs_dict.get("id") or ""
            if (
                "wikitable" in cls
                and table_id == self.TARGET_ID
                and not self._seen_target_table
            ):
                self._seen_target_table = True
                self._depth_table = 1
            elif self._depth_table > 0:
                self._depth_table += 1
            return

        if self._depth_table != 1:
            return

        if tag == "tr":
            self._in_tr = True
            self._cell_index_in_row = -1
            # header row is the first row whose cells are <th>
            if self._symbol_col is None:
                self._in_header_row = True
                self._header_cells = []
        elif tag == "th" and self._in_tr and self._symbol_col is None:
            self._cell_index_in_row += 1
            self._collect_text = True
            self._buffer = []
        elif tag == "td" and self._in_tr:
            self._cell_index_in_row += 1
            if self._symbol_col is not None and self._cell_index_in_row == self._symbol_col:
                self._collect_text = True
                self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._depth_table > 0:
            self._depth_table -= 1
            return

        if self._depth_table != 1:
            return

        if tag == "th" and self._collect_text and self._symbol_col is None:
            self._header_cells.append("".join(self._buffer).strip().lower())
            self._collect_text = False
            self._buffer = []
        elif tag == "td" and self._collect_text:
            text = "".join(self._buffer).strip()
            self._maybe_record(text)
            self._collect_text = False
            self._buffer = []
        elif tag == "tr" and self._in_tr:
            if self._in_header_row and self._symbol_col is None and self._header_cells:
                for idx, name in enumerate(self._header_cells):
                    if any(p in name for p in self.SYMBOL_HEADER_PATTERNS):
                        self._symbol_col = idx
                        break
            self._in_tr = False
            self._in_header_row = False
            self._collect_text = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._collect_text:
            self._buffer.append(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(token: str) -> str:
        return token.replace(".", "-").upper()

    def _maybe_record(self, raw: str) -> None:
        if not raw:
            return
        token = raw.split()[0].strip().rstrip(",")
        normalized = self._normalize(token)
        if _TICKER_RE.match(token) or _TICKER_RE.match(normalized):
            self.symbols.append(normalized)


def _parse_symbols(html: str) -> list[str]:
    parser = _FirstColumnSymbolParser()
    parser.feed(html)
    # dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for sym in parser.symbols:
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


# ---------------------------------------------------------------------------
# Wikipedia fetchers
# ---------------------------------------------------------------------------


def fetch_sp500_from_wikipedia() -> list[str]:
    """Parse the S&P 500 components table. Returns ~503 symbols (May 2026)."""
    html = _http_get(SP500_WIKI_URL)
    symbols = _parse_symbols(html)
    if not (SP500_MIN <= len(symbols) <= SP500_MAX):
        raise RuntimeError(
            f"S&P 500 parse returned {len(symbols)} symbols, expected "
            f"{SP500_MIN}-{SP500_MAX}. Wikipedia structure may have changed."
        )
    return symbols


def fetch_russell1000_from_wikipedia() -> list[str]:
    """Parse the Russell 1000 components table. Returns ~1000 symbols."""
    html = _http_get(R1000_WIKI_URL)
    symbols = _parse_symbols(html)
    if not (R1000_MIN <= len(symbols) <= R1000_MAX):
        raise RuntimeError(
            f"Russell 1000 parse returned {len(symbols)} symbols, expected "
            f"{R1000_MIN}-{R1000_MAX}. Wikipedia structure may have changed."
        )
    return symbols


# ---------------------------------------------------------------------------
# FMP fallback (best-effort — endpoints may not exist on the current plan)
# ---------------------------------------------------------------------------


def fetch_from_fmp_fallback(fmp_client: Any) -> list[str] | None:
    """Try FMP's index constituent endpoints. Returns None on any failure.

    fmp_client must provide a low-level ``_get(path, params=None, headers=None)``
    that mirrors the existing :class:`ifds.data.fmp.FMPClient` private GET. We
    use it directly to avoid bloating FMPClient with new wrappers for an
    optional fallback.
    """
    if fmp_client is None:
        return None
    try:
        sp500_resp = fmp_client._get(
            "/stable/sp500-constituent",
            params={"apikey": getattr(fmp_client, "_api_key", "")},
            headers=getattr(fmp_client, "_auth_headers", lambda: {})(),
        )
        r1000_resp = fmp_client._get(
            "/stable/russell1000-constituent",
            params={"apikey": getattr(fmp_client, "_api_key", "")},
            headers=getattr(fmp_client, "_auth_headers", lambda: {})(),
        )
    except Exception as exc:  # network, auth, schema mismatch — fall back
        logger.warning("FMP constituent fallback failed: %s", exc)
        return None

    def _symbols(resp: list[dict] | None) -> list[str]:
        if not resp:
            return []
        return [
            (row.get("symbol") or row.get("ticker") or "").upper().replace(".", "-")
            for row in resp
            if (row.get("symbol") or row.get("ticker"))
        ]

    union = sorted(set(_symbols(sp500_resp)) | set(_symbols(r1000_resp)))
    if UNION_MIN <= len(union) <= UNION_MAX:
        return union
    logger.warning(
        "FMP fallback returned %d symbols, outside expected %d-%d window",
        len(union), UNION_MIN, UNION_MAX,
    )
    return None


# ---------------------------------------------------------------------------
# Cache + public API
# ---------------------------------------------------------------------------


class SwingUniverseSource:
    """S&P 500 + Russell 1000 union universe with a 7-day cache.

    Usage:

        src = SwingUniverseSource(cache_dir=Path("state/swing_universe"))
        symbols = src.get_universe(fmp_client=optional_fmp)
    """

    CACHE_FILE = "universe.json"

    def __init__(
        self,
        cache_dir: Path,
        cache_ttl_days: int = 7,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = timedelta(days=cache_ttl_days)

    # -- public ---------------------------------------------------------

    def get_universe(self, fmp_client: Any | None = None) -> list[str]:
        """Return the deduped union, fetching + caching as needed."""
        cached = self._load_cache()
        if cached is not None:
            return cached

        union = self._fetch_fresh(fmp_client)

        if not (UNION_MIN <= len(union) <= UNION_MAX):
            raise RuntimeError(
                f"Swing universe union returned {len(union)} symbols, "
                f"outside expected {UNION_MIN}-{UNION_MAX} window."
            )

        self._write_cache(union)
        return union

    # -- internals ------------------------------------------------------

    def _fetch_fresh(self, fmp_client: Any | None) -> list[str]:
        """Wikipedia primary; FMP fallback; raise if both fail."""
        try:
            sp500 = fetch_sp500_from_wikipedia()
            r1000 = fetch_russell1000_from_wikipedia()
            return sorted(set(sp500) | set(r1000))
        except (URLError, RuntimeError) as wiki_exc:
            logger.warning("Wikipedia swing universe fetch failed: %s", wiki_exc)

        fallback = fetch_from_fmp_fallback(fmp_client)
        if fallback is not None:
            logger.info("Swing universe sourced from FMP fallback (%d symbols)",
                        len(fallback))
            return fallback

        raise RuntimeError(
            "Swing universe fetch failed: Wikipedia parse failed AND "
            "FMP fallback unavailable. Caller should fall back to legacy "
            "FMP screener."
        )

    def _cache_path(self) -> Path:
        return self.cache_dir / self.CACHE_FILE

    def _load_cache(self) -> list[str] | None:
        path = self._cache_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Swing universe cache unreadable: %s", exc)
            return None

        fetched_at_str = payload.get("fetched_at")
        if not fetched_at_str:
            return None
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
        except ValueError:
            return None
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - fetched_at
        if age > self.cache_ttl:
            return None

        symbols = payload.get("symbols") or []
        if not (UNION_MIN <= len(symbols) <= UNION_MAX):
            logger.warning(
                "Cached swing universe has %d symbols, outside window — refetching",
                len(symbols),
            )
            return None
        return list(symbols)

    def _write_cache(self, symbols: list[str]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(symbols),
            "symbols": symbols,
        }
        self._cache_path().write_text(json.dumps(payload, indent=2))
