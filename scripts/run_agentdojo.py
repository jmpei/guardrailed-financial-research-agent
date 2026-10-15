"""Run AgentDojo: --config none|progent, --subset (debug) or full. PAID: quote and get approval first."""
import argparse
import json
import subprocess
from pathlib import Path

from gfra.agentdojo_eval import commands, fetch_published, sample_subset, summarize
from gfra.config import MODEL


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["none", "progent"], required=True)
    parser.add_argument("--subset", action="store_true", help="stratified 5 user x 5 injection tasks per suite")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--force-rerun", action="store_true", help="re-run tasks that already have a log")
    args = parser.parse_args()
    subset = sample_subset() if args.subset else None
    logdir = Path("runs") / "agentdojo" / args.config
    if not args.summarize_only:
        for env, argv in commands(args.config, subset, logdir, force_rerun=args.force_rerun):
            subprocess.run(argv, env=env, check=True)
    # Printed before the download, so a network failure there cannot lose the paid result.
    print(json.dumps({"ours": summarize(logdir, MODEL, subset)}, indent=2), flush=True)
    if subset:
        published = fetch_published(subset, Path("runs") / "agentdojo" / "published")
        print(json.dumps({"published": summarize(published, MODEL, subset)}, indent=2))


if __name__ == "__main__":
    main()
