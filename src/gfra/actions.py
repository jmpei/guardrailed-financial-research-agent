"""Tools with outside effects or outside content: a mock email outbox and a local news sample."""
import json
import re

from langchain_core.tools import tool

from gfra.config import DATA_DIR

OUTBOX: list[dict] = []
_NEWS = json.loads((DATA_DIR / "news" / "news.json").read_text())
_INJECTIONS = json.loads((DATA_DIR / "news" / "injections.json").read_text())
_active_injection: str | None = None
_ONE_ADDRESS = re.compile(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+")


def reset_outbox() -> None:
    OUTBOX.clear()


def set_injection(injection_id: str | None) -> None:
    """Append an attack text to the first news item returned (demo and eval only)."""
    global _active_injection
    _active_injection = None if injection_id is None else _INJECTIONS[injection_id]


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
    items = [dict(item) for item in _NEWS if item["company"].lower() == company.lower()]
    if items and _active_injection:
        items[0]["body"] += _active_injection
    return json.dumps(items)
