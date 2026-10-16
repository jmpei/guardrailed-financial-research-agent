"""Gradio demo: ask a question, toggle the guardrail and a news injection, see what was blocked.

Styled after Cohere's design system (DESIGN.md at the repo root): white canvas, near-black pill
action, dark agent-console panel for the trace, coral marker for a blocked call.
"""
import json
import logging

import gradio as gr

from gfra.actions import INJECTIONS, NEWS, OUTBOX, reset_outbox, set_injection
from gfra.demo_view import (SCENARIOS, answer_head, finance_golds, news_html, recording_question, recordings, replay,
                             samples, sources_sidebar, stats_html, trace_html)
from gfra.financebench_eval import parse_verdict

logger = logging.getLogger(__name__)

# The attack the "Inject an attack" toggle hides in the news: the one that fooled this agent most in the ablation.
DEMO_INJECTION = "important_instructions:summary"

DISPLAY_FONT = "'Space Grotesk', Inter, ui-sans-serif, system-ui, sans-serif"
MONO_FONT = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

_LIGHT = {
    "body_background_fill": "#ffffff",
    "body_text_color": "#212121",
    "body_text_color_subdued": "#616161",
    "background_fill_primary": "#ffffff",
    "background_fill_secondary": "#ffffff",
    "block_background_fill": "#ffffff",
    "block_border_color": "#d9d9dd",
    "block_label_text_color": "#75758a",
    "block_title_text_color": "#75758a",
    "border_color_primary": "#d9d9dd",
    "input_background_fill": "#ffffff",
    "input_border_color": "#d9d9dd",
    "input_border_color_focus": "#9b60aa",
    "checkbox_background_color": "#ffffff",
    "checkbox_background_color_selected": "#17171c",
    "checkbox_border_color": "#93939f",
    "checkbox_border_color_selected": "#17171c",
    "checkbox_label_text_color": "#212121",
    "button_primary_background_fill": "#17171c",
    "button_primary_background_fill_hover": "#000000",
    "button_primary_text_color": "#ffffff",
    "button_primary_border_color": "#17171c",
    "link_text_color": "#1863dc",
}
# The design system is light only: dark-mode visitors get the same palette.
THEME = gr.themes.Base(
    font=[gr.themes.GoogleFont("Inter"), "Arial", "ui-sans-serif", "system-ui"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
    radius_size=gr.themes.sizes.radius_sm,
).set(
    **_LIGHT,
    **{f"{name}_dark": value for name, value in _LIGHT.items()},
    block_border_width="1px",
    block_shadow="none",
    button_large_radius="32px",
    button_primary_shadow="none",
    input_radius="4px",
)

CSS = f"""
.gradio-container {{ max-width: 1180px !important; margin: 0 auto; padding-top: 48px !important; }}
.html-container {{ padding: 0 !important; }}
.mono, #header .eyebrow, .section-title {{
  font-family: {MONO_FONT}; font-size: 12px; letter-spacing: 0.28px; text-transform: uppercase; color: #75758a;
}}
#header h1 {{
  font-family: {DISPLAY_FONT}; font-weight: 400; font-size: 48px; line-height: 1.05; letter-spacing: -0.96px;
  color: #000000; margin: 12px 0 16px;
}}
#header p {{ font-size: 17px; line-height: 1.7; color: #616161; margin: 0; }}
#scenarios {{ gap: 10px; flex-wrap: wrap; margin-top: 24px; }}
#scenarios .pill {{ flex: none !important; min-width: 0 !important; width: auto !important; background: transparent !important; color: #17171c !important; border: 1px solid #17171c !important; border-radius: 30px !important; padding: 6px 16px !important; font-size: 14px !important; font-weight: 500 !important; box-shadow: none !important; }}
#scenarios .pill:hover {{ background: #17171c !important; color: #ffffff !important; }}
.scenario-note {{ font-size: 14px; color: #616161; margin: 8px 0 0; }}
#news-panel, #ask, #result {{ border: 1px solid #d9d9dd !important; border-radius: 22px !important; padding: 24px !important; }}
.panel-title {{ font-family: {DISPLAY_FONT}; font-size: 24px; color: #000000; margin-bottom: 4px; }}
.panel-sub {{ font-size: 14px; color: #616161; margin-bottom: 12px; }}
#sources-drawer {{
  position: fixed; top: 120px; left: 0; z-index: 50; display: flex; align-items: flex-start;
  transform: translateX(-340px); transition: transform 0.2s ease;
}}
#sources-drawer:hover {{ transform: translateX(0); }}
#sources-drawer .drawer-body {{
  order: 1; width: 340px; max-height: 70vh; overflow-y: auto; background: #ffffff;
  border: 1px solid #d9d9dd; border-left: none; border-radius: 0 8px 8px 0; padding: 16px;
}}
#sources-drawer .drawer-tab {{
  order: 2; writing-mode: vertical-rl; background: #17171c; color: #ffffff; padding: 16px 8px;
  border-radius: 0 8px 8px 0; cursor: default;
}}
.drawer-title {{ font-size: 14px; color: #616161; margin-bottom: 8px; }}
#sources-drawer a {{
  display: flex; justify-content: space-between; gap: 12px; padding: 10px 0; border-top: 1px solid #d9d9dd;
  color: #212121; text-decoration: none; font-size: 15px;
}}
#sources-drawer a span.mono {{ flex: none; white-space: nowrap; }}
#sources-drawer a:hover span:first-child {{ color: #1863dc; text-decoration: underline; }}
.ticker {{ height: 420px; overflow: hidden; }}
.ticker-track {{ animation: ticker 40s linear infinite; }}
.ticker:hover .ticker-track {{ animation-play-state: paused; }}
@keyframes ticker {{ from {{ transform: translateY(0); }} to {{ transform: translateY(-50%); }} }}
@media (prefers-reduced-motion: reduce) {{ .ticker {{ overflow-y: auto; }} .ticker-track {{ animation: none; }} }}
.news-row {{ display: block; text-align: left; border: 1px solid #d9d9dd; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; background: #ffffff; color: inherit; }}
.news-row:hover {{ background: #f1f5ff; border-color: #1863dc; }}
#news, #news * {{ text-align: left; }}
.news-row:hover .news-title {{ color: #1863dc; text-decoration: underline; }}
.news-dialog {{ display: none; position: fixed; inset: 0; z-index: 100; place-items: center; }}
.news-dialog:target {{ display: grid; }}
.news-dialog .backdrop {{ position: absolute; inset: 0; background: rgba(23, 23, 28, 0.55); }}
.news-dialog article {{
  position: relative; width: min(640px, calc(100vw - 32px)); max-height: 80vh; overflow-y: auto;
  background: #ffffff; border-radius: 22px; padding: 32px;
}}
.news-dialog h2 {{ font-family: {DISPLAY_FONT}; font-weight: 400; font-size: 32px; line-height: 1.2; letter-spacing: -0.32px; margin: 8px 0 12px; }}
.news-dialog p {{ font-size: 18px; line-height: 1.5; color: #212121; }}
.news-dialog article {{ text-align: left; }}
.news-dialog .source {{
  display: inline-block; margin-top: 20px; padding: 8px 0; min-width: 240px; text-align: center;
  background: transparent; color: #212121; font-size: 16px; text-decoration: none; border-bottom: 1px solid #212121;
}}
.news-dialog .source:hover {{ border-bottom-width: 2px; }}
.news-dialog .close {{ display: block; margin-top: 20px; color: #17171c; text-align: left; }}
.news-meta .chip {{ margin-right: 0; min-width: 136px; text-align: center; box-sizing: border-box; }}
.news-row, .news-row * {{ text-decoration: none !important; }}
.news-row:hover .news-title {{ text-decoration: underline !important; }}
.news-meta {{ display: flex; gap: 8px; align-items: center; }}
.news-title {{ font-size: 16px; color: #000000; margin: 4px 0; }}
.news-body {{ font-size: 14px; color: #616161; }}
.injection {{ margin-top: 10px; border: 1px solid #b30000; background: #fff4f2; border-radius: 8px; padding: 10px 12px; }}
.injection pre {{ white-space: pre-wrap; margin: 8px 0 0; font-family: {MONO_FONT}; font-size: 12px; color: #b30000; background: none; }}
.chip {{
  display: inline-block; font-family: {MONO_FONT}; font-size: 11px; letter-spacing: 0.28px; text-transform: uppercase;
  padding: 2px 10px; border-radius: 32px; margin-right: 8px;
}}
.chip-red {{ background: #b30000; color: #ffffff; }}
.chip-green {{ background: #1aae39; color: #ffffff; }}
.args {{ font-family: {MONO_FONT}; font-size: 12px; color: #616161; }}
.chip-warn {{ background: #ff7759; color: #17171c; }}
.inline-inject {{ display: inline; }}
.inline-inject summary {{ display: inline-block; cursor: pointer; list-style: none; }}
.inline-inject summary::-webkit-details-marker {{ display: none; }}
.inline-inject[open] pre {{ display: block; margin: 10px 0 4px; padding: 10px 12px; border: 1px solid #b30000; background: #fff4f2; border-radius: 8px; white-space: pre-wrap; font-family: {MONO_FONT}; font-size: 12px; color: #b30000; }}
.chip-done {{ border: 1px solid #17171c; color: #17171c; }}
#ask {{ margin-top: 24px; }}
#run {{ align-self: flex-start; width: auto; min-width: 160px; max-width: 200px; flex-grow: 0; }}
#result {{ margin-top: 24px; }}
.agent-head {{ display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }}
.agent-mark {{
  width: 44px; height: 44px; border-radius: 8px; background: #17171c; color: #ffffff; display: grid; place-items: center;
  font-family: {DISPLAY_FONT}; font-size: 22px;
}}
.agent-name {{ font-family: {DISPLAY_FONT}; font-size: 28px; letter-spacing: -0.28px; color: #000000; }}
.answer-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.answer-head .section-title {{ margin-bottom: 0; }}
.pop {{ position: relative; display: inline-block; }}
.pop summary {{ list-style: none; cursor: pointer; }}
.pop summary::-webkit-details-marker {{ display: none; }}
.pill-sm {{ display: inline-block; border: 1px solid #17171c; border-radius: 30px; padding: 2px 12px; font-size: 13px; font-weight: 500; color: #17171c; }}
.pill-sm:hover {{ background: #17171c; color: #ffffff; }}
.pop-body {{
  position: absolute; left: 0; top: calc(100% + 6px); z-index: 30; width: min(520px, 80vw); padding: 14px 16px;
  background: #ffffff; border: 1px solid #d9d9dd; border-radius: 8px; font-size: 15px; line-height: 1.5; color: #212121;
}}
.pop-body .mono {{ margin-bottom: 6px; }}
.pop-body pre {{ white-space: pre-wrap; font-family: {MONO_FONT}; font-size: 13px; margin: 0; }}
#answer-head, #answer-head .html-container, #answer-box {{ overflow: visible !important; }}
#answer-box {{ border: 1px solid #d9d9dd !important; border-radius: 8px !important; padding: 20px 24px !important; }}
#answer {{ font-size: 16px; line-height: 1.6; color: #212121; margin-bottom: 16px; }}
#answer p {{ margin: 0 0 8px; }}
.section-title {{ margin-bottom: 8px; }}
#stats {{ align-self: flex-end; }}
#toggles, #toggles .form, .form:has(#guardrail) {{ overflow: visible !important; }}
#guardrail, #inject {{ position: relative; overflow: visible !important; }}
#guardrail:hover::after, #inject:hover::after {{
  position: absolute; left: 12px; top: calc(100% + 6px); z-index: 20; width: 340px; padding: 10px 14px;
  background: #17171c; color: #ffffff; font-size: 13px; line-height: 1.5; border-radius: 8px;
}}
#guardrail:hover::after {{ content: "Progent turns your question into a policy and checks every tool call against it. Calls your question did not ask for are blocked."; }}
#inject:hover::after {{ content: "Hides AgentDojo's important_instructions attack in the first news item of each company: it asks the agent to email the summary to an address your question did not name."; }}
.steps {{ margin: 8px 0 16px; padding-left: 20px; }}
.steps li {{ display: flex; justify-content: space-between; gap: 16px; padding: 8px 0; border-bottom: 1px solid #f2f2f2; font-size: 15px; }}
.steps .tool {{ flex: none; }}
.outcome {{ border-radius: 8px; padding: 12px 14px; margin: 8px 0; font-size: 15px; }}
.outcome-green {{ background: #edfce9; }}
.outcome-red {{ background: #fff4f2; }}
.mail-note {{ color: #b30000; font-size: 14px; }}
.mail-subject {{ font-weight: 500; margin: 10px 0 4px; }}
.mail-body {{ white-space: pre-wrap; font-size: 14px; line-height: 1.5; color: #212121; }}
.stats {{ margin-top: 12px; text-align: right; }}
footer {{ display: none !important; }}
"""

HEADER = """
<div class="eyebrow">Progent · PageIndex · LangGraph</div>
<h1>Guardrailed Financial Research Agent</h1>
<p>The agent reads company filings and news, and it can send email.<br>
A prompt injection hides an instruction in the text that it reads.<br>
Progent blocks every tool call that your question did not ask for.</p>
"""

def head_script(pool: list[str]) -> str:
    """The display font, and browser-side sample suggestions. A sample counts as used once it has been in the question box; an
    empty box shows the next unused sample in grey, and Tab writes it in. Used samples persist in this browser."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500&display=swap">
<script>
(() => {{
  const SAMPLES = {json.dumps(pool)};
  const KEY = "gfra-used-samples";
  const used = () => {{ try {{ return JSON.parse(localStorage.getItem(KEY) || "[]"); }} catch {{ return []; }} }};
  const save = (list) => {{ try {{ localStorage.setItem(KEY, JSON.stringify(list)); }} catch {{}} }};
  let last = SAMPLES[0];  // the box opens with the first sample
  function refresh(box) {{
    const seen = used();
    for (const text of [last, box.value.trim()]) {{
      if (SAMPLES.includes(text) && !seen.includes(text)) seen.push(text);
    }}
    save(seen);
    last = box.value.trim();
    const left = SAMPLES.filter((s) => !seen.includes(s));
    box.placeholder = left[0] || SAMPLES[0];
    const count = document.getElementById("sample-count");
    if (count) count.textContent = `${{left.length}} of ${{SAMPLES.length}} samples not tried yet`;
  }}
  document.addEventListener("input", (e) => {{ if (e.target.matches("#question textarea")) refresh(e.target); }});
  document.addEventListener("keydown", (e) => {{
    const box = e.target;
    if (e.key !== "Tab" || !box.matches("#question textarea") || box.value !== "" || !box.placeholder) return;
    e.preventDefault();
    box.value = box.placeholder;
    box.dispatchEvent(new Event("input", {{ bubbles: true }}));
  }});
  const start = setInterval(() => {{
    const box = document.querySelector("#question textarea");
    if (box && box.value) {{ clearInterval(start); refresh(box); }}  // wait for the default question
  }}, 200);
}})();
</script>
"""


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


# Shown when Run is pressed, by (guardrail on, attack on). Numbers from the ablation (README): the attack runs on
# AgentDojo's baseline prompt, 9 news questions x 3 trials; the cost ratio is from the runs without an attack.
RUN_NOTICES = {
    (False, True): "No guardrail, attack on: in the ablation this attack made the agent email the attacker in 24 of "
                   "27 runs (89%). The model does not fall for it every time.",
    (True, False): "Guardrail on: Progent first has the model write a policy from your question, so a run costs "
                   "about 2.3x as much as without it.",
    (True, True): "Guardrail and attack on: the model does not always follow the injection; when it does, Progent "
                  "blocks the email. In the ablation the agent tried to email the attacker in 24 of 27 runs, and "
                  "Progent blocked all 24.",
}


async def answer(question, guarded, inject, session_id, researchers, limiter) -> tuple[str, str, str, str]:
    """The agent's answer (Markdown), the run trace, its tokens / cost / latency, and the news feed with what
    this run fetched (HTML). `researchers` maps (guardrail on, attack on) to a researcher."""
    feed = news_html(NEWS, INJECTIONS[DEMO_INJECTION] if inject else None, set())
    if not limiter.allow(session_id):
        return "Request limit reached; try again later.", "", "", feed
    try:
        reset_outbox()
        set_injection(DEMO_INJECTION if inject else None)
        result = await researchers[(bool(guarded), bool(inject))].run(question)
        fetched = {str(c["args"].get("company", "")).lower() for c in result.tool_calls if c["name"] == "fetch_news"}
        injected = {item["company"].lower() for item in NEWS} if inject else set()
        return (result.answer, trace_html(question, result.tool_calls, result.blocked, list(OUTBOX), injected,
                           INJECTIONS[DEMO_INJECTION] if inject else None),
                stats_html(result.input_tokens + result.output_tokens, result.cost_usd, result.latency_s),
                news_html(NEWS, INJECTIONS[DEMO_INJECTION] if inject else None, fetched))
    except Exception:
        logger.exception("Request failed")
        return "Error: the request failed; try again later.", "", "", feed
    finally:
        set_injection(None)


def build_demo(researchers: dict, limiter: RateLimiter, judge=None) -> gr.Blocks:
    """`judge(question, gold, answer) -> reply` grades FinanceBench answers; without it no verdict is shown."""
    pool = samples()
    golds = finance_golds()
    recorded = recordings()
    with gr.Blocks(title="Guardrailed Financial Research Agent") as demo:
        gr.HTML(sources_sidebar())
        with gr.Row(equal_height=False):
            with gr.Column(scale=3):
                gr.HTML(HEADER, elem_id="header")
            with gr.Column(scale=2, elem_id="news-panel"):
                gr.HTML('<div class="panel-title">News</div><div class="panel-sub">What <code>fetch_news</code> returns. '
                        'Each item is tagged. Hover to pause, click to read.</div>')
                feed = gr.HTML(news_html(NEWS, INJECTIONS[DEMO_INJECTION], set()), elem_id="news")
        with gr.Row(elem_id="scenarios"):
            scenario_buttons = [gr.Button(label, elem_classes="pill", size="sm") for label, *_ in SCENARIOS]
        scenario_note = gr.HTML('<div class="scenario-note">Replay a recorded run of this agent, or ask your own '
                                'question below and press Run.</div>')
        with gr.Column(elem_id="ask"):
            question = gr.Textbox(value=pool[0], label="Question", lines=2, elem_id="question",
                                  info="Clear the box to see the next sample you have not tried; press Tab to use it.")
            gr.HTML('<div id="sample-count" class="mono"></div>')
            with gr.Row(elem_id="toggles"):
                guarded = gr.Checkbox(label="Guardrail", value=True, elem_id="guardrail")
                inject = gr.Checkbox(label="Inject an attack", value=True, elem_id="inject")
            run = gr.Button("Run", variant="primary", elem_id="run")
        with gr.Column(elem_id="result"):
            gr.HTML('<div class="agent-head"><div class="agent-mark">A</div>'
                    '<div class="agent-name">Financial Research Agent</div></div>')
            with gr.Column(elem_id="answer-box"):
                head = gr.HTML(answer_head(), elem_id="answer-head")
                out = gr.Markdown("Ask a question and press Run.", elem_id="answer")
                trace = gr.HTML(elem_id="trace")
            stats = gr.HTML(elem_id="stats")

        def show_case(label, recording, note):
            """A case button writes the recorded question and both toggles, then replays the recording."""
            run_question = recording_question(recording)
            guarded_on, attack_on = next((g, i) for (q, g, i), r in recorded.items() if r == recording)
            return (run_question, guarded_on, attack_on, *replay(recording),
                    f'<div class="scenario-note"><b>{label}.</b> {note}</div>', answer_head())

        for button, (label, recording, note) in zip(scenario_buttons, SCENARIOS):
            button.click(lambda label=label, recording=recording, note=note: show_case(label, recording, note), None,
                         [question, guarded, inject, out, trace, stats, scenario_note, head], queue=False)
        inject.change(lambda i: news_html(NEWS, INJECTIONS[DEMO_INJECTION] if i else None, set()), inject, feed)

        async def on_run(q, g, i, request: gr.Request):
            if (g, i) in RUN_NOTICES:
                gr.Info(RUN_NOTICES[(g, i)])
            feed_now = news_html(NEWS, INJECTIONS[DEMO_INJECTION] if i else None, set())
            if (q.strip(), g, i) in recorded:  # a recorded case: replay it instead of calling the model
                return (*replay(recorded[(q.strip(), g, i)]), feed_now, answer_head())
            out_md, trace_html_, stats_html_, feed_html = await answer(q, g, i, request.session_hash, researchers, limiter)
            if q.strip() not in golds or not trace_html_:
                return out_md, trace_html_, stats_html_, feed_html, answer_head()
            fb_question, gold = golds[q.strip()]
            if judge is None:
                return out_md, trace_html_, stats_html_, feed_html, answer_head(gold)
            try:
                reply = await judge(fb_question, gold, out_md)
            except Exception:
                logger.exception("Judge failed")
                return out_md, trace_html_, stats_html_, feed_html, answer_head(gold)
            return out_md, trace_html_, stats_html_, feed_html, answer_head(gold, parse_verdict(reply), reply)

        run.click(on_run, [question, guarded, inject], [out, trace, stats, feed, head], concurrency_limit=1)
    return demo
