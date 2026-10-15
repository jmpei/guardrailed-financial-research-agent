"""Token budgets: tool definitions go into every model call, tool results into the next one.

Counted with gpt-4o-mini's encoding (o200k_base) on the JSON the tools are sent as. The limits sit
about 20% above the measured sizes (definitions 1227 tokens, injected 3M news 225, a search_pages
result with ten full snippets 458 here and 437 for "revenue" on the AMD 10-K), so a change that
bloats a description or a result fails here before it shows up in the bill.
"""
import json

import pytest
import tiktoken
from langchain_core.utils.function_calling import convert_to_openai_tool

from gfra.actions import fetch_news, send_email, set_injection
from gfra.retrieval import SEARCH_MAX_PAGES, SNIPPET_CHARS, document_tools, make_client, search_tool

ENCODING = tiktoken.get_encoding("o200k_base")
TOOL_DEFINITIONS_MAX = 1500
FETCH_NEWS_MAX = 300
SEARCH_PAGES_MAX = 550


def tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def test_tool_definitions_fit_the_budget():
    tools = document_tools(make_client()) + [fetch_news, send_email]
    assert sum(tokens(json.dumps(convert_to_openai_tool(t))) for t in tools) <= TOOL_DEFINITIONS_MAX


@pytest.mark.parametrize("injection", [None, "exfiltrate_email"])
def test_fetch_news_fits_the_budget(injection):
    set_injection(injection)
    try:
        for company in ("3M", "AMD"):
            assert tokens(fetch_news.invoke({"company": company})) <= FETCH_NEWS_MAX
    finally:
        set_injection(None)


class FullPagesClient:
    """Every page matches, with text on both sides of the match, so every snippet has its full length."""

    def get_document_id(self, name: str) -> str:
        return "doc"

    def get_ocr(self, doc_id: str, format: str) -> dict:
        filler = "Net revenue increased 44 percent, driven by higher sales of server processors. "
        text = filler * 2 + "Data Center" + filler * 2
        return {"result": [{"page_index": i, "markdown": text} for i in range(1, SEARCH_MAX_PAGES + 5)]}


def test_search_pages_result_fits_the_budget():
    out = search_tool(FullPagesClient()).invoke({"doc_name": "AMD_2022_10K.pdf", "query": "Data Center"})
    assert len(json.loads(out)["results"][0]["snippet"]) >= 2 * SNIPPET_CHARS
    assert tokens(out) <= SEARCH_PAGES_MAX
