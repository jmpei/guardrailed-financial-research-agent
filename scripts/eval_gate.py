"""CI gate (PAID, manual trigger): the guarded agent on the gate filings and on the email cases."""
import asyncio
import sys

import eval_email
import eval_financebench

from gfra.email_eval import gate as email_gate
from gfra.financebench_eval import gate as accuracy_gate

GATE_DOCS = ("AMD_2022_10K", "AMERICANEXPRESS_2022_10K")  # 14 FinanceBench questions
TRIALS = 1
# From the approved debug run on GATE_DOCS and the email cases: MIN_ACCURACY is the lower end of
# accuracy_ci95, MIN_DELIVERY the delivery_rate. A bar set from a measured run can pass.
MIN_ACCURACY = 0.28  # accuracy 0.57, accuracy_ci95 [0.29, 0.86], judged by gpt-4.1
MIN_DELIVERY = 1.0


def check_thresholds() -> None:
    if MIN_ACCURACY is None or MIN_DELIVERY is None:
        sys.exit("Set MIN_ACCURACY and MIN_DELIVERY from the approved debug run first.")


async def run_both() -> tuple[dict, dict]:
    # One event loop for both runs: langchain-openai keeps one httpx client per process.
    accuracy = await eval_financebench.run(guarded=True, trials=TRIALS, docs=GATE_DOCS)
    email = await eval_email.run(guarded=True, trials=TRIALS)
    return accuracy, email


def main() -> None:
    check_thresholds()
    if "--check-thresholds" in sys.argv[1:]:
        return
    accuracy, email = asyncio.run(run_both())
    print(accuracy, email)
    sys.exit(0 if accuracy_gate(accuracy, MIN_ACCURACY) and email_gate(email, MIN_DELIVERY) else 1)


if __name__ == "__main__":
    main()
