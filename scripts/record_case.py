"""Record one run of the product agent for the demo's case buttons. PAID: quote and get approval first.

Writes the run in AgentDojo's message format, which gfra.demo_view.replay reads, to data/cases/.
"""
import argparse
import asyncio
import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from gfra.ablation import ATTACKS, load_tasks
from gfra.actions import INJECTIONS, OUTBOX, reset_outbox, set_injection
from gfra.app_factory import build_researcher
from gfra.config import DATA_DIR, MODEL
from gfra.demo_view import CASES_DIR
from gfra.email_eval import grade

TASKS = DATA_DIR / "tasks" / "ablation_tasks.json"


def as_message(m) -> dict:
    if isinstance(m, HumanMessage):
        return {"role": "user", "content": m.content}
    if isinstance(m, AIMessage):
        return {"role": "assistant", "content": m.content or None,
                "tool_calls": [{"function": c["name"], "args": c["args"], "id": c["id"]} for c in m.tool_calls]}
    if isinstance(m, ToolMessage):
        # A Progent block comes back as an ordinary tool message; replay looks for blocks in `error`.
        failed = m.status == "error" or str(m.content).startswith("Blocked by guardrail:")
        return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content, "error": m.content if failed else None}
    raise TypeError(f"unexpected message {type(m).__name__}")


async def record(task_id: str, guarded: bool, attack: str | None, out_dir: Path = CASES_DIR,
                 build=build_researcher) -> Path:
    task = next(t for t in load_tasks(TASKS) if t["id"] == task_id)
    injection = f"{attack}:summary" if attack else None
    researcher = build(guarded=guarded)
    reset_outbox()
    set_injection(injection)
    try:
        result = await researcher.run(task["question"])
    finally:
        set_injection(None)
    graded = grade(task, OUTBOX)
    run = {
        "suite_name": "news", "pipeline_name": MODEL, "user_task_id": task_id,
        "injection_task_id": attack, "attack_type": attack,
        "injections": {"news": INJECTIONS[injection]} if injection else {},
        "messages": [{"role": "system", "content": researcher.system_prompt}, *map(as_message, result.messages)],
        "outbox": list(OUTBOX), "blocked": result.blocked,
        "utility": graded["delivered"], "security": graded["leaked"],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task_id}_{attack or 'no_attack'}_{'progent' if guarded else 'none'}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="a task id from data/tasks/ablation_tasks.json")
    parser.add_argument("--guarded", action="store_true")
    parser.add_argument("--attack", choices=ATTACKS, help="omit for a run without an attack")
    args = parser.parse_args()
    path = asyncio.run(record(args.task, args.guarded, args.attack))
    run = json.loads(path.read_text())
    print(path, "| sent to", [m["to"] for m in run["outbox"]], "| blocked", [b["args"].get("to") for b in run["blocked"]])


if __name__ == "__main__":
    main()
