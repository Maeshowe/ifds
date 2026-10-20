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
Fallback: FMP `/stable/sp500-constituent` + the iShares Russell 1000 ETF holdings
(`/stable/etf/holdings?symbol=IWB`). An ETF's holdings file IS index membership by
construction, which is why it replaces `/stable/russell1000-constituent` — that path
never existed on FMP: it returns 404 with a body byte-identical to a fabricated route,
on the same key that serves sp500/nasdaq/dowjones with 200. It was extrapolated from
the sp500 sibling and shipped unprobed in 2026-05-18 (`50dfb3c`), so the "fallback"
was structurally unsatisfiable from day one — 503 S&P names alone can never clear the
950-1100 union window. Both fail → caller falls open to the legacy FMP screener.

Cache: `state/swing_universe/universe.json` with 7-day TTL (covers
monthly rebalances with margin).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
import types
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# The Russell 1000 constituent table was MOVED OUT of the index article on
# 2026-08-12T20:04:06Z: `Russell_1000_Index` went from 81,878 to 6,541 bytes in one
# edit ("move to [[List of Russell 1000 companies]], format"), and the destination
# article (pageid 83952056) was created ten seconds later and is actively maintained.
# The old URL still returns HTTP 200 — it just has no constituent table any more, so
# the parser returned 0 and the union guard rejected the result. Every weekly run from
# 2026-08-16 on failed this way and fell open to the legacy screener in silence.
# Verified live 2026-10-19 with the UNCHANGED parser: 1021 symbols from the new URL,
# 503 from S&P 500, union 1027 — all three plausibility windows pass untouched.
R1000_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Russell_1000_companies"

# Plausibility windows. Indexes shift slightly month-to-month; if the parse
# result is outside these bounds we treat it as a parsing failure and either
# fall back to FMP or refuse to write the cache.
#: Russell 1000 proxy for the FMP fallback. An ETF's holdings file is index
#: membership by construction; VONE is the cross-issuer control.
R1000_ETF = "IWB"
R1000_ETF_CONTROL = "VONE"

SP500_MIN, SP500_MAX = 480, 525
R1000_MIN, R1000_MAX = 950, 1050
UNION_MIN, UNION_MAX = 950, 1100

# Tickers on Wikipedia sometimes appear with class-share suffixes ("BRK.B").
# IFDS uses bare symbols ("BRK") or hyphen variants ("BRK-B") depending on
# data provider; we normalize to the form FMP/Polygon use (hyphen, uppercase).
_TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z]{1,2})?$")


#: Staleness ladder for a cached membership list (D-U1/F-1b, approved 2026-10-20).
#:
#: For an index-membership list the critical property is NOT freshness but IDENTITY.
#: Measured 2026-10-20: a 77-day-old cache held 1018 names against today's 1027 —
#: Jaccard 0.927, a few percent of drift — because the Russell 1000 reconstitutes
#: annually in June with quarterly IPO adds. Substituting a different population, by
#: contrast, swapped 377 of 730 names (52%) for non-members. So serving a stale list
#: is nearly harmless and substituting one is not, and the old code had it backwards:
#: a 7-day TTL that, on expiry, SUBSTITUTED instead of EXTENDING.
#:
#: WARN at the TTL (a refetch is overdue), ERROR well before the June reconstitution
#: window would make the list genuinely wrong.
STALE_WARN_DAYS = 7
STALE_ERROR_DAYS = 45

#: Where a universe came from. Recorded in the pipeline context so every downstream
#: artifact (Phase 4 snapshot, scan matrix, FRL attempt) is self-describing.
SOURCE_WIKIPEDIA = "wikipedia"
SOURCE_FMP = "fmp_index_and_etf"
SOURCE_CACHE = "cache"


