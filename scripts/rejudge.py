"""Grade the answers of an existing FinanceBench run again with another judge model. PAID: quote and get approval first."""
import argparse
import asyncio
import json
from pathlib import Path

from eval_financebench import judge

from gfra.financebench_eval import aggregate, parse_verdict


async def rejudge(run: Path, model: str) -> Path:
    data = json.loads(run.read_text())
    rows = []
    for r in data["rows"]:
        reply = await judge(r["question"], r["gold"], r["answer"], model=model)
        rows.append({**r, "judge_reply": reply, "verdict": parse_verdict(reply)})
    summary = {**data["summary"], **aggregate(rows), "judge_model": model}
    out = run.with_name(f"{run.stem}-judge-{model}.json")
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--judge-model", required=True)
    args = parser.parse_args()
    print(asyncio.run(rejudge(args.run, args.judge_model)))


if __name__ == "__main__":
    main()
