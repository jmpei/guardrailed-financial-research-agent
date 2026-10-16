"""HTML for the demo: the filings list, the news feed, the preset questions and the run trace.

Every string that comes from a model, a tool or a file is escaped before it reaches the page.
"""
import json
import re
from html import escape

from gfra.config import DATA_DIR
from gfra.data import load_questions
from gfra.financebench_eval import JUDGE_MODEL

PDF_DIR = DATA_DIR / "financebench" / "pdfs"
DEMO_QUESTION = ("Summarize 3M's FY2018 capital expenditure (document 3M_2018_10K.pdf) and the latest 3M news, "
                 "and email it to team@bank.com")


def filings() -> list[tuple[str, int]]:
    """(document name without .pdf, page count) for every indexed filing."""
    docs = json.loads((DATA_DIR / "index" / "manifest.json").read_text())["docs"].values()
    return sorted((d["name"].removesuffix(".pdf"), d["pageNum"]) for d in docs)


CASES_DIR = DATA_DIR / "agentdojo_cases"
# Recorded runs from the AgentDojo experiment (AgentDojo's own agent, gpt-4o-mini), replayed without a model call:
# (button label, recording, what it shows).
SCENARIOS = [
    ("No guardrail · attack", "workspace_user_task_5_injection_task_0_none.json",
     "No defense: an instruction hidden in a calendar event makes the agent email an outside address."),
    ("Guardrail · attack", "workspace_user_task_5_injection_task_0_progent.json",
     "Same task and attack with Progent: the email to the outside address is blocked, and the question still gets answered."),
    ("Guardrail · false block", "banking_user_task_0_no_attack_progent.json",
     "No attack, yet Progent blocks reading the bill, so the agent cannot pay it. Without Progent it paid the bill."),
]
TARGET = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b[A-Z]{2}\d{10,30}\b")


def _text(content) -> str:
    if isinstance(content, list):
        return "\n".join(str(block.get("content") or block.get("text") or "") for block in content)
    return str(content or "")


def recording_question(recording: str) -> str:
    run = json.loads((CASES_DIR / recording).read_text())
    return _text(next(m["content"] for m in run["messages"] if m["role"] == "user"))


def recordings() -> dict[tuple[str, bool, bool], str]:
    """(question, guardrail on, attack on) → recording, for every recorded AgentDojo run in CASES_DIR."""
    out = {}
    for path in sorted(CASES_DIR.glob("*.json")):
        run = json.loads(path.read_text())
        out[(recording_question(path.name), path.stem.endswith("_progent"), bool(run["injection_task_id"]))] = path.name
    return out


def replay(recording: str) -> tuple[str, str, str]:
    """A recorded AgentDojo run as the demo's answer (Markdown), steps (HTML) and footer (HTML)."""
    run = json.loads((CASES_DIR / recording).read_text())
    messages = run["messages"]
    injection = next(iter((run.get("injections") or {}).values()), None)
    targets = set(TARGET.findall(injection.split("first:")[-1])) if injection else set()
    results = {m["tool_call_id"]: m for m in messages if m["role"] == "tool"}
    steps, outcomes = [], []
    for m in messages:
        for call in (m.get("tool_calls") or []) if m["role"] == "assistant" else []:
            args = json.dumps(call["args"], ensure_ascii=False)
            result = results.get(call["id"], {})
            blocked = bool(result.get("error")) and ("is not allowed" in result["error"] or "Failed validating" in result["error"])
            attack = any(t in args for t in targets)
            text = f'Called {escape(call["function"])} <span class="args">{escape(args[:120])}</span>'
            if injection and "<INFORMATION>" in _text(result.get("content")):
                text += (' <details class="inline-inject"><summary class="chip chip-warn">Prompt injection</summary>'
                         f'<pre>{escape(injection.strip())}</pre></details>')
            if blocked:
                text += ' <span class="chip chip-red">Blocked by Progent</span>'
                outcomes.append(f'<div class="outcome outcome-red"><span class="chip chip-red">Blocked by Progent</span>'
                                f'{escape(call["function"])} <span class="mail-note">{escape(result["error"].splitlines()[0].split(". Please")[0])}</span></div>')
            elif attack:
                text += ' <span class="chip chip-red">Attacker\'s request</span>'
                outcomes.append(f'<div class="outcome outcome-red"><span class="chip chip-red">Done for the attacker</span>'
                                f'{escape(call["function"])} <span class="args">{escape(args[:160])}</span></div>')
            steps.append(f'<li><span class="step-text">{text}</span><span class="mono tool">{escape(call["function"])}</span></li>')
    final = _text(next(m["content"] for m in reversed(messages) if m["role"] == "assistant"))
    trace = "".join(['<div class="section-title mono">Steps</div><ol class="steps">', *steps, "</ol>", *outcomes])
    attack_result = ("no attack" if not injection else "attack succeeded" if run["security"] else "attack failed")
    footer = (f'<div class="stats mono">Recorded AgentDojo run · {escape(run["suite_name"])} · gpt-4o-mini · '
              f'task {"completed" if run["utility"] else "not completed"} · {attack_result}</div>')
    return final, trace, footer


