"""Drive Progent's AgentDojo fork: no defense vs Progent, on a stratified subset or the full benchmark."""
import json
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

from gfra.config import MODEL

SUITES = ("banking", "slack", "travel", "workspace")
ATTACK = "important_instructions"
BENCHMARK_VERSION = "v1.1.2"
UPSTREAM_RUNS = "https://raw.githubusercontent.com/ethz-spylab/agentdojo/main/runs"


def _task_ids(suite: str) -> tuple[list[str], list[str]]:
    from agentdojo.task_suite.load_suites import get_suite
    s = get_suite(BENCHMARK_VERSION, suite)
    return sorted(s.user_tasks), sorted(s.injection_tasks)


def sample_subset(seed: int = 0, user_tasks_per_suite: int = 5, injection_tasks_per_suite: int = 5) -> dict:
    rng = random.Random(seed)
    subset = {}
    for suite in SUITES:
        users, injections = _task_ids(suite)
        subset[suite] = {
            "user_tasks": sorted(rng.sample(users, user_tasks_per_suite)),
            "injection_tasks": sorted(rng.sample(injections, injection_tasks_per_suite)),
        }
    return subset


def commands(config: str, subset: dict | None, logdir: Path) -> list[tuple[dict, list[str]]]:
    out = []
    for suite in SUITES:
        if config == "none":
            env = {"SECAGENT_GENERATE": "False"}
        else:
            env = {"SECAGENT_SUITE": suite, "SECAGENT_GENERATE": "True", "SECAGENT_UPDATE": "True",
                   "SECAGENT_IGNORE_UPDATE_ERROR": "True", "SECAGENT_POLICY_MODEL": MODEL}
        base = [sys.executable, "-m", "agentdojo.scripts.benchmark", "-s", suite, "--model", MODEL,
                "--benchmark-version", BENCHMARK_VERSION, "--logdir", str(logdir)]
        if subset:
            for task in subset[suite]["user_tasks"]:
                base += ["-ut", task]
        attack = base + ["--attack", ATTACK]
        if subset:
            for task in subset[suite]["injection_tasks"]:
                attack += ["-it", task]
        out += [(env, base), (env, attack)]
    return out


def _in_subset(row: dict, subset: dict | None) -> bool:
    if not subset:
        return True
    s = subset[row["suite_name"]]
    if row["user_task_id"] not in s["user_tasks"]:
        return False
    return row["injection_task_id"] is None or row["injection_task_id"] in s["injection_tasks"]


def summarize(run_dir: Path, pipeline: str, subset: dict | None = None) -> dict:
    benign, attacked = [], []
    for path in Path(run_dir, pipeline).rglob("*.json"):
        row = json.loads(path.read_text())
        # An attack run also logs each injection task solved as a user task; those are not benchmark tasks.
        if row["user_task_id"].startswith("injection_task") or not _in_subset(row, subset):
            continue
        (attacked if row.get("injection_task_id") else benign).append(row)
    rate = lambda rows, key: sum(bool(r[key]) for r in rows) / len(rows) if rows else float("nan")
    return {
        "utility": rate(benign, "utility"),
        "utility_under_attack": rate(attacked, "utility"),
        "attack_success_rate": rate(attacked, "security"),
        "n_benign": len(benign),
        "n_attack": len(attacked),
    }


def fetch_published(subset: dict, dest: Path, pipeline: str = MODEL, attack: str = ATTACK) -> Path:
    """Download AgentDojo's own published runs for the same tasks (free), for the sanity check."""
    for suite, s in subset.items():
        for user_task in s["user_tasks"]:
            targets = [("none", "none")] + [(attack, inj) for inj in s["injection_tasks"]]
            for folder, name in targets:
                rel = f"{pipeline}/{suite}/{user_task}/{folder}/{name}.json"
                out = dest / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                try:
                    urllib.request.urlretrieve(f"{UPSTREAM_RUNS}/{rel}", out)
                except urllib.error.HTTPError:
                    out.unlink(missing_ok=True)
    return dest
