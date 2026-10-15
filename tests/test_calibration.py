import pytest

from gfra.calibration import agreement, cohen_kappa, load_labels, sample_rows


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
