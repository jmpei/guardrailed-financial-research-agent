import asyncio

from fastmcp import Client

from gfra.agent import ResearchResult
from gfra.mcp_server import build_server


class FakeResearcher:
    async def run(self, question):
        return ResearchResult(answer=f"answer to {question}", tool_calls=[], blocked=[{"tool": "send_email"}],
                              input_tokens=1, output_tokens=1, cost_usd=0.001, latency_s=0.1)


async def test_research_tool_returns_answer_and_blocks():
    async with Client(build_server(FakeResearcher())) as client:
        assert [t.name for t in await client.list_tools()] == ["research"]
        result = await client.call_tool("research", {"question": "3M capex?"})
        assert result.data["answer"] == "answer to 3M capex?"
        assert result.data["blocked"] == [{"tool": "send_email"}]
        assert result.data["cost_usd"] == 0.001


class SlowResearcher:
    def __init__(self):
        self.active = self.peak = 0

    async def run(self, question):
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.05)
        self.active -= 1
        return ResearchResult(answer=f"answer to {question}", tool_calls=[], blocked=[],
                              input_tokens=1, output_tokens=1, cost_usd=0.0, latency_s=0.05)


async def test_concurrent_calls_run_one_at_a_time():
    researcher = SlowResearcher()
    async with Client(build_server(researcher)) as client:
        first, second = await asyncio.gather(
            client.call_tool("research", {"question": "a"}), client.call_tool("research", {"question": "b"}))
    assert researcher.peak == 1
    assert {first.data["answer"], second.data["answer"]} == {"answer to a", "answer to b"}
