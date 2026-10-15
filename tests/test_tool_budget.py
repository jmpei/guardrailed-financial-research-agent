"""Token budgets: tool definitions go into every model call, tool results into the next one.

Counted with gpt-4o-mini's encoding (o200k_base) on the JSON the tools are sent as. The limits sit
about 20% above the measured sizes (definitions 1077 tokens, injected 3M news 225), so a change that
bloats a description or a result fails here before it shows up in the bill.
"""
import json

import pytest
import tiktoken
from langchain_core.utils.function_calling import convert_to_openai_tool

from gfra.actions import fetch_news, send_email, set_injection
from gfra.retrieval import document_tools, make_client

ENCODING = tiktoken.get_encoding("o200k_base")
TOOL_DEFINITIONS_MAX = 1300
FETCH_NEWS_MAX = 300


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
