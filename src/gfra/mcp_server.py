"""MCP server: any MCP client (Claude Desktop, Claude Code) can call the guarded research agent."""
import asyncio

from fastmcp import FastMCP


def build_server(researcher) -> FastMCP:
    mcp = FastMCP("guardrailed-financial-research-agent")
    lock = asyncio.Lock()  # the guard keeps its policy in process-wide state: one request at a time

    @mcp.tool
    async def research(question: str) -> dict:
        """Answer a question about a FinanceBench filing; may email results if asked. Guardrail is on."""
        async with lock:
            result = await researcher.run(question)
        return {"answer": result.answer, "blocked": result.blocked, "cost_usd": result.cost_usd}

    return mcp


if __name__ == "__main__":
    from gfra.app_factory import build_researcher
    from gfra.config import AGENT_MODEL
    build_server(build_researcher(guarded=True, model=AGENT_MODEL)).run()
