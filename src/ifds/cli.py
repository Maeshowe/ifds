"""IFDS CLI — entry point for python -m ifds."""

import argparse
import sys
from pathlib import Path

from ifds import __version__


def _load_env():
    """Load .env file from project root if it exists (no external dependency)."""
    # Walk up from this file to find .env
    for parent in [Path.cwd(), Path(__file__).resolve().parent.parent.parent]:
        env_file = parent / ".env"
        if env_file.exists():
            import os
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key, val = key.strip(), val.strip().strip('"')
                    if key not in os.environ:  # Don't override explicit env vars
                        os.environ[key] = val
            break


def main():
    _load_env()
    parser = argparse.ArgumentParser(
        prog="ifds",
        description="IFDS — Institutional Flow Decision Suite v2.0",
    )
    parser.add_argument(
        "--version", action="version", version=f"ifds {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # run — execute the pipeline
    run_parser = subparsers.add_parser("run", help="Run the trading signal pipeline")
    run_parser.add_argument(
        "--phase",
        type=int,
        choices=[0, 1, 2, 3, 4, 5, 6],
        help="Run only a specific phase (default: all phases)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and API health without running the pipeline",
    )
    run_parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config file (default: built-in defaults + env vars)",
    )

    # check — validate config and API connectivity
    check_parser = subparsers.add_parser("check", help="Validate configuration and API connectivity")
    check_parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config file (default: built-in defaults + env vars)",
    )

    # compare — parameter sweep comparison (SIM-L2)
    compare_parser = subparsers.add_parser(
        "compare", help="Run parameter sweep comparison (SIM-L2)")
    compare_parser.add_argument(
        "--config", type=str,
        help="Path to YAML variant config file",
    )
    compare_parser.add_argument(
        "--baseline", type=str, default="baseline",
        help="Baseline variant name (default: baseline)",
    )
    compare_parser.add_argument(
        "--challenger", type=str,
        help="Challenger variant name",
    )
    compare_parser.add_argument(
        "--override-sl-atr", type=float,
        help="Override stop loss ATR multiple for challenger",
    )
    compare_parser.add_argument(
        "--override-tp1-atr", type=float,
        help="Override TP1 ATR multiple for challenger",
    )
    compare_parser.add_argument(
        "--override-tp2-atr", type=float,
        help="Override TP2 ATR multiple for challenger",
    )
    compare_parser.add_argument(
        "--override-hold-days", type=int,
        help="Override max hold days for challenger",
    )
    compare_parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Directory with execution plan CSVs (default: output)",
    )

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "check":
        _cmd_check(args)
    elif args.command == "compare":
        _cmd_compare(args)


def _cmd_run(args):
    """Execute the pipeline."""
    from ifds.pipeline.runner import run_pipeline

    result = run_pipeline(
        phase=args.phase,
        dry_run=args.dry_run,
        config_path=args.config,
    )
    sys.exit(0 if result.success else 1)


def _cmd_check(args):
    """Validate configuration and API connectivity."""
    from ifds.pipeline.runner import check_system

    result = check_system(config_path=args.config)
    sys.exit(0 if result.success else 1)


def _cmd_compare(args):
    """Run parameter sweep comparison."""
    import os

    from ifds.sim.models import SimVariant
    from ifds.sim.replay import load_variants_from_yaml, run_comparison
    from ifds.sim.report import print_comparison_report, write_comparison_csv

    # Build variants from YAML or CLI args
    if args.config:
        variants = load_variants_from_yaml(args.config)
    else:
        # Build from CLI args
        variants = [SimVariant(name=args.baseline, description="Current production config")]

        if args.challenger:
            overrides = {}
            if args.override_sl_atr is not None:
                overrides["stop_loss_atr_multiple"] = args.override_sl_atr
            if args.override_tp1_atr is not None:
                overrides["tp1_atr_multiple"] = args.override_tp1_atr
            if args.override_tp2_atr is not None:
                overrides["tp2_atr_multiple"] = args.override_tp2_atr
            if args.override_hold_days is not None:
                overrides["max_hold_days"] = args.override_hold_days
            variants.append(SimVariant(
                name=args.challenger,
                overrides=overrides,
            ))
        else:
            print("Error: --challenger required when not using --config")
            sys.exit(1)

    polygon_key = os.environ.get("IFDS_POLYGON_API_KEY", "")
    cache_dir = os.environ.get("IFDS_CACHE_DIR", "data/cache")

    report = run_comparison(
        variants,
        output_dir=args.output_dir,
        polygon_api_key=polygon_key if polygon_key else None,
        cache_dir=cache_dir,
    )

    print_comparison_report(report)
    csv_path = write_comparison_csv(report, args.output_dir)
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