@dataclass(frozen=True)
class UniverseResult:
    """A membership list together with where it came from and how old it is."""

    symbols: tuple[str, ...]
    source: str
    fetched_at: datetime
    age_days: float
    degraded_stale: bool
    #: {symbol: GICS sector}, from the SAME Wikipedia fetch as the membership.
    #: BEST EFFORT: empty when the list came from the FMP fallback (ETF holdings
    #: carry no sector) or from a cache written before 2026-10-20.
    sectors: Mapping[str, str] = types.MappingProxyType({})

    def __len__(self) -> int:  # so callers can treat it like the old list
        return len(self.symbols)

    def __iter__(self):
        return iter(self.symbols)

    def provenance(self) -> dict:
        """The record that goes into the pipeline context (D-U1/F-2)."""
        return {
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat(),
            "count": len(self.symbols),
            "age_days": round(self.age_days, 2),
            "degraded_stale": self.degraded_stale,
            "sectors_known": len(self.sectors),
        }


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
    #: Both pages carry a "GICS Sector" column, so the sector comes from the SAME
    #: fetch as the membership — no second provider, no second failure mode. Before
    #: 2026-10-20 the sector came only from the FMP screener, which meant a name the
    #: screener happened not to return had no sector and was dropped. Exact header:
    #: S&P 500 ['Symbol','Security','GICS Sector','GICS Sub-Industry',...],
    #: Russell 1000 ['Company','Symbol','GICS Sector','GICS Sub-Industry'].
    SECTOR_HEADER_PATTERNS = ("gics sector", "sector")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth_table = 0  # nesting depth in the target wikitable
        self._seen_target_table = False
        self._symbol_col: int | None = None
        self._in_tr = False
        self._cell_index_in_row = -1
        self._in_header_row = False
        self._header_done = False
        self._collect_text = False
        self._buffer: list[str] = []
        self._header_cells: list[str] = []
        self._sector_col: int | None = None
        self._row_symbol: str | None = None
        self._row_sector: str | None = None
        self.symbols: list[str] = []
        #: {symbol: GICS sector}, populated from the same table rows.
        self.sectors: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Tag handlers
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table":
            cls = (attrs_dict.get("class") or "").lower()
            table_id = attrs_dict.get("id") or ""
            if "wikitable" in cls and table_id == self.TARGET_ID and not self._seen_target_table:
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
        elif tag == "th" and self._in_tr and not self._header_done:
            self._cell_index_in_row += 1
            self._collect_text = True
            self._buffer = []
        elif tag == "td" and self._in_tr:
            self._cell_index_in_row += 1
            if self._cell_index_in_row in (self._symbol_col, self._sector_col):
                self._collect_text = True
                self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._depth_table > 0:
            self._depth_table -= 1
            return

        if self._depth_table != 1:
            return

        if tag == "th" and self._collect_text and not self._header_done:
            self._header_cells.append("".join(self._buffer).strip().lower())
            self._collect_text = False
            self._buffer = []
        elif tag == "td" and self._collect_text:
            text = "".join(self._buffer).strip()
            if self._cell_index_in_row == self._symbol_col:
                self._row_symbol = text
            elif self._cell_index_in_row == self._sector_col:
                self._row_sector = text
            self._collect_text = False
            self._buffer = []
        elif tag == "tr" and self._in_tr:
            if self._in_header_row and not self._header_done and self._header_cells:
                for idx, name in enumerate(self._header_cells):
                    if self._symbol_col is None and any(
                        p in name for p in self.SYMBOL_HEADER_PATTERNS
                    ):
                        self._symbol_col = idx
                    elif self._sector_col is None and any(
                        p in name for p in self.SECTOR_HEADER_PATTERNS
                    ):
                        self._sector_col = idx
                # The symbol column is mandatory; the sector is best-effort, so the
                # header is "done" once the symbol is located and a further header
                # row cannot overwrite it.
                if self._symbol_col is not None:
                    self._header_done = True
            self._record_row()
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

    def _record_row(self) -> None:
        """Commit one body row: the symbol, and its sector when the column exists."""
        raw, sector = self._row_symbol, self._row_sector
        self._row_symbol = self._row_sector = None
        if not raw:
            return
        token = raw.split()[0].strip().rstrip(",")
        normalized = self._normalize(token)
        if not (_TICKER_RE.match(token) or _TICKER_RE.match(normalized)):
            return
        self.symbols.append(normalized)
        if sector:
            self.sectors.setdefault(normalized, sector)


def _parse_constituents(html: str) -> tuple[list[str], dict[str, str]]:
    """Symbols plus ``{symbol: GICS sector}`` from one parse of one fetch.

    The sector is BEST EFFORT: a page without a sector column yields an empty dict
    and the symbols are unaffected. Callers must treat a missing sector as legal.
    """
    parser = _FirstColumnSymbolParser()
    parser.feed(html)
    seen: set[str] = set()
    symbols: list[str] = []
    for sym in parser.symbols:
        if sym not in seen:
            seen.add(sym)
            symbols.append(sym)
    return symbols, dict(parser.sectors)


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


