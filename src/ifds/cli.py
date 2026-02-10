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

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "check":
        _cmd_check(args)


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


if __name__ == "__main__":
    main()
