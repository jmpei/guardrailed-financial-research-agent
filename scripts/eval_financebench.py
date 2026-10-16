"""FinanceBench accuracy with or without the guardrail. PAID: quote and get approval first."""
import argparse
import asyncio
import json
import os
import time

from langchain_openai import ChatOpenAI

from gfra.app_factory import build_researcher
from gfra.config import DATA_DIR, MODEL
from gfra.data import load_questions
from gfra.financebench_eval import JUDGE_PROMPT, aggregate, evaluate

# Picked against the user's labels on 14 answers: Cohen's kappa 0.74, against 0.20 for gpt-4o-mini.
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4.1-2025-04-14")
RUNS = DATA_DIR.parent / "runs" / "financebench"


async def judge(question, gold, answer, model: str = JUDGE_MODEL):
    llm = ChatOpenAI(model=model, temperature=0)
    reply = await llm.ainvoke(JUDGE_PROMPT.format(question=question, gold=gold, answer=answer))
    return str(reply.content)


async def run(guarded: bool, limit: int | None = None, trials: int = 1, docs=None, agent_model: str = MODEL) -> dict:
    questions = load_questions(DATA_DIR / "financebench" / "financebench_open_source.jsonl")
    if docs:
        questions = [q for q in questions if q.doc_name in docs]
    rows = await evaluate(questions[:limit], build_researcher(guarded=guarded, model=agent_model), judge, trials)
    summary = {**aggregate(rows), "guarded": guarded, "agent_model": agent_model, "judge_model": JUDGE_MODEL}
    RUNS.mkdir(parents=True, exist_ok=True)
    suffix = "" if agent_model == MODEL else f"-agent-{agent_model}"
    out = RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-{'guarded' if guarded else 'unguarded'}{suffix}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guarded", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--docs", nargs="*", help="only questions about these filings")
    parser.add_argument("--agent-model", default=MODEL, help="the model that answers; the policy and judge models stay")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.guarded, args.limit, args.trials, args.docs, args.agent_model)), indent=2))


if __name__ == "__main__":
    main()
