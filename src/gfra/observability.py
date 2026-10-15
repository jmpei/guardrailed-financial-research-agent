"""Langfuse tracing (OpenTelemetry-based); off when no Langfuse keys are set."""
import os


def callbacks() -> list:
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return []
    from langfuse.langchain import CallbackHandler
    return [CallbackHandler()]
