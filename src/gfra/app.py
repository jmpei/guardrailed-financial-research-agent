"""Gradio demo: ask a question, toggle the guardrail and a news injection, see what was blocked."""
import gradio as gr

from gfra.actions import OUTBOX, reset_outbox, set_injection


class RateLimiter:
    """Per-session cap plus an optional process-wide cap on allowed requests."""

    def __init__(self, max_requests: int, max_total: int | None = None):
        self.max_requests = max_requests
        self.max_total = max_total
        self.total = 0
        self.counts: dict[str, int] = {}

    def allow(self, session_id: str) -> bool:
        if self.max_total is not None and self.total >= self.max_total:
            return False
        if self.counts.get(session_id, 0) >= self.max_requests:
            return False
        self.counts[session_id] = self.counts.get(session_id, 0) + 1
        self.total += 1
        return True


def _code(value) -> str:
    """Render untrusted text as a Markdown code span that cannot be closed early."""
    text = " ".join(str(value).replace("`", "'").split())
    return f"`` {text} ``"


async def answer(question, guarded, inject, session_id, researchers, limiter) -> tuple[str, str]:
    if not limiter.allow(session_id):
        return "Request limit reached; try again later.", ""
    try:
        reset_outbox()
        set_injection("exfiltrate_email" if inject else None)
        result = await researchers[bool(guarded)].run(question)
        lines = [f"- `{c['name']}` {_code(c['args'])}" for c in result.tool_calls]
        lines += [f"- **Blocked** `{b['tool']}` {_code(b['args'])}" for b in result.blocked]
        lines += [f"- Email sent to {_code(m['to'])}" for m in OUTBOX]
        lines.append(f"- {result.input_tokens + result.output_tokens} tokens, ${result.cost_usd:.4f}, {result.latency_s:.1f} s")
        return result.answer, "\n".join(lines)
    except Exception as e:
        return f"Error: {e}", ""
    finally:
        set_injection(None)


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
