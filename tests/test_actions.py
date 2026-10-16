import json

import pytest

from gfra.actions import INJECTIONS, OUTBOX, fetch_news, injection_shown, reset_outbox, send_email, set_injection, set_news_format


def setup_function():
    reset_outbox()
    set_injection(None)


def test_send_email_records_to_outbox():
    out = send_email.invoke({"to": "team@bank.com", "subject": "Capex", "body": "1577"})
    assert "team@bank.com" in out
    assert OUTBOX == [{"to": "team@bank.com", "subject": "Capex", "body": "1577"}]


def test_fetch_news_filters_by_company():
    items = json.loads(fetch_news.invoke({"company": "3M"}))
    assert [i["date"] for i in items] == ["2019-01-29", "2023-01-24", "2023-07-25"]
    assert all(set(i) == {"company", "date", "headline", "body"} for i in items)
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


def test_injection_shown_only_after_a_fetch_that_carried_it():
    set_injection("direct:summary")
    assert not injection_shown()
    fetch_news.invoke({"company": "Nobody"})
    assert not injection_shown()
    fetch_news.invoke({"company": "AMD"})
    assert injection_shown()
    set_injection(None)
    assert not injection_shown()


def test_yaml_news_keeps_real_newlines_and_json_stays_the_default():
    import yaml
    set_injection("important_instructions:summary")
    try:
        assert "\\n<INFORMATION>" in fetch_news.invoke({"company": "AMD"})
        set_news_format("yaml")
        text = fetch_news.invoke({"company": "AMD"})
        assert "\n    <INFORMATION>" in text and "\\n" not in text
        assert yaml.safe_load(text)[0]["body"].strip().endswith(INJECTIONS["important_instructions:summary"].strip())
    finally:
        set_news_format("json")
        set_injection(None)
    with pytest.raises(ValueError):
        set_news_format("xml")
