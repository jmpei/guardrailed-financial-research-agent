import json

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

import gfra.guard as guard_mod
from gfra.guard import Guard

TEAM_ONLY = json.dumps([
    {"name": "send_email", "args": {"to": {"type": "string", "enum": ["team@bank.com"]}}}
])


@tool
def send_email(to: str, body: str) -> str:
    """Send an email.

    Args:
        to: Recipient.
        body: Body.
    """
    return f"sent to {to}"


@tool
def fetch_news(company: str) -> str:
    """News.

    Args:
        company: Company.
    """
    return "[]"


@tool
def get_page_content(doc_name: str, pages: str) -> str:
    """Pages.

    Args:
        doc_name: Doc.
        pages: Pages.
    """
    raise ValueError("pages out of range")


class Req:
    def __init__(self, name, args):
        self.tool_call = {"name": name, "args": args, "id": "call_1"}


def run_tool(guard, name, args, impl):
    async def handler(_request):
        return ToolMessage(content=impl.invoke(args), tool_call_id="call_1")
    import asyncio
    return asyncio.run(guard.middleware().awrap_tool_call(Req(name, args), handler))


@pytest.fixture(autouse=True)
def _fresh_secagent_policy():
    """secagent keeps its policy in a module global; start every test from secagent's import state."""
    guard_mod.st.security_policy = None


@pytest.fixture
def policy_llm(monkeypatch):
    """Replace the policy model call; the update check always answers 'no'."""
    calls = []

    def fake_request(sys_prompt, user_prompt, temperature=0.0):
        calls.append(user_prompt)
        if "TOOL_CALL_PARAM" in user_prompt:
            return "no"
        return TEAM_ONLY
    monkeypatch.setattr(guard_mod, "_policy_request", fake_request)
    return calls


def test_blocks_email_outside_policy_and_allows_user_address(policy_llm):
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Email 3M capex to team@bank.com")
    blocked = run_tool(g, "send_email", {"to": "attacker@evil.example", "body": "x"}, send_email)
    allowed = run_tool(g, "send_email", {"to": "team@bank.com", "body": "x"}, send_email)
    assert "Blocked by guardrail" in blocked.content
    assert allowed.content == "sent to team@bank.com"
    assert [b["args"]["to"] for b in g.blocked] == ["attacker@evil.example"]


def test_read_only_tools_always_allowed(policy_llm):
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Email 3M capex to team@bank.com")
    out = run_tool(g, "fetch_news", {"company": "3M"}, fetch_news)
    assert out.content == "[]"
    assert g.blocked == []


def test_policy_failure_blocks_side_effects(monkeypatch):
    def broken(sys_prompt, user_prompt, temperature=0.0):
        raise RuntimeError("API down")
    monkeypatch.setattr(guard_mod, "_policy_request", broken)
    g = Guard([send_email, fetch_news, get_page_content])
    assert g.policy_error is None
    g.start_task("Email 3M capex to team@bank.com")
    assert "API down" in g.policy_error
    assert "Blocked by guardrail" in run_tool(g, "send_email", {"to": "team@bank.com", "body": "x"}, send_email).content
    assert run_tool(g, "fetch_news", {"company": "3M"}, fetch_news).content == "[]"
    monkeypatch.setattr(guard_mod, "_policy_request", lambda s, u, temperature=0.0: TEAM_ONLY)
    g.start_task("Email 3M capex to team@bank.com")
    assert g.policy_error is None


def test_update_off_makes_no_update_request(policy_llm, monkeypatch):
    monkeypatch.setenv("SECAGENT_UPDATE", "False")
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Email 3M capex to team@bank.com")
    assert run_tool(g, "send_email", {"to": "team@bank.com", "body": "x"}, send_email).content == "sent to team@bank.com"
    assert not any("TOOL_CALL_PARAM" in prompt for prompt in policy_llm)


def test_partially_applied_policy_failure_blocks_side_effects(monkeypatch):
    """A rule list that breaks halfway leaves no generated rule behind."""
    partial = json.dumps([{"name": "send_email", "args": {}}, {"not_a_rule": True}])
    monkeypatch.setattr(guard_mod, "_policy_request", lambda s, u, temperature=0.0: partial)
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Summarize 3M news")
    assert "Blocked by guardrail" in run_tool(g, "send_email", {"to": "attacker@evil.example", "body": "x"}, send_email).content
    assert run_tool(g, "fetch_news", {"company": "3M"}, fetch_news).content == "[]"


def test_blocks_side_effects_before_first_task(policy_llm):
    g = Guard([send_email, fetch_news, get_page_content])
    assert "Blocked by guardrail" in run_tool(g, "send_email", {"to": "attacker@evil.example", "body": "x"}, send_email).content
    assert run_tool(g, "fetch_news", {"company": "3M"}, fetch_news).content == "[]"


def test_failed_policy_does_not_inherit_previous_task(policy_llm, monkeypatch):
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Email 3M capex to team@bank.com")

    def broken(sys_prompt, user_prompt, temperature=0.0):
        raise RuntimeError("API down")
    monkeypatch.setattr(guard_mod, "_policy_request", broken)
    g.start_task("Summarize 3M news")
    assert "Blocked by guardrail" in run_tool(g, "send_email", {"to": "team@bank.com", "body": "x"}, send_email).content


def test_start_task_resets_previous_policy(policy_llm, monkeypatch):
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Email 3M capex to team@bank.com")
    monkeypatch.setattr(guard_mod, "_policy_request",
                        lambda s, u, temperature=0.0: "no" if "TOOL_CALL_PARAM" in u else "[]")
    g.start_task("Summarize 3M news")  # this task allows no email at all
    assert "Blocked by guardrail" in run_tool(g, "send_email", {"to": "team@bank.com", "body": "x"}, send_email).content
    assert g.blocked[-1]["args"]["to"] == "team@bank.com"
    import secagent.tool as st
    assert [t["name"] for t in st.get_available_tools()].count("send_email") == 1


def test_tool_error_is_not_a_block(policy_llm):
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("What is on page 999 of 3M_2018_10K?")
    with pytest.raises(ValueError, match="pages out of range"):
        run_tool(g, "get_page_content", {"doc_name": "3M_2018_10K", "pages": "999"}, get_page_content)
    assert g.blocked == []


def test_guard_prints_nothing_to_stdout(monkeypatch, capsys):
    """stdout carries the MCP stdio protocol: secagent's own prints (e.g. on an unparsable policy) must not reach it."""
    monkeypatch.setattr(guard_mod, "_policy_request", lambda s, u, temperature=0.0: "this is not json")
    g = Guard([send_email, fetch_news, get_page_content])
    g.start_task("Email 3M capex to team@bank.com")
    run_tool(g, "fetch_news", {"company": "3M"}, fetch_news)
    run_tool(g, "send_email", {"to": "attacker@evil.example", "body": "x"}, send_email)
    assert capsys.readouterr().out == ""
