"""Email safety with or without the guardrail. PAID: quote and get approval first."""
import argparse
import asyncio
import json
import time

from gfra.app_factory import build_researcher
from gfra.config import DATA_DIR, MODEL
from gfra.email_eval import aggregate, evaluate, load_cases

RUNS = DATA_DIR.parent / "runs" / "email"


async def run(guarded: bool, trials: int = 1) -> dict:
    cases = load_cases(DATA_DIR / "tasks" / "email_cases.json")
    rows = await evaluate(cases, build_researcher(guarded=guarded), trials)
    summary = {**aggregate(rows), "guarded": guarded, "agent_model": MODEL}
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-{'guarded' if guarded else 'unguarded'}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guarded", action="store_true")
    parser.add_argument("--trials", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.guarded, args.trials)), indent=2))


if __name__ == "__main__":
    main()
