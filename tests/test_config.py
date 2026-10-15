from gfra.config import MODEL, PRICES, READ_ONLY_TOOLS, cost_usd


def test_model_has_price():
    assert MODEL in PRICES


def test_cost_usd_uses_per_million_prices():
    # gpt-4o-mini: $0.15 input, $0.60 output per 1M tokens
    assert cost_usd("gpt-4o-mini-2024-07-18", 1_000_000, 1_000_000) == 0.75


def test_send_email_is_not_read_only():
    assert "send_email" not in READ_ONLY_TOOLS
    assert "fetch_news" in READ_ONLY_TOOLS


def test_search_pages_is_read_only():
    assert "search_pages" in READ_ONLY_TOOLS
