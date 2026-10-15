"""Run AgentDojo: --config none|progent, --subset (debug) or full. PAID: quote and get approval first."""
import argparse
import json
import os
import subprocess
from pathlib import Path

from gfra.agentdojo_eval import commands, fetch_published, sample_subset, summarize
from gfra.config import MODEL


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["none", "progent"], required=True)
    parser.add_argument("--subset", action="store_true", help="stratified 5 user x 5 injection tasks per suite")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    subset = sample_subset() if args.subset else None
    logdir = Path("runs") / "agentdojo" / args.config
    if not args.summarize_only:
        for env, argv in commands(args.config, subset, logdir):
            subprocess.run(argv, env={**os.environ, **env}, check=True)
    result = {"ours": summarize(logdir, MODEL, subset)}
    if subset:
        published = fetch_published(subset, Path("runs") / "agentdojo" / "published")
        result["published"] = summarize(published, MODEL, subset)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
