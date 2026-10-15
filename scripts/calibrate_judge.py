"""Label a sample of answers yourself (the judge's verdict stays hidden), then compare judges with your labels.

Free: no API calls.
  uv run python scripts/calibrate_judge.py label runs/financebench/<run>.json --n 30
  uv run python scripts/calibrate_judge.py report runs/financebench/<run>.json [<rejudged run>.json ...]

Labels live in runs/labels/<run name>.jsonl, one file per labelled run; a re-judged run is scored with the labels of its source run.
"""
import argparse
import json
from pathlib import Path

from gfra.calibration import KEYS, agreement, load_labels, sample_rows

LABELS_DIR = Path(__file__).resolve().parents[1] / "runs" / "labels"


def labels_path(run_stem: str) -> Path:
    return LABELS_DIR / f"{run_stem}.jsonl"


def label(run: Path, n: int) -> None:
    rows = json.loads(run.read_text())["rows"]
    path = labels_path(run.stem)
    done = load_labels(path)
    todo = [r for r in sample_rows([r for r in rows if r["verdict"] != "error"], n) if (r["id"], r["trial"]) not in done]
    path.parent.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {r['id']}\n\nQUESTION\n{r['question']}\n\nGOLD\n{r['gold']}\n\nANSWER\n{r['answer']}\n")
        key = ""
        while key not in KEYS:
            key = input("c = correct, i = incorrect, r = refused, u = unknown > ").strip().lower()
        with path.open("a") as f:
            f.write(json.dumps({"id": r["id"], "trial": r["trial"], "label": KEYS[key]}) + "\n")


def report(runs: list[Path]) -> None:
    for run in runs:
        data = json.loads(run.read_text())
        labels = load_labels(labels_path(data["summary"].get("source_run", run.stem)))
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