def fetch_sp500_from_wikipedia(with_sectors: bool = False):
    """Parse the S&P 500 components table. ~503 symbols (May 2026).

    With ``with_sectors`` the return is ``(symbols, {symbol: GICS sector})`` from the
    SAME fetch — verified 2026-10-20: 503 symbols, 503 sectors, 11 distinct sectors.
    """
    html = _http_get(SP500_WIKI_URL)
    symbols, sectors = _parse_constituents(html)
    if not (SP500_MIN <= len(symbols) <= SP500_MAX):
        raise RuntimeError(
            f"S&P 500 parse returned {len(symbols)} symbols, expected "
            f"{SP500_MIN}-{SP500_MAX}. Wikipedia structure may have changed."
        )
    return (symbols, sectors) if with_sectors else symbols


def fetch_russell1000_from_wikipedia(with_sectors: bool = False):
    """Parse the Russell 1000 components table. ~1021 symbols (Oct 2026).

    With ``with_sectors`` the return is ``(symbols, {symbol: GICS sector})`` from the
    SAME fetch — verified 2026-10-20: 1021 symbols, 1021 sectors.
    """
    html = _http_get(R1000_WIKI_URL)
    symbols, sectors = _parse_constituents(html)
    if not (R1000_MIN <= len(symbols) <= R1000_MAX):
        raise RuntimeError(
            f"Russell 1000 parse returned {len(symbols)} symbols, expected "
            f"{R1000_MIN}-{R1000_MAX}. Wikipedia structure may have changed."
        )
    return (symbols, sectors) if with_sectors else symbols


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
        # IWB = iShares Russell 1000 ETF. Its holdings file is index membership by
        # construction. Cross-validated 2026-10-19 against VONE (Vanguard Russell
        # 1000 — a different issuer tracking the same index): Jaccard 0.9951, so the
        # list is membership and not one issuer's artifact.
        r1000_resp = fmp_client._get(
            "/stable/etf/holdings",
            params={"symbol": R1000_ETF, "apikey": getattr(fmp_client, "_api_key", "")},
            headers=getattr(fmp_client, "_auth_headers", lambda: {})(),
        )
    except Exception as exc:  # network, auth, schema mismatch — fall back
        logger.warning("FMP constituent fallback failed: %s", exc)
        return None

    def _symbols(resp: list[dict] | None, field: str = "symbol") -> list[str]:
        """Extract tickers, normalising class shares to the hyphen form.

        ``field`` matters: in an ETF-holdings row ``symbol`` is the ETF ITSELF and the
        constituent ticker is ``asset``. Reading ``symbol`` there yields 1 distinct
        name, the union collapses to 504 and the guard rejects it — a silent,
        plausible-looking failure, so the field is named explicitly at every call.
        """
        if not resp:
            return []
        return [
            (row.get(field) or "").upper().replace(".", "-")
            for row in resp
            if row.get(field)
        ]

    union = sorted(
        set(_symbols(sp500_resp, "symbol")) | set(_symbols(r1000_resp, "asset"))
    )
    if UNION_MIN <= len(union) <= UNION_MAX:
        return union
    logger.warning(
        "FMP fallback returned %d symbols, outside expected %d-%d window",
        len(union),
        UNION_MIN,
        UNION_MAX,
    )
    return None


# ---------------------------------------------------------------------------
# Cache + public API
# ---------------------------------------------------------------------------


