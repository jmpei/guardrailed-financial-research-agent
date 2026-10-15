"""Export the failed answers of a run to a CSV you read and label, then count the failure modes. Free: no API calls.

  uv run python scripts/error_analysis.py export runs/financebench/<run>.json
  (read each row; write what went wrong in `note`; group the notes into a few names and put one in `failure_mode`)
  uv run python scripts/error_analysis.py count runs/financebench/<run>-failures.csv
"""
import argparse
import json
import sys
from pathlib import Path

from gfra.error_analysis import count_modes, write_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("export").add_argument("run", type=Path)
    sub.add_parser("count").add_argument("csv", type=Path)
    args = parser.parse_args()
    if args.command == "export":
        out = args.run.with_name(f"{args.run.stem}-failures.csv")
        if out.exists():
            print(f"{out} exists; delete it to export again")
            sys.exit(1)
        print(f"{write_csv(json.loads(args.run.read_text())['rows'], out)} failures -> {out}")
    else:
        for mode, n in count_modes(args.csv).most_common():
            print(f"{n:4d}  {mode}")


if __name__ == "__main__":
    main()
