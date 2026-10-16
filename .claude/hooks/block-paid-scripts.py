"""PreToolUse hook: the scripts that call OpenAI need the user's approval.

A Bash command that runs Python (or `uv run`) anywhere and names a paid entry
point anywhere (a heredoc that imports one counts) is held for the user's
confirmation in the main session and denied inside a subagent, where nobody is
there to approve it. A false match only costs one confirmation.
"""
import json
import re
import sys

PAID = re.compile(r"\b(run_agentdojo|eval_financebench|eval_email|eval_ablation|record_case|eval_gate|rejudge|index_documents"
                  r"|agentdojo\.scripts\.benchmark|build_researcher|submit_document|gfra\.mcp_server|app\.py)\b")
RUNS_PYTHON = re.compile(r"\bpython[0-9.]*\b|\buv\s+run\b")

event = json.load(sys.stdin)
command = event.get("tool_input", {}).get("command", "")
match = PAID.search(command)
if match is None or not RUNS_PYTHON.search(command):
    sys.exit(0)
hit = match.group(0)

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
