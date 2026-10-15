"""FinanceBench accuracy: the agent answers, an LLM judge compares with the gold answer."""
import math
import re

from gfra.stats import bootstrap_ci, per_item

JUDGE_PROMPT = """You grade answers to questions about company filings.
Question: {question}
Gold answer: {gold}
Model answer: {answer}
The model answer is correct if it states the same fact or number as the gold answer (rounding and units may differ).
It is refused if it declines to answer or says the information is unavailable.
It is unknown if you cannot tell whether it matches the gold answer.
Reply with one line: VERDICT: correct, VERDICT: incorrect, VERDICT: refused, or VERDICT: unknown."""


def parse_verdict(text: str) -> str:
    match = re.search(r"verdict\W*\s*(correct|incorrect|refused|unknown)\b", text, re.IGNORECASE)
    return match.group(1).lower() if match else "unparsed"


def _question_text(q) -> str:
    return f"{q.question}\nUse the document named {q.doc_name}.pdf."


async def evaluate(questions, researcher, judge, trials: int = 1) -> list[dict]:
    rows = []
    for q in questions:
        for trial in range(trials):
            row = {"id": q.id, "trial": trial, "question": q.question, "gold": q.answer}
            try:
                result = await researcher.run(_question_text(q))
            except Exception as exc:
                row.update({"answer": "", "judge_reply": "", "verdict": "error", "error": repr(exc),
                            "tool_calls": [], "cost_usd": 0.0, "latency_s": 0.0, "blocked": 0,
                            "policy_error": None})
                rows.append(row)
                continue
            row.update({"answer": result.answer, "tool_calls": result.tool_calls, "cost_usd": result.cost_usd,
                        "latency_s": result.latency_s, "blocked": len(result.blocked),
                        "policy_error": result.policy_error})
            try:
                reply = await judge(q.question, q.answer, result.answer)
                row.update({"judge_reply": reply, "verdict": parse_verdict(reply)})
            except Exception as exc:
                row.update({"judge_reply": "", "verdict": "error", "error": repr(exc)})
            rows.append(row)
    return rows


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    by_id = per_item(rows, lambda r: r["verdict"] == "correct")
    latencies = sorted(r["latency_s"] for r in rows)

    def rate(verdict):
        return sum(r["verdict"] == verdict for r in rows) / n

    return {
        "n_questions": len(by_id),
        "trials": n // len(by_id),
        "accuracy": rate("correct"),
        "accuracy_ci95": bootstrap_ci([sum(v) / len(v) for v in by_id.values()]),
        "pass_all_k": sum(all(v) for v in by_id.values()) / len(by_id),
        "pass_any_k": sum(any(v) for v in by_id.values()) / len(by_id),
        "refusal_rate": rate("refused"),
        "unknown_rate": rate("unknown"),
        "unparsed_rate": rate("unparsed"),
        "error_rate": rate("error"),
        "policy_error_rate": sum(r.get("policy_error") is not None for r in rows) / n,
        "mean_cost_usd": sum(r["cost_usd"] for r in rows) / n,
        "p95_latency_s": latencies[max(0, math.ceil(0.95 * n) - 1)],
    }


def gate(summary: dict, min_accuracy: float) -> bool:
    return summary["accuracy"] >= min_accuracy
