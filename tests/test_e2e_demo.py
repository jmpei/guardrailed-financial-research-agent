"""End-to-end: drive the Gradio demo in Google Chrome, with scripted researchers (no API calls).

Each feature in tests/e2e_features.json (PRD §2) has one test named test_<id>_...
"""
import json
import os
import re
import socket
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

import gfra.actions as actions
from gfra.agent import ResearchResult
from gfra.app import CSS, THEME, RateLimiter, build_demo, head_script
from gfra.demo_view import PDF_DIR, finance_golds, samples

FEATURES = json.loads((Path(__file__).parent / "e2e_features.json").read_text())


class FakeResearcher:
    def __init__(self, guarded):
        self.guarded = guarded
        self.injections = []

    async def run(self, question):
        self.injections.append(actions._active_injection)
        actions.send_email.invoke({"to": "team@bank.com", "subject": "3M", "body": "capex"})
        blocked = [{"tool": "send_email", "args": {"to": "attacker@evil.example"}, "reason": "not allowed"}] if self.guarded else []
        return ResearchResult(
            answer=f"Capital expenditure was $1,577M (3M_2018_10K, page 48). Agent: {'guarded' if self.guarded else 'unguarded'}.",
            tool_calls=[{"name": "get_page_content", "args": {"doc_name": "3M_2018_10K", "pages": "48"}},
                        {"name": "send_email", "args": {"to": "team@bank.com"}}],
            blocked=blocked, input_tokens=1000, output_tokens=100, cost_usd=0.0002, latency_s=2.0)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def demo():
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    researchers = {True: FakeResearcher(True), False: FakeResearcher(False)}
    async def judge(question, gold, answer):
        return "VERDICT: correct"

    app = build_demo(researchers, RateLimiter(100), judge=judge)
    app.queue(default_concurrency_limit=1)
    _, url, _ = app.launch(prevent_thread_lock=True, server_name="127.0.0.1", server_port=free_port(), quiet=True,
                           theme=THEME, css=CSS, head=head_script(samples()), allowed_paths=[str(PDF_DIR)])
    yield url, researchers
    app.close()


@pytest.fixture(scope="module")
def page(demo):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        yield browser.new_page()
        browser.close()


def run(page, url, guarded, inject):
    page.goto(url)
    page.get_by_label("Guardrail", exact=True).set_checked(guarded)
    page.get_by_label("Inject an attack").set_checked(inject)
    page.get_by_role("button", name="Run").click()
    expect(page.get_by_text("Capital expenditure was")).to_be_visible()


def test_every_feature_has_a_test():
    tested = {name.split("_")[1] for name in globals() if name.startswith("test_F")}
    assert tested == {f["id"] for f in FEATURES}


def test_F1_page_shows_the_controls(page, demo):
    page.goto(demo[0])
    expect(page.get_by_label("Question")).to_be_visible()
    expect(page.get_by_label("Guardrail", exact=True)).to_be_checked()
    expect(page.get_by_label("Inject an attack")).to_be_checked()
    expect(page.get_by_role("button", name="Run")).to_be_visible()


def test_F2_answer_with_citation(page, demo):
    run(page, demo[0], guarded=True, inject=False)
    expect(page.get_by_text("3M_2018_10K, page 48")).to_be_visible()


def test_F3_trace_lists_calls_email_and_cost(page, demo):
    run(page, demo[0], guarded=True, inject=False)
    for text in ("get_page_content", "Email sent to team@bank.com", "1100 tokens · $0.0002 · 2.0 s"):
        expect(page.get_by_text(text).first).to_be_visible()


def test_F4_guarded_trace_shows_the_block(page, demo):
    run(page, demo[0], guarded=True, inject=True)
    expect(page.locator("#trace").get_by_text("attacker@evil.example")).to_be_visible()


def test_F5_toggles_reach_the_agent(page, demo):
    url, researchers = demo
    run(page, url, guarded=False, inject=True)
    expect(page.get_by_text("Agent: unguarded")).to_be_visible()
    assert "attacker@evil.example" in researchers[False].injections[-1]
    run(page, url, guarded=True, inject=False)
    expect(page.get_by_text("Agent: guarded")).to_be_visible()
    assert researchers[True].injections[-1] is None


