"""MCP server: any MCP client (Claude Desktop, Claude Code) can call the guarded research agent."""
from fastmcp import FastMCP


def build_server(researcher) -> FastMCP:
    mcp = FastMCP("guardrailed-financial-research-agent")

    @mcp.tool
    async def research(question: str) -> dict:
        """Answer a question about a FinanceBench filing; may email results if asked. Guardrail is on."""
        result = await researcher.run(question)
        return {"answer": result.answer, "blocked": result.blocked, "cost_usd": result.cost_usd}

    return mcp


if __name__ == "__main__":
    from gfra.app_factory import build_researcher
    build_server(build_researcher(guarded=True)).run()
