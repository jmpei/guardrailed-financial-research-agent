"""PreToolUse hook: the scripts that call OpenAI need the user's approval.

A Bash segment that runs Python (or `uv run`) and names one of the paid scripts
is held for the user's confirmation in the main session and denied inside a
subagent, where nobody is there to approve it.
"""
import json
import re
import sys

PAID = re.compile(r"\b(run_agentdojo|eval_financebench|eval_email|eval_gate|index_documents)\b")
RUNS_PYTHON = re.compile(r"\bpython[0-9.]*\b|\buv\s+run\b")

event = json.load(sys.stdin)
command = event.get("tool_input", {}).get("command", "")
segments = re.split(r"&&|\|\||[;|\n]", command)
hit = next((s.strip() for s in segments if PAID.search(s) and RUNS_PYTHON.search(s)), None)
if hit is None:
    sys.exit(0)

in_subagent = "agent_id" in event
reason = (
    f"`{hit}` runs a script that spends OpenAI tokens. "
    + ("Subagents never run paid scripts; report back to the main session instead."
       if in_subagent else "Quote the cost and get the user's explicit OK first.")
)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny" if in_subagent else "ask",
    "permissionDecisionReason": reason,
}}))
