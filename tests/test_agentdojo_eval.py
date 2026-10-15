from pathlib import Path

from gfra.agentdojo_eval import SUITES, commands, sample_subset, summarize

FIX = Path(__file__).parent / "fixtures" / "agentdojo"


def test_summarize_counts_utility_and_attack_success():
    s = summarize(FIX, "gpt-4o-mini-2024-07-18")
    assert s["n_benign"] == 1 and s["n_attack"] == 2
    assert s["utility"] == 1.0
    assert s["utility_under_attack"] == 0.5
    # AgentDojo marks a successful injection with security == true
    assert s["attack_success_rate"] == 0.5
    assert s["n_error"] == 1


def test_sample_subset_is_stratified_and_deterministic():
    a, b = sample_subset(seed=0), sample_subset(seed=0)
    assert a == b
    assert set(a) == set(SUITES)
    for suite in SUITES:
        assert len(a[suite]["user_tasks"]) == 5
        assert len(a[suite]["injection_tasks"]) == 5


def test_progent_commands_set_suite_env_and_baseline_does_not(tmp_path):
    sub = sample_subset(seed=0)
    base = commands("none", sub, tmp_path)
    prog = commands("progent", sub, tmp_path)
    assert len(base) == len(prog) == 2 * len(SUITES)  # benign run + attack run per suite
    assert all(env["SECAGENT_GENERATE"] == "False" and "SECAGENT_SUITE" not in env for env, _ in base)
    assert all(env["SECAGENT_SUITE"] in SUITES and env["SECAGENT_POLICY_MODEL"] == "gpt-4o-mini-2024-07-18" for env, _ in prog)
    assert all("--model" in argv and "gpt-4o-mini-2024-07-18" in argv for _, argv in prog)


def test_child_env_drops_inherited_secagent_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("SECAGENT_SUITE", "banking")
    monkeypatch.setenv("SECAGENT_UPDATE", "True")
    monkeypatch.setenv("UNRELATED_VAR", "kept")
    base = commands("none", None, tmp_path)
    prog = commands("progent", None, tmp_path)
    for env, _ in base:
        assert not any(k.startswith("SECAGENT_") and k != "SECAGENT_GENERATE" for k in env)
        assert env["UNRELATED_VAR"] == "kept"
    for (env, argv), suite in zip(prog, [s for s in SUITES for _ in range(2)]):
        assert env["SECAGENT_SUITE"] == suite == argv[argv.index("-s") + 1]
        assert env["SECAGENT_UPDATE"] == "True"


def test_force_rerun_flag_only_when_asked(tmp_path):
    assert all("--force-rerun" not in argv for _, argv in commands("none", None, tmp_path))
    assert all("--force-rerun" in argv for _, argv in commands("none", None, tmp_path, force_rerun=True))
