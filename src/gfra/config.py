from pathlib import Path

MODEL = "gpt-4o-mini-2024-07-18"
# The stronger answering model (FinanceBench held-out accuracy 50% → 68% at 1.9× the cost). Not in use: the demo and
# the MCP server answer with MODEL; pass model=AGENT_MODEL to build_researcher to switch.
AGENT_MODEL = "gpt-4.1-mini-2025-04-14"

# USD per 1M tokens (input, output), OpenAI pricing page
PRICES = {
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "gpt-4.1-mini-2025-04-14": (0.40, 1.60),
}

READ_ONLY_TOOLS = frozenset({
    "browse_documents",
    "get_document",
    "get_document_structure",
    "get_page_content",
    "search_pages",
    "fetch_news",
})

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000
