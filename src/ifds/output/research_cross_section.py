"""v2 research cross-section sink — full scored table, daily persist (FRL spec §4.4).

Freeze carve-out (§4.2/1, D_A approved by Tamás 2026-07-21): this module **only
writes**. It touches no scoring, sizing or exit path, and its output feeds no
production decision — it exists so the Factor Research Loop's v2 lane (raw
sub-component hypotheses) has a forward-collected sample. Every day it is not
running is permanent data loss from the post-Day-63 dev window.

Why it is not the phase4 snapshot: that one persists only the ~3-7 *winners*, so
it is not a cross-section. This sink persists **every row where scoring ran**.

Score semantics (FRL-0 gate finding, encoded here on purpose): the swing S_j and
the legacy composite are written to **separate fields**. In the scan-matrix CSV a
single ``Total_Score`` column means different things per era, which cost the FRL
a dedicated audit to untangle; downstream consumers of this sink never face that
ambiguity. ``combined_score`` is the live value the pipeline ended up using.
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DIR = "state/research_cross_section"

SCHEMA_VERSION = 1


def build_records(
    analyzed: list,
    sector_scores: list | None = None,
    swing_scoring_enabled: bool = False,
) -> list[dict]:
    """Build one record per analyzed ticker, richest available fields.

    Args:
        analyzed: every ``StockAnalysis`` Phase 4 produced (passed + excluded).
        sector_scores: Phase 3 sector scores, for sector context per row.
        swing_scoring_enabled: whether the swing rescore ran this session. Decides
            which field ``combined_score`` was written into.

    Returns:
        List of flat dicts. Rows where scoring never ran (tech-filter rejects)
        carry ``scored: False`` and a null score — never a 0.0 that would read as
        a real factor value downstream (the dp_pct structural-zero error class).
    """
    from ifds.data.phase4_snapshot import _stock_to_dict

    sector_map = {}
    for score in sector_scores or []:
        sector_map[score.sector_name] = score

    records: list[dict] = []
    for stock in analyzed:
        record = _stock_to_dict(stock)

        reason = getattr(stock, "exclusion_reason", None)
        excluded = bool(getattr(stock, "excluded", False))
        # "Scored" means scoring actually ran: the structural filters drop a
        # ticker before any score exists, and its combined_score is a dataclass
        # default, not a measurement.
        scored = reason not in ("tech_filter", "danger_zone")

        live_score = record.get("combined_score")
        record.update(
            {
                "scored": scored,
                "excluded": excluded,
                "exclusion_reason": reason,
                # Era-explicit score fields — never one ambiguous column.
                "swing_score": live_score if (scored and swing_scoring_enabled) else None,
                "legacy_composite": live_score if (scored and not swing_scoring_enabled) else None,
                "combined_score": live_score if scored else None,
                "scoring_mode": "swing" if swing_scoring_enabled else "legacy",
            }
        )

        sector_score = sector_map.get(stock.sector)
        if sector_score is not None:
            record.update(
                {
                    "sector_etf": sector_score.etf,
                    "sector_bmi": sector_score.sector_bmi,
                    "sector_vetoed": bool(getattr(sector_score, "vetoed", False)),
                    "sector_regime": (
                        sector_score.sector_bmi_regime.value
                        if sector_score.sector_bmi_regime is not None
                        else None
                    ),
                }
            )

        records.append(record)

    return records


def write_cross_section(
    analyzed: list,
    sector_scores: list | None = None,
    swing_scoring_enabled: bool = False,
    output_dir: str = DEFAULT_DIR,
    trading_date: str | None = None,
) -> Path:
    """Persist the full scored cross-section to ``{output_dir}/{date}.json.gz``.

    Atomic (temp file + ``os.replace``), so a crashed run cannot leave a half
    written file that a later loader would silently accept.

    Returns:
        Path of the written file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    day = trading_date or date.today().isoformat()
    file_path = out_dir / f"{day}.json.gz"

    records = build_records(analyzed, sector_scores, swing_scoring_enabled)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "trading_date": day,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "scoring_mode": "swing" if swing_scoring_enabled else "legacy",
        "n_rows": len(records),
        "n_scored": sum(1 for r in records if r["scored"]),
        "records": records,
    }

    fd, tmp = tempfile.mkstemp(dir=str(out_dir), suffix=".tmp")
    os.close(fd)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, str(file_path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    return file_path


def load_cross_section(
    trading_date: str,
    output_dir: str = DEFAULT_DIR,
) -> dict | None:
    """Read a persisted cross-section back, or None if absent."""
    path = Path(output_dir) / f"{trading_date}.json.gz"
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)
