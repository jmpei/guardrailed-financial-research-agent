from gfra.observability import callbacks


def test_no_langfuse_keys_means_no_callbacks(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert callbacks() == []


def test_langfuse_keys_add_one_handler(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    handlers = callbacks()
    assert len(handlers) == 1
    assert "CallbackHandler" in type(handlers[0]).__name__