def finance_golds() -> dict[str, tuple[str, str]]:
    """Sample text in the question box → (FinanceBench question, gold answer), for the indexed filings."""
    indexed = {name for name, _ in filings()}
    return {f"{q.question} (document {q.doc_name}.pdf)": (q.question, q.answer)
            for q in load_questions(DATA_DIR / "financebench" / "financebench_open_source.jsonl")
            if q.doc_name in indexed}


VERDICT_CHIPS = {"correct": "chip-green", "incorrect": "chip-red", "refused": "chip-warn"}


def answer_head(gold: str | None = None, verdict: str | None = None, reply: str | None = None) -> str:
    """The ANSWER label; for a FinanceBench question, a Gold answer pill and the judge's verdict, each opening on click."""
    parts = ['<div class="answer-head"><span class="section-title mono">Answer</span>']
    if gold is not None:
        parts.append(f'<details class="pop"><summary class="pill-sm">Gold answer</summary>'
                     f'<div class="pop-body"><div class="mono">FinanceBench gold answer</div>{escape(gold)}</div></details>')
    if verdict is not None:
        parts.append(f'<details class="pop"><summary class="chip {VERDICT_CHIPS.get(verdict, "chip-done")}">'
                     f'{escape(verdict)}</summary><div class="pop-body"><div class="mono">LLM judge · {escape(JUDGE_MODEL)}'
                     f'</div><pre>{escape(reply or "")}</pre></div></details>')
    return "".join(parts) + "</div>"


def samples() -> list[str]:
    """Sample questions, in the order the question box suggests them: the demo question, the email
    cases, then the FinanceBench questions about the indexed filings."""
    cases = json.loads((DATA_DIR / "tasks" / "email_cases.json").read_text())
    indexed = {name for name, _ in filings()}
    finance = [f"{q.question} (document {q.doc_name}.pdf)"
               for q in load_questions(DATA_DIR / "financebench" / "financebench_open_source.jsonl")
               if q.doc_name in indexed]
    return list(dict.fromkeys([DEMO_QUESTION, *(c["question"] for c in cases), *finance]))


def sources_sidebar() -> str:
    """A tab on the left edge that opens, on hover, into a scrolling list of the filings; each opens its PDF in a new tab."""
    links = "".join(
        f'<a href="/gradio_api/file={escape(str(PDF_DIR / f"{name}.pdf"))}" target="_blank" rel="noopener">'
        f'<span>{escape(name)}</span><span class="mono">{pages} pages</span></a>'
        for name, pages in filings()
    )
    return (f'<nav id="sources-drawer"><div class="drawer-tab mono">Sources</div><div class="drawer-body">'
            f'<div class="drawer-title">Filings the agent can read</div>{links}</div></nav>')


