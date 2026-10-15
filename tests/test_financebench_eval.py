import pytest

from gfra.agent import ResearchResult
from gfra.data import Question
from gfra.financebench_eval import aggregate, evaluate, gate, parse_verdict


def test_parse_verdict():
    assert parse_verdict("VERDICT: correct") == "correct"
    assert parse_verdict("verdict: INCORRECT because ...") == "incorrect"
    assert parse_verdict("VERDICT: refused") == "refused"
    assert parse_verdict("VERDICT: unknown") == "unknown"
    assert parse_verdict("no idea") == "unparsed"


class FakeResearcher:
    async def run(self, question):
        return ResearchResult(answer="$1577M", tool_calls=[], blocked=[], input_tokens=10,
                              output_tokens=1, cost_usd=0.002, latency_s=1.0)


async def test_evaluate_and_aggregate():
    qs = [Question("fb_1", "3M_2018_10K", "Capex?", "$1577.00", "metrics-generated"),
          Question("fb_2", "3M_2018_10K", "Debt?", "$13B", "novel-generated")]

    async def judge(question, gold, answer):
        return "VERDICT: correct" if gold == "$1577.00" else "I cannot grade this"

    rows = await evaluate(qs, FakeResearcher(), judge)
    summary = aggregate(rows)
    assert summary["n_questions"] == 2 and summary["trials"] == 1
    assert summary["accuracy"] == 0.5 and summary["unparsed_rate"] == 0.5
    assert summary["mean_cost_usd"] == 0.002
    assert rows[0]["answer"] == "$1577M" and rows[0]["judge_reply"] == "VERDICT: correct"
    assert rows[0]["tool_calls"] == []
    assert gate(summary, min_accuracy=0.5) and not gate(summary, min_accuracy=0.6)


async def test_trials_give_pass_all_and_pass_any():
    q = Question("fb_1", "3M_2018_10K", "Capex?", "$1577.00", "metrics-generated")
    replies = iter(["VERDICT: correct", "VERDICT: incorrect", "VERDICT: correct"])

    async def judge(question, gold, answer):
        return next(replies)

    summary = aggregate(await evaluate([q], FakeResearcher(), judge, trials=3))
    assert summary["trials"] == 3
    assert summary["accuracy"] == pytest.approx(2 / 3)
    assert summary["pass_all_k"] == 0 and summary["pass_any_k"] == 1
