"""End-to-end: drive the Gradio demo in Google Chrome, with scripted researchers (no API calls).

Each feature in tests/e2e_features.json (PRD §2) has one test named test_<id>_...
"""
import json
import os
import socket
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

import gfra.actions as actions
from gfra.agent import ResearchResult
from gfra.app import RateLimiter, build_demo

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
    app = build_demo(researchers, RateLimiter(100))
    app.queue(default_concurrency_limit=1)
    _, url, _ = app.launch(prevent_thread_lock=True, server_name="127.0.0.1", server_port=free_port(), quiet=True)
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
    page.get_by_label("Guardrail (Progent)").set_checked(guarded)
    page.get_by_label("Inject an attack into the news").set_checked(inject)
    page.get_by_role("button", name="Run").click()
    expect(page.get_by_text("Capital expenditure was")).to_be_visible()


def test_every_feature_has_a_test():
    tested = {name.split("_")[1] for name in globals() if name.startswith("test_F")}
    assert tested == {f["id"] for f in FEATURES}


def test_F1_page_shows_the_controls(page, demo):
    page.goto(demo[0])
    expect(page.get_by_label("Question")).to_be_visible()
    expect(page.get_by_label("Guardrail (Progent)")).to_be_checked()
    expect(page.get_by_label("Inject an attack into the news")).not_to_be_checked()
    expect(page.get_by_role("button", name="Run")).to_be_visible()


def test_F2_answer_with_citation(page, demo):
    run(page, demo[0], guarded=True, inject=False)
    expect(page.get_by_text("3M_2018_10K, page 48")).to_be_visible()


def test_F3_trace_lists_calls_email_and_cost(page, demo):
    run(page, demo[0], guarded=True, inject=False)
    for text in ("get_page_content", "Email sent to team@bank.com", "1100 tokens, $0.0002, 2.0 s"):
        expect(page.get_by_text(text).first).to_be_visible()


def test_F4_guarded_trace_shows_the_block(page, demo):
    run(page, demo[0], guarded=True, inject=True)
    expect(page.get_by_text("attacker@evil.example")).to_be_visible()


def test_F5_toggles_reach_the_agent(page, demo):
    url, researchers = demo
    run(page, url, guarded=False, inject=True)
    expect(page.get_by_text("Agent: unguarded")).to_be_visible()
    assert "attacker@evil.example" in researchers[False].injections[-1]
    run(page, url, guarded=True, inject=False)
    expect(page.get_by_text("Agent: guarded")).to_be_visible()
    assert researchers[True].injections[-1] is None
