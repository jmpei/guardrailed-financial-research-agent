import asyncio

import pytest

from gfra.calibration import agreement, cohen_kappa, load_labels, rejudge_rows, sample_rows


def test_cohen_kappa():
    assert cohen_kappa(["c", "i", "c"], ["c", "i", "c"]) == 1.0
    assert cohen_kappa(["c", "c", "i", "i"], ["c", "i", "c", "i"]) == 0.0
    # 8 of 10 agree; both raters say "c" 5 times: expected 0.5, kappa 0.6
    a = ["c"] * 5 + ["i"] * 5
    b = ["c"] * 4 + ["i"] + ["c"] + ["i"] * 4
    assert cohen_kappa(a, b) == pytest.approx(0.6)


def test_sample_rows_is_fixed_and_capped():
    rows = [{"id": f"q{i}", "trial": 0} for i in range(50)]
    assert sample_rows(rows, 30) == sample_rows(list(reversed(rows)), 30)
    assert len(sample_rows(rows, 30)) == 30 and len(sample_rows(rows, 80)) == 50


def test_agreement_uses_only_labelled_rows(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text('{"id": "q1", "trial": 0, "label": "correct"}\n{"id": "q2", "trial": 0, "label": "incorrect"}\n')
    rows = [{"id": "q1", "trial": 0, "verdict": "correct"}, {"id": "q2", "trial": 0, "verdict": "correct"},
            {"id": "q3", "trial": 0, "verdict": "refused"}]
    result = agreement(load_labels(path), rows)
    assert result["n"] == 2 and result["agreement"] == 0.5
    assert result["confusion"] == {"correct -> correct": 1, "incorrect -> correct": 1}
    assert load_labels(tmp_path / "missing.jsonl") == {}


def test_agreement_without_overlap():
    result = agreement({("q9", 0): "correct"}, [{"id": "q1", "trial": 0, "verdict": "correct"}])
    assert result == {"n": 0, "agreement": None, "cohen_kappa": None, "confusion": {}}


def test_rejudge_rows_skips_errors_and_survives_failures():
    calls = []

    async def fake_judge(question, gold, answer):
        calls.append(question)
        if question == "boom":
            raise RuntimeError("api down")
        return "Verdict: correct"

    rows = [
        {"id": "a", "trial": 0, "question": "ok", "gold": "g", "answer": "x", "judge_reply": "old", "verdict": "incorrect"},
        {"id": "b", "trial": 0, "question": "err", "gold": "g", "answer": "", "judge_reply": "", "verdict": "error", "error": "e"},
        {"id": "c", "trial": 0, "question": "boom", "gold": "g", "answer": "x", "judge_reply": "old", "verdict": "correct"},
    ]
    out = asyncio.run(rejudge_rows(rows, fake_judge))
    assert out[0]["verdict"] == "correct" and out[0]["judge_reply"] == "Verdict: correct"
    assert out[1] == rows[1] and "err" not in calls
    assert out[2]["verdict"] == "error" and "api down" in out[2]["error"]
