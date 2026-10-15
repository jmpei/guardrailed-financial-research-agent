"""Gradio demo: ask a question, toggle the guardrail and a news injection, see what was blocked."""
from collections import defaultdict

import gradio as gr

from gfra.actions import OUTBOX, reset_outbox, set_injection


class RateLimiter:
    def __init__(self, max_requests: int):
        self.max_requests = max_requests
        self.counts: dict[str, int] = defaultdict(int)

    def allow(self, session_id: str) -> bool:
        if self.counts[session_id] >= self.max_requests:
            return False
        self.counts[session_id] += 1
        return True


async def answer(question, guarded, inject, session_id, researchers, limiter) -> tuple[str, str]:
    if not limiter.allow(session_id):
        return "Request limit reached for this session.", ""
    reset_outbox()
    set_injection("exfiltrate_email" if inject else None)
    result = await researchers[bool(guarded)].run(question)
    lines = [f"- `{c['name']}` {c['args']}" for c in result.tool_calls]
    lines += [f"- **Blocked** `{b['tool']}` {b['args']}" for b in result.blocked]
    lines += [f"- Email sent to {m['to']}" for m in OUTBOX]
    lines.append(f"- {result.input_tokens + result.output_tokens} tokens, ${result.cost_usd:.4f}, {result.latency_s:.1f} s")
    return result.answer, "\n".join(lines)


def build_demo(researchers: dict, limiter: RateLimiter) -> gr.Blocks:
    with gr.Blocks(title="Guardrailed Financial Research Agent") as demo:
        question = gr.Textbox(label="Question", value="Summarize 3M's FY2018 capital expenditure "
                              "(document 3M_2018_10K.pdf) and the latest 3M news, and email it to team@bank.com")
        guarded = gr.Checkbox(label="Guardrail (Progent)", value=True)
        inject = gr.Checkbox(label="Inject an attack into the news", value=False)
        run = gr.Button("Run")
        out = gr.Markdown()
        trace = gr.Markdown()

        async def on_run(q, g, i, request: gr.Request):
            return await answer(q, g, i, request.session_hash, researchers, limiter)

        run.click(on_run, [question, guarded, inject], [out, trace], concurrency_limit=1)
    return demo
