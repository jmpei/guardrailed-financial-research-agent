"""Label a sample of answers yourself (the judge's verdict stays hidden), then compare judges with your labels.

Free: no API calls.
  uv run python scripts/calibrate_judge.py label runs/financebench/<run>.json --n 30
  uv run python scripts/calibrate_judge.py report runs/financebench/<run>.json [<rejudged run>.json ...]
"""
import argparse
import json
from pathlib import Path

from gfra.calibration import KEYS, agreement, load_labels, sample_rows

LABELS = Path(__file__).resolve().parents[1] / "runs" / "labels.jsonl"


def label(run: Path, n: int) -> None:
    rows = json.loads(run.read_text())["rows"]
    done = load_labels(LABELS)
    todo = [r for r in sample_rows(rows, n) if (r["id"], r["trial"]) not in done]
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {r['id']}\n\nQUESTION\n{r['question']}\n\nGOLD\n{r['gold']}\n\nANSWER\n{r['answer']}\n")
        key = ""
        while key not in KEYS:
            key = input("c = correct, i = incorrect, r = refused, u = unknown > ").strip().lower()
        with LABELS.open("a") as f:
            f.write(json.dumps({"id": r["id"], "trial": r["trial"], "label": KEYS[key]}) + "\n")


def report(runs: list[Path]) -> None:
    labels = load_labels(LABELS)
    for run in runs:
        data = json.loads(run.read_text())
        print(data["summary"]["judge_model"], json.dumps(agreement(labels, data["rows"]), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_label = sub.add_parser("label")
    p_label.add_argument("run", type=Path)
    p_label.add_argument("--n", type=int, default=30)
    p_report = sub.add_parser("report")
    p_report.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args()
    label(args.run, args.n) if args.command == "label" else report(args.runs)


if __name__ == "__main__":
    main()
