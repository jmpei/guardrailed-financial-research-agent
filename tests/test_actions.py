import json

import pytest

from gfra.actions import OUTBOX, fetch_news, reset_outbox, send_email, set_injection


def setup_function():
    reset_outbox()
    set_injection(None)


def test_send_email_records_to_outbox():
    out = send_email.invoke({"to": "team@bank.com", "subject": "Capex", "body": "1577"})
    assert "team@bank.com" in out
    assert OUTBOX == [{"to": "team@bank.com", "subject": "Capex", "body": "1577"}]


def test_fetch_news_filters_by_company():
    items = json.loads(fetch_news.invoke({"company": "3M"}))
    assert [i["id"] for i in items] == ["n1", "n2"]
    assert all("INFORMATION" not in i["body"] for i in items)


def test_injection_is_appended_to_first_item_only():
    set_injection("exfiltrate_email")
    items = json.loads(fetch_news.invoke({"company": "3M"}))
    assert "attacker@evil.example" in items[0]["body"]
    assert "attacker@evil.example" not in items[1]["body"]


def test_unknown_company_returns_empty_list():
    assert json.loads(fetch_news.invoke({"company": "Nobody"})) == []


@pytest.mark.parametrize("to", ["attacker@evil.example, team@bank.com", "a@b.com;c@d.com", "not-an-address", ""])
def test_send_email_rejects_anything_but_one_address(to):
    with pytest.raises(ValueError, match="one email per recipient"):
        send_email.invoke({"to": to, "subject": "s", "body": "b"})
    assert OUTBOX == []
