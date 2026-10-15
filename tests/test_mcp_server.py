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
