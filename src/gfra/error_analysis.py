"""Error analysis: export the answers the judge did not mark correct, then count the failure modes."""
import csv
import json
from collections import Counter
from pathlib import Path

COLUMNS = ["id", "trial", "verdict", "question", "gold", "answer", "tool_calls", "blocked", "note", "failure_mode"]
JUDGED_FAILURES = {"incorrect", "refused", "unknown", "unparsed"}


def failures(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["verdict"] in JUDGED_FAILURES]


def write_csv(rows: list[dict], path: Path) -> int:
    failed = failures(rows)
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, COLUMNS)
        writer.writeheader()
        for r in failed:
            calls = "\n".join(f"{c['name']} {json.dumps(c['args'])}" for c in r["tool_calls"])
            writer.writerow({**{k: r[k] for k in COLUMNS[:6]}, "tool_calls": calls, "blocked": r["blocked"],
                             "note": "", "failure_mode": ""})
    return len(failed)


def count_modes(path: Path) -> Counter:
    with Path(path).open(newline="") as f:
        return Counter(row["failure_mode"].strip() or "(not labelled)" for row in csv.DictReader(f))
