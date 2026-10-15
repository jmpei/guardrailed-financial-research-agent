import pytest


@pytest.fixture(autouse=True)
def _no_real_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-no-network")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
