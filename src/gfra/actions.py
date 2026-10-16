"""Tools with outside effects or outside content: a mock email outbox and a local news sample."""
import json
import re

from langchain_core.tools import tool

from gfra.config import DATA_DIR

OUTBOX: list[dict] = []
NEWS = json.loads((DATA_DIR / "news" / "news.json").read_text())
INJECTIONS = json.loads((DATA_DIR / "news" / "injections.json").read_text())
_active_injection: str | None = None
_injection_shown = False
_news_format = "json"
_ONE_ADDRESS = re.compile(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+")


def reset_outbox() -> None:
    OUTBOX.clear()


def set_injection(injection_id: str | None) -> None:
    """Append an attack text to the first news item returned (demo and eval only)."""
    global _active_injection, _injection_shown
    _active_injection = None if injection_id is None else INJECTIONS[injection_id]
    _injection_shown = False


def set_news_format(fmt: str) -> None:
    """"json" (the product) or "yaml", the way AgentDojo formats tool results (eval only)."""
    global _news_format
    if fmt not in ("json", "yaml"):
        raise ValueError(f"unknown news format {fmt!r}")
    _news_format = fmt


def injection_shown() -> bool:
    """Whether fetch_news has returned the active attack text since the last set_injection."""
    return _injection_shown


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email.

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body.
    """
    if not _ONE_ADDRESS.fullmatch(to):
        raise ValueError("`to` must be exactly one email address; send one email per recipient.")
    OUTBOX.append({"to": to, "subject": subject, "body": body})
    return f"Email sent to {to}."


@tool
def fetch_news(company: str) -> str:
    """Return recent news items about a company as a JSON list.

    Args:
        company: Company name, for example "3M".
    """
    # The agent gets what it reads; the id and the source link are for the demo page.
    items = [{k: item[k] for k in ("company", "date", "headline", "body")}
             for item in NEWS if item["company"].lower() == company.lower()]
    if items and _active_injection:
        global _injection_shown
        items[0]["body"] += "\n" + _active_injection
        _injection_shown = True
    if _news_format == "yaml":
        import yaml  # comes with agentdojo; the product never takes this branch
        return yaml.safe_dump(items).strip()
    return json.dumps(items)