def _symbols_and_sectors(fetcher) -> tuple[list[str], dict[str, str]]:
    """Call a Wikipedia fetcher and accept either shape it may return.

    Production asks for sectors; a test that patches the fetcher with a plain list
    still works and simply yields no sectors. That is not looseness — the sector is
    documented as BEST EFFORT, so its absence is a legal state, and tolerating it
    here keeps the symbol path (which is NOT optional) independent of it.
    """
    try:
        result = fetcher(with_sectors=True)
    except TypeError:
        result = fetcher()
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
        return list(result[0]), dict(result[1])
    return list(result), {}


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
        #: Sectors from the most recent live fetch, persisted with the cache.
        self._last_sectors: dict[str, str] = {}

    # -- public ---------------------------------------------------------

    def get_universe(self, fmp_client: Any | None = None) -> UniverseResult:
        """Return the membership list with its provenance.

        Staleness ladder (D-U1/F-1a..F-1c, approved 2026-10-20): a cache inside the
        TTL is used as-is; past the TTL a refetch is attempted, and if it FAILS the
        stale cache is served anyway, labelled, with an escalating alarm. Only the
        total absence of a usable list raises — and then the caller must refuse to
        write the pipeline context rather than substitute a different population.

        The old code returned None from the cache on expiry, which sent the caller
        down the screener fallback: nine consecutive weekly runs (2026-08-16 ..
        10-19) silently swapped the population instead of serving a slightly old
        and nearly identical one.
        """
        cached = self._load_cache()
        if cached is not None and cached.age_days <= self.cache_ttl.days:
            return cached

        try:
            union, source = self._fetch_fresh(fmp_client)
        except (URLError, RuntimeError) as exc:
            if cached is None:
                raise RuntimeError(
                    f"Swing universe unavailable: fetch failed ({exc}) and no usable "
                    "cache exists. The caller must NOT substitute another population."
                ) from exc
            self._log_staleness(cached)
            return cached

        if not (UNION_MIN <= len(union) <= UNION_MAX):
            message = (
                f"Swing universe union returned {len(union)} symbols, "
                f"outside expected {UNION_MIN}-{UNION_MAX} window."
            )
            if cached is None:
                raise RuntimeError(message)
            logger.error("%s — serving the cached list instead.", message)
            self._log_staleness(cached)
            return cached

        self._write_cache(list(union))
        now = datetime.now(timezone.utc)
        return UniverseResult(
            symbols=tuple(union),
            source=source,
            fetched_at=now,
            age_days=0.0,
            degraded_stale=False,
            sectors=types.MappingProxyType(dict(self._last_sectors)),
        )

    def _log_staleness(self, cached: UniverseResult) -> None:
        """Escalating alarm on the served cache's age (F-1b)."""
        age = cached.age_days
        detail = (
            f"serving the CACHED membership: {len(cached)} symbols, "
            f"fetched {cached.fetched_at:%Y-%m-%d}, age {age:.1f}d"
        )
        if age > STALE_ERROR_DAYS:
            logger.error(
                "%s — past %dd, the list may predate an index reconstitution. "
                "Fix the source.",
                detail,
                STALE_ERROR_DAYS,
            )
        elif age > STALE_WARN_DAYS:
            logger.warning("%s — a refetch is overdue (TTL %dd).", detail, STALE_WARN_DAYS)
        else:
            logger.info("%s.", detail)

    # -- internals ------------------------------------------------------

    def _fetch_fresh(self, fmp_client: Any | None) -> tuple[list[str], str]:  # noqa: D401
        """Wikipedia primary; FMP fallback; raise if both fail.

        Returns ``(symbols, source_label)`` so the provenance records which of the
        two independent providers actually answered.
        """
        try:
            sp500, sp_sectors = _symbols_and_sectors(fetch_sp500_from_wikipedia)
            r1000, r_sectors = _symbols_and_sectors(fetch_russell1000_from_wikipedia)
            # Russell first so the broader list wins a disagreement; both pages
            # carry GICS so collisions are rare and cosmetic.
            self._last_sectors = {**sp_sectors, **r_sectors}
            return sorted(set(sp500) | set(r1000)), SOURCE_WIKIPEDIA
        except (URLError, RuntimeError) as wiki_exc:
            logger.warning("Wikipedia swing universe fetch failed: %s", wiki_exc)

        fallback = fetch_from_fmp_fallback(fmp_client)
        if fallback is not None:
            logger.info("Swing universe sourced from FMP fallback (%d symbols)", len(fallback))
            return fallback, SOURCE_FMP

        raise RuntimeError(
            "Swing universe fetch failed: Wikipedia parse failed AND the FMP "
            "fallback is unavailable. The caller must NOT substitute the legacy "
            "screener — it is a different population, not a staler list."
        )

    def _cache_path(self) -> Path:
        return self.cache_dir / self.CACHE_FILE

    def _load_cache(self) -> UniverseResult | None:
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

        # Age is REPORTED, never used to discard: an expired cache is still a valid
        # membership list, and the caller decides whether to refetch (F-1a).
        age_days = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 86400.0

        symbols = payload.get("symbols") or []
        if not (UNION_MIN <= len(symbols) <= UNION_MAX):
            logger.warning(
                "Cached swing universe has %d symbols, outside the %d-%d window — "
                "treating the cache as unusable",
                len(symbols),
                UNION_MIN,
                UNION_MAX,
            )
            return None
        return UniverseResult(
            symbols=tuple(symbols),
            source=SOURCE_CACHE,
            fetched_at=fetched_at,
            age_days=age_days,
            degraded_stale=age_days > self.cache_ttl.days,
            sectors=types.MappingProxyType(dict(payload.get("sectors") or {})),
        )

    def _write_cache(self, symbols: list[str]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(symbols),
            "symbols": symbols,
            # Persisted so a cache hit still carries sectors. Absent in files written
            # before 2026-10-20, which read back as an empty mapping.
            "sectors": dict(self._last_sectors),
        }
        self._cache_path().write_text(json.dumps(payload, indent=2))
