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
MIN_ACCURACY = None
MIN_DELIVERY = None


def main() -> None:
    if MIN_ACCURACY is None or MIN_DELIVERY is None:
        sys.exit("Set MIN_ACCURACY and MIN_DELIVERY from the approved debug run first.")
    accuracy = asyncio.run(eval_financebench.run(guarded=True, trials=TRIALS, docs=GATE_DOCS))
    email = asyncio.run(eval_email.run(guarded=True, trials=TRIALS))
    print(accuracy, email)
    sys.exit(0 if accuracy_gate(accuracy, MIN_ACCURACY) and email_gate(email, MIN_DELIVERY) else 1)


if __name__ == "__main__":
    main()
