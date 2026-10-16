"""Gradio demo: ask a question, toggle the guardrail and a news injection, see what was blocked.

Styled after Cohere's design system (DESIGN.md at the repo root): white canvas, near-black pill
action, dark agent-console panel for the trace, coral marker for a blocked call.
"""
import json
import logging
from html import escape

import gradio as gr

from gfra.actions import INJECTIONS, NEWS, OUTBOX, reset_outbox, set_injection
from gfra.demo_view import (HOW, SETUPS, answer_head, finance_golds, news_html, recordings, replay, run_view, samples,
                             setup_grid, sources_sidebar, stats_text)
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
.mono, #header .eyebrow, .label {{
  font-family: {MONO_FONT}; font-size: 12px; letter-spacing: 0.28px; text-transform: uppercase; color: #75758a;
}}
#header h1 {{
  font-family: {DISPLAY_FONT}; font-weight: 400; font-size: 48px; line-height: 1.05; letter-spacing: -0.96px;
  color: #000000; margin: 12px 0 16px;
}}
#header p {{ font-size: 17px; line-height: 1.7; color: #616161; margin: 0; }}
#news-panel, #setup, #result {{ border: 1px solid #d9d9dd !important; border-radius: 22px !important; padding: 24px !important; }}
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
.chip-warn {{ background: #ff7759; color: #17171c; }}
.chip-done {{ border: 1px solid #17171c; color: #17171c; }}
#run {{ flex: none !important; width: auto; min-width: 160px; max-width: 200px; }}
#result {{ margin-top: 24px; }}
.answer-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
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
.mail-body {{ white-space: pre-wrap; font-size: 14px; line-height: 1.5; color: #212121; }}
footer {{ display: none !important; }}
/* The news panel takes the header's height; its ticker fills what is left. */
#top {{ align-items: stretch !important; }}
#news-panel {{ display: flex !important; flex-direction: column; }}
#news {{ flex: 1 1 0 !important; min-height: 0; position: relative; overflow: hidden; }}
#news .ticker {{ position: absolute; inset: 0; height: auto; }}
.how {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.how div {{ background: #f7f7f8; border-radius: 12px; padding: 12px 14px; font-size: 14px; color: #616161; }}
.how b {{ display: block; color: #212121; font-weight: 600; margin-bottom: 2px; }}
#setup {{ gap: 24px; }}
#toggles {{ display: none !important; }}
.label {{ display: block; margin-bottom: 10px; }}
.matrix {{ display: grid; grid-template-columns: auto 1fr 1fr; gap: 8px; }}
.matrix .axis {{ font-family: {MONO_FONT}; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; color: #75758a; align-self: end; padding: 0 4px 2px; }}
.matrix .row-axis {{ align-self: center; writing-mode: vertical-rl; transform: rotate(180deg); padding: 4px 0; }}
.cell {{ text-align: left; border: 1px solid #d9d9dd; border-radius: 12px; padding: 12px; background: #ffffff; cursor: pointer; display: grid; gap: 6px; align-content: start; min-height: 112px; }}
.cell:hover {{ border-color: #212121; }}
.cell[aria-pressed="true"] {{ border-color: #17171c; box-shadow: 0 0 0 1px #17171c inset; }}
.cell .stat {{ font-family: {DISPLAY_FONT}; font-size: 22px; line-height: 1.1; color: #000000; font-variant-numeric: tabular-nums; }}
.cell .what {{ font-size: 12.5px; color: #616161; }}
.cell .chip {{ width: fit-content; margin: 0; }}
.foot {{ font-size: 13px; color: #75758a; margin: 10px 0 0; }}
.chip-grey {{ background: #f2f2f2; color: #75758a; }}
.chip-blue {{ background: #f1f5ff; color: #1863dc; }}
.chip-coral {{ background: #ff7759; color: #17171c; }}
.samples {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.sample-chip {{ border: 1px dashed #d9d9dd; background: none; border-radius: 30px; padding: 4px 12px; font-size: 13px; color: #616161; cursor: pointer; }}
.sample-chip:hover {{ border-style: solid; color: #212121; }}
.explain {{ border-radius: 8px; padding: 10px 12px; background: #f7f7f8; font-size: 14px; color: #212121; }}
#run-row {{ align-items: center; gap: 12px; }}
.run-note {{ font-size: 13px; color: #75758a; }}
#result {{ gap: 18px; }}
.verdict {{ border-radius: 14px; padding: 18px 20px; }}
.verdict h3 {{ font-family: {DISPLAY_FONT}; font-weight: 400; font-size: 26px; line-height: 1.2; margin: 0 0 4px; color: #000000; }}
.verdict p {{ margin: 0; font-size: 14px; color: #616161; }}
.v-red {{ background: #fff4f2; }} .v-red h3 {{ color: #b30000; }}
.v-green {{ background: #edfce9; }} .v-green h3 {{ color: #1a7f37; }}
.v-grey {{ background: #f7f7f8; }}
.verdict .meta {{ display: flex; gap: 8px 16px; flex-wrap: wrap; margin-top: 8px; font-family: {MONO_FONT}; font-size: 12px; color: #75758a; font-variant-numeric: tabular-nums; }}
.path {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); }}
.node {{ position: relative; padding-right: 12px; display: grid; gap: 8px; align-content: start; min-width: 0; animation: node-in 0.3s both; }}
.node:nth-child(2) {{ animation-delay: 0.15s; }} .node:nth-child(3) {{ animation-delay: 0.3s; }}
.node:nth-child(4) {{ animation-delay: 0.45s; }} .node:nth-child(5) {{ animation-delay: 0.6s; }}
@keyframes node-in {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
.node::before {{ content: ""; position: absolute; left: 22px; right: 0; top: 9px; height: 2px; background: #d9d9dd; }}
.node:last-child::before {{ display: none; }}
.dot {{ width: 20px; height: 20px; border-radius: 50%; background: #17171c; position: relative; z-index: 1; }}
.node.bad .dot {{ background: #b30000; }} .node.stop .dot {{ background: #ff7759; }} .node.ok .dot {{ background: #1a7f37; }}
.node h4 {{ margin: 0; font-family: {MONO_FONT}; font-weight: 500; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; color: #75758a; }}
.node .body {{ font-size: 14px; color: #212121; overflow-wrap: anywhere; }}
.node .body p {{ margin: 2px 0 0; color: #616161; }}
.node ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }}
.node .tool, .node .more {{ font-family: {MONO_FONT}; font-size: 11px; color: #93939f; }}
.node details summary {{ cursor: pointer; font-family: {MONO_FONT}; font-size: 12px; color: #b30000; }}
.node .mail {{ display: grid; gap: 2px; }}
.node .mail details summary {{ color: #1863dc; }}
pre.inj {{ margin: 6px 0 0; border: 1px solid #b30000; background: #fff4f2; border-radius: 8px; padding: 8px 10px; white-space: pre-wrap; font-family: {MONO_FONT}; font-size: 11.5px; color: #b30000; }}
@media (max-width: 860px) {{
  #news {{ flex: none !important; }} #news .ticker {{ position: static; height: 260px; }}
  .path {{ grid-template-columns: minmax(0, 1fr); gap: 14px; }}
  .node::before {{ display: none; }}
  .how {{ grid-template-columns: minmax(0, 1fr); }}
}}
@media (prefers-reduced-motion: reduce) {{ .node {{ animation: none; }} }}
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
    empty box shows the next unused sample in grey, and Tab writes it in. Used samples persist in this browser.
    Also wires the setup grid to the two hidden checkboxes, the sample chips to the question box, and the setup note
    and the Run note (replay or live call) to both."""
    notes = {f"{int(g)},{int(a)}": note for (g, a), (*_, note) in SETUPS.items()}
    recorded = {f"{int(g)},{int(a)}": q for q, g, a in recordings()}
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
  const NOTES = {json.dumps(notes)};
  const RECORDED = {json.dumps(recorded)};
  const question = () => document.querySelector("#question textarea");
  const toggle = (id) => document.querySelector(`#${{id}} input[type=checkbox]`);
  const fill = (text) => {{ const box = question(); if (box) {{ box.value = text; box.dispatchEvent(new Event("input", {{ bubbles: true }})); }} }};
  function sync() {{
    const g = toggle("guardrail"), a = toggle("inject"), box = question();
    if (!g || !a || !box) return;
    const key = `${{+g.checked}},${{+a.checked}}`;
    document.querySelectorAll(".cell").forEach((c) => c.setAttribute("aria-pressed", String(`${{c.dataset.g}},${{c.dataset.a}}` === key)));
    document.getElementById("setup-note").textContent = NOTES[key];
    document.getElementById("run-note").textContent =
      RECORDED[key] === box.value.trim() ? "Replays a recorded run · free" : "Live call to gpt-4o-mini";
  }}
  document.addEventListener("click", (e) => {{
    const cell = e.target.closest(".cell"), chip = e.target.closest(".sample-chip");
    if (cell) {{
      for (const [id, on] of [["guardrail", cell.dataset.g === "1"], ["inject", cell.dataset.a === "1"]]) {{
        const box = toggle(id);
        if (box && box.checked !== on) box.click();
      }}
      const recordedQuestion = RECORDED[`${{cell.dataset.g}},${{cell.dataset.a}}`];
      if (recordedQuestion) fill(recordedQuestion);
      sync();
    }} else if (chip) {{
      fill(chip.dataset.q);
    }}
  }});
  document.addEventListener("input", sync);
  document.addEventListener("change", sync);
  const start = setInterval(() => {{
    const box = question();
    if (box && box.value && document.getElementById("run-note")) {{ clearInterval(start); refresh(box); sync(); }}  // wait for the default question
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


async def answer(question, guarded, inject, session_id, researchers, limiter) -> tuple[str, str, str, str]:
    """The agent's answer (Markdown), the verdict and the path of the email (HTML), and the news feed with what
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
        meta = ["Live run", "AgentDojo default prompt" if inject else "product prompt",
                "Progent on" if guarded else "no Progent",
                stats_text(result.input_tokens + result.output_tokens, result.cost_usd, result.latency_s)]
        verdict, path = run_view(question, bool(guarded), result.tool_calls, result.blocked, list(OUTBOX),
                                 INJECTIONS[DEMO_INJECTION] if inject else None, injected, meta)
        return result.answer, verdict, path, news_html(NEWS, INJECTIONS[DEMO_INJECTION] if inject else None, fetched)
    except Exception:
        logger.exception("Request failed")
        return "Error: the request failed; try again later.", "", "", feed
    finally:
        set_injection(None)


IDLE_VERDICT = ('<div class="verdict v-grey"><h3>Press Run to see the outcome</h3><p>The verdict, the path the email '
                'took, and the cost appear here.</p></div>')


def sample_chips(golds: dict) -> str:
    """Three questions that show the attack (news), Progent's allow path (a named address) and accuracy (FinanceBench)."""
    capex = next(q for q in golds if "3M_2018_10K" in q and "capital expenditure amount" in q)
    chips = [("Latest AmEx news", "What is the latest American Express news?"),
             ("AMD news → team@bank.com", "Summarize the latest AMD news and email it to team@bank.com."),
             ("3M FY2018 capex · FinanceBench", capex)]
    return '<div class="samples">' + "".join(
        f'<button type="button" class="sample-chip" data-q="{escape(q)}">{escape(label)}</button>' for label, q in chips
    ) + "</div>"


def build_demo(researchers: dict, limiter: RateLimiter, judge=None) -> gr.Blocks:
    """`judge(question, gold, answer) -> reply` grades FinanceBench answers; without it no verdict is shown."""
    pool = samples()
    golds = finance_golds()
    recorded = recordings()
    with gr.Blocks(title="Guardrailed Financial Research Agent") as demo:
        gr.HTML(sources_sidebar())
        with gr.Row(equal_height=True, elem_id="top"):
            with gr.Column(scale=3):
                gr.HTML(HEADER, elem_id="header")
            with gr.Column(scale=2, elem_id="news-panel"):
                gr.HTML('<div class="panel-title">News</div><div class="panel-sub">What <code>fetch_news</code> returns. '
                        'Each item is tagged. Hover to pause, click to read.</div>')
                feed = gr.HTML(news_html(NEWS, INJECTIONS[DEMO_INJECTION], set()), elem_id="news")
        gr.HTML(HOW)
        with gr.Row(elem_id="setup", equal_height=False):
            with gr.Column(scale=5, min_width=280):
                gr.HTML(setup_grid())
            with gr.Column(scale=6, min_width=280):
                question = gr.Textbox(value=pool[0], label="Question", lines=2, elem_id="question",
                                      info="Clear the box to see the next sample you have not tried; press Tab to use it.")
                gr.HTML('<div id="sample-count" class="mono"></div>')
                gr.HTML(sample_chips(golds))
                gr.HTML('<div id="setup-note" class="explain"></div>')
                with gr.Row(elem_id="toggles"):  # hidden: the setup grid sets them
                    guarded = gr.Checkbox(label="Guardrail", value=True, elem_id="guardrail")
                    inject = gr.Checkbox(label="Inject an attack", value=True, elem_id="inject")
                with gr.Row(elem_id="run-row"):
                    run = gr.Button("Run", variant="primary", elem_id="run")
                    gr.HTML('<span id="run-note" class="run-note"></span>')
        with gr.Column(elem_id="result"):
            verdict = gr.HTML(IDLE_VERDICT, elem_id="verdict")
            path = gr.HTML(elem_id="trace")
            with gr.Column(elem_id="answer-box"):
                head = gr.HTML(answer_head(), elem_id="answer-head")
                out = gr.Markdown("Ask a question and press Run.", elem_id="answer")

        inject.change(lambda i: news_html(NEWS, INJECTIONS[DEMO_INJECTION] if i else None, set()), inject, feed)

        async def on_run(q, g, i, request: gr.Request):
            feed_now = news_html(NEWS, INJECTIONS[DEMO_INJECTION] if i else None, set())
            if (q.strip(), g, i) in recorded:  # a recorded case: replay it instead of calling the model
                return (*replay(recorded[(q.strip(), g, i)]), feed_now, answer_head())
            out_md, verdict_html, path_html, feed_html = await answer(q, g, i, request.session_hash, researchers, limiter)
            if q.strip() not in golds or not path_html:
                return out_md, verdict_html, path_html, feed_html, answer_head()
            fb_question, gold = golds[q.strip()]
            if judge is None:
                return out_md, verdict_html, path_html, feed_html, answer_head(gold)
            try:
                reply = await judge(fb_question, gold, out_md)
            except Exception:
                logger.exception("Judge failed")
                return out_md, verdict_html, path_html, feed_html, answer_head(gold)
            return out_md, verdict_html, path_html, feed_html, answer_head(gold, parse_verdict(reply), reply)

        run.click(on_run, [question, guarded, inject], [out, verdict, path, feed, head], concurrency_limit=1)
    return demo
