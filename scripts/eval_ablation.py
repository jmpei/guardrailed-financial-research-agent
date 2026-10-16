"""Ablation on our own agent: prompt defense x Progent, AgentDojo attacks in the news. PAID: quote and get approval first."""
import argparse
import asyncio
import json
import time

from gfra.ablation import ATTACKS, CONFIGS, GOALS, SYSTEM_PROMPTS, aggregate, load_tasks, make_cases
from gfra.actions import set_news_format
from gfra.app_factory import build_researcher
from gfra.config import DATA_DIR, MODEL
from gfra.email_eval import evaluate

RUNS = DATA_DIR.parent / "runs" / "ablation"


async def run(configs: str = "ABCD", trials: int = 1, tasks: str | None = None, news_format: str = "json",
              system_prompt: str = "agentdojo", goal: str = "summary", attacks: str | None = None,
              clean: bool = True) -> dict:
    """`tasks`: comma-separated task ids to run (default all). `news_format`: how fetch_news returns items.
    `system_prompt`: the base prompt under the defense lines: "product", or a key of SYSTEM_PROMPTS. The default is
    AgentDojo's, so A matches AgentDojo's no-defense baseline. `goal`: a key of GOALS.
    `attacks`: comma-separated attack names (default all). `clean`: also run each task once without an attack."""
    prompt = None if system_prompt == "product" else SYSTEM_PROMPTS[system_prompt]
    set_news_format(news_format)
    all_tasks = load_tasks(DATA_DIR / "tasks" / "ablation_tasks.json")
    cases = make_cases([t for t in all_tasks if tasks is None or t["id"] in tasks.split(",")], goal,
                       ATTACKS if attacks is None else tuple(a for a in attacks.split(",") if a), clean)
    summary, rows = {}, []
    # One config at a time, in one event loop: the Progent policy lives in module globals.
    for name in configs:
        config_rows = await evaluate(cases, build_researcher(**CONFIGS[name], system_prompt=prompt), trials)
        summary[name] = {**CONFIGS[name], **aggregate(config_rows, cases)}
        rows += [{"config": name, **r} for r in config_rows]
    RUNS.mkdir(parents=True, exist_ok=True)
    set_news_format("json")
    suffix = ("-subset" if tasks else "") + ("" if news_format == "json" else f"-news-{news_format}") \
        + f"-prompt-{system_prompt}" + ("" if goal == "summary" else f"-goal-{goal}") \
        + ("" if attacks is None else f"-attacks-{attacks.replace(',', '+') or 'none'}") + ("" if clean else "-attacked-only")
    out = RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-{configs}{suffix}.json"
    out.write_text(json.dumps({"summary": summary, "agent_model": MODEL, "trials": trials, "news_format": news_format,
                               "system_prompt": system_prompt, "goal": goal,
                               "attacks": attacks or ",".join(ATTACKS), "rows": rows}, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", default="ABCD", help="any of A (no defense), B (prompt), C (Progent), D (both)")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--tasks", help="comma-separated task ids from data/tasks/ablation_tasks.json (default all)")
    parser.add_argument("--news-format", choices=("json", "yaml"), default="json",
                        help="yaml: fetch_news returns items the way AgentDojo formats tool results")
    parser.add_argument("--system-prompt", choices=("product", *SYSTEM_PROMPTS), default="agentdojo",
                        help="base prompt under the defense lines: agentdojo (default, AgentDojo's baseline), product, none")
    parser.add_argument("--goal", choices=tuple(GOALS), default="summary", help="what the attack asks the agent to do")
    parser.add_argument("--attacks", help=f"comma-separated, from {','.join(ATTACKS)} (default all)")
    parser.add_argument("--clean-only", action="store_true", help="only the runs without an attack (false blocks)")
    parser.add_argument("--attacked-only", action="store_true",
                        help="skip the runs without an attack (they only matter where Progent can block: C, D)")
    args = parser.parse_args()
    if set(args.configs) - set(CONFIGS):
        parser.error(f"--configs takes letters from {''.join(CONFIGS)}")
    if args.attacks and set(args.attacks.split(",")) - set(ATTACKS):
        parser.error(f"--attacks takes names from {','.join(ATTACKS)}")
    if args.clean_only and (args.attacked_only or args.attacks):
        parser.error("--clean-only runs no attacks: drop --attacks and --attacked-only")
    if args.clean_only:
        args.attacks = ""
    print(json.dumps(asyncio.run(run(args.configs, args.trials, args.tasks, args.news_format, args.system_prompt, args.goal,
                                     args.attacks, not args.attacked_only)), indent=2))


if __name__ == "__main__":
    main()