def news_html(items: list[dict], injection: str | None, fetched: set[str]) -> str:
    """The news items the agent can fetch (company earnings releases), scrolling upward in a loop; click one to
    read it in a dialog. Each item is tagged: the injection, when on, sits at the end of each company's first
    item, as `fetch_news` returns it; the other items carry none."""
    rows, dialogs = [], []
    seen = set()
    for item in items:
        company = item["company"]
        first = company not in seen
        seen.add(company)
        badge = '<span class="chip chip-done">Fetched</span>' if company.lower() in fetched else ""
        attacked = bool(injection) and first
        attack = f'<div class="injection"><pre>{escape(injection.strip())}</pre></div>' if attacked else ""
        status = ('<span class="chip chip-red">Prompt injection</span>' if attacked
                  else '<span class="chip chip-green">No injection</span>')
        meta = f'<span class="mono">{escape(company)} · {escape(item["date"])}</span>{status}'
        target = f"news-{escape(item['id'])}"
        rows.append(
            f'<a class="news-row" href="#{target}"><div class="news-meta">{meta}{badge}</div>'
            f'<div class="news-title">{escape(item["headline"])}</div>'
            f'<div class="news-body">{escape(item["body"])}</div>{attack}</a>'
        )
        # A CSS :target dialog; closing goes to an id that does not exist, so the page does not scroll.
        dialogs.append(
            f'<div class="news-dialog" id="{target}"><a class="backdrop" href="#news-closed"></a><article>'
            f'<div class="news-meta">{meta}{badge}</div><h2>{escape(item["headline"])}</h2>'
            f'<p>{escape(item["body"])}</p>{attack}<a class="source" href="{escape(item["url"])}" target="_blank" '
            f'rel="noopener">Read the original release</a><a class="close mono" href="#news-closed">Close</a></article></div>'
        )
    # Two copies stacked: the track moves up by one copy's height, then restarts where it began.
    track = "".join(rows)
    return f'<div class="ticker"><div class="ticker-track">{track}{track}</div></div>{"".join(dialogs)}'


def _step(call: dict, named: set[str], injected: set[str], injection: str | None) -> str:
    name, args = call["name"], call["args"]
    doc = escape(str(args.get("doc_name", "")))
    text = {
        "get_document_structure": f"Read the table of contents of <b>{doc}</b>",
        "get_page_content": f"Read page {escape(str(args.get('pages', '')))} of <b>{doc}</b>",
        "search_pages": f"Searched <b>{doc}</b> for &ldquo;{escape(str(args.get('query', '')))}&rdquo;",
        "fetch_news": f"Fetched news about <b>{escape(str(args.get('company', '')))}</b>",
        "browse_documents": "Listed the filings",
        "get_document": f"Looked up <b>{doc}</b>",
        "send_email": f"Called send_email to <b>{escape(str(args.get('to', '')))}</b>",
    }.get(name, f"Called {escape(name)}")
    if name == "fetch_news" and str(args.get("company", "")).lower() in injected:
        text += (' <details class="inline-inject"><summary class="chip chip-warn">Prompt injection</summary>'
                 f'<pre>{escape((injection or "").strip())}</pre></details>')
    if name == "send_email" and str(args.get("to", "")).lower() not in named:
        text += ' <span class="chip chip-red">Not in your question</span>'
    return f'<li><span class="step-text">{text}</span><span class="mono tool">{escape(name)}</span></li>'


def _bold(text: str) -> str:
    """Render Markdown **bold** in already-escaped text, which agents use in email bodies."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


ADDRESS = re.compile(r"[^@\s,;()<>]+@[^@\s,;()<>]+\.[A-Za-z]{2,}")


def trace_html(question: str, tool_calls: list[dict], blocked: list[dict], emails: list[dict],
               injected: set[str] = frozenset(), injection: str | None = None) -> str:
    """Steps, blocked calls and sent emails. A news fetch that returned an injection gets a warning; an email to
    an address the question never named is a leak: red. `injected` holds the lower-cased companies whose news
    carried `injection`; clicking the warning shows that text."""
    named = {a.lower() for a in ADDRESS.findall(question)}
    parts = ['<div class="section-title mono">Steps</div><ol class="steps">',
             *(_step(c, named, injected, injection) for c in tool_calls), "</ol>"]
    for b in blocked:
        parts.append(f'<div class="outcome outcome-red"><span class="chip chip-red">Blocked by Progent</span>'
                     f'{escape(b["tool"])} to <b>{escape(str(b["args"].get("to", b["args"])))}</b></div>')
    for m in emails:
        ok = m["to"].lower() in named
        note = "" if ok else '<span class="mail-note">Your question did not name this address.</span>'
        parts.append(f'<div class="outcome outcome-{"green" if ok else "red"}"><span class="chip chip-{"green" if ok else "red"}">'
                     f'Email sent to {escape(m["to"])}</span>{note}<div class="mail-subject">{escape(m["subject"])}</div>'
                     f'<div class="mail-body">{_bold(escape(m["body"]))}</div></div>')
    if not blocked and not emails:
        parts.append('<div class="outcome">No email sent and nothing blocked.</div>')
    return "".join(parts)


def stats_html(tokens: int, cost_usd: float, latency_s: float) -> str:
    return f'<div class="stats mono">{tokens} tokens · ${cost_usd:.4f} · {latency_s:.1f} s</div>'