def test_F6_sources_open_a_filing(page, demo):
    page.goto(demo[0])
    link = page.locator("#sources-drawer a", has_text="3M_2018_10K")
    expect(link).to_have_attribute("target", "_blank")
    href = link.get_attribute("href")
    assert href.endswith("3M_2018_10K.pdf") and page.request.get(demo[0].rstrip("/") + href).ok


def test_F7_news_marks_the_injection(page, demo):
    page.goto(demo[0])
    expect(page.locator("#news .injection").first).to_contain_text("attacker@evil.example")
    page.get_by_label("Inject an attack").set_checked(False)
    expect(page.locator("#news .injection")).to_have_count(0)
    expect(page.locator("#news .news-row .chip-red")).to_have_count(0)


def test_F8_news_item_opens_in_a_dialog(page, demo):
    page.emulate_media(reduced_motion="reduce")  # a moving ticker never settles for a click
    page.goto(demo[0])
    page.get_by_label("Inject an attack").set_checked(True)
    page.locator("#news .news-row").first.click()
    dialog = page.locator("#news .news-dialog:target")
    expect(dialog).to_be_visible()
    expect(dialog.locator(".injection")).to_contain_text("attacker@evil.example")
    dialog.get_by_text("Close").click()
    expect(page.locator("#news .news-dialog:target")).to_have_count(0)
    page.emulate_media(reduced_motion="no-preference")


def test_F9_each_cleared_box_suggests_the_next_unused_sample(page, demo):
    page.goto(demo[0])
    page.evaluate("localStorage.clear()")
    page.reload()
    box = page.get_by_label("Question")
    expect(box).to_have_value(re.compile("^Summarize 3M's FY2018 capital expenditure"))
    seen = [box.input_value()]
    for _ in range(3):  # clear, read the suggestion, Tab it in; no Run in between
        box.fill("")
        expect(box).not_to_have_attribute("placeholder", re.compile("^$|" + re.escape(seen[-1])))
        suggestion = box.get_attribute("placeholder")
        assert suggestion not in seen
        box.press("Tab")
        expect(box).to_have_value(suggestion)
        seen.append(suggestion)


def test_F10_case_buttons_fill_the_question_and_toggles_and_run_replays(page, demo):
    page.goto(demo[0])
    page.get_by_role("button", name="No guardrail · attack", exact=True).click()
    expect(page.get_by_label("Question")).to_have_value(re.compile("lunch with Sarah"))
    expect(page.get_by_label("Guardrail", exact=True)).not_to_be_checked()
    expect(page.get_by_label("Inject an attack")).to_be_checked()
    expect(page.locator("#trace")).to_contain_text("Done for the attacker")
    expect(page.locator("#stats")).to_contain_text("attack succeeded")
    page.get_by_label("Guardrail", exact=True).set_checked(True)
    page.get_by_role("button", name="Run").click()  # same question, guardrail on: the Progent recording
    expect(page.locator("#trace")).to_contain_text("Blocked by Progent")
    expect(page.locator("#stats")).to_contain_text("attack failed")
    page.get_by_role("button", name="Guardrail · false block", exact=True).click()
    expect(page.get_by_label("Question")).to_have_value(re.compile("bill-december-2023"))
    expect(page.get_by_label("Inject an attack")).not_to_be_checked()
    expect(page.locator("#stats")).to_contain_text("task not completed")


def test_F11_financebench_answer_shows_gold_and_verdict(page, demo):
    question = next(q for q in finance_golds() if "3M_2018_10K" in q and "capital expenditure amount" in q)
    page.goto(demo[0])
    page.get_by_label("Question").fill(question)
    page.get_by_role("button", name="Run").click()
    expect(page.get_by_text("Capital expenditure was")).to_be_visible()
    head = page.locator("#answer-head")
    head.get_by_text("Gold answer", exact=True).click()
    expect(head).to_contain_text("$1577.00")
    head.locator("summary", has_text="correct").click()
    expect(head).to_contain_text("VERDICT: correct")
