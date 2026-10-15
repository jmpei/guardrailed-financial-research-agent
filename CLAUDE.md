# CLAUDE.md

## Commands

| What | Command |
|---|---|
| Install | `uv sync` |
| Tests (no network, fake models) | `uv run pytest -q` |
| Download FinanceBench PDFs (free) | `uv run python scripts/download_financebench.py` |

## Paid runs

- Any script that calls OpenAI or PageIndex costs money: `scripts/index_documents.py` and every eval runner (`run_agentdojo`, `eval_financebench`, `eval_email`, `eval_gate`). Quote the cost and get the user's explicit OK before each run.
- `.claude/hooks/block-paid-scripts.py` enforces this: it asks the user in the main session and denies the call in a subagent.
- Tests never spend money: `tests/conftest.py` replaces `OPENAI_API_KEY` with a fake key and removes the Langfuse keys.

## Progent (`secagent`)

- Pinned at `sunblaze-ucb/progent@5be7b63`. Never edit files under `.venv/`.
- `secagent` reads its `SECAGENT_*` environment variables once, at import time. Set them before the first `import secagent` (`src/gfra/guard.py` does this).
- The policy lives in module globals: run one request at a time per process.
- The guard fails closed: if policy generation fails, `send_email` is blocked and the read-only tools still work.
- Only `send_email` goes through the generated policy. The read-only tools are listed in `READ_ONLY_TOOLS` in `src/gfra/config.py`.

## Model

`gpt-4o-mini-2024-07-18` for the agent and the policy (`MODEL` in `src/gfra/config.py`).
