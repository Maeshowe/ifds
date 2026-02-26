#!/usr/bin/env python3
"""merge_mms_state.py — MMS baseline merge: Mac Mini (obsidian/) + MacBook (mms/)

Összefésüli a két forrás JSON fájljait date alapján.
Konflikt esetén a Mini nyeri (frissebb, prod forrás).
Eredmény: state/mms/ (a MacBook helyi mappája).

Használat:
    # 1. Lehúzza a Mini state/obsidian/ tartalmát egy ideiglenes mappába:
    rsync -avz safrtam@negotium.ddns.net:~/SSH-Services/ifds/state/obsidian/ \\
        /Users/safrtam/SSH-Services/ifds/state/mms_from_mini/

    # 2. Futtatja a merge-t:
    python scripts/merge_mms_state.py [--dry-run]

    # 3. Ha minden OK, törli az ideiglenes mappát:
    rm -rf /Users/safrtam/SSH-Services/ifds/state/mms_from_mini/
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SOURCE_MINI = REPO_ROOT / "state" / "mms_from_mini"   # rsync ide húzza a Mini-t
SOURCE_MACBOOK = REPO_ROOT / "state" / "mms"           # MacBook jelenlegi állapota
OUTPUT = REPO_ROOT / "state" / "mms"                   # eredmény (in-place)


def load_entries(path: Path) -> dict[str, dict]:
    """JSON fájl betöltése, date → entry dict visszaadása."""
    try:
        entries = json.loads(path.read_text())
        if not isinstance(entries, list):
            return {}
        return {e["date"]: e for e in entries if "date" in e}
    except Exception as e:
        print(f"  ⚠️  Betöltési hiba ({path.name}): {e}")
        return {}


def merge_ticker(ticker: str, mini_path: Path | None, macbook_path: Path | None,
                 dry_run: bool) -> tuple[int, int, int]:
    """Egy ticker merge-je. Visszaad: (mini_only, macbook_only, conflict_mini_wins)."""
    mini_entries = load_entries(mini_path) if mini_path else {}
    macbook_entries = load_entries(macbook_path) if macbook_path else {}

    all_dates = sorted(set(mini_entries) | set(macbook_entries))

    mini_only = conflict_mini_wins = macbook_only = 0
    merged = []

    for date in all_dates:
        in_mini = date in mini_entries
        in_macbook = date in macbook_entries

        if in_mini and in_macbook:
            if mini_entries[date] != macbook_entries[date]:
                conflict_mini_wins += 1
            merged.append(mini_entries[date])   # Mini nyeri konfliktnál
        elif in_mini:
            mini_only += 1
            merged.append(mini_entries[date])
        else:
            macbook_only += 1
            merged.append(macbook_entries[date])

    if not dry_run:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT / f"{ticker}.json"
        out_path.write_text(json.dumps(merged, separators=(",", ":")))

    return mini_only, macbook_only, conflict_mini_wins


def main():
    parser = argparse.ArgumentParser(description="Merge MMS state: Mini + MacBook")
    parser.add_argument("--dry-run", action="store_true",
                        help="Csak logolás, nem ír fájlt")
    args = parser.parse_args()

    if not SOURCE_MINI.exists():
        print(f"❌  Hiányzik: {SOURCE_MINI}")
        print("   Futtasd először:")
        print(f"   rsync -avz safrtam@negotium.ddns.net:~/SSH-Services/ifds/state/obsidian/ \\")
        print(f"       {SOURCE_MINI}/")
        sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN — nem ír fájlt ===\n")

    # Összes ticker mindkét forrásból
    mini_tickers = {p.stem for p in SOURCE_MINI.glob("*.json")}
    macbook_tickers = {p.stem for p in SOURCE_MACBOOK.glob("*.json")} if SOURCE_MACBOOK.exists() else set()
    all_tickers = sorted(mini_tickers | macbook_tickers)

    print(f"Mini    (mms_from_mini/): {len(mini_tickers):>4} ticker")
    print(f"MacBook (mms/):           {len(macbook_tickers):>4} ticker")
    print(f"Összesen (union):         {len(all_tickers):>4} ticker")
    print()

    # Statisztikák
    total_mini_only = total_macbook_only = total_conflicts = 0
    tickers_with_new = []       # Mini-n van ami MacBook-on nincs
    tickers_with_conflict = []  # Ugyanaz a date, eltérő tartalom

    for ticker in all_tickers:
        mini_path = SOURCE_MINI / f"{ticker}.json" if ticker in mini_tickers else None
        macbook_path = SOURCE_MACBOOK / f"{ticker}.json" if ticker in macbook_tickers else None

        mini_only, macbook_only, conflicts = merge_ticker(
            ticker, mini_path, macbook_path, args.dry_run
        )

        total_mini_only += mini_only
        total_macbook_only += macbook_only
        total_conflicts += conflicts

        if mini_only > 0:
            tickers_with_new.append((ticker, mini_only))
        if conflicts > 0:
            tickers_with_conflict.append((ticker, conflicts))

    # Összefoglaló
    print("=" * 50)
    print(f"✓ Merge {'(DRY RUN) ' if args.dry_run else ''}kész")
    print()
    print(f"  Mini-n új entry (MacBook-on nem volt): {total_mini_only}")
    print(f"  MacBook-on volt, Mini-n nem:           {total_macbook_only}")
    print(f"  Konflikt (Mini nyert):                 {total_conflicts}")
    print()

    if tickers_with_new:
        print(f"  Tickerek ahol Mini frissebb ({len(tickers_with_new)} db):")
        for ticker, count in sorted(tickers_with_new, key=lambda x: -x[1])[:20]:
            print(f"    {ticker}: +{count} entry")
        if len(tickers_with_new) > 20:
            print(f"    ... és még {len(tickers_with_new) - 20} db")
        print()

    if tickers_with_conflict:
        print(f"  ⚠️  Konflikt tickerek ({len(tickers_with_conflict)} db) — Mini nyert:")
        for ticker, count in tickers_with_conflict:
            print(f"    {ticker}: {count} konflikt")
        print()

    if not args.dry_run:
        print(f"  Output: {OUTPUT}/")
        print()
        print("  Következő lépés ha minden OK:")
        print(f"  rm -rf {SOURCE_MINI}/")


if __name__ == "__main__":
    main()
