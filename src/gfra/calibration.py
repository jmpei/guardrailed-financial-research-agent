"""Check an LLM judge against the user's own labels: raw agreement and Cohen's kappa."""
import json
import random
from collections import Counter
from pathlib import Path

from gfra.financebench_eval import parse_verdict

KEYS = {"c": "correct", "i": "incorrect", "r": "refused", "u": "unknown"}


def sample_rows(rows: list[dict], n: int, seed: int = 0) -> list[dict]:
    ordered = sorted(rows, key=lambda r: (r["id"], r["trial"]))
    return random.Random(seed).sample(ordered, min(n, len(ordered)))


def load_labels(path: Path) -> dict[tuple[str, int], str]:
    if not Path(path).exists():
        return {}
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    return {(r["id"], r["trial"]): r["label"] for r in rows}


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    count_a, count_b = Counter(a), Counter(b)
    expected = sum(count_a[k] * count_b[k] for k in count_a) / n**2
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def agreement(labels: dict[tuple[str, int], str], rows: list[dict]) -> dict:
    """Compare one judge's verdicts (rows of a run file) with the labelled rows."""
    pairs = [(labels[(r["id"], r["trial"])], r["verdict"]) for r in rows if (r["id"], r["trial"]) in labels]
    if not pairs:
        return {"n": 0, "agreement": None, "cohen_kappa": None, "confusion": {}}
    human, judge = [h for h, _ in pairs], [j for _, j in pairs]
    return {
        "n": len(pairs),
        "agreement": sum(h == j for h, j in pairs) / len(pairs),
        "cohen_kappa": cohen_kappa(human, judge),
        "confusion": dict(sorted(Counter(f"{h} -> {j}" for h, j in pairs).items())),
    }


async def rejudge_rows(rows: list[dict], judge) -> list[dict]:
    """Grade every non-error row again with `judge(question, gold, answer)`; a failing call marks that row as an error."""
    out = []
    for r in rows:
        if r["verdict"] == "error":
            out.append(r)
            continue
        try:
            reply = await judge(r["question"], r["gold"], r["answer"])
        except Exception as exc:
            out.append({**r, "judge_reply": "", "verdict": "error", "error": repr(exc)})
        else:
            out.append({**r, "judge_reply": reply, "verdict": parse_verdict(reply)})
    return out
