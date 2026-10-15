import csv

from gfra.error_analysis import count_modes, write_csv


def row(id_, verdict):
    return {"id": id_, "trial": 0, "verdict": verdict, "question": "Capex?", "gold": "$1577M", "answer": "n/a",
            "tool_calls": [{"name": "get_page_content", "args": {"pages": "48"}}], "blocked": 0}


def test_export_keeps_only_failures_and_shows_tool_calls(tmp_path):
    path = tmp_path / "failures.csv"
    assert write_csv([row("q1", "correct"), row("q2", "incorrect"), row("q3", "unparsed")], path) == 2
    rows = list(csv.DictReader(path.open()))
    assert [r["id"] for r in rows] == ["q2", "q3"]
    assert rows[0]["tool_calls"] == 'get_page_content {"pages": "48"}'
    assert rows[0]["note"] == rows[0]["failure_mode"] == ""


def test_export_skips_infrastructure_errors_but_keeps_refusals(tmp_path):
    path = tmp_path / "failures.csv"
    assert write_csv([row("q1", "error"), row("q2", "refused")], path) == 1
    rows = list(csv.DictReader(path.open()))
    assert [r["id"] for r in rows] == ["q2"]


def test_count_modes(tmp_path):
    path = tmp_path / "failures.csv"
    write_csv([row("q1", "incorrect"), row("q2", "incorrect"), row("q3", "refused")], path)
    rows = list(csv.DictReader(path.open()))
    rows[0]["failure_mode"], rows[1]["failure_mode"] = "wrong page", "wrong page"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    assert count_modes(path) == {"wrong page": 2, "(not labelled)": 1}
