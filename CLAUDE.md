# CLAUDE.md

## Commands

| What | Command |
|---|---|
| Install | `uv sync` |
| Tests (fake models, no paid calls) | `uv run pytest -q` |
| End-to-end demo tests | need Google Chrome installed (Playwright uses channel "chrome") |
| Download FinanceBench PDFs (free) | `uv run python scripts/download_financebench.py` |
| Check a run's page citations (free) | `uv run python scripts/check_citations.py runs/financebench/<run>.json` |

## Paid runs

- Anything that calls OpenAI or PageIndex costs money: `scripts/index_documents.py`, every eval runner (`run_agentdojo`, `eval_financebench`, `eval_email`, `eval_gate`, `rejudge`, `python -m agentdojo.scripts.benchmark`), and every request to `app.py` or `python -m gfra.mcp_server`. Quote the cost and get the user's explicit OK before each run.
- `.claude/hooks/block-paid-scripts.py` holds any command that runs Python and names one of these anywhere (heredocs included): it asks the user in the main session and denies the call in a subagent.
- Tests never spend money: `tests/conftest.py` replaces `OPENAI_API_KEY` with a fake key and removes the Langfuse keys.

## Progent (`secagent`)

- Pinned at `sunblaze-ucb/progent@5be7b63`. Never edit files under `.venv/`.
- `secagent` reads its `SECAGENT_*` environment variables once, at import time; `SECAGENT_UPDATE` is the exception, read by the guard on every tool call. Set them before the first `import secagent` (`src/gfra/guard.py` does this).
- The policy lives in module globals: run one request at a time per process.
- The guard fails closed: if policy generation fails, `send_email` is blocked and the read-only tools still work.
- Only `send_email` goes through the generated policy. The read-only tools are listed in `READ_ONLY_TOOLS` in `src/gfra/config.py`.

## Model

- `gpt-4o-mini-2024-07-18` for the agent and the policy (`MODEL` in `src/gfra/config.py`).
- `gpt-4.1-2025-04-14` for the FinanceBench judge (`JUDGE_MODEL` in `scripts/eval_financebench.py`): a different model from the agent, checked against the user's labels.
- `eval_financebench.py --agent-model <model>` swaps only the answering model for a comparison run; the policy and judge models stay.
